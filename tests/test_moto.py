"""One test against a pretend AWS (moto), to check the real boto3 calls are shaped right."""

from datetime import UTC, datetime

import boto3
from moto import mock_aws

from finder import scan


@mock_aws
def test_scan_against_a_pretend_aws():
    ec2 = boto3.client("ec2", region_name="us-east-1")
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket="test-reports")

    volume_id = ec2.create_volume(AvailabilityZone="us-east-1a", Size=20)["VolumeId"]
    allocation_id = ec2.allocate_address(Domain="vpc")["AllocationId"]
    image_id = ec2.describe_images()["Images"][0]["ImageId"]
    instance_id = ec2.run_instances(ImageId=image_id, MinCount=1, MaxCount=1)["Instances"][0][
        "InstanceId"
    ]

    settings = scan.Settings(
        region="us-east-1",
        bucket="test-reports",
        max_snapshot_age_days=90,
        required_tags=("owner",),
    )
    report = scan.run(ec2, s3, settings, datetime.now(UTC))

    found = {finding["resource_id"] for finding in report["findings"]}
    assert volume_id in found
    assert allocation_id in found
    assert instance_id in found
    assert s3.list_objects_v2(Bucket="test-reports")["KeyCount"] == 1
