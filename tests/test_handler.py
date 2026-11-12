import os
from unittest.mock import patch

from fakes import FakeEC2, FakeS3
from finder import handler


def test_handler_returns_a_short_summary():
    ec2 = FakeEC2(volumes=[{"VolumeId": "vol-1", "Size": 10, "State": "available"}])
    s3 = FakeS3()
    env = {"AWS_REGION": "us-east-1", "REPORT_BUCKET": "my-reports", "REQUIRED_TAGS": "owner"}
    with patch.dict(os.environ, env), patch("finder.aws.make_clients", return_value=(ec2, s3)):
        result = handler.handler({}, None)
    assert result["finding_count"] == 1
    assert result["estimated_monthly_waste_usd"] == 0.8
    assert result["report_location"].startswith("s3://my-reports/reports/")
    assert len(s3.puts) == 1
