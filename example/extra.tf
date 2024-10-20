data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

data "aws_iam_policy_document" "ssm_read" {
  statement {
    sid       = "SSMRead"
    effect    = "Allow"
    resources = ["arn:aws:ssm:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:parameter/picorun_zendesk/*"]

    actions = [
      "ssm:GetParameter",
      "ssm:GetParametersByPath",
      "ssm:GetParameters",
    ]
  }
}

resource "aws_iam_policy" "ssm_read" {
  name        = "pf-zendesk-ssm-read"
  description = "Allow reading of SSM parameters"
  policy      = data.aws_iam_policy_document.ssm_read.json
}

resource "aws_iam_role_policy_attachment" "ssm_read" {
  role       = aws_iam_role.lambda.name
  policy_arn = aws_iam_policy.ssm_read.arn
}

data "aws_vpc_endpoint" "cloudwatch" {
  service_name = "com.amazonaws.us-east-1.logs"
}

# I was lazy when I set this up so all my VPCendpoints are in the same security group.
# This is a bad idea! For real workloads you should have a security group per VPC endpoint.
resource "aws_vpc_security_group_egress_rule" "lambda_to_cloudwatch" {
  for_each = toset(data.aws_vpc_endpoint.cloudwatch.security_group_ids)

  security_group_id = aws_security_group.lambda.id

  referenced_security_group_id = each.value

  from_port   = 443
  ip_protocol = "tcp"
  to_port     = 443
}

resource "aws_vpc_security_group_ingress_rule" "lambda_to_cloudwatch" {
  for_each = toset(data.aws_vpc_endpoint.cloudwatch.security_group_ids)

  security_group_id = each.value

  referenced_security_group_id = aws_security_group.lambda.id

  from_port   = 443
  ip_protocol = "tcp"
  to_port     = 443
}

resource "aws_vpc_security_group_egress_rule" "zendesk" {
  # See https://developer.zendesk.com/api-reference/ticketing/account-configuration/public_ips/
  # for getting thses IPs. I used `curl -q 'https://[my-subdomain].zendesk.com/ips' | jq -r '.ips.ingress.all | sort'`
  # to generate the list.
  for_each = toset([
    "104.18.172.234/32",
    "104.18.173.234/32",
    "104.18.248.37/32",
    "104.18.249.37/32",
    "104.18.70.113/32",
    "104.18.71.113/32",
    "104.18.72.113/32",
    "104.18.73.113/32",
    "104.18.74.113/32",
    "162.159.128.7/32",
    "162.159.138.6/32",
    "216.198.0.0/18",
  ])

  security_group_id = aws_security_group.lambda.id

  cidr_ipv4   = each.value
  from_port   = 443
  ip_protocol = "tcp"
  to_port     = 443
}

terraform {
  required_version = "~> 1.0"
  required_providers {
    archive = {
      source  = "hashicorp/archive"
      version = ">= 2.0, < 3.0"
    }
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0, < 6.0"
    }
    null = {
      source  = "hashicorp/null"
      version = ">= 3.0, < 4.0"
    }
  }
}
