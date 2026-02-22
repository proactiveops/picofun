# CDK Example

This example PicoFun project demonstrates generating an AWS CDK Construct for the [Petstore API](https://petstore3.swagger.io/).

## Generating the CDK Construct

To generate the Lambda functions and CDK construct, run:

```sh
picofun --config-file examples/cdk/picofun.toml petstore https://petstore3.swagger.io/api/v3/openapi.json
```

This produces:
- `output/construct.py` — an L3 CDK Construct class
- `output/lambdas/` — generated Lambda function files
- `output/layer/` — Lambda layer code

## Project Setup

Install dependencies with `uv`:

```sh
cd examples/cdk
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
from output.construct import PetstoreFunctions

petstore = PetstoreFunctions(self, "PetstoreFunctions")

# Wire a specific function into a Step Function task
get_pet_task = sfn_tasks.LambdaInvoke(
    self, "GetPet",
    lambda_function=petstore.functions["get_pet_pet_id"],
)
```

The construct also exposes a `role` property for the shared IAM role.
