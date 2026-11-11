import json
from datetime import UTC, datetime

from finder.checks import Finding
from finder.report import build_report, report_key

NOW = datetime(2026, 11, 10, 19, 3, 5, tzinfo=UTC)


def make_findings():
    return [
        Finding("unattached_volume", "vol-b", "small", 1.6),
        Finding("unassociated_ip", "eipalloc-a", "idle ip", 3.65),
        Finding("unattached_volume", "vol-a", "big", 8.0),
    ]


def test_total_is_the_sum_of_the_findings():
    report = build_report(make_findings(), "us-east-1", NOW)
    assert report["estimated_monthly_waste_usd"] == 13.25
    assert report["finding_count"] == 3


def test_most_expensive_finding_comes_first():
    report = build_report(make_findings(), "us-east-1", NOW)
    assert [f["resource_id"] for f in report["findings"]] == ["vol-a", "eipalloc-a", "vol-b"]


def test_counts_by_kind():
    report = build_report(make_findings(), "us-east-1", NOW)
    assert report["by_kind"] == {"unassociated_ip": 1, "unattached_volume": 2}


def test_empty_report_is_still_valid():
    report = build_report([], "eu-west-1", NOW)
    assert report["finding_count"] == 0
    assert report["estimated_monthly_waste_usd"] == 0
    assert report["findings"] == []


def test_report_can_be_written_as_json():
    report = build_report(make_findings(), "us-east-1", NOW)
    assert json.loads(json.dumps(report))["region"] == "us-east-1"


def test_report_key_has_the_date_and_time():
    assert report_key(NOW) == "reports/2026-11-10/report-190305.json"
