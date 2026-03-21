# Meraki CDK Example

This example PicoFun project demonstrates generating an AWS CDK Construct for the [Cisco Meraki Dashboard API](https://developer.cisco.com/meraki/api-v1/) using a [Swagger 2.0 spec](https://raw.githubusercontent.com/meraki/openapi/refs/heads/master/openapi/spec2.json).

The Meraki API uses API key authentication via the `X-Cisco-Meraki-API-Key` header. PicoFun auto-detects this from the spec and generates the necessary auth hooks.

## Generating the CDK Construct

To generate the Lambda functions and CDK construct, run:

```sh
picofun --config-file examples/swagger-meraki/picofun.toml meraki https://raw.githubusercontent.com/meraki/openapi/refs/heads/master/openapi/spec2.json
```

This produces:
- `output/construct.py` — an L3 CDK Construct class
- `output/lambdas/` — generated Lambda function files
- `output/layer/` — Lambda layer code (including auth hooks)

## Project Setup

Install dependencies with `uv`:

```sh
cd examples/swagger-meraki
uv sync
```

## Deployment

Synthesize the CloudFormation template:

```sh
cdk synth
```

Deploy:

```sh
cdk deploy
```

## Using the Construct

The generated construct exposes a `functions` property (a `dict[str, lambda_.Function]`) for wiring into Step Functions or other CDK constructs:

```python
from output.construct import MerakiFunctions

meraki = MerakiFunctions(self, "MerakiFunctions")

# Wire a specific function into a Step Function task
get_device_task = sfn_tasks.LambdaInvoke(
    self, "GetDevice",
    lambda_function=meraki.functions["get_devices_serial"],
)
```

The construct also exposes a `role` property for the shared IAM role.
