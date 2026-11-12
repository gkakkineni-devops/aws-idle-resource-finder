import json
from datetime import UTC, datetime, timedelta

from fakes import FakeEC2, FakeS3
from finder import aws, scan

NOW = datetime(2026, 11, 10, 12, 0, tzinfo=UTC)


def make_ec2():
    return FakeEC2(
        volumes=[
            {"VolumeId": "vol-1", "Size": 10, "State": "available"},
            {"VolumeId": "vol-2", "Size": 20, "State": "available"},
            {"VolumeId": "vol-3", "Size": 30, "State": "available"},
        ],
        addresses=[{"AllocationId": "eipalloc-1", "PublicIp": "203.0.113.1"}],
        snapshots=[
            {"SnapshotId": "snap-old", "VolumeSize": 100, "StartTime": NOW - timedelta(days=200)},
            {"SnapshotId": "snap-new", "VolumeSize": 100, "StartTime": NOW - timedelta(days=5)},
        ],
        instances=[{"InstanceId": "i-1", "State": {"Name": "running"}}],
    )


def make_settings(bucket=None):
    return scan.Settings(
        region="us-east-1",
        bucket=bucket,
        max_snapshot_age_days=90,
        required_tags=("owner",),
    )


def test_run_collects_findings_from_every_check():
    report = scan.run(make_ec2(), FakeS3(), make_settings(), NOW)
    assert report["by_kind"] == {
        "old_snapshot": 1,
        "unassociated_ip": 1,
        "unattached_volume": 3,
        "untagged_instance": 1,
    }
    assert report["estimated_monthly_waste_usd"] == 13.45


def test_run_without_a_bucket_does_not_write_to_s3():
    s3 = FakeS3()
    report = scan.run(make_ec2(), s3, make_settings(bucket=None), NOW)
    assert s3.puts == []
    assert "report_location" not in report


def test_run_with_a_bucket_saves_the_report():
    s3 = FakeS3()
    report = scan.run(make_ec2(), s3, make_settings(bucket="my-reports"), NOW)
    assert len(s3.puts) == 1
    put = s3.puts[0]
    assert put["Bucket"] == "my-reports"
    assert put["Key"] == "reports/2026-11-10/report-120000.json"
    assert json.loads(put["Body"])["finding_count"] == report["finding_count"]
    assert report["report_location"] == "s3://my-reports/reports/2026-11-10/report-120000.json"


def test_volumes_are_requested_with_the_available_filter():
    ec2 = make_ec2()
    aws.list_volumes(ec2)
    name, kwargs = ec2.calls[0]
    assert name == "describe_volumes"
    assert kwargs["Filters"] == [{"Name": "status", "Values": ["available"]}]


def test_every_page_is_read():
    assert len(aws.list_volumes(make_ec2())) == 3
    assert len(aws.list_instances(make_ec2())) == 1


def test_settings_defaults():
    settings = scan.load_settings({})
    assert settings.region == "us-east-1"
    assert settings.bucket is None
    assert settings.max_snapshot_age_days == 90
    assert settings.required_tags == ("owner", "project")


def test_settings_from_environment():
    settings = scan.load_settings(
        {
            "AWS_REGION": "eu-west-1",
            "REPORT_BUCKET": "b",
            "MAX_SNAPSHOT_AGE_DAYS": "30",
            "REQUIRED_TAGS": " owner , team ,",
        }
    )
    assert settings.region == "eu-west-1"
    assert settings.bucket == "b"
    assert settings.max_snapshot_age_days == 30
    assert settings.required_tags == ("owner", "team")
