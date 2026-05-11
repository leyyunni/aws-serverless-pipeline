variable "aws_region" {
  description = "AWS region to deploy resources"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project name used to prefix all resource names"
  type        = string
  default     = "federal-spending"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "prod"
}

variable "lambda_memory_mb" {
  description = "Memory allocated to the Lambda function (MB)"
  type        = number
  default     = 256
}

variable "lambda_timeout_seconds" {
  description = "Lambda function timeout in seconds"
  type        = number
  default     = 60
}
