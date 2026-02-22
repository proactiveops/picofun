"""Minimal CDK app demonstrating the PicoFun-generated construct."""

import aws_cdk as cdk  # noqa: I001 RUF100 Make ruff happy dunno why it needs this. Giving up!
from constructs import Construct

from output.construct import (
    PetstoreFunctions,
)


class PetstoreStack(cdk.Stack):
    """Stack that deploys the Petstore Lambda functions."""

    def __init__(self, scope: Construct, construct_id: str, **kwargs: dict) -> None:
        """Create the Petstore stack."""
        super().__init__(scope, construct_id, **kwargs)

        petstore = PetstoreFunctions(self, "PetstoreFunctions")

        # Access individual Lambda functions for Step Functions wiring
        for name, fn in petstore.functions.items():
            cdk.CfnOutput(self, f"Fn{name}", value=fn.function_arn)

        cdk.CfnOutput(self, "RoleArn", value=petstore.role.role_arn)


app = cdk.App()
PetstoreStack(app, "PetstoreLambdas")
app.synth()
