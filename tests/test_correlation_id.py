from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path

import httpx

from app import logging_config
from app.main import app

CHAT_BODY = {
    "user_id": "student-01",
    "session_id": "session-01",
    "feature": "qa",
    "message": "My email is student@vinuni.edu.vn and phone 0987654321",
}


def _post_chat(headers: dict[str, str] | None = None) -> httpx.Response:
    async def send() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post("/chat", json=CHAT_BODY, headers=headers or {})

    return asyncio.run(send())


def _events(log_path: Path) -> list[dict]:
    return [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]


def test_generates_correlation_id_and_returns_headers(monkeypatch, tmp_path: Path) -> None:
    log_path = tmp_path / "logs.jsonl"
    monkeypatch.setattr(logging_config, "LOG_PATH", log_path)

    response = _post_chat()

    correlation_id = response.headers["x-request-id"]
    assert re.fullmatch(r"req-[0-9a-f]{8}", correlation_id)
    assert float(response.headers["x-response-time-ms"]) >= 0
    assert response.json()["correlation_id"] == correlation_id
    for event in _events(log_path):
        assert event["correlation_id"] == correlation_id


def test_reuses_incoming_request_id(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(logging_config, "LOG_PATH", tmp_path / "logs.jsonl")

    response = _post_chat({"x-request-id": "req-abcdef01"})

    assert response.headers["x-request-id"] == "req-abcdef01"


def test_rejects_unsafe_incoming_request_id(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(logging_config, "LOG_PATH", tmp_path / "logs.jsonl")

    response = _post_chat({"x-request-id": "bad id with spaces"})

    assert re.fullmatch(r"req-[0-9a-f]{8}", response.headers["x-request-id"])


def test_logs_are_enriched_and_free_of_raw_pii(monkeypatch, tmp_path: Path) -> None:
    log_path = tmp_path / "logs.jsonl"
    monkeypatch.setattr(logging_config, "LOG_PATH", log_path)

    _post_chat()

    raw = log_path.read_text(encoding="utf-8")
    assert "student@vinuni.edu.vn" not in raw
    assert "0987654321" not in raw
    for event in _events(log_path):
        if event.get("service") == "api":
            for field in ("user_id_hash", "session_id", "feature", "model", "env"):
                assert event.get(field), field
            assert event["user_id_hash"] != CHAT_BODY["user_id"]


def test_context_does_not_leak_between_requests(monkeypatch, tmp_path: Path) -> None:
    log_path = tmp_path / "logs.jsonl"
    monkeypatch.setattr(logging_config, "LOG_PATH", log_path)

    first = _post_chat().headers["x-request-id"]
    second = _post_chat().headers["x-request-id"]

    assert first != second
    ids_by_request = {event["correlation_id"] for event in _events(log_path)}
    assert ids_by_request == {first, second}
