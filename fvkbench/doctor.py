"""Preflight checks and a real Codex session-cleanliness canary."""

import importlib.util
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from fvkbench import codex_runner, config

_SUPPORTED_ARCHS = {"x86_64", "amd64"}
_MIN_FREE_BYTES = 120 * 10**9
_CANARY_PROMPT = "Reply with exactly: OK. Do not use any tools."


def _importable(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


def _codex_version_token(output: str) -> str:
    parts = output.strip().split()
    if len(parts) >= 2 and parts[0] == "codex-cli":
        return parts[1]
    return parts[0] if parts else "version unknown"


def _check_codex(codex_bin: str = "codex") -> tuple[str, bool | None, str]:
    path = shutil.which(codex_bin)
    if not path:
        return ("codex", False, "not found on PATH")
    try:
        proc = subprocess.run(
            [path, "--version"], capture_output=True, text=True, timeout=30
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return ("codex", False, f"{path} ({exc})")
    if proc.returncode != 0:
        return ("codex", False, f"{path} (--version exited {proc.returncode})")
    version = proc.stdout.strip() or "version unknown"
    leading = _codex_version_token(version)
    if leading != config.TESTED_CODEX_VERSION:
        return (
            "codex",
            None,
            f"untested version {leading} "
            f"(validated against {config.TESTED_CODEX_VERSION})",
        )
    return ("codex", True, f"{version} ({path})")


def _check_codex_auth(codex_bin: str = "codex") -> tuple[str, bool | None, str]:
    path = shutil.which(codex_bin)
    if not path:
        return ("codex_auth", False, "codex not found")
    try:
        proc = subprocess.run(
            [path, "login", "status"], capture_output=True, text=True, timeout=30
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return ("codex_auth", False, str(exc))
    detail = (proc.stdout or proc.stderr or "").strip() or "no login status output"
    if proc.returncode != 0:
        return ("codex_auth", False, f"{detail} (exit {proc.returncode})")
    if "Logged in using ChatGPT" not in detail:
        return (
            "codex_auth",
            False,
            f"{detail} (need ChatGPT/Codex subscription auth)",
        )
    return ("codex_auth", True, "Logged in using ChatGPT")


def _check_docker(eval_checks: bool) -> tuple[str, bool | None, str]:
    try:
        proc = subprocess.run(
            ["docker", "info"], capture_output=True, text=True, timeout=60
        )
        reachable = proc.returncode == 0
        lines = (proc.stderr or proc.stdout or "").strip().splitlines()
        detail = lines[0] if (not reachable and lines) else "daemon reachable"
    except (OSError, subprocess.TimeoutExpired) as exc:
        reachable, detail = False, str(exc)
    if reachable:
        return ("docker", True, detail)
    verdict: bool | None = False if eval_checks else None
    return ("docker", verdict, f"not reachable: {detail} (required for evaluate)")


def run_checks(
    *, eval_checks: bool = True, codex_bin: str = "codex"
) -> list[tuple[str, bool | None, str]]:
    checks = [_check_codex(codex_bin), _check_codex_auth(codex_bin)]
    git_path = shutil.which("git")
    checks.append(("git", bool(git_path), git_path or "not found on PATH"))
    machine = platform.machine()
    checks.append(
        ("arch", machine in _SUPPORTED_ARCHS, f"{machine} (eval images require x86_64)")
    )
    version = ".".join(str(value) for value in tuple(sys.version_info)[:3])
    checks.append(
        ("python", tuple(sys.version_info)[:2] >= (3, 10), f"{version} (need >= 3.10)")
    )
    checks.append(
        (
            "swebench",
            _importable("swebench"),
            "importable" if _importable("swebench") else "not importable (pip install -e .)",
        )
    )
    datasets_ok = _importable("datasets")
    checks.append(
        (
            "datasets",
            True if datasets_ok else None,
            "importable" if datasets_ok else "not importable (needed only for vendor-instances)",
        )
    )
    checks.append(_check_docker(eval_checks))
    try:
        free = shutil.disk_usage(Path.cwd()).free
        disk_ok: bool | None = True if free >= _MIN_FREE_BYTES else None
        detail = f"{free / 10**9:.0f} GB free (evaluate needs ~120 GB)"
    except OSError as exc:
        disk_ok, detail = None, f"disk_usage failed: {exc}"
    checks.append(("disk", disk_ok, detail))
    return checks


def run_codex_canary(
    *, model: str = config.CODEX_MODEL, codex_bin: str = "codex"
) -> dict:
    runner = codex_runner.CodexRunner(codex_bin=codex_bin, model=model)
    with tempfile.TemporaryDirectory(prefix="fvk_codex_canary_") as tmp:
        ws = Path(tmp)
        (ws / ".fvk_bench").mkdir()
        result = runner.run_fresh(ws, "baseline", _CANARY_PROMPT, timeout=300)
        audit = None
        if result.session_id:
            transcript = runner.transcript_path(ws, result.session_id)
            if transcript is not None:
                audit = runner.audit_transcript(transcript)
    clean = bool(
        result.ok
        and audit is not None
        and audit["ok"]
        and not audit["exec_warnings"]
        and not audit["tool_uses"]
    )
    return {
        "result_ok": result.ok,
        "error": result.error,
        "session_id": result.session_id,
        "audit": audit,
        "clean": clean,
    }
