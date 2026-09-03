"""Two-arm orchestration: baseline solution followed by an FVK review.

One workspace hosts both arms in order **baseline → fvk**. The FVK session
resumes the frozen baseline transcript. Between the arms this module:

- extracts cumulative solution patches (``git add -A`` + ``git diff --cached
  --binary HEAD`` so brand-new files are captured),
- resets ``repo/`` deterministically to *V1* (base commit + the baseline
  patch re-applied),
- scrubs stale FVK output before a retry, and
- guards the baseline workspace with :func:`core_tree_hash`, a
  content hash of everything a session can observe **except** the
  orchestrator-private and arm-private areas (``.fvk_bench/``, ``fvk/``,
  ``repo/.git/``).

State lives in ``<ws>/.fvk_bench/state.json`` and is re-saved (atomically)
after every transition, so a crashed or interrupted run resumes exactly where
it stopped: completed arms are skipped, failed arms are skipped unless
``retry_failed`` is set. There are never silent automatic retries — every
attempt is counted.
"""

import hashlib
import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from fvkbench import config, scaffold
from fvkbench.instances import Instance
from fvkbench.prompting import render_prompt
from fvkbench.runner import AgentResult, AgentRunner, get_runner

#: Top-level workspace entries excluded from :func:`core_tree_hash`.
_HASH_EXCLUDED_TOP: tuple[str, ...] = (".fvk_bench", "fvk")

#: Per-arm artifact paths (relative to the workspace) snapshotted after success.
_ARM_ARTIFACTS: dict[str, tuple[str, ...]] = {
    "baseline": ("reports/baseline_notes.md",),
    "fvk": ("fvk", "reports/fvk_notes.md"),
}

_STATE_FILE = ".fvk_bench/state.json"


def _git(
    *args: str, cwd: Path, text: bool = True
) -> subprocess.CompletedProcess:
    """Run one git command, raising RuntimeError with command + stderr on failure.

    Mirrors the scaffold module's helper (duplicated rather than importing a
    private). ``text=False`` is used where output must stay raw bytes (binary
    patch extraction).
    """
    cmd = ["git", *args]
    try:
        return subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, text=text)
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr
        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", errors="replace")
        raise RuntimeError(
            f"git command failed: {' '.join(cmd)}\n{(stderr or '').strip()}"
        ) from exc


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash_excluded(parts: tuple[str, ...]) -> bool:
    """True if a workspace-relative path (as parts) is outside the core tree."""
    if parts and parts[0] in _HASH_EXCLUDED_TOP:
        return True
    return len(parts) >= 2 and parts[0] == "repo" and parts[1] == ".git"


def core_tree_hash(ws: Path) -> str:
    """Content hash of the workspace tree a session can observe.

    sha256 over every file under ``ws`` excluding ``.fvk_bench/**``, ``fvk/**``
    and ``repo/.git/**``. Deterministic:
    files are visited in sorted relative-path (posix) order and the hash is
    updated with ``relpath + NUL + content + NUL``. Symlinks contribute their
    readlink target string instead of file content (and are never followed);
    empty directories are ignored.
    """
    ws = Path(ws)
    entries: list[tuple[str, Path]] = []
    for root, dirnames, filenames in os.walk(ws):
        rel_parts = Path(root).relative_to(ws).parts
        kept_dirs: list[str] = []
        for name in dirnames:
            parts = rel_parts + (name,)
            if _hash_excluded(parts):
                continue
            child = Path(root) / name
            if child.is_symlink():
                # Hash the link itself; os.walk(followlinks=False) won't descend.
                entries.append(("/".join(parts), child))
            else:
                kept_dirs.append(name)
        dirnames[:] = kept_dirs
        for name in filenames:
            parts = rel_parts + (name,)
            if not _hash_excluded(parts):
                entries.append(("/".join(parts), Path(root) / name))

    digest = hashlib.sha256()
    for rel, path in sorted(entries, key=lambda entry: entry[0]):
        digest.update(rel.encode("utf-8"))
        digest.update(b"\0")
        if path.is_symlink():
            digest.update(os.readlink(path).encode("utf-8"))
        else:
            digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def extract_patch(ws: Path, arm: str) -> Path:
    """Extract the cumulative diff-from-base for ``arm`` from ``ws/repo``.

    ``git add -A`` first so newly created files appear in the diff, then
    ``git diff --cached --binary HEAD`` (raw bytes — binary-safe) is written to
    ``.fvk_bench/solutions/solution_<arm>.patch``. The index is always restored
    with ``git reset -q`` (working tree untouched), even if writing the patch
    fails. An empty diff yields an empty file.
    """
    ws = Path(ws)
    repo = ws / "repo"
    out = ws / ".fvk_bench" / "solutions" / f"solution_{arm}.patch"
    out.parent.mkdir(parents=True, exist_ok=True)
    _git("add", "-A", cwd=repo)
    try:
        diff = _git("diff", "--cached", "--binary", "HEAD", cwd=repo, text=False)
        out.write_bytes(diff.stdout)
    finally:
        _git("reset", "-q", cwd=repo)
    return out


def reset_repo_to_v1(ws: Path) -> None:
    """Deterministically reset ``ws/repo`` to V1 = base commit + baseline patch.

    ``git checkout -q -f <base_commit>`` discards tracked edits, ``git clean
    -fdxq`` removes everything untracked (including previously applied new
    files), then the baseline solution patch — if it exists and is non-empty —
    is re-applied with ``git apply --whitespace=nowarn``.
    """
    ws = Path(ws)
    meta = json.loads((ws / "benchmark" / "instance.json").read_text(encoding="utf-8"))
    repo = ws / "repo"
    _git("checkout", "-q", "-f", meta["base_commit"], cwd=repo)
    _git("clean", "-fdxq", cwd=repo)
    v1 = ws / ".fvk_bench" / "solutions" / "solution_baseline.patch"
    if v1.exists() and v1.stat().st_size > 0:
        _git("apply", "--whitespace=nowarn", str(v1.resolve()), cwd=repo)


def stage_fvk(ws: Path) -> None:
    """Prepare the workspace for the fvk arm.

    Resets ``repo/`` to V1 and creates the empty ``fvk/`` output directory for
    the arm's artifacts. The FVK methodology is delivered by the installed Codex
    skill (see :func:`fvkbench.codex_runner.install_fvk_skill`), not by copying
    material files into the workspace.
    """
    ws = Path(ws)
    reset_repo_to_v1(ws)
    (ws / "fvk").mkdir(parents=True, exist_ok=True)


def scrub_fvk(ws: Path) -> None:
    """Remove every fvk trace from the workspace (missing entries tolerated).

    Deletes ``fvk/`` and ``reports/fvk_notes.md`` before an FVK retry. Snapshot
    successful artifacts before scrubbing.
    """
    ws = Path(ws)
    target = ws / "fvk"
    if target.exists():
        shutil.rmtree(target)
    (ws / "reports" / "fvk_notes.md").unlink(missing_ok=True)


def snapshot_artifacts(ws: Path, arm: str) -> None:
    """Copy ``arm``'s artifacts into ``.fvk_bench/artifacts/<arm>/``.

    Preserves the workspace-relative layout (e.g. ``fvk/SPEC.md`` lands at
    ``artifacts/fvk/fvk/SPEC.md``); paths that don't exist are skipped. This
    runs before :func:`scrub_fvk`, so fvk artifacts survive the scrub.
    """
    ws = Path(ws)
    dest_root = ws / ".fvk_bench" / "artifacts" / arm
    for rel in _ARM_ARTIFACTS[arm]:
        src = ws / rel
        if not src.exists():
            continue
        dst = dest_root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            shutil.copytree(src, dst, dirs_exist_ok=True)
        else:
            shutil.copy2(src, dst)


def load_state(ws: Path) -> dict:
    """Load ``.fvk_bench/state.json``; empty dict if no state exists yet."""
    path = Path(ws) / _STATE_FILE
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_state(ws: Path, state: dict) -> None:
    """Atomically persist ``state`` to ``.fvk_bench/state.json`` (tmp+rename)."""
    path = Path(ws) / _STATE_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _fresh_state(run_id: str, inst: Instance) -> dict:
    return {
        "run_id": run_id,
        "instance_id": inst.instance_id,
        "baseline_session_id": None,
        "core_hash_post_baseline": None,
        "arms": {
            arm: {
                "status": "pending",
                "reason": None,
                "session_id": None,
                "attempts": 0,
                "started_at": None,
                "ended_at": None,
                "num_turns": None,
                "duration_seconds": None,
                "audit": None,
            }
            for arm in config.ARMS
        },
    }


def _eligible(arm_state: dict, retry_failed: bool) -> bool:
    """Decide whether an arm should run now; resets failed arms on retry."""
    if arm_state["status"] == "completed":
        return False
    if arm_state["status"] == "failed":
        if not retry_failed:
            return False
        # Reset to pending and clear every per-arm field left over from the
        # failed attempt so the state never mixes stale and fresh session
        # data; ``attempts`` stays cumulative — it counts launched sessions.
        arm_state["status"] = "pending"
        for field in (
            "reason",
            "session_id",
            "started_at",
            "ended_at",
            "num_turns",
            "duration_seconds",
            "audit",
        ):
            arm_state[field] = None
    return True  # pending, skipped, or failed-being-retried


def _record_result(arm_state: dict, result: AgentResult) -> None:
    """Book-keep one session attempt (recorded whether it succeeded or not)."""
    arm_state["attempts"] += 1
    arm_state["ended_at"] = _utc_now()
    arm_state["num_turns"] = result.num_turns
    arm_state["duration_seconds"] = result.duration_seconds


def _apply_audit(
    ws: Path, runner: AgentRunner, arm_state: dict, session_id: str | None
) -> None:
    """Audit the session transcript; a dirty tool surface fails the arm.

    Artifacts already extracted/snapshotted are deliberately kept — the audit
    verdict changes the arm's *status*, not the forensic record.
    """
    if not session_id:
        return
    transcript = runner.transcript_path(ws, session_id)
    if transcript is None:
        arm_state["audit"] = {"ok": None, "note": "transcript_not_found"}
        return
    audit = runner.audit_transcript(transcript)
    arm_state["audit"] = audit
    if audit["ok"] is False:
        arm_state["status"] = "failed"
        arm_state["reason"] = "contaminated_session"


def run_instance(
    run_id: str,
    inst: Instance,
    ws_root: Path,
    *,
    arms: tuple = config.ARMS,
    agent: str = config.DEFAULT_AGENT,
    runner: AgentRunner | None = None,
    codex_bin: str = "codex",
    model: str | None = None,
    timeout: int = config.ARM_TIMEOUT_SECONDS,
    retry_failed: bool = False,
    cache_dir: Path | None = None,
) -> dict:
    """Run the requested arms for one instance and return the final state dict.

    The state machine (see module docstring) is crash-resumable: state is
    saved after every transition, completed arms are never re-run, and failed
    arms re-run only when ``retry_failed`` is set (the retry resets them to
    pending; attempts accumulate). When the baseline arm is not completed the
    FVK review cannot exist (nothing to fork), so a requested-and-pending FVK
    arm is marked ``skipped(baseline_failed)``.
    """
    unknown = [arm for arm in arms if arm not in config.ARMS]
    if unknown:
        raise ValueError(f"unknown arms {unknown}; expected a subset of {config.ARMS}")

    if runner is None:
        runner = get_runner(agent, codex_bin=codex_bin, model=model)

    cache = (
        Path(cache_dir)
        if cache_dir is not None
        else config.workspace_root() / "cache" / "repos"
    )
    mirror = scaffold.ensure_mirror(inst.repo, cache)
    ws = scaffold.create_workspace(run_id, inst, Path(ws_root), mirror)

    state = load_state(ws) or _fresh_state(run_id, inst)
    state["agent"] = runner.name  # recorded so harvest can pick the right runner
    save_state(ws, state)

    # --- baseline: fresh Codex session ---------------------------------------
    baseline = state["arms"]["baseline"]
    if "baseline" in arms and _eligible(baseline, retry_failed):
        pre_id = runner.new_session_id()
        state["baseline_session_id"] = pre_id
        baseline["session_id"] = pre_id
        baseline["started_at"] = _utc_now()
        save_state(ws, state)

        result = runner.run_fresh(
            ws, "baseline", render_prompt("baseline", inst),
            session_id=pre_id, timeout=timeout,
        )
        _record_result(baseline, result)
        if result.ok:
            sid = result.session_id or pre_id
            state["baseline_session_id"] = sid
            baseline["session_id"] = sid
            extract_patch(ws, "baseline")
            snapshot_artifacts(ws, "baseline")
            state["core_hash_post_baseline"] = core_tree_hash(ws)
            baseline["status"] = "completed"
            baseline["reason"] = None
        else:
            baseline["status"] = "failed"
            baseline["reason"] = result.error or "agent_error"
        _apply_audit(ws, runner, baseline, baseline["session_id"])
        save_state(ws, state)

    # Without a completed baseline there is no frozen session to fork and no
    # V1 to review: skip the FVK arm if it was requested and is still pending.
    if baseline["status"] != "completed":
        if "fvk" in arms and state["arms"]["fvk"]["status"] == "pending":
            state["arms"]["fvk"]["status"] = "skipped"
            state["arms"]["fvk"]["reason"] = "baseline_failed"
        save_state(ws, state)
        return state

    # --- fvk: forked resume with FVK materials staged, always scrubbed ------
    fvk = state["arms"]["fvk"]
    if "fvk" in arms and _eligible(fvk, retry_failed):
        # Staging must reproduce the post-baseline tree after a crashed or
        # failed earlier FVK attempt.
        scrub_fvk(ws)
        stage_fvk(ws)
        if core_tree_hash(ws) != state["core_hash_post_baseline"]:
            # The staging reset itself failed to reproduce the post-baseline
            # tree: the review cannot be trusted. Scrub and abort the instance.
            scrub_fvk(ws)
            fvk["status"] = "failed"
            fvk["reason"] = "staging_hash_mismatch"
            save_state(ws, state)
            return state

        fvk["started_at"] = _utc_now()
        save_state(ws, state)
        try:
            result = runner.run_fork(
                ws, "fvk", render_prompt("fvk", inst),
                state["baseline_session_id"], timeout=timeout,
            )
            _record_result(fvk, result)
            fvk["session_id"] = result.session_id
            if result.ok:
                extract_patch(ws, "fvk")
                snapshot_artifacts(ws, "fvk")  # before the scrub deletes fvk/
                fvk["status"] = "completed"
                fvk["reason"] = None
            else:
                fvk["status"] = "failed"
                fvk["reason"] = result.error or "agent_error"
        finally:
            scrub_fvk(ws)
        _apply_audit(ws, runner, fvk, result.session_id)
        save_state(ws, state)

    return state
