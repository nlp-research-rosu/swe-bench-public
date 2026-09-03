"""Shared runner interface and the single Codex backend factory."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

from fvk_bench import config


@dataclass
class AgentResult:
    ok: bool
    session_id: str | None
    num_turns: int | None
    subtype: str | None
    duration_seconds: float
    raw_json: dict | None
    error: str | None


@runtime_checkable
class AgentRunner(Protocol):
    name: str

    def new_session_id(self) -> str | None: ...

    def run_fresh(
        self,
        ws: Path,
        arm: str,
        prompt: str,
        *,
        session_id: str | None = None,
        timeout: int = config.ARM_TIMEOUT_SECONDS,
        max_turns: int | None = None,
    ) -> AgentResult: ...

    def run_fork(
        self,
        ws: Path,
        arm: str,
        prompt: str,
        baseline_session_id: str,
        *,
        timeout: int = config.ARM_TIMEOUT_SECONDS,
        max_turns: int | None = None,
    ) -> AgentResult: ...

    def transcript_path(self, ws: Path, session_id: str) -> Path | None: ...

    def audit_transcript(self, path: Path) -> dict: ...

    def version(self) -> str | None: ...


def get_runner(
    agent: str = config.DEFAULT_AGENT, *, codex_bin: str = "codex", model: str | None = None
) -> AgentRunner:
    if agent != "codex":
        raise ValueError(f"unknown agent {agent!r}; expected 'codex'")
    from fvk_bench.codex_runner import CodexRunner

    return CodexRunner(codex_bin=codex_bin, model=model or config.CODEX_MODEL)


__all__ = ["AgentRunner", "AgentResult", "get_runner"]
