"""The only file that knows how to ask AWS questions.

Every function takes a client as an argument instead of making its own. That lets the
tests hand in a fake client, and it keeps boto3 out of everything else.
"""

import json


def make_clients(region: str):
    import boto3  # imported here so the rest of the code works without boto3 installed

    return boto3.client("ec2", region_name=region), boto3.client("s3", region_name=region)


def list_volumes(ec2) -> list[dict]:
    volumes = []
    pages = ec2.get_paginator("describe_volumes").paginate(
        Filters=[{"Name": "status", "Values": ["available"]}]
    )
    for page in pages:
        volumes.extend(page["Volumes"])
    return volumes


def list_addresses(ec2) -> list[dict]:
    return ec2.describe_addresses()["Addresses"]


def list_snapshots(ec2) -> list[dict]:
    snapshots = []
    for page in ec2.get_paginator("describe_snapshots").paginate(OwnerIds=["self"]):
        snapshots.extend(page["Snapshots"])
    return snapshots


def list_instances(ec2) -> list[dict]:
    instances = []
    for page in ec2.get_paginator("describe_instances").paginate():
        for reservation in page["Reservations"]:
            instances.extend(reservation["Instances"])
    return instances


def save_report(s3, bucket: str, key: str, report: dict) -> None:
    s3.put_object(
        Bucket=bucket,
        Key=key,
        Body=json.dumps(report, indent=2).encode("utf-8"),
        ContentType="application/json",
    )
