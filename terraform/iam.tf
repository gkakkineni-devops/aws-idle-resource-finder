data "aws_iam_policy_document" "assume_role" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "lambda" {
  name               = "${var.name}-role"
  assume_role_policy = data.aws_iam_policy_document.assume_role.json
}

# Read-only on EC2, write-only on one folder of one bucket, and logs to one log group.
# Nothing here can delete or change a resource.
data "aws_iam_policy_document" "permissions" {
  statement {
    sid = "ReadEc2"
    actions = [
      "ec2:DescribeVolumes",
      "ec2:DescribeAddresses",
      "ec2:DescribeSnapshots",
      "ec2:DescribeInstances",
    ]
    # Describe calls can't be limited to single resources, so "*" is the only option.
    resources = ["*"]
  }

  statement {
    sid       = "WriteReports"
    actions   = ["s3:PutObject"]
    resources = ["${aws_s3_bucket.reports.arn}/reports/*"]
  }

  statement {
    sid       = "WriteLogs"
    actions   = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["${aws_cloudwatch_log_group.lambda.arn}:*"]
  }
}

resource "aws_iam_role_policy" "lambda" {
  name   = "${var.name}-policy"
  role   = aws_iam_role.lambda.id
  policy = data.aws_iam_policy_document.permissions.json
}
