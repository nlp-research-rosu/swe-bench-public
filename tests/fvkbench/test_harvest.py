import gzip
import json
from types import SimpleNamespace

from fvkbench import config, harvest
from fvkbench.instances import Instance


INSTANCE = Instance(
    instance_id="demo__demo-1",
    repo="demo/demo",
    base_commit="a" * 40,
    version="1.0",
    problem_statement="Fix it.",
    hints_text="",
    fail_to_pass_count=1,
    pass_to_pass_count=1,
)


class TranscriptRunner:
    def __init__(self, paths):
        self.paths = paths

    def transcript_path(self, ws, session_id):
        return self.paths.get(session_id)


def test_harvest_two_arm_artifacts(tmp_path, monkeypatch):
    ws = tmp_path / "ws"
    private = ws / ".fvk_bench"
    for name in ("prompts", "solutions", "raw"):
        (private / name).mkdir(parents=True, exist_ok=True)
    state = {
        "run_id": "run",
        "instance_id": INSTANCE.instance_id,
        "agent": "codex",
        "arms": {
            arm: {"status": "completed", "session_id": f"{arm}-id"}
            for arm in config.ARMS
        },
    }
    (private / "state.json").write_text(json.dumps(state), encoding="utf-8")
    for arm in config.ARMS:
        (private / "prompts" / f"{arm}.md").write_text(arm, encoding="utf-8")
        (private / "solutions" / f"solution_{arm}.patch").write_text(
            f"diff {arm}\n", encoding="utf-8"
        )
    (private / "artifacts" / "fvk" / "fvk").mkdir(parents=True)
    (private / "artifacts" / "fvk" / "fvk" / "FINDINGS.md").write_text(
        "finding\n", encoding="utf-8"
    )
    transcripts = {}
    for arm in config.ARMS:
        path = tmp_path / f"{arm}.jsonl"
        path.write_text("{}\n", encoding="utf-8")
        transcripts[f"{arm}-id"] = path
    monkeypatch.setattr(harvest, "get_runner", lambda agent: TranscriptRunner(transcripts))

    dst = harvest.harvest_instance(ws, "run", INSTANCE, tmp_path / "results")
    assert {path.name for path in (dst / "prompts").iterdir()} == {
        "baseline.md",
        "fvk.md",
    }
    assert (dst / "fvk" / "FINDINGS.md").is_file()
    with gzip.open(dst / "transcripts" / "baseline.jsonl.gz", "rt") as handle:
        assert handle.read() == "{}\n"
    manifest = json.loads((dst / "manifest.json").read_text(encoding="utf-8"))
    assert set(manifest["template_hashes"]) == set(config.ARMS)
    assert set(manifest["raw_envelopes"]) == set(config.ARMS)


def test_run_manifest_is_codex_verified500(tmp_path, monkeypatch):
    def fake_run(command, **kwargs):
        if command[:2] == ["/opt/codex", "--version"]:
            return SimpleNamespace(returncode=0, stdout="codex-cli test\n")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(harvest.subprocess, "run", fake_run)
    path = harvest.write_run_manifest(
        "run",
        tmp_path,
        extra={"codex_bin": "/opt/codex", "arms": list(config.ARMS)},
    )
    manifest = json.loads(path.read_text(encoding="utf-8"))
    assert manifest["agent"] == "codex"
    assert manifest["codex_version"] == "codex-cli test"
    assert manifest["dataset"] == "princeton-nlp/SWE-bench_Verified"
    assert manifest["invocation"]["model"] == config.CODEX_MODEL
    assert manifest["arms"] == ["baseline", "fvk"]
