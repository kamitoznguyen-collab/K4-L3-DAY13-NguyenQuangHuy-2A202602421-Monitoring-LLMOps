"""Dựng dashboard 6 panel từ `data/logs.jsonl` theo contract `config/dashboard.yaml`.

Kết quả là một file HTML tự chứa (không cần server), tự refresh theo
`refresh_seconds` và hiển thị time range, đơn vị và threshold của từng panel.

  python scripts/build_dashboard.py                    # 60 phút gần nhất
  python scripts/build_dashboard.py --out submission/evidence/dashboard.html
  python scripts/build_dashboard.py --watch            # build lại mỗi refresh_seconds
"""
from __future__ import annotations

import argparse
import html
import sys
import time
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from statistics import mean

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.cli import configure_utf8_stdio
from app.metrics import percentile
from scripts.log_query import DEFAULT_LOG_PATH, in_window, load_events, parse_ts
from scripts.validate_dashboard import load_dashboard_config

W, H, PAD_L, PAD_R, PAD_T, PAD_B = 560, 190, 52, 12, 12, 26
SERIES_COLORS = ("var(--s1)", "var(--s2)", "var(--s3)", "var(--s4)")


def _buckets(start: datetime, minutes: int) -> list[datetime]:
    base = start.replace(second=0, microsecond=0)
    return [base + timedelta(minutes=i) for i in range(minutes + 1)]


def _group_by_minute(events: list[dict], buckets: list[datetime]) -> list[list[dict]]:
    groups: list[list[dict]] = [[] for _ in buckets]
    base = buckets[0]
    for event in events:
        idx = int((event["_ts"] - base).total_seconds() // 60)
        if 0 <= idx < len(buckets):
            groups[idx].append(event)
    return groups


def _fmt(value: float | None, unit: str) -> str:
    if value is None:
        return "—"
    if unit == "usd":
        return f"${value:.4f}"
    if unit in {"percent"}:
        return f"{value:.1f}%"
    if unit == "score_0_to_1":
        return f"{value:.2f}"
    return f"{value:,.0f}"


def _svg_chart(
    buckets: list[datetime],
    series: dict[str, list[float | None]],
    threshold: float | None,
    kind: str = "line",
) -> str:
    values = [v for s in series.values() for v in s if v is not None]
    data_max = max(values + [1e-9])
    # Threshold quá xa dữ liệu thì ghi chú ở mép trên thay vì ép dữ liệu thành đường phẳng.
    threshold_in_scale = threshold is not None and threshold <= data_max * 3
    y_max = max(data_max, threshold * 1.15 if threshold_in_scale else 0) * 1.08
    n = len(buckets)
    plot_w, plot_h = W - PAD_L - PAD_R, H - PAD_T - PAD_B

    def x(i: int) -> float:
        return PAD_L + plot_w * i / max(1, n - 1)

    def y(v: float) -> float:
        return PAD_T + plot_h * (1 - v / y_max)

    parts = [f'<svg viewBox="0 0 {W} {H}" role="img" preserveAspectRatio="none">']
    for frac in (0, 0.5, 1):
        gy = PAD_T + plot_h * (1 - frac)
        label = y_max * frac
        text = f"{label:.3g}" if label < 100 else f"{label:,.0f}"
        parts.append(f'<line x1="{PAD_L}" x2="{W - PAD_R}" y1="{gy:.1f}" y2="{gy:.1f}" class="grid"/>')
        parts.append(f'<text x="{PAD_L - 6}" y="{gy + 4:.1f}" class="axis" text-anchor="end">{text}</text>')
    for i in (0, n // 2, n - 1):
        parts.append(
            f'<text x="{x(i):.1f}" y="{H - 8}" class="axis" text-anchor="middle">{buckets[i]:%H:%M}</text>'
        )

    bar_w = max(1.5, plot_w / n * 0.7)
    for (name, points), color in zip(series.items(), SERIES_COLORS):
        if kind == "bar":
            for i, v in enumerate(points):
                if v:
                    parts.append(
                        f'<rect x="{x(i) - bar_w / 2:.1f}" y="{y(v):.1f}" width="{bar_w:.1f}" '
                        f'height="{PAD_T + plot_h - y(v):.1f}" fill="{color}" rx="1"><title>{buckets[i]:%H:%M} {name}: {v:.4g}</title></rect>'
                    )
            continue
        path, pen_up = [], True
        for i, v in enumerate(points):
            if v is None:
                pen_up = True
                continue
            path.append(f"{'M' if pen_up else 'L'}{x(i):.1f},{y(v):.1f}")
            pen_up = False
            parts.append(f'<circle cx="{x(i):.1f}" cy="{y(v):.1f}" r="2.2" fill="{color}"><title>{buckets[i]:%H:%M} {name}: {v:.4g}</title></circle>')
        if path:
            parts.append(f'<path d="{" ".join(path)}" fill="none" stroke="{color}" stroke-width="2"/>')

    if threshold is not None and not threshold_in_scale:
        parts.append(
            f'<text x="{W - PAD_R - 4}" y="{PAD_T + 10}" class="threshold-label" text-anchor="end">'
            f"threshold {threshold:g} (above scale)</text>"
        )
    elif threshold is not None:
        ty = y(threshold)
        parts.append(f'<line x1="{PAD_L}" x2="{W - PAD_R}" y1="{ty:.1f}" y2="{ty:.1f}" class="threshold"/>')
        parts.append(f'<text x="{W - PAD_R - 4}" y="{ty - 4:.1f}" class="threshold-label" text-anchor="end">threshold {threshold:g}</text>')
    parts.append("</svg>")
    return "".join(parts)


def _cumulative(points: list[float | None]) -> list[float]:
    total, out = 0.0, []
    for v in points:
        total += v or 0
        out.append(round(total, 6))
    return out


def _panel_data(panel_id: str, events: list[dict], buckets: list[datetime]) -> dict:
    groups = _group_by_minute(events, buckets)
    responses = [[e for e in g if e.get("event") == "response_sent"] for g in groups]
    all_responses = [e for g in responses for e in g]

    def per_minute(fn):
        return [fn(g) if g else None for g in responses]

    if panel_id == "latency":
        lat = [e["latency_ms"] for e in all_responses if e.get("latency_ms") is not None]
        ttft = [e["ttft_ms"] for e in all_responses if e.get("ttft_ms") is not None]
        stats = {
            "p50": percentile(lat, 50), "p95": percentile(lat, 95),
            "p99": percentile(lat, 99), "ttft_p95": percentile(ttft, 95),
        }
        series = {
            "P50": per_minute(lambda g: percentile([e["latency_ms"] for e in g], 50)),
            "P95": per_minute(lambda g: percentile([e["latency_ms"] for e in g], 95)),
            "P99": per_minute(lambda g: percentile([e["latency_ms"] for e in g], 99)),
            "TTFT P95": per_minute(lambda g: percentile([e["ttft_ms"] for e in g], 95)),
        }
        return {"stats": stats, "series": series, "kind": "line"}

    if panel_id == "traffic":
        counts = [sum(1 for e in g if e.get("event") == "request_received") for g in groups]
        active = [c for c in counts if c]
        stats = {
            "count": sum(counts),
            "rate_per_minute": round(sum(counts) / max(1, len(active)), 2) if active else 0,
        }
        return {"stats": stats, "series": {"requests/min": counts}, "kind": "bar",
                "note": "rate_per_minute tính trên các phút có traffic"}

    if panel_id == "errors":
        received = [sum(1 for e in g if e.get("event") == "request_received") for g in groups]
        failed = [sum(1 for e in g if e.get("event") == "request_failed") for g in groups]
        tool = [e for g in groups for e in g if e.get("tool_success") is not None]
        breakdown = Counter(
            e.get("error_type") for g in groups for e in g if e.get("event") == "request_failed"
        )
        stats = {
            "error_rate_pct": round(sum(failed) / sum(received) * 100, 2) if sum(received) else 0.0,
            "tool_success_rate_pct": round(
                sum(1 for e in tool if e["tool_success"]) / len(tool) * 100, 2
            ) if tool else None,
            "count_by_value": dict(breakdown) or {"none": 0},
        }
        series = {
            "error rate %": [round(f / r * 100, 2) if r else None for f, r in zip(failed, received)],
            "retrieval success %": [
                round(sum(1 for e in g if e.get("tool_success")) /
                      max(1, sum(1 for e in g if e.get("tool_success") is not None)) * 100, 2)
                if any(e.get("tool_success") is not None for e in g) else None
                for g in groups
            ],
        }
        return {"stats": stats, "series": series, "kind": "line"}

    if panel_id == "cost":
        per_min = [round(sum(e.get("cost_usd") or 0 for e in g), 6) if g else None for g in responses]
        stats = {"total": round(sum(v or 0 for v in per_min), 4),
                 "sum_by_minute": max((v or 0) for v in per_min)}
        return {"stats": stats, "series": {"cumulative $": _cumulative(per_min), "$/min": per_min},
                "kind": "line", "note": "sum_by_minute hiển thị phút cao nhất"}

    if panel_id == "tokens":
        tin = [sum(e.get("tokens_in") or 0 for e in g) if g else None for g in responses]
        tout = [sum(e.get("tokens_out") or 0 for e in g) if g else None for g in responses]
        stats = {"sum_by_field": sum(v or 0 for v in tin) + sum(v or 0 for v in tout),
                 "tokens_in": sum(v or 0 for v in tin), "tokens_out": sum(v or 0 for v in tout)}
        return {"stats": stats, "series": {"cumulative tokens": _cumulative(
            [(a or 0) + (b or 0) for a, b in zip(tin, tout)]), "tokens_in/min": tin, "tokens_out/min": tout},
            "kind": "line"}

    if panel_id == "quality":
        scores = [e["quality_score"] for e in all_responses if e.get("quality_score") is not None]
        stats = {"mean": round(mean(scores), 3) if scores else None}
        series = {"mean quality": per_minute(
            lambda g: round(mean(e["quality_score"] for e in g), 3))}
        return {"stats": stats, "series": series, "kind": "line"}

    raise ValueError(panel_id)


def _threshold_status(panel: dict, stats: dict) -> tuple[str, float | None]:
    threshold = panel["threshold"]
    value = stats.get(threshold["aggregation"])
    if not isinstance(value, (int, float)):
        return "no-data", None
    ok = value <= threshold["value"] if threshold["operator"] == "lte" else value >= threshold["value"]
    return ("ok" if ok else "breach"), value


def render(config: dict, events: list[dict], start: datetime, end: datetime, source: Path) -> str:
    dashboard = config["dashboard"]
    minutes = dashboard["time_range_minutes"]
    buckets = _buckets(start, minutes)
    cards = []
    for panel in dashboard["panels"]:
        data = _panel_data(panel["id"], events, buckets)
        status, value = _threshold_status(panel, data["stats"])
        threshold = panel["threshold"]
        stats_html = "".join(
            f'<div class="stat"><span>{html.escape(k)}</span><b>'
            f'{html.escape(str(v) if isinstance(v, dict) else _fmt(v, panel["unit"]) if isinstance(v, (int, float)) else "—")}'
            f"</b></div>"
            for k, v in data["stats"].items()
        )
        legend = "".join(
            f'<span><i style="background:{c}"></i>{html.escape(name)}</span>'
            for name, c in zip(data["series"], SERIES_COLORS)
        )
        op = "≤" if threshold["operator"] == "lte" else "≥"
        cards.append(f"""
<section class="panel {status}">
  <header>
    <h2>{html.escape(panel["title"])}</h2>
    <span class="badge {status}">{status.upper()}</span>
  </header>
  <p class="meta">unit: <b>{html.escape(panel["unit"])}</b> · threshold: <b>{threshold["aggregation"]} {op} {threshold["value"]:g}</b>
   · current: <b>{_fmt(value, panel["unit"]) if value is not None else "—"}</b></p>
  <div class="stats">{stats_html}</div>
  {_svg_chart(buckets, data["series"], threshold["value"], data["kind"])}
  <div class="legend">{legend}</div>
  <p class="query"><code>{html.escape(panel["query"])}</code>{f'<br><small>{html.escape(data["note"])}</small>' if data.get("note") else ""}</p>
</section>""")

    return f"""<!doctype html>
<html lang="vi"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="refresh" content="{dashboard["refresh_seconds"]}">
<title>Day13 Monitoring Dashboard</title>
<style>
:root {{ --bg:#f6f7f9; --card:#fff; --fg:#1b1f24; --muted:#5f6b7a; --grid:#e3e7ec;
  --s1:#2f6fdb; --s2:#d9480f; --s3:#7048e8; --s4:#0c8599; --ok:#2b8a3e; --bad:#c92a2a; --warn:#868e96; }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg:#111418; --card:#1a1f25; --fg:#e8ebef; --muted:#9aa5b1;
  --grid:#2a3139; --s1:#6ea8fe; --s2:#ff8a4c; --s3:#b197fc; --s4:#3bc9db; --ok:#51cf66; --bad:#ff6b6b; }} }}
* {{ box-sizing:border-box }}
body {{ margin:0; background:var(--bg); color:var(--fg); font:14px/1.45 system-ui,-apple-system,Segoe UI,sans-serif; }}
main {{ max-width:1240px; margin:0 auto; padding:20px 16px 40px }}
h1 {{ font-size:20px; margin:0 0 4px }}
.sub {{ color:var(--muted); margin:0 0 18px }}
.grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(360px,1fr)); gap:14px }}
.panel {{ background:var(--card); border-radius:10px; padding:14px 16px; border-top:3px solid var(--warn) }}
.panel.ok {{ border-top-color:var(--ok) }} .panel.breach {{ border-top-color:var(--bad) }}
.panel header {{ display:flex; justify-content:space-between; align-items:center; gap:8px }}
h2 {{ font-size:15px; margin:0 }}
.badge {{ font-size:11px; font-weight:700; padding:2px 8px; border-radius:99px; color:#fff; background:var(--warn) }}
.badge.ok {{ background:var(--ok) }} .badge.breach {{ background:var(--bad) }}
.meta {{ color:var(--muted); margin:6px 0 }}
.stats {{ display:flex; flex-wrap:wrap; gap:6px 16px; margin:4px 0 6px }}
.stat span {{ display:block; font-size:11px; color:var(--muted) }} .stat b {{ font-size:15px; font-variant-numeric:tabular-nums }}
svg {{ width:100%; height:190px; display:block }}
.grid line.grid, svg .grid {{ stroke:var(--grid); stroke-width:1 }}
svg .axis {{ fill:var(--muted); font-size:10px }}
svg .threshold {{ stroke:var(--bad); stroke-width:1.5; stroke-dasharray:6 4 }}
svg .threshold-label {{ fill:var(--bad); font-size:10px; font-weight:600 }}
.legend {{ display:flex; flex-wrap:wrap; gap:4px 14px; font-size:12px; color:var(--muted) }}
.legend i {{ display:inline-block; width:10px; height:10px; border-radius:2px; margin-right:5px; vertical-align:-1px }}
.query {{ font-size:11px; color:var(--muted); margin:8px 0 0; overflow-wrap:anywhere }}
</style></head>
<body><main>
<h1>{html.escape(dashboard["title"])}</h1>
<p class="sub">Time range: <b>last {minutes} minutes</b> ({start:%Y-%m-%d %H:%M} → {end:%H:%M} UTC) ·
auto-refresh: <b>{dashboard["refresh_seconds"]}s</b> · source: <code>{html.escape(str(source))}</code> ·
{len(events)} log events · generated {datetime.now().astimezone():%Y-%m-%d %H:%M:%S %Z}</p>
<div class="grid">{"".join(cards)}</div>
</main></body></html>"""


def build(args: argparse.Namespace) -> Path:
    config = load_dashboard_config(args.config)
    minutes = config["dashboard"]["time_range_minutes"]
    until = parse_ts(args.until) if args.until else None
    events, start, end = in_window(load_events(args.log), minutes, until=until)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(render(config, events, start, end, args.log), encoding="utf-8")
    return args.out


def main() -> None:
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", type=Path, default=REPO_ROOT / "config" / "dashboard.yaml")
    parser.add_argument("--log", type=Path, default=DEFAULT_LOG_PATH)
    parser.add_argument("--out", type=Path, default=Path("data/dashboard.html"))
    parser.add_argument("--until", help="ISO timestamp kết thúc cửa sổ (mặc định: bây giờ)")
    parser.add_argument("--watch", action="store_true", help="build lại theo refresh_seconds")
    args = parser.parse_args()

    out = build(args)
    print(f"Dashboard: {out.resolve()}")
    if args.watch:
        refresh = load_dashboard_config(args.config)["dashboard"]["refresh_seconds"]
        while True:
            time.sleep(refresh)
            build(args)


if __name__ == "__main__":
    main()
