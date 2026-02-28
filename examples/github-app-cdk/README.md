# GitHub App CDK Example

This example PicoFun project demonstrates generating an AWS CDK Construct for the [GitHub REST API](https://docs.github.com/en/rest) with **GitHub App authentication**.

## Architecture

```
                                    ┌──────────────────────┐
                                    │   Secrets Manager    │
                                    │                      │
  ┌──────────────────┐   write      │  picofun/githubapp/  │
  │ Token Rotation   │─────────────▶│    token             │
  │ Lambda           │              │    app-credentials   │
  │ (every 30 min)   │◀─────────────│                      │
  └──────────────────┘   read       └──────────┬───────────┘
                                               │ read token
                                               ▼
                                    ┌──────────────────────┐
                                    │  API Lambdas         │
                                    │  (PicoFun-generated) │
                                    │                      │
                                    │  Preprocessor adds   │
                                    │  Bearer token header │
                                    └──────────┬───────────┘
                                               │
                                               ▼
                                    ┌─────────────────────┐
                                    │  GitHub REST API    │
                                    └─────────────────────┘
```

**Token flow:**
1. A rotation Lambda runs every 30 minutes via an EventBridge schedule
2. It reads the GitHub App credentials from Secrets Manager, generates a JWT, exchanges it for an installation token via the GitHub API, and writes the token back to Secrets Manager
3. API Lambdas read the installation token from Secrets Manager (cached in-memory for 5 minutes) and set the `Authorization: Bearer` header via a preprocessor

## Prerequisites

- [AWS CLI](https://aws.amazon.com/cli/) configured with appropriate credentials
- [AWS CDK CLI](https://docs.aws.amazon.com/cdk/latest/guide/cli.html)
- Python 3.13+
- [uv](https://docs.astral.sh/uv/)
- A [GitHub App](https://docs.github.com/en/apps/creating-github-apps) with:
  - A generated private key (PEM format)
  - The App ID and Installation ID

## Generating the CDK Construct

From the `examples/github-app-cdk/` directory, generate the Lambda functions and CDK construct:

```sh
uv run picofun --config-file examples/github-app-cdk/picofun.toml --output-dir examples/github-app-cdk/output githubapp https://raw.githubusercontent.com/github/rest-api-description/main/descriptions/api.github.com/api.github.com.json
```

This produces:
- `output/construct.py` -- an L3 CDK Construct class (`GithubappFunctions`)
- `output/lambdas/` -- generated Lambda function files
- `output/layer/` -- Lambda layer code (includes the preprocessor from `helpers/`)

## Project Setup

```sh
cd examples/github-app-cdk
uv sync
```

## Deployment

Synthesize the CloudFormation template:

```sh
uv run cdk synth
```

Deploy:

```sh
uv run cdk deploy
```

## Configuring Secrets

After deployment, update the secrets with your GitHub App credentials:

```sh
aws secretsmanager update-secret \
  --secret-id "picofun/githubapp/app-credentials" \
  --secret-string "{\"private_key\": \"$(cat /path/to/your-app.pem)\", \"app_id\": \"YOUR_APP_ID\", \"installation_id\": \"YOUR_INSTALLATION_ID\"}"
```

After configuring the secret, manually invoke the rotation Lambda to generate the first installation token:

```sh
aws lambda invoke \
  --function-name $(aws cloudformation describe-stacks \
    --stack-name GitHubAppLambdas \
    --query 'Stacks[0].Outputs[?OutputKey==`RotationFunctionArn`].OutputValue' \
    --output text) \
  /dev/stdout
```

The EventBridge schedule will then rotate the token every 30 minutes automatically.

## Using the Construct

The generated construct exposes a `functions` property (`dict[str, lambda_.Function]`) for wiring into Step Functions or other CDK constructs:

```python
from output.construct import GithubappFunctions

github_api = GithubappFunctions(self, "GithubappFunctions")

# Wire a specific function into a Step Function task
get_repo_task = sfn_tasks.LambdaInvoke(
    self, "GetRepo",
    lambda_function=github_api.functions["get_repos_owner_repo"],
)
```

The construct also exposes a `role` property for the shared IAM role.

## Invoking a Lambda

Example event payload for getting a repository:

```json
{
  "pathParameters": {
    "owner": "proactiveops",
    "repo": "picofun"
  }
}
```

Invoke via the AWS CLI:

```sh
aws lambda invoke \
  --function-name <function-name-from-stack-outputs> \
  --payload '{"pathParameters": {"owner": "proactiveops", "repo": "picofun"}}' \
  /dev/stdout
```
