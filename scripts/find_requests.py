"""Bước Logs của quy trình Metrics → Logs → Traces.

Lọc `data/logs.jsonl` để lấy correlation_id và trace_id của request bất thường.

Ví dụ:
  python scripts/find_requests.py --slowest 5
  python scripts/find_requests.py --failed
  python scripts/find_requests.py --costliest 5 --minutes 15
  python scripts/find_requests.py --id req-1a2b3c4d
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.cli import configure_utf8_stdio
from scripts.log_query import DEFAULT_LOG_PATH, in_window, load_events

COLUMNS = (
    "ts", "event", "correlation_id", "trace_id", "feature", "prompt_version",
    "latency_ms", "ttft_ms", "tokens_out", "cost_usd", "error_type", "tool_success",
)


def _row(event: dict) -> str:
    return " | ".join(f"{col}={event.get(col)}" for col in COLUMNS if event.get(col) is not None)


def main() -> None:
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--slowest", type=int, metavar="N")
    group.add_argument("--costliest", type=int, metavar="N")
    group.add_argument("--failed", action="store_true")
    group.add_argument("--id", metavar="CORRELATION_ID")
    parser.add_argument("--minutes", type=int, default=60, help="cửa sổ thời gian gần nhất")
    parser.add_argument("--log", type=Path, default=DEFAULT_LOG_PATH)
    args = parser.parse_args()

    events, start, end = in_window(load_events(args.log), args.minutes)
    print(f"Window: {start:%Y-%m-%d %H:%M:%S} → {end:%H:%M:%S} UTC | {len(events)} events")

    if args.id:
        selected = [e for e in events if e.get("correlation_id") == args.id]
    elif args.failed:
        selected = [e for e in events if e.get("event") == "request_failed"]
    else:
        key = "latency_ms" if args.slowest else "cost_usd"
        responses = [e for e in events if e.get("event") == "response_sent"]
        selected = sorted(responses, key=lambda e: e.get(key) or 0, reverse=True)
        selected = selected[: args.slowest or args.costliest]

    for event in selected:
        print(_row(event))
    if not selected:
        print("Không có request phù hợp.")


if __name__ == "__main__":
    main()
