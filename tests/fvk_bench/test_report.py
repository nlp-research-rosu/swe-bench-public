import json

from fvk_bench import config, report


def _eval(instance_id, resolved):
    return {
        instance_id: {
            "resolved": resolved,
            "tests_status": {
                "FAIL_TO_PASS": {"success": ["f"] if resolved else [], "failure": [] if resolved else ["f"]},
                "PASS_TO_PASS": {"success": ["p"], "failure": []},
            },
        }
    }


def test_two_arm_scores_and_flip(tmp_path):
    run_id = "run"
    instance_id = "demo__demo-1"
    instance = tmp_path / run_id / instance_id
    (instance / "solutions").mkdir(parents=True)
    (instance / "eval").mkdir()
    (instance / "manifest.json").write_text(
        json.dumps(
            {
                "arms": {
                    arm: {"status": "completed", "session_id": f"{arm}-id"}
                    for arm in config.ARMS
                }
            }
        ),
        encoding="utf-8",
    )
    for arm in config.ARMS:
        (instance / "solutions" / f"solution_{arm}.patch").write_text(
            "diff\n", encoding="utf-8"
        )
    (instance / "eval" / "baseline.report.json").write_text(
        json.dumps(_eval(instance_id, False)), encoding="utf-8"
    )
    (instance / "eval" / "fvk.report.json").write_text(
        json.dumps(_eval(instance_id, True)), encoding="utf-8"
    )

    scores = report.collect_scores(run_id, results_dir=tmp_path)
    assert scores["aggregates"]["arms"] == {
        "baseline": {"resolved": 0, "evaluated": 1},
        "fvk": {"resolved": 1, "evaluated": 1},
    }
    assert scores["aggregates"]["flips"]["baseline_to_fvk"] == {
        "up": [instance_id],
        "down": [],
    }
    markdown = report.render_scores_md(scores, None)
    assert "baseline→fvk" in markdown
    assert "control" not in markdown


def test_completed_empty_patch_scores_unresolved(tmp_path):
    instance = tmp_path / "run" / "demo__demo-1"
    instance.mkdir(parents=True)
    (instance / "manifest.json").write_text(
        json.dumps({"arms": {"baseline": {"status": "completed"}}}),
        encoding="utf-8",
    )
    scores = report.collect_scores("run", results_dir=tmp_path, arms=("baseline",))
    assert scores["instances"]["demo__demo-1"]["baseline"]["eval"]["reason"] == "empty_patch"
