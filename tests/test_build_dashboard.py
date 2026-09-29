from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scripts import build_dashboard
from scripts.log_query import in_window, load_events
from scripts.validate_dashboard import load_dashboard_config

REPO_ROOT = Path(__file__).resolve().parents[1]


def _write_logs(path: Path, now: datetime) -> None:
    rows = []
    for i in range(10):
        ts = (now - timedelta(minutes=i)).isoformat().replace("+00:00", "Z")
        cid = f"req-{i:08x}"
        rows.append({"ts": ts, "level": "info", "service": "api", "event": "request_received", "correlation_id": cid})
        if i == 0:
            rows.append({"ts": ts, "level": "error", "service": "api", "event": "request_failed",
                         "correlation_id": cid, "error_type": "RuntimeError", "tool_success": False})
            continue
        rows.append({"ts": ts, "level": "info", "service": "api", "event": "response_sent", "correlation_id": cid,
                     "latency_ms": 100 * i, "ttft_ms": 50, "tokens_in": 30, "tokens_out": 100,
                     "cost_usd": 0.0016, "quality_score": 0.8, "tool_success": True})
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")


def test_dashboard_renders_all_contract_panels_with_thresholds(tmp_path: Path) -> None:
    now = datetime.now(timezone.utc)
    log_path = tmp_path / "logs.jsonl"
    _write_logs(log_path, now)
    config = load_dashboard_config(REPO_ROOT / "config" / "dashboard.yaml")

    events, start, end = in_window(load_events(log_path), 60, until=now)
    page = build_dashboard.render(config, events, start, end, log_path)

    for panel in config["dashboard"]["panels"]:
        assert panel["title"] in page
        assert f"threshold: <b>{panel['threshold']['aggregation']}" in page
    assert "last 60 minutes" in page
    assert 'http-equiv="refresh" content="30"' in page


def test_error_panel_counts_failures_and_retrieval_success(tmp_path: Path) -> None:
    now = datetime.now(timezone.utc)
    log_path = tmp_path / "logs.jsonl"
    _write_logs(log_path, now)
    events, start, _ = in_window(load_events(log_path), 60, until=now)
    buckets = build_dashboard._buckets(start, 60)

    stats = build_dashboard._panel_data("errors", events, buckets)["stats"]

    assert stats["error_rate_pct"] == 10.0
    assert stats["tool_success_rate_pct"] == 90.0
    assert stats["count_by_value"] == {"RuntimeError": 1}
