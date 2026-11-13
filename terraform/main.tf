data "aws_caller_identity" "current" {}

locals {
  bucket_name = "${var.name}-reports-${data.aws_caller_identity.current.account_id}"
}

# --- The code -----------------------------------------------------------------
# Zips only the .py files in src/finder, so no __pycache__ ends up in the package.
data "archive_file" "lambda" {
  type        = "zip"
  output_path = "${path.module}/finder.zip"

  dynamic "source" {
    for_each = fileset("${path.module}/../src", "finder/*.py")
    content {
      content  = file("${path.module}/../src/${source.value}")
      filename = source.value
    }
  }
}

resource "aws_lambda_function" "finder" {
  function_name    = var.name
  role             = aws_iam_role.lambda.arn
  runtime          = "python3.13"
  handler          = "finder.handler.handler"
  filename         = data.archive_file.lambda.output_path
  source_code_hash = data.archive_file.lambda.output_base64sha256
  timeout          = 60
  memory_size      = 256

  environment {
    variables = {
      REPORT_BUCKET         = aws_s3_bucket.reports.bucket
      MAX_SNAPSHOT_AGE_DAYS = tostring(var.max_snapshot_age_days)
      REQUIRED_TAGS         = join(",", var.required_tags)
    }
  }

  depends_on = [aws_cloudwatch_log_group.lambda]
}

# --- Logs ---------------------------------------------------------------------
# Created here so we control how long logs are kept. Lambda would otherwise create
# the group itself and keep the logs forever.
resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${var.name}"
  retention_in_days = var.log_retention_days
}

# --- Where the reports go -----------------------------------------------------
resource "aws_s3_bucket" "reports" {
  bucket        = local.bucket_name
  force_destroy = true # so "terraform destroy" works even when reports are inside
}

resource "aws_s3_bucket_public_access_block" "reports" {
  bucket                  = aws_s3_bucket.reports.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "reports" {
  bucket = aws_s3_bucket.reports.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "reports" {
  bucket = aws_s3_bucket.reports.id

  rule {
    id     = "expire-old-reports"
    status = "Enabled"

    filter {}

    expiration {
      days = var.report_retention_days
    }
  }
}

# --- The schedule -------------------------------------------------------------
resource "aws_cloudwatch_event_rule" "schedule" {
  name                = "${var.name}-schedule"
  description         = "Runs the idle resource finder on a schedule."
  schedule_expression = var.schedule
}

resource "aws_cloudwatch_event_target" "finder" {
  rule = aws_cloudwatch_event_rule.schedule.name
  arn  = aws_lambda_function.finder.arn
}

resource "aws_lambda_permission" "allow_schedule" {
  statement_id  = "AllowEventBridgeInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.finder.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.schedule.arn
}
