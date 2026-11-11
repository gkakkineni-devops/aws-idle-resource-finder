"""The rules for spotting idle resources.

Nothing in this file talks to AWS. Each function takes plain data (the dictionaries
boto3 returns) and gives back a list of findings, so it is easy to test.
"""

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta

# Rough us-east-1 list prices in US dollars. These are estimates: prices change by
# region and over time, so check the AWS pricing pages before you trust the totals.
EBS_USD_PER_GB_MONTH = 0.08
SNAPSHOT_USD_PER_GB_MONTH = 0.05
ELASTIC_IP_USD_PER_MONTH = 3.65  # $0.005 per hour, about 730 hours a month


@dataclass(frozen=True)
class Finding:
    kind: str
    resource_id: str
    reason: str
    monthly_cost_usd: float

    def to_dict(self) -> dict:
        return asdict(self)


def find_unattached_volumes(volumes: list[dict]) -> list[Finding]:
    """EBS volumes that are not attached to anything still cost money every month."""
    findings = []
    for volume in volumes:
        if volume.get("State") != "available":
            continue
        size = volume["Size"]
        findings.append(
            Finding(
                kind="unattached_volume",
                resource_id=volume["VolumeId"],
                reason=f"{size} GB volume is not attached to any instance",
                monthly_cost_usd=round(size * EBS_USD_PER_GB_MONTH, 2),
            )
        )
    return findings


def find_unassociated_ips(addresses: list[dict]) -> list[Finding]:
    """Elastic IPs that point at nothing. AWS charges for them by the hour."""
    findings = []
    for address in addresses:
        if address.get("AssociationId") or address.get("InstanceId"):
            continue
        findings.append(
            Finding(
                kind="unassociated_ip",
                resource_id=address.get("AllocationId", address["PublicIp"]),
                reason=f"Elastic IP {address['PublicIp']} is not associated with anything",
                monthly_cost_usd=ELASTIC_IP_USD_PER_MONTH,
            )
        )
    return findings


def find_old_snapshots(snapshots: list[dict], now: datetime, max_age_days: int) -> list[Finding]:
    """Snapshots older than max_age_days. The cost is an upper bound.

    Snapshots are incremental, so the real bill is often lower than size times price.
    """
    cutoff = now - timedelta(days=max_age_days)
    findings = []
    for snapshot in snapshots:
        started = snapshot["StartTime"]
        if started >= cutoff:
            continue
        age_days = (now - started).days
        size = snapshot["VolumeSize"]
        findings.append(
            Finding(
                kind="old_snapshot",
                resource_id=snapshot["SnapshotId"],
                reason=f"{size} GB snapshot is {age_days} days old",
                monthly_cost_usd=round(size * SNAPSHOT_USD_PER_GB_MONTH, 2),
            )
        )
    return findings


def find_untagged_instances(
    instances: list[dict], required_tags: tuple[str, ...] | list[str]
) -> list[Finding]:
    """Instances missing a tag you require, such as owner or project.

    Without an owner tag nobody knows who to ask before switching a machine off.
    """
    findings = []
    for instance in instances:
        if instance["State"]["Name"] in ("terminated", "shutting-down"):
            continue
        present = {tag["Key"] for tag in instance.get("Tags", [])}
        missing = [tag for tag in required_tags if tag not in present]
        if not missing:
            continue
        findings.append(
            Finding(
                kind="untagged_instance",
                resource_id=instance["InstanceId"],
                reason="missing tags: " + ", ".join(missing),
                monthly_cost_usd=0.0,
            )
        )
    return findings
