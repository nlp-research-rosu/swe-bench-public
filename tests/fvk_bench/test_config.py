import os
from pathlib import Path

from fvk_bench import config


def test_experiment_is_pinned_to_verified500_codex_two_arm():
    assert config.ARMS == ("baseline", "fvk")
    assert config.MAX_TURNS == {"baseline": 200, "fvk": 200}
    assert config.INSTANCE_SETS == ("verified500",)
    assert config.DEFAULT_INSTANCE_SET == "verified500"
    assert config.AGENTS == ("codex",)
    assert config.DEFAULT_AGENT == "codex"
    assert config.dataset_identity() == "princeton-nlp/SWE-bench_Verified"


def test_workspace_root_env_override(monkeypatch, tmp_path):
    monkeypatch.setenv("FVK_BENCH_WORKSPACE", str(tmp_path / "ws"))
    assert config.workspace_root() == tmp_path / "ws"
    monkeypatch.delenv("FVK_BENCH_WORKSPACE")
    assert config.workspace_root() == Path.home() / ".swe-fvk-runs"


def test_session_env_allowlist():
    env = config.session_env()
    assert set(env) == {"HOME", "PATH", "USER", "TERM", "LANG", "TZ"}
    assert env["HOME"] == os.environ["HOME"]
    assert (env["TERM"], env["LANG"], env["TZ"]) == ("dumb", "C.UTF-8", "UTC")
