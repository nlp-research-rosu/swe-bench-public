"""Load and vendor public metadata for SWE-bench Verified's 500 instances."""

import json
from dataclasses import dataclass
from pathlib import Path

from fvkbench import config


@dataclass(frozen=True)
class Instance:
    instance_id: str
    repo: str
    base_commit: str
    version: str
    problem_statement: str
    hints_text: str
    fail_to_pass_count: int
    pass_to_pass_count: int


def _instance_set_path(instance_set: str) -> Path:
    try:
        return config.REGISTRY[instance_set].data_file
    except KeyError as exc:
        raise RuntimeError(
            f"unknown instance set {instance_set!r}; choose from verified500"
        ) from exc


def _expected_count(instance_set: str) -> int:
    try:
        return config.REGISTRY[instance_set].expected_count
    except KeyError as exc:
        raise RuntimeError(
            f"unknown instance set {instance_set!r}; choose from verified500"
        ) from exc


def _visible_row(row: dict) -> dict:
    fail_to_pass = row["FAIL_TO_PASS"]
    if isinstance(fail_to_pass, str):
        fail_to_pass = json.loads(fail_to_pass)
    pass_to_pass = row["PASS_TO_PASS"]
    if isinstance(pass_to_pass, str):
        pass_to_pass = json.loads(pass_to_pass)
    return {
        "instance_id": row["instance_id"],
        "repo": row["repo"],
        "base_commit": row["base_commit"],
        "version": row["version"],
        "problem_statement": row["problem_statement"],
        "hints_text": row["hints_text"] or "",
        "fail_to_pass_count": len(fail_to_pass),
        "pass_to_pass_count": len(pass_to_pass),
    }


def load_instances(
    path: Path | None = None, *, instance_set: str = config.DEFAULT_INSTANCE_SET
) -> dict[str, Instance]:
    if instance_set not in config.INSTANCE_SETS:
        raise RuntimeError(
            f"unknown instance set {instance_set!r}; choose from verified500"
        )
    source = Path(path) if path is not None else _instance_set_path(instance_set)
    try:
        raw = json.loads(source.read_text(encoding="utf-8"))
        loaded = {
            row["instance_id"]: Instance(
                instance_id=row["instance_id"],
                repo=row["repo"],
                base_commit=row["base_commit"],
                version=row["version"],
                problem_statement=row["problem_statement"],
                hints_text=row["hints_text"],
                fail_to_pass_count=int(row["fail_to_pass_count"]),
                pass_to_pass_count=int(row["pass_to_pass_count"]),
            )
            for row in raw
        }
    except (json.JSONDecodeError, KeyError, TypeError, OSError) as exc:
        raise RuntimeError(f"Failed to load instance metadata from {source}: {exc}") from exc
    expected = _expected_count(instance_set)
    if len(loaded) != expected:
        raise RuntimeError(
            f"Expected exactly {expected} instances in {source}, found {len(loaded)}."
        )
    return loaded


def vendor_instances(
    out_path: Path | None = None, *, instance_set: str = config.DEFAULT_INSTANCE_SET
) -> int:
    if instance_set not in config.INSTANCE_SETS:
        raise RuntimeError(
            f"unknown instance set {instance_set!r}; choose from verified500"
        )
    import datasets

    target = Path(out_path) if out_path is not None else _instance_set_path(instance_set)
    dataset = datasets.load_dataset(config.dataset_identity(instance_set), split="test")
    rows = sorted((_visible_row(row) for row in dataset), key=lambda row: row["instance_id"])
    expected = _expected_count(instance_set)
    if len({row["instance_id"] for row in rows}) != expected:
        raise RuntimeError(
            f"Expected exactly {expected} instances for {instance_set}, dataset produced {len(rows)}."
        )
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(rows, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return len(rows)
