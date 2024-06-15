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
