from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from app import logging_config


def test_concurrent_writes_produce_valid_jsonl(monkeypatch, tmp_path: Path) -> None:
    log_path = tmp_path / "logs.jsonl"
    monkeypatch.setattr(logging_config, "LOG_PATH", log_path)
    processor = logging_config.JsonlFileProcessor()
    payload = "x" * 2000  # dòng dài để dễ lộ việc ghi đan xen

    def write(i: int) -> None:
        processor(None, "info", {"event": "e", "i": i, "payload": payload})

    with ThreadPoolExecutor(max_workers=16) as pool:
        list(pool.map(write, range(400)))

    lines = log_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 400
    assert sorted(json.loads(line)["i"] for line in lines) == list(range(400))
