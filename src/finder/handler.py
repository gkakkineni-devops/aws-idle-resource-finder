"""The entry point AWS Lambda calls."""

import json
import logging
import os
from datetime import UTC, datetime

from finder import aws, scan

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event, context):
    settings = scan.load_settings(os.environ)
    ec2, s3 = aws.make_clients(settings.region)
    result = scan.run(ec2, s3, settings, datetime.now(UTC))

    logger.info("report: %s", json.dumps(result))
    return {
        "finding_count": result["finding_count"],
        "estimated_monthly_waste_usd": result["estimated_monthly_waste_usd"],
        "report_location": result.get("report_location"),
    }
