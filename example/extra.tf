data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

terraform {
  required_version = "~> 1.0"
  required_providers {
    archive = {
      source  = "hashicorp/archive"
      version = ">= 2.0, < 3.0"
    }

    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0, < 7.0"
    }
  }
}
