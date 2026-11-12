"""Runs every check and builds the report."""

from dataclasses import dataclass
from datetime import datetime

from finder import aws, checks, report


@dataclass(frozen=True)
class Settings:
    region: str
    bucket: str | None
    max_snapshot_age_days: int
    required_tags: tuple[str, ...]


def load_settings(env: dict) -> Settings:
    """Read the settings from environment variables, with sensible defaults."""
    raw_tags = env.get("REQUIRED_TAGS", "owner,project")
    tags = tuple(t.strip() for t in raw_tags.split(",") if t.strip())
    return Settings(
        region=env.get("AWS_REGION", "us-east-1"),
        bucket=env.get("REPORT_BUCKET") or None,
        max_snapshot_age_days=int(env.get("MAX_SNAPSHOT_AGE_DAYS", "90")),
        required_tags=tags,
    )


def run(ec2, s3, settings: Settings, now: datetime) -> dict:
    findings = []
    findings += checks.find_unattached_volumes(aws.list_volumes(ec2))
    findings += checks.find_unassociated_ips(aws.list_addresses(ec2))
    findings += checks.find_old_snapshots(
        aws.list_snapshots(ec2), now, settings.max_snapshot_age_days
    )
    findings += checks.find_untagged_instances(aws.list_instances(ec2), settings.required_tags)

    result = report.build_report(findings, settings.region, now)
    if settings.bucket:
        key = report.report_key(now)
        aws.save_report(s3, settings.bucket, key, result)
        result["report_location"] = f"s3://{settings.bucket}/{key}"
    return result
