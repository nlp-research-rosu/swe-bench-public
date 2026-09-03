from pathlib import Path

from fvkbench import arms, scaffold
from fvkbench.runner import AgentResult


def _result(ok: bool, session_id: str, error: str | None = None) -> AgentResult:
    return AgentResult(
        ok=ok,
        session_id=session_id,
        num_turns=1,
        subtype=None,
        duration_seconds=0.1,
        raw_json=None,
        error=error,
    )


class FakeRunner:
    name = "codex"

    def __init__(self, baseline_ok: bool = True):
        self.baseline_ok = baseline_ok
        self.calls: list[str] = []

    def new_session_id(self):
        return None

    def run_fresh(self, ws, arm, prompt, **kwargs):
        self.calls.append(arm)
        if not self.baseline_ok:
            return _result(False, "baseline-id", "agent_error:test")
        repo = Path(ws) / "repo"
        (repo / "lib.py").write_text(
            "def add(a, b):\n    return a + b\n\nBASELINE = True\n",
            encoding="utf-8",
        )
        reports = Path(ws) / "reports"
        (reports / "baseline_notes.md").write_text("baseline\n", encoding="utf-8")
        return _result(True, "baseline-id")

    def run_fork(self, ws, arm, prompt, baseline_session_id, **kwargs):
        self.calls.append(arm)
        assert baseline_session_id == "baseline-id"
        repo = Path(ws) / "repo"
        with (repo / "lib.py").open("a", encoding="utf-8") as handle:
            handle.write("FVK = True\n")
        (Path(ws) / "fvk" / "FINDINGS.md").write_text("finding\n", encoding="utf-8")
        (Path(ws) / "reports" / "fvk_notes.md").write_text("fvk\n", encoding="utf-8")
        return _result(True, "fvk-id")

    def transcript_path(self, ws, session_id):
        return None

    def audit_transcript(self, path):
        raise AssertionError("no transcript was returned")

    def version(self):
        return "test"


def _run(monkeypatch, fixture_remote_repo, fixture_instance, tmp_path, runner):
    remote, _ = fixture_remote_repo
    monkeypatch.setattr(scaffold, "_clone_url", lambda repo: f"file://{remote}")
    return arms.run_instance(
        "run",
        fixture_instance,
        tmp_path / "workspaces",
        runner=runner,
        cache_dir=tmp_path / "cache",
    )


def test_two_arm_happy_path(monkeypatch, fixture_remote_repo, fixture_instance, tmp_path):
    runner = FakeRunner()
    state = _run(monkeypatch, fixture_remote_repo, fixture_instance, tmp_path, runner)
    assert runner.calls == ["baseline", "fvk"]
    assert {name: value["status"] for name, value in state["arms"].items()} == {
        "baseline": "completed",
        "fvk": "completed",
    }
    ws = tmp_path / "workspaces" / "run" / fixture_instance.instance_id
    assert (ws / ".fvk_bench" / "solutions" / "solution_baseline.patch").stat().st_size
    assert (ws / ".fvk_bench" / "solutions" / "solution_fvk.patch").stat().st_size
    assert (ws / ".fvk_bench" / "artifacts" / "fvk" / "fvk" / "FINDINGS.md").is_file()
    assert not (ws / "fvk").exists()


def test_failed_baseline_skips_fvk(
    monkeypatch, fixture_remote_repo, fixture_instance, tmp_path
):
    runner = FakeRunner(baseline_ok=False)
    state = _run(monkeypatch, fixture_remote_repo, fixture_instance, tmp_path, runner)
    assert runner.calls == ["baseline"]
    assert state["arms"]["baseline"]["status"] == "failed"
    assert state["arms"]["fvk"] == {
        **state["arms"]["fvk"],
        "status": "skipped",
        "reason": "baseline_failed",
    }


def test_core_hash_ignores_private_artifacts(tmp_path):
    ws = tmp_path / "ws"
    (ws / "repo").mkdir(parents=True)
    (ws / "repo" / "source.py").write_text("x = 1\n", encoding="utf-8")
    before = arms.core_tree_hash(ws)
    (ws / ".fvk_bench").mkdir()
    (ws / ".fvk_bench" / "state.json").write_text("{}\n", encoding="utf-8")
    (ws / "fvk").mkdir()
    (ws / "fvk" / "FINDINGS.md").write_text("proof\n", encoding="utf-8")
    assert arms.core_tree_hash(ws) == before
    (ws / "repo" / "source.py").write_text("x = 2\n", encoding="utf-8")
    assert arms.core_tree_hash(ws) != before
