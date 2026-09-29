from __future__ import annotations

import re
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
REQUIRED_FIELDS = ("name", "severity", "condition", "duration", "type", "channel", "owner", "runbook")


def test_three_complete_symptom_based_alerts_with_runbooks() -> None:
    alerts = yaml.safe_load((REPO_ROOT / "config" / "alert_rules.yaml").read_text(encoding="utf-8"))["alerts"]
    runbook = (REPO_ROOT / "docs" / "alerts.md").read_text(encoding="utf-8")

    assert len(alerts) == 3
    for alert in alerts:
        for field in REQUIRED_FIELDS:
            value = str(alert.get(field, ""))
            assert value and "TODO" not in value, f"{alert.get('name')}.{field}"
        assert alert["type"] == "symptom-based"
        assert alert["channel"] == "slack"
        assert re.fullmatch(r"\d+[mh]", alert["duration"])
        anchor = alert["runbook"].split("#", 1)[1]  # alert-1 → "## Alert 1"
        assert f"## {anchor.replace('-', ' ').title()}" in runbook
        assert alert["name"] in runbook


def test_slo_error_budget_matches_target() -> None:
    slo = yaml.safe_load((REPO_ROOT / "config" / "slo.yaml").read_text(encoding="utf-8"))["primary_slo"]
    assert round(100 - slo["target_percent"], 3) == slo["error_budget_percent"]
