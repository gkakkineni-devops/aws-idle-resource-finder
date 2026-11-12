"""Run it from your own computer: python -m finder --region us-east-1

This only reads from AWS and prints the report. It does not change anything.
"""

import argparse
import json
import os
from datetime import UTC, datetime

from finder import aws, scan


def main() -> None:
    parser = argparse.ArgumentParser(description="Find idle AWS resources.")
    parser.add_argument("--region", default=os.environ.get("AWS_REGION", "us-east-1"))
    parser.add_argument("--max-snapshot-age-days", type=int, default=90)
    parser.add_argument("--required-tags", default="owner,project")
    args = parser.parse_args()

    settings = scan.load_settings(
        {
            "AWS_REGION": args.region,
            "MAX_SNAPSHOT_AGE_DAYS": str(args.max_snapshot_age_days),
            "REQUIRED_TAGS": args.required_tags,
        }
    )
    ec2, s3 = aws.make_clients(settings.region)
    print(json.dumps(scan.run(ec2, s3, settings, datetime.now(UTC)), indent=2))


if __name__ == "__main__":
    main()
