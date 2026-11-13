output "function_name" {
  description = "Name of the Lambda function."
  value       = aws_lambda_function.finder.function_name
}

output "report_bucket" {
  description = "S3 bucket where the reports are written."
  value       = aws_s3_bucket.reports.bucket
}

output "schedule" {
  description = "When the finder runs."
  value       = var.schedule
}
