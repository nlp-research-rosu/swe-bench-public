"""Pinned parameters for the Verified500 baseline/FVK Codex experiment."""

import os
from dataclasses import dataclass
from pathlib import Path

CODEX_MODEL: str = "gpt-5.5"
CODEX_EFFORT: str = "xhigh"
CODEX_SANDBOX: str = "workspace-write"
MAX_TURNS: dict[str, int] = {"baseline": 200, "fvk": 200}
ARMS: tuple[str, ...] = tuple(MAX_TURNS)
ARM_TIMEOUT_SECONDS: int = 4 * 3600
TESTED_CODEX_VERSION: str = "0.132.0"

REPO_ROOT: Path = Path(__file__).resolve().parent.parent
PACKAGE_DIR: Path = Path(__file__).resolve().parent
PROMPTS_DIR: Path = PACKAGE_DIR / "prompts"
VERIFIED_INSTANCES_JSON: Path = PACKAGE_DIR / "data" / "instances_verified500.json"
FVK_SUBMODULE: Path = REPO_ROOT / "third_party" / "formal-verification-kit"
RESULTS_DIR: Path = REPO_ROOT / "results"


@dataclass(frozen=True)
class InstanceSet:
    name: str
    dataset_identity: str
    expected_count: int
    data_file: Path
    batch_scheme: str


REGISTRY: dict[str, InstanceSet] = {
    "verified500": InstanceSet(
        name="verified500",
        dataset_identity="princeton-nlp/SWE-bench_Verified",
        expected_count=500,
        data_file=VERIFIED_INSTANCES_JSON,
        batch_scheme="verified_sorted10",
    ),
}

INSTANCE_SETS: tuple[str, ...] = tuple(REGISTRY)
DEFAULT_INSTANCE_SET: str = "verified500"
AGENTS: tuple[str, ...] = ("codex",)
DEFAULT_AGENT: str = "codex"


def resolve_dataset(instance_set: str = DEFAULT_INSTANCE_SET) -> str:
    return REGISTRY[instance_set].dataset_identity


def dataset_identity(instance_set: str = DEFAULT_INSTANCE_SET) -> str:
    return REGISTRY[instance_set].dataset_identity


def workspace_root() -> Path:
    raw = os.environ.get("FVK_BENCH_WORKSPACE")
    return Path(raw) if raw else Path.home() / ".swe-fvk-runs"


def session_env() -> dict[str, str]:
    return {
        "HOME": os.environ["HOME"],
        "PATH": os.environ["PATH"],
        "USER": os.environ.get("USER", "bench"),
        "TERM": "dumb",
        "LANG": "C.UTF-8",
        "TZ": "UTC",
    }
