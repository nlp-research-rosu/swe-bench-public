import json
import sys
import types
from dataclasses import FrozenInstanceError

import pytest

from fvk_bench import instances


def _row(index: int) -> dict:
    return {
        "instance_id": f"repo__repo-{index:03d}",
        "repo": "repo/repo",
        "base_commit": "abc123",
        "version": "1.0",
        "problem_statement": "Fix it.",
        "hints_text": "",
        "fail_to_pass_count": 1,
        "pass_to_pass_count": 2,
    }


def test_load_verified500(tmp_path):
    path = tmp_path / "instances.json"
    path.write_text(json.dumps([_row(index) for index in range(500)]), encoding="utf-8")
    loaded = instances.load_instances(path)
    assert len(loaded) == 500
    assert loaded["repo__repo-499"].pass_to_pass_count == 2
    with pytest.raises(FrozenInstanceError):
        loaded["repo__repo-000"].repo = "changed"  # type: ignore[misc]


def test_load_rejects_wrong_count_and_unknown_set(tmp_path):
    path = tmp_path / "instances.json"
    path.write_text("[]", encoding="utf-8")
    with pytest.raises(RuntimeError, match="exactly 500"):
        instances.load_instances(path)
    with pytest.raises(RuntimeError, match="verified500"):
        instances.load_instances(path, instance_set="fvk45")


def test_vendor_keeps_only_public_metadata(monkeypatch, tmp_path):
    rows = []
    for index in range(500):
        row = _row(index)
        row.pop("fail_to_pass_count")
        row.pop("pass_to_pass_count")
        row.update(
            {
                "hints_text": None,
                "FAIL_TO_PASS": '["f"]',
                "PASS_TO_PASS": ["p1", "p2"],
                "patch": "hidden",
                "test_patch": "hidden",
            }
        )
        rows.append(row)
    module = types.ModuleType("datasets")
    module.load_dataset = lambda name, split: rows  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "datasets", module)
    target = tmp_path / "vendored.json"
    assert instances.vendor_instances(target) == 500
    text = target.read_text(encoding="utf-8")
    assert "hidden" not in text
    written = json.loads(text)
    assert written[0]["hints_text"] == ""
    assert written[0]["fail_to_pass_count"] == 1
    assert written[0]["pass_to_pass_count"] == 2
