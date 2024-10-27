# PicoFun

*There's little fun in writing boilerplate*

PicoFun is a tool for generating Python based clients for OpenAPI spec files. The client for each endpoint is packaged as an AWS Lambda function. A terraform module is also generated to deploy the clients to AWS. The generated functions are designed to be be invoked using Step Functions or the Lambda Invoke API.

**PicoFun only supports OpenAPI version 3 spec files.** Swagger files and versions of OpenAPI prior to 3 are not supported.

## Installation

PicoFun can be installed using `pip`, but it is recommended to use `pipx`. This is particularly useful in a CI/CD pipeline. Invoke PicoFun with `pipx` like this:

```bash
pipx run picofun [ARGS]
```

If you need to install `pipx`, please [refer to the documention](https://pypa.github.io/pipx/).

## Configuration

PicoFun is configured using a TOML file. The default configuration file is `picofun.toml` in the current working directory. An alternative location for the configuration file can be specified using the optional `--config` argument.

The configuration file has the following structure:

```toml
bundle="/path/containing/code/to/bundle/into/build" # default is none
iam_role_prefix="my-prefix-" # default is "pf-" for PicoFun
layers=[ # default is none, but if AWS Powertools isn't present it is added
  "arn:aws:lambda:us-east-1:012345678910:layer:example:1",
  "arn:aws:lambda:us-east-1:012345678910:layer:another-example:123"
]
output_dir="/path/to/write/output-files" # default is current-working-directory/output
postprocessor="fully.qualified.reference.to.postprocessor" # default is none
preprocessor="fully.qualified.reference.to.preprocessor" # default is none
role_permissions_boundary="arn:aws:iam::012345678910:policy/..." # default is none
subnets=[ # default is none. Unless specified VPC networking is not enabled
  "subnet-1234567890abcdef0",
  "subnet-234567890abcdef01"
]
template_path="/path/to/templates" # default is current-working-directory/templates
xray_tracing=false # default is to enable xray tracing, set this to false to turn it off

[tags] # defaults to none
key="value"
anotherKey="some other value"
```

## Usage

PicoFun is invoked using the `picofun` command. The minimum arguments required to invoke PicoFun are the project namespace and the OpenAPI spec file. The project namespace is used to generate the names of the generated functions and the terraform module. The OpenAPI spec file is used to generate the clients.

Here is a minimal example:

```bash

picofun example https://raw.githubusercontent.com/OAI/OpenAPI-Specification/main/examples/v3.0/api-with-examples.json

```

This will create a directory called `output` in the current working directory. The directory will contain the generated functions and the terraform module. The terraform module is in the root directory of `output/`. The generated functions are in the `lambdas` sub directory and the code for lambda layer is in the `layer` sub directory.

While the `config.toml` file is the preferred way to manage the configuration for the project, there are times when it is useful to override the configuration file. The following arguments can be used to override the configuration file:

```
  --config-file  # Full path to the alternate configuration file
  --output-dir   # Directory to output the generated files
  --layers       # Comma separated list of Lambda layer ARNs to include in the function configuration
  --bundle       # Path to code to bundle into a layer. If requirements.txt present pip install will be run.  
```

Here is an example of overriding the configuration file:

```bash

picofun --config ~/picofun-example.toml example example.json

```

Commonly the layers argument is used to provide different layer ARNs based on the target environment, region and AWS account. Here is an example of overriding the layers argument:

```bash

picofun --layers "arn:aws:lambda:us-east-1:012345678912:layer:example:1,arn:aws:lambda:us-east-1:012345678912:layer:another-example:123" example example.yaml

```

## Bundle

PicoFun supports bundling code into a Lambda layer. The code to bundle is specified using the `bundle` entry in the configuration file or the `--bundle` argument on the command line. If a `requirements.txt` file is present in the bundle directory, `pip install` will be run by terraform before creating the layer.

The most common use case for using code bundles is to include pre and post processors.

## Preprocessing and Postprocessing Requests

Out of the box PicoFun generates Lambda functions that make unauthenicated calls to endpoints. Often this isn't what teams need. The preprocessing and postprocessing hooks allow engineers to customize the request payload and response. A common use case for this is to add authentication headers to requests.

An example implementation of these hooks can be found in the [`example/zendesk_common`](example/zendesk_common) directory. The example pulls values from SSM Parameter store and uses them for the domain name and authorization header.

## Template Overrides

The default templates bundled with PicoFun are usually adequate for most use cases. There are times where more customisation is needed. This could be to include custom logic in the Lambda function or additional resources in the terraform module. 

If you need to override one PicoFun template, you need to copy both from the package. The templates are located in the `templates` directory in the PicoFun package.

You can add the path to the templates to the `config.toml` file using the `template_path` entry.

## Terraform

PicoFun generates a terraform module to deploy the generated functions to AWS. The module is located in the root of your configured output directory. It `output`s the Lambda function ARNs and IAM role ARN.

The module can be included in your terraform project like this:

```hcl
module "example_lambdas" {
  source = "/path/to/picofun/output"
}
```