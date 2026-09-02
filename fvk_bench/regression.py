"""Full developer-test regression checks for verified500 baseline/fvk patches."""

from __future__ import annotations

import csv
import io
import json
import platform
import re
import shlex
import tarfile
import textwrap
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

from swebench.harness.constants import (
    DOCKER_WORKDIR,
    MAP_REPO_VERSION_TO_SPECS,
    TestStatus,
)
from swebench.harness.log_parsers import MAP_REPO_TO_PARSER
from swebench.harness.test_spec.python import ASTROPY_LEGACY_WARNING_SHIM
from swebench.harness.test_spec.test_spec import make_test_spec
from swebench.harness.utils import load_swebench_dataset

from fvk_bench import config

ROOT = config.REPO_ROOT / "verified500_regression"
MATRIX_PATH = ROOT / "candidate_matrix.json"
RESULTS_DIR = ROOT / "results"
DATASET = "princeton-nlp/SWE-bench_Verified"


@dataclass(frozen=True)
class Candidate:
    instance_id: str
    source_run_id: str
    category: str
    arms_to_run: tuple[str, ...]
    baseline_patch: str
    fvk_patch: str
    regression_batch: str | None


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_matrix(path: Path = MATRIX_PATH) -> dict[str, Any]:
    return _read_json(path)


def candidates_for(
    *,
    batch: str | None = None,
    instances: list[str] | None = None,
    matrix_path: Path = MATRIX_PATH,
) -> list[Candidate]:
    matrix = load_matrix(matrix_path)
    wanted = set(instances or [])
    out: list[Candidate] = []
    for raw in matrix.get("candidates") or []:
        if batch and raw.get("regression_batch") != batch:
            continue
        if wanted and raw["instance_id"] not in wanted:
            continue
        out.append(
            Candidate(
                instance_id=raw["instance_id"],
                source_run_id=raw["source_run_id"],
                category=raw["category"],
                arms_to_run=tuple(raw["arms_to_run"]),
                baseline_patch=raw["baseline_patch"],
                fvk_patch=raw["fvk_patch"],
                regression_batch=raw.get("regression_batch"),
            )
        )
    return out


def _run_dir(run_id: str, results_dir: Path = RESULTS_DIR) -> Path:
    return results_dir / run_id


def write_plan(run_id: str, *, results_dir: Path = RESULTS_DIR) -> Path:
    run_dir = _run_dir(run_id, results_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    dst = run_dir / "candidate_matrix.json"
    dst.write_text(json.dumps(load_matrix(), indent=2) + "\n", encoding="utf-8")
    return dst


def _load_dataset_rows(instance_ids: list[str]) -> dict[str, dict[str, Any]]:
    rows = load_swebench_dataset(DATASET, "test", instance_ids)
    return {row["instance_id"]: row for row in rows}


def _put_text(container: Any, directory: str, filename: str, text: str) -> None:
    payload = text.encode("utf-8")
    data = io.BytesIO()
    with tarfile.open(fileobj=data, mode="w") as archive:
        info = tarfile.TarInfo(filename)
        info.size = len(payload)
        archive.addfile(info, io.BytesIO(payload))
    data.seek(0)
    container.put_archive(directory, data.getvalue())


def _get_text(container: Any, path: str) -> str | None:
    try:
        chunks, _stat = container.get_archive(path)
    except Exception:
        return None
    data = b"".join(chunks)
    with tarfile.open(fileobj=io.BytesIO(data), mode="r") as archive:
        member = archive.next()
        if member is None:
            return None
        extracted = archive.extractfile(member)
        if extracted is None:
            return None
        return extracted.read().decode("utf-8", errors="replace")


def _apply_patch_script(path: str) -> str:
    quoted = shlex.quote(path)
    return textwrap.dedent(
        f"""
        applied=0
        for cmd in "git apply --verbose" "git apply --verbose --reject" "patch --batch --fuzz=5 -p1 -i"; do
          if $cmd {quoted}; then
            applied=1
            break
          fi
        done
        if [ "$applied" -ne 1 ]; then
          exit 101
        fi
        """
    ).strip()


def _discovery_python(
    repo: str,
    test_cmd: str,
    directive_timeout: int,
    max_directives: int | None,
) -> str:
    return textwrap.dedent(
        f"""
        import json
        import os
        import subprocess
        import time
        from pathlib import Path

        repo = {repo!r}
        test_cmd = {test_cmd!r}
        directive_timeout = {directive_timeout!r}
        max_directives = {max_directives!r}
        root = Path.cwd()

        excluded = {{'.git', '.tox', '.nox', '.eggs', '__pycache__', 'build', 'dist'}}

        def blocked(path):
            return any(part in excluded for part in path.parts)

        def discover_pytest():
            paths = []
            for path in root.rglob('*.py'):
                rel = path.relative_to(root)
                if blocked(rel):
                    continue
                name = path.name
                if name.startswith('test') or name.endswith('_test.py'):
                    paths.append(rel.as_posix())
            return sorted(paths)

        def discover_django():
            tests = root / 'tests'
            paths = []
            for path in tests.rglob('*.py'):
                rel = path.relative_to(root)
                if blocked(rel) or path.name == '__init__.py':
                    continue
                if path.name.startswith('test') or path.name == 'tests.py':
                    item = rel.with_suffix('').as_posix()
                    if item.startswith('tests/'):
                        item = item[len('tests/'):]
                    paths.append(item.replace('/', '.'))
            return sorted(paths)

        directives = discover_django() if repo == 'django/django' else discover_pytest()
        if max_directives is not None:
            directives = directives[:max_directives]
        results = []
        print('### REGRESSION_DISCOVERY_START')
        print(json.dumps(directives, indent=2))
        print('### REGRESSION_DISCOVERY_END')
        for directive in directives:
            command = "{{}} {{}}".format(test_cmd, directive)
            print("### REGRESSION_DIRECTIVE_START {{}}".format(directive))
            start = time.time()
            try:
                proc = subprocess.run(
                    command,
                    shell=True,
                    universal_newlines=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    timeout=directive_timeout,
                )
                output = proc.stdout
                exit_code = proc.returncode
                timed_out = False
            except subprocess.TimeoutExpired as exc:
                output = exc.stdout or ''
                if isinstance(output, bytes):
                    output = output.decode('utf-8', errors='replace')
                exit_code = 124
                timed_out = True
            print(output, end='' if output.endswith('\\n') else '\\n')
            duration = time.time() - start
            results.append({{
                'directive': directive,
                'exit_code': exit_code,
                'timed_out': timed_out,
                'duration_seconds': round(duration, 3),
            }})
            print("### REGRESSION_DIRECTIVE_END {{}}".format(directive))
        Path('/tmp/regression/results.json').write_text(
            json.dumps({{'directives': directives, 'results': results}}, indent=2) + '\\n',
            encoding='utf-8',
        )
        """
    ).strip()


def _context_script(
    row: dict[str, Any],
    test_cmd: str,
    directive_timeout: int,
    max_directives: int | None,
    skip_install: bool,
) -> str:
    specs = MAP_REPO_VERSION_TO_SPECS[row["repo"]][row["version"]]
    lines = [
        "set -uxo pipefail",
        "source /opt/miniconda3/bin/activate",
        "conda activate testbed",
        f"cd {shlex.quote(DOCKER_WORKDIR)}",
        _apply_patch_script("/tmp/regression/model.patch"),
    ]
    if not skip_install:
        for command in specs.get("eval_commands") or []:
            lines.append(command)
    if specs.get("install") and not skip_install:
        lines.append(specs["install"])
    if row["repo"] == "astropy/astropy":
        lines.append(ASTROPY_LEGACY_WARNING_SHIM)
    lines += [
        "git apply -v /tmp/regression/test.patch || exit 102",
        "cat > /tmp/regression/run_directives.py <<'PY'",
        _discovery_python(row["repo"], test_cmd, directive_timeout, max_directives),
        "PY",
        ": START_REGRESSION_TEST_OUTPUT",
        "python /tmp/regression/run_directives.py",
        "runner_rc=$?",
        ": END_REGRESSION_TEST_OUTPUT",
        "exit $runner_rc",
    ]
    return "\n".join(lines) + "\n"


def _test_command(row: dict[str, Any]) -> str:
    raw = MAP_REPO_VERSION_TO_SPECS[row["repo"]][row["version"]]["test_cmd"]
    if isinstance(raw, list):
        return raw[-1]
    return raw


def _parse_status_map(row: dict[str, Any], log_text: str) -> dict[str, str]:
    test_spec = make_test_spec(row, namespace="swebench")
    parser = MAP_REPO_TO_PARSER[row["repo"]]
    if "START_REGRESSION_TEST_OUTPUT" in log_text and "END_REGRESSION_TEST_OUTPUT" in log_text:
        log_text = log_text.split("START_REGRESSION_TEST_OUTPUT", 1)[1].split(
            "END_REGRESSION_TEST_OUTPUT", 1
        )[0]
    return parser(log_text, test_spec)


def _context_paths(run_dir: Path, iid: str, context: str) -> tuple[Path, Path]:
    log_path = run_dir / "logs" / iid / f"{context}.log"
    report_path = (
        run_dir / "oracle" / f"{iid}.json"
        if context == "oracle"
        else run_dir / "contexts" / iid / f"{context}.json"
    )
    return report_path, log_path


def _write_context_report(
    *,
    row: dict[str, Any],
    context: str,
    image: str,
    report_path: Path,
    log_path: Path,
    output: str,
    metadata_text: str | None,
    runtime: float,
    exit_code: int,
    timed_out: bool,
    max_directives: int | None,
    skip_install: bool,
    started_utc: str,
    status_override: str | None = None,
    error_type: str | None = None,
    error_message: str | None = None,
) -> dict[str, Any]:
    log_path.write_text(output, encoding="utf-8")
    status_map = _parse_status_map(row, output) if metadata_text else {}
    metadata = json.loads(metadata_text) if metadata_text else {"directives": [], "results": []}
    context_report = {
        "instance_id": row["instance_id"],
        "context": context,
        "repo": row["repo"],
        "version": row["version"],
        "image": image,
        "host_platform": platform.platform(),
        "started_utc": started_utc,
        "duration_seconds": round(runtime, 3),
        "exit_code": exit_code,
        "timed_out": timed_out,
        "status": status_override or ("ran" if metadata_text else "infra_error"),
        "test_command": _test_command(row),
        "max_directives": max_directives,
        "skip_install": skip_install,
        "directive_count": len(metadata.get("directives") or []),
        "directives": metadata.get("directives") or [],
        "directive_results": metadata.get("results") or [],
        "status_map": status_map,
        "log_path": str(log_path),
    }
    if error_type:
        context_report["error_type"] = error_type
    if error_message:
        context_report["error_message"] = error_message
    if exit_code == 101:
        context_report["status"] = "patch_apply_error"
    elif exit_code == 102:
        context_report["status"] = "test_patch_apply_error"
    elif timed_out:
        context_report["status"] = "timeout"
    report_path.write_text(json.dumps(context_report, indent=2) + "\n", encoding="utf-8")
    return context_report


def _exec_with_timeout(container: Any, cmd: str, timeout: int | None) -> tuple[str, int, bool, float]:
    output = b""
    exec_id = container.client.api.exec_create(container.id, cmd)["Id"]
    exception = None

    def run() -> None:
        nonlocal output, exception
        try:
            stream = container.client.api.exec_start(exec_id, stream=True)
            for chunk in stream:
                output += chunk
        except Exception as exc:
            exception = exc

    thread = threading.Thread(target=run)
    start = time.time()
    thread.start()
    thread.join(timeout)
    timed_out = thread.is_alive()
    if timed_out:
        try:
            pid = container.client.api.exec_inspect(exec_id).get("Pid")
            if pid:
                container.exec_run(f"kill -TERM {pid}", detach=True)
        except Exception:
            pass
        exit_code = 124
    else:
        if exception is not None:
            raise exception
        exit_code = container.client.api.exec_inspect(exec_id).get("ExitCode")
        if exit_code is None:
            exit_code = 1
    elapsed = time.time() - start
    return output.decode("utf-8", errors="replace"), int(exit_code), timed_out, elapsed


def run_context(
    *,
    run_id: str,
    row: dict[str, Any],
    context: str,
    patch_text: str,
    results_dir: Path = RESULTS_DIR,
    timeout: int = 7200,
    directive_timeout: int = 1800,
    max_directives: int | None = None,
    skip_install: bool = False,
    force: bool = False,
) -> dict[str, Any]:
    import docker

    run_dir = _run_dir(run_id, results_dir)
    report_path, log_path = _context_paths(run_dir, row["instance_id"], context)
    if report_path.is_file() and not force:
        return _read_json(report_path)

    report_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    test_spec = make_test_spec(row, namespace="swebench")
    client = docker.from_env()
    image = test_spec.instance_image_key
    started_utc = datetime.now(timezone.utc).isoformat()
    started = time.time()
    output = ""
    metadata_text = None
    exit_code = 1
    timed_out = False
    runtime = 0.0
    status_override = None
    error_type = None
    error_message = None

    try:
        try:
            client.images.get(image)
        except docker.errors.ImageNotFound:
            client.images.pull(image)
        container = client.containers.create(
            image,
            command="sleep infinity",
            detach=True,
            platform="linux/amd64",
        )
    except Exception as exc:
        runtime = time.time() - started
        error_type = type(exc).__name__
        error_message = str(exc)
        output = f"container_create_error: {error_type}: {error_message}\n"
        return _write_context_report(
            row=row,
            context=context,
            image=image,
            report_path=report_path,
            log_path=log_path,
            output=output,
            metadata_text=None,
            runtime=runtime,
            exit_code=125,
            timed_out=False,
            max_directives=max_directives,
            skip_install=skip_install,
            started_utc=started_utc,
            status_override="infra_error",
            error_type=error_type,
            error_message=error_message,
        )

    try:
        try:
            container.start()
            container.exec_run("mkdir -p /tmp/regression")
            _put_text(container, "/tmp/regression", "model.patch", patch_text or "")
            _put_text(container, "/tmp/regression", "test.patch", row["test_patch"] or "")
            script = _context_script(
                row,
                _test_command(row),
                directive_timeout,
                max_directives,
                skip_install,
            )
            _put_text(container, "/tmp/regression", "run.sh", script)
            output, exit_code, timed_out, runtime = _exec_with_timeout(
                container,
                "/bin/bash /tmp/regression/run.sh",
                timeout,
            )
            metadata_text = _get_text(container, "/tmp/regression/results.json")
        except Exception as exc:
            runtime = time.time() - started
            status_override = "infra_error"
            error_type = type(exc).__name__
            error_message = str(exc)
            output += f"\ncontainer_exec_error: {error_type}: {error_message}\n"
    finally:
        try:
            container.remove(force=True)
        except Exception:
            pass

    return _write_context_report(
        row=row,
        context=context,
        image=image,
        report_path=report_path,
        log_path=log_path,
        output=output,
        metadata_text=metadata_text,
        runtime=runtime,
        exit_code=exit_code,
        timed_out=timed_out,
        max_directives=max_directives,
        skip_install=skip_install,
        started_utc=started_utc,
        status_override=status_override,
        error_type=error_type,
        error_message=error_message,
    )


def cleanup_instance_image(
    *,
    run_id: str,
    row: dict[str, Any],
    results_dir: Path = RESULTS_DIR,
) -> dict[str, Any]:
    import docker

    run_dir = _run_dir(run_id, results_dir)
    log_path = run_dir / "logs" / row["instance_id"] / "image_cleanup.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    image = make_test_spec(row, namespace="swebench").instance_image_key
    started_utc = datetime.now(timezone.utc).isoformat()
    report: dict[str, Any] = {
        "instance_id": row["instance_id"],
        "image": image,
        "started_utc": started_utc,
        "status": "removed",
    }
    try:
        docker.from_env().images.remove(image=image, force=True, noprune=False)
        message = f"{started_utc} removed {image}\n"
    except docker.errors.ImageNotFound:
        report["status"] = "not_found"
        message = f"{started_utc} not found {image}\n"
    except Exception as exc:
        report["status"] = "error"
        report["error_type"] = type(exc).__name__
        report["error_message"] = str(exc)
        message = f"{started_utc} error removing {image}: {type(exc).__name__}: {exc}\n"
    log_path.write_text(message, encoding="utf-8")
    return report


def _passed(status: str | None) -> bool:
    return status in {TestStatus.PASSED.value, TestStatus.XFAIL.value}


def compare_contexts(
    *,
    candidate: Candidate,
    arm: str,
    oracle: dict[str, Any],
    generated: dict[str, Any],
    run_dir: Path,
) -> dict[str, Any]:
    oracle_status = oracle.get("status")
    generated_status = generated.get("status")
    if oracle_status != "ran":
        status = "oracle_" + str(oracle_status or "infra_error")
        triggers: list[dict[str, str | None]] = []
    elif generated_status != "ran":
        status = str(generated_status or "infra_error")
        triggers = []
    else:
        oracle_map = oracle.get("status_map") or {}
        generated_map = generated.get("status_map") or {}
        triggers = [
            {
                "test_id": test_id,
                "oracle_status": o_status,
                "generated_status": generated_map.get(test_id),
            }
            for test_id, o_status in sorted(oracle_map.items())
            if _passed(o_status) and not _passed(generated_map.get(test_id))
        ]
        status = "regression_fail" if triggers else "clean"

    report = {
        "instance_id": candidate.instance_id,
        "arm": arm,
        "source_run_id": candidate.source_run_id,
        "category": candidate.category,
        "regression_batch": candidate.regression_batch,
        "status": status,
        "trigger_count": len(triggers),
        "triggers": triggers,
        "oracle_report": str(run_dir / "oracle" / f"{candidate.instance_id}.json"),
        "generated_context_report": str(
            run_dir / "contexts" / candidate.instance_id / f"{arm}.json"
        ),
    }
    out = run_dir / "arms" / candidate.instance_id / f"{arm}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def _patch_for(candidate: Candidate, arm: str) -> str:
    path = config.REPO_ROOT / (candidate.baseline_patch if arm == "baseline" else candidate.fvk_patch)
    return path.read_text(encoding="utf-8", errors="replace")


def run_candidate(
    *,
    run_id: str,
    candidate: Candidate,
    row: dict[str, Any],
    arms: tuple[str, ...] | None = None,
    results_dir: Path = RESULTS_DIR,
    timeout: int = 7200,
    directive_timeout: int = 1800,
    max_directives: int | None = None,
    skip_install: bool = False,
    force: bool = False,
    cleanup_instance_images: bool = False,
) -> list[dict[str, Any]]:
    try:
        run_dir = _run_dir(run_id, results_dir)
        oracle = run_context(
            run_id=run_id,
            row=row,
            context="oracle",
            patch_text=row["patch"],
            results_dir=results_dir,
            timeout=timeout,
            directive_timeout=directive_timeout,
            max_directives=max_directives,
            skip_install=skip_install,
            force=force,
        )
        requested = tuple(arms or candidate.arms_to_run)
        reports = []
        for arm in requested:
            if arm not in candidate.arms_to_run:
                continue
            arm_report = run_dir / "arms" / candidate.instance_id / f"{arm}.json"
            if arm_report.is_file() and not force:
                reports.append(_read_json(arm_report))
                continue
            generated = run_context(
                run_id=run_id,
                row=row,
                context=arm,
                patch_text=_patch_for(candidate, arm),
                results_dir=results_dir,
                timeout=timeout,
                directive_timeout=directive_timeout,
                max_directives=max_directives,
                skip_install=skip_install,
                force=force,
            )
            reports.append(
                compare_contexts(
                    candidate=candidate,
                    arm=arm,
                    oracle=oracle,
                    generated=generated,
                    run_dir=run_dir,
                )
            )
        return reports
    finally:
        if cleanup_instance_images:
            cleanup_instance_image(run_id=run_id, row=row, results_dir=results_dir)


def run_batch(
    *,
    run_id: str,
    batch: str,
    instances: list[str] | None = None,
    arms: tuple[str, ...] | None = None,
    max_workers: int = 1,
    results_dir: Path = RESULTS_DIR,
    timeout: int = 7200,
    directive_timeout: int = 1800,
    max_directives: int | None = None,
    skip_install: bool = False,
    force: bool = False,
    cleanup_instance_images: bool = False,
) -> dict[str, Any]:
    write_plan(run_id, results_dir=results_dir)
    selected = candidates_for(batch=batch, instances=instances)
    rows = _load_dataset_rows([c.instance_id for c in selected])
    run_dir = _run_dir(run_id, results_dir)
    manifest = {
        "run_id": run_id,
        "batch": batch,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "max_workers": max_workers,
        "timeout": timeout,
        "directive_timeout": directive_timeout,
        "max_directives": max_directives,
        "skip_install": skip_install,
        "cleanup_instance_images": cleanup_instance_images,
        "instances": [c.instance_id for c in selected],
        "arms": list(arms) if arms else None,
    }
    (run_dir / "run_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )

    def one(candidate: Candidate) -> tuple[str, list[dict[str, Any]]]:
        return candidate.instance_id, run_candidate(
            run_id=run_id,
            candidate=candidate,
            row=rows[candidate.instance_id],
            arms=arms,
            results_dir=results_dir,
            timeout=timeout,
            directive_timeout=directive_timeout,
            max_directives=max_directives,
            skip_install=skip_install,
            force=force,
            cleanup_instance_images=cleanup_instance_images,
        )

    with ThreadPoolExecutor(max_workers=max(1, max_workers)) as executor:
        finished = list(executor.map(one, selected))

    return {
        "run_id": run_id,
        "batch": batch,
        "instances": len(selected),
        "arm_reports": sum(len(reports) for _iid, reports in finished),
    }


def collect_arm_reports(run_id: str, *, results_dir: Path = RESULTS_DIR) -> list[dict[str, Any]]:
    run_dir = _run_dir(run_id, results_dir)
    reports = []
    for path in sorted((run_dir / "arms").glob("*/*.json")):
        reports.append(_read_json(path))
    return reports


def write_report(run_id: str, *, results_dir: Path = RESULTS_DIR) -> tuple[Path, Path, Path]:
    run_dir = _run_dir(run_id, results_dir)
    reports = collect_arm_reports(run_id, results_dir=results_dir)
    counts: dict[str, dict[str, int]] = {}
    for report in reports:
        arm = report["arm"]
        status = report["status"]
        counts.setdefault(arm, {})
        counts[arm][status] = counts[arm].get(status, 0) + 1

    payload = {"run_id": run_id, "counts": counts, "reports": reports}
    json_path = run_dir / "score_sheet.json"
    md_path = run_dir / "score_sheet.md"
    csv_path = run_dir / "score_sheet.csv"
    json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    lines = [f"# Full Regression Score Sheet - {run_id}", "", "## Counts", ""]
    for arm in sorted(counts):
        parts = ", ".join(f"{k}: {v}" for k, v in sorted(counts[arm].items()))
        lines.append(f"- {arm}: {parts}")
    lines += ["", "## Arms", "", "| instance | arm | batch | status | triggers | source run |", "|---|---|---|---|---:|---|"]
    for report in reports:
        lines.append(
            "| {instance_id} | {arm} | {regression_batch} | {status} | {trigger_count} | {source_run_id} |".format(
                **report
            )
        )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    with csv_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "instance_id",
                "arm",
                "regression_batch",
                "status",
                "trigger_count",
                "source_run_id",
            ],
        )
        writer.writeheader()
        for report in reports:
            writer.writerow({key: report.get(key) for key in writer.fieldnames})
    return json_path, md_path, csv_path
