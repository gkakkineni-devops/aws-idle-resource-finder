"""Turns a list of findings into the JSON report."""

from datetime import datetime

from finder.checks import Finding


def build_report(findings: list[Finding], region: str, now: datetime) -> dict:
    ordered = sorted(findings, key=lambda f: (-f.monthly_cost_usd, f.resource_id))
    by_kind: dict[str, int] = {}
    for finding in ordered:
        by_kind[finding.kind] = by_kind.get(finding.kind, 0) + 1
    return {
        "generated_at": now.isoformat(),
        "region": region,
        "finding_count": len(ordered),
        "estimated_monthly_waste_usd": round(sum(f.monthly_cost_usd for f in ordered), 2),
        "by_kind": dict(sorted(by_kind.items())),
        "findings": [f.to_dict() for f in ordered],
    }


def report_key(now: datetime) -> str:
    """Where the report goes in S3, for example reports/2026-11-10/report-190300.json."""
    return f"reports/{now:%Y-%m-%d}/report-{now:%H%M%S}.json"
