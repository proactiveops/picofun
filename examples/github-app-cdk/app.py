"""CDK app for GitHub App authenticated API Lambdas with token rotation."""

__author__ = "Dave Hall <skwashd@gmail.com>"
__copyright__ = "Copyright 2024 - 2026, Dave Hall https://proactiveops.io"
__license__ = "MIT"

import aws_cdk as cdk  # noqa: I001
from aws_cdk import (
    Duration,
    aws_events as events,
    aws_events_targets as targets,
    aws_lambda as lambda_,
    aws_secretsmanager as secretsmanager,
)
from constructs import Construct

from output.construct import (
    GithubappFunctions,
)

SECRET_PREFIX = "picofun/githubapp"  # noqa: S105


class GitHubAppStack(cdk.Stack):
    """Stack deploying GitHub App authenticated Lambda functions with token rotation."""

    def __init__(self, scope: Construct, construct_id: str, **kwargs: dict) -> None:
        """Create the GitHub App stack."""
        super().__init__(scope, construct_id, **kwargs)

        # Secrets Manager secrets with placeholder values
        app_credentials_secret = secretsmanager.Secret(
            self,
            "AppCredentialsSecret",
            secret_name=f"{SECRET_PREFIX}/app-credentials",
            secret_string_value=cdk.SecretValue.unsafe_plain_text(
                '{"private_key": "REPLACE", "app_id": "REPLACE", "installation_id": "REPLACE"}'
            ),
        )

        token_secret = secretsmanager.Secret(
            self,
            "TokenSecret",
            secret_name=f"{SECRET_PREFIX}/token",
            secret_string_value=cdk.SecretValue.unsafe_plain_text(
                "REPLACE_AFTER_FIRST_ROTATION"
            ),
        )

        # PicoFun-generated construct for GitHub API Lambdas
        github_api = GithubappFunctions(self, "GithubappFunctions")

        # Grant API Lambdas read access to the installation token
        for fn in github_api.functions.values():
            token_secret.grant_read(fn)

        # Rotation Lambda
        rotation_fn = lambda_.Function(
            self,
            "TokenRotationFunction",
            runtime=lambda_.Runtime.PYTHON_3_13,
            architecture=lambda_.Architecture.ARM_64,
            handler="handler.handler",
            code=lambda_.Code.from_asset(
                "rotation",
                bundling=cdk.BundlingOptions(
                    image=lambda_.Runtime.PYTHON_3_13.bundling_image,
                    platform="linux/arm64",
                    command=[
                        "bash",
                        "-c",
                        "export UV_CACHE_DIR=/tmp/uv-cache"
                        " && pip install uv"
                        " && uv pip install --target /asset-output ."
                        " && cp handler.py /asset-output/",
                    ],
                ),
            ),
            timeout=Duration.seconds(10),
            memory_size=128,
        )

        # Rotation Lambda IAM permissions
        app_credentials_secret.grant_read(rotation_fn)
        token_secret.grant_read(rotation_fn)
        token_secret.grant_write(rotation_fn)

        # EventBridge rule for 30-minute token rotation schedule
        events.Rule(
            self,
            "TokenRotationSchedule",
            schedule=events.Schedule.rate(Duration.minutes(30)),
            targets=[
                targets.LambdaFunction(
                    rotation_fn,
                    retry_attempts=5,
                    max_event_age=Duration.minutes(3),
                )
            ],
        )

        # Outputs
        for name, fn in github_api.functions.items():
            cdk.CfnOutput(self, f"Fn{name}", value=fn.function_arn)

        cdk.CfnOutput(self, "RoleArn", value=github_api.role.role_arn)
        cdk.CfnOutput(self, "RotationFunctionArn", value=rotation_fn.function_arn)


app = cdk.App()
GitHubAppStack(app, "GitHubAppLambdas")
app.synth()
