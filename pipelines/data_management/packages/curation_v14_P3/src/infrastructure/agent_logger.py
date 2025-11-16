#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional


DEFAULT_LOG_ROOT = Path("logs/agents")
MASTER_INDEX = DEFAULT_LOG_ROOT / "master_index.jsonl"


def _ensure_dir(p: Path) -> None:
    try:
        p.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass


@dataclass
class AgentRunRecord:
    timestamp: float
    agent: str
    change_id: Optional[str]
    rationale: Optional[str]
    params: Dict[str, Any]
    pages: List[str]
    metrics: Dict[str, Any]
    status: str
    artifacts: Dict[str, Any]
    tags: List[str]


class AgentLogger:
    def __init__(self, agent_name: str, log_root: Path | None = None) -> None:
        self.agent_name = agent_name
        self.log_root = (log_root or DEFAULT_LOG_ROOT).resolve()
        self.agent_dir = self.log_root / agent_name
        _ensure_dir(self.agent_dir)
        _ensure_dir(self.log_root)

    def append(self, record: AgentRunRecord) -> None:
        # Per-agent log
        agent_log = self.agent_dir / "runs.jsonl"
        try:
            with agent_log.open("a", encoding="utf-8") as f:
                f.write(json.dumps(asdict(record)) + "\n")
        except Exception:
            pass
        # Master index
        try:
            with MASTER_INDEX.open("a", encoding="utf-8") as f:
                f.write(json.dumps(asdict(record)) + "\n")
        except Exception:
            pass

    @staticmethod
    def now_ts() -> float:
        return time.time()

    @staticmethod
    def short_change_id(note: str) -> str:
        # simple normalized id from text; not cryptographically unique
        base = "".join(ch.lower() if ch.isalnum() else "-" for ch in (note or ""))
        base = "-".join([p for p in base.split("-") if p])
        return base[:64] or "unnamed-change"

