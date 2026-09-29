"""Tiện ích đọc `data/logs.jsonl` dùng chung cho dashboard và điều tra incident."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

DEFAULT_LOG_PATH = Path("data/logs.jsonl")


def parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def load_events(path: Path = DEFAULT_LOG_PATH) -> list[dict]:
    events = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(event.get("ts"), str):
            event["_ts"] = parse_ts(event["ts"])
            events.append(event)
    return sorted(events, key=lambda e: e["_ts"])


def in_window(
    events: list[dict],
    minutes: int,
    until: datetime | None = None,
    since: datetime | None = None,
) -> tuple[list[dict], datetime, datetime]:
    end = until or datetime.now(timezone.utc)
    start = since or end - timedelta(minutes=minutes)
    return [e for e in events if start <= e["_ts"] <= end], start, end
