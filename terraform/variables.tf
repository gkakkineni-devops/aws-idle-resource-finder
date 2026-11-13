variable "region" {
  description = "AWS region to deploy to and to scan."
  type        = string
  default     = "us-east-1"
}

variable "name" {
  description = "Name used for the function, role, rule and log group."
  type        = string
  default     = "idle-resource-finder"
}

variable "schedule" {
  description = "When the finder runs, as an EventBridge cron expression (UTC). Default: Mondays at 13:00."
  type        = string
  default     = "cron(0 13 ? * MON *)"
}

variable "max_snapshot_age_days" {
  description = "Snapshots older than this many days are reported."
  type        = number
  default     = 90
}

variable "required_tags" {
  description = "Instances missing any of these tags are reported."
  type        = list(string)
  default     = ["owner", "project"]
}

variable "log_retention_days" {
  description = "How long CloudWatch keeps the function logs."
  type        = number
  default     = 14
}

variable "report_retention_days" {
  description = "How long reports stay in S3 before they are deleted."
  type        = number
  default     = 90
}
