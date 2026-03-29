"""Minimal CDK app demonstrating the PicoFun-generated construct for the Meraki API."""

import aws_cdk as cdk
from constructs import Construct

from output.construct import (
    MerakiFunctions,
)


class MerakiStack(cdk.Stack):
    """Stack that deploys the Meraki device API Lambda functions."""

    def __init__(self, scope: Construct, construct_id: str, **kwargs: dict) -> None:
        """Create the Meraki stack."""
        super().__init__(scope, construct_id, **kwargs)

        meraki = MerakiFunctions(self, "MerakiFunctions")

        # Access individual Lambda functions for Step Functions wiring
        for name, fn in meraki.functions.items():
            cdk.CfnOutput(self, f"Fn{name}", value=fn.function_arn)

        cdk.CfnOutput(self, "RoleArn", value=meraki.role.role_arn)


app = cdk.App()
MerakiStack(app, "MerakiLambdas")
app.synth()
