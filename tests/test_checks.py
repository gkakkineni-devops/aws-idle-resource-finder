from datetime import UTC, datetime, timedelta

from finder import checks

NOW = datetime(2026, 11, 10, 12, 0, tzinfo=UTC)


def test_unattached_volume_is_flagged_with_cost():
    volumes = [{"VolumeId": "vol-1", "Size": 100, "State": "available"}]
    findings = checks.find_unattached_volumes(volumes)
    assert len(findings) == 1
    assert findings[0].kind == "unattached_volume"
    assert findings[0].resource_id == "vol-1"
    assert findings[0].monthly_cost_usd == 8.0


def test_attached_volume_is_ignored():
    volumes = [{"VolumeId": "vol-2", "Size": 50, "State": "in-use"}]
    assert checks.find_unattached_volumes(volumes) == []


def test_unassociated_ip_is_flagged():
    addresses = [{"AllocationId": "eipalloc-1", "PublicIp": "203.0.113.10"}]
    findings = checks.find_unassociated_ips(addresses)
    assert len(findings) == 1
    assert findings[0].resource_id == "eipalloc-1"
    assert findings[0].monthly_cost_usd == checks.ELASTIC_IP_USD_PER_MONTH


def test_associated_ip_is_ignored():
    addresses = [
        {"AllocationId": "eipalloc-2", "PublicIp": "203.0.113.11", "InstanceId": "i-1"},
        {"AllocationId": "eipalloc-3", "PublicIp": "203.0.113.12", "AssociationId": "eipassoc-1"},
    ]
    assert checks.find_unassociated_ips(addresses) == []


def test_old_snapshot_is_flagged():
    snapshots = [
        {"SnapshotId": "snap-1", "VolumeSize": 200, "StartTime": NOW - timedelta(days=120)}
    ]
    findings = checks.find_old_snapshots(snapshots, NOW, max_age_days=90)
    assert len(findings) == 1
    assert findings[0].resource_id == "snap-1"
    assert findings[0].monthly_cost_usd == 10.0
    assert "120 days old" in findings[0].reason


def test_recent_snapshot_is_ignored():
    snapshots = [{"SnapshotId": "snap-2", "VolumeSize": 200, "StartTime": NOW - timedelta(days=10)}]
    assert checks.find_old_snapshots(snapshots, NOW, max_age_days=90) == []


def test_snapshot_exactly_at_the_limit_is_not_flagged():
    snapshots = [{"SnapshotId": "snap-3", "VolumeSize": 10, "StartTime": NOW - timedelta(days=90)}]
    assert checks.find_old_snapshots(snapshots, NOW, max_age_days=90) == []


def test_instance_missing_tags_is_flagged():
    instances = [
        {
            "InstanceId": "i-1",
            "State": {"Name": "running"},
            "Tags": [{"Key": "owner", "Value": "gopala"}],
        }
    ]
    findings = checks.find_untagged_instances(instances, ["owner", "project"])
    assert len(findings) == 1
    assert findings[0].reason == "missing tags: project"
    assert findings[0].monthly_cost_usd == 0.0


def test_instance_with_no_tags_at_all_is_flagged():
    instances = [{"InstanceId": "i-2", "State": {"Name": "stopped"}}]
    findings = checks.find_untagged_instances(instances, ["owner"])
    assert [f.resource_id for f in findings] == ["i-2"]


def test_fully_tagged_instance_is_ignored():
    instances = [
        {
            "InstanceId": "i-3",
            "State": {"Name": "running"},
            "Tags": [{"Key": "owner", "Value": "a"}, {"Key": "project", "Value": "b"}],
        }
    ]
    assert checks.find_untagged_instances(instances, ["owner", "project"]) == []


def test_terminated_instance_is_ignored():
    instances = [{"InstanceId": "i-4", "State": {"Name": "terminated"}}]
    assert checks.find_untagged_instances(instances, ["owner"]) == []


def test_no_required_tags_means_nothing_to_flag():
    instances = [{"InstanceId": "i-5", "State": {"Name": "running"}}]
    assert checks.find_untagged_instances(instances, []) == []
