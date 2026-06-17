terraform {
  required_version = ">= 1.3.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    null = {
      source  = "hashicorp/null"
      version = "~> 3.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

resource "aws_iam_role" "lambda_exec" {
  name = "${var.project_name}-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_s3_bucket" "repo_output" {
  bucket = "${var.project_name}-${var.aws_region}-repo-output"
}

resource "aws_s3_bucket_public_access_block" "repo_output_block" {
  bucket = aws_s3_bucket.repo_output.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_iam_policy" "lambda_s3_access" {
  name = "${var.project_name}-lambda-s3-access"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject"
        ]
        Resource = [
          "${aws_s3_bucket.repo_output.arn}/*"
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_s3_access" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = aws_iam_policy.lambda_s3_access.arn
}

resource "null_resource" "build_lambda_package" {
  triggers = {
    always_run = timestamp()
  }

  provisioner "local-exec" {
    command = "bash ../lambda/build_package.sh"
  }
}

resource "aws_lambda_function" "repo_analyzer" {
  function_name    = "${var.project_name}-repo-analyzer"
  role             = aws_iam_role.lambda_exec.arn
  runtime          = "python3.11"
  handler          = "lambda_function.lambda_handler"
  timeout          = 300
  memory_size      = 512
  filename         = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256

  environment {
    variables = {
      GITHUB_ORG     = var.github_org
      GITHUB_TOKEN   = var.github_token
      OUTPUT_FILE    = "/tmp/repositories.json"
      RECENT_MONTHS  = var.recent_months
      S3_BUCKET_NAME = aws_s3_bucket.repo_output.bucket
      S3_BUCKET_KEY  = "reports/repositories.json"
    }
  }

  depends_on = [null_resource.build_lambda_package]
}

resource "aws_cloudwatch_log_group" "lambda_logs" {
  name              = "/aws/lambda/${aws_lambda_function.repo_analyzer.function_name}"
  retention_in_days = 14
}

resource "aws_cloudwatch_event_rule" "weekly_schedule" {
  name                = "${var.project_name}-weekly-schedule"
  description         = "Run the GitHub repository analyzer weekly"
  schedule_expression = "cron(0 3 ? * SUN *)"
}

resource "aws_cloudwatch_event_target" "weekly_target" {
  rule      = aws_cloudwatch_event_rule.weekly_schedule.name
  target_id = "lambda"
  arn       = aws_lambda_function.repo_analyzer.arn
}

resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.repo_analyzer.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.weekly_schedule.arn
}

data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../lambda/package"
  output_path = "${path.module}/../.terraform/lambda.zip"

  depends_on = [null_resource.build_lambda_package]
}

variable "aws_region" {
  description = "AWS region for the infrastructure"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project name used for AWS resource naming"
  type        = string
  default     = "git-analizer"
}

variable "github_org" {
  description = "GitHub organization or user to analyze"
  type        = string
}

variable "github_token" {
  description = "GitHub API token stored in Terraform variables or secrets"
  type        = string
  sensitive   = true
}

variable "recent_months" {
  description = "Number of months to use for the update cutoff"
  type        = number
  default     = 3
}

output "lambda_function_name" {
  value = aws_lambda_function.repo_analyzer.function_name
}

output "schedule_rule" {
  value = aws_cloudwatch_event_rule.weekly_schedule.name
}
