# PicoFun

*There's little fun in writing boilerplate*

PicoFun is a tool for generating Python based clients for OpenAPI spec files. The client for each endpoint is packaged as an AWS Lambda function. A terraform module is also generated to deploy the clients to AWS. The generated functions are designed to be be invoked using Step Functions or the Lambda Invoke API.

**PicoFun only supports OpenAPI version 3 spec files.** Swagger files and versions of OpenAPI prior to 3 are not supported.

## Installation

PicoFun can be installed using `uv`, but it is recommended to use `uvx`. This is particularly useful in a CI/CD pipeline. Invoke PicoFun with `uvx` like this:

```bash
uvx picofun [ARGS]
```

If you need to install `uv`/`uvx`, please [refer to the documention](https://docs.astral.sh/uv/getting-started/installation/).

## Configuration

PicoFun is configured using a TOML file. The default configuration file is `picofun.toml` in the current working directory. An alternative location for the configuration file can be specified using the optional `--config` argument.

The configuration file has the following structure:

```toml
bundle="/path/containing/code/to/bundle/into/build" # default is none
iam_role_prefix="my-prefix-" # default is "pf-" for PicoFun
include_endpoints="include-endpoints.yaml" # default is none, generates all endpoints if omitted
layers=[ # default is none, but if AWS Powertools isn't present it is added
  "arn:aws:lambda:us-east-1:012345678910:layer:example:1",
  "arn:aws:lambda:us-east-1:012345678910:layer:another-example:123"
]
output_dir="/path/to/write/output-files" # default is current-working-directory/output
postprocessor="fully.qualified.reference.to.postprocessor" # default is none
preprocessor="fully.qualified.reference.to.preprocessor" # default is none
role_permissions_boundary="arn:aws:iam::012345678910:policy/..." # default is none
subnets=[ # default is none. Must be set if vpc_id is set
  "subnet-1234567890abcdef0",
  "subnet-234567890abcdef01"
]
template_path="/path/to/templates" # default is current-working-directory/templates
xray_tracing=false # default is to enable xray tracing, set this to false to turn it off
vpc_id = "vpc-0011223344556677f" # Default is none. Must be set if using subnets

[auth]
enabled=true # default is true. Set to false to disable automatic authentication
ttl_minutes=5 # default is 5 minutes. TTL for caching credentials in Lambda memory

[server] # Optional: Override or customize server URLs from OpenAPI spec
url = "https://api.example.com" # Full URL override (mutually exclusive with variables)
# OR
variables = { subdomain = "api", version = "v2" } # Override server URL variables

[tags] # defaults to none
key="value"
anotherKey="some other value"
```

### Server URL Configuration

Some OpenAPI specs define server URLs with variables (e.g., `https://{subdomain}.example.com/api/{version}`). The `[server]` block allows you to:

1. **Override the entire server URL**: Use `url` to replace the spec's server URL completely
2. **Customize server variables**: Use `variables` to provide or override default values for tokenized URLs

**Note**: `url` and `variables` are mutually exclusive. You must use one or the other, not both.

**Examples**:

```toml
# Override the entire server URL
[server]
url = "https://production.api.example.com"
```

```toml
# Override specific variables in a tokenized URL
# If spec has: https://{environment}.example.com/api/{version}
[server]
variables = { environment = "staging", version = "v2" }
```

Server variables from the config override any defaults in the spec. Variables without defaults (in either spec or config) trigger a fatal error.
```

## Usage

PicoFun is invoked using the `picofun` command. The minimum arguments required to invoke PicoFun are the project namespace and the OpenAPI spec file. The project namespace is used to generate the names of the generated functions and the terraform module. The OpenAPI spec file is used to generate the clients.

Here is a minimal example:

```bash

uv -m picofun example https://raw.githubusercontent.com/OAI/OpenAPI-Specification/main/examples/v3.0/api-with-examples.json

```

This will create a directory called `output` in the current working directory. The directory will contain the generated functions and the terraform module. The terraform module is in the root directory of `output/`. The generated functions are in the `lambdas` sub directory and the code for lambda layer is in the `layer` sub directory.

While the `config.toml` file is the preferred way to manage the configuration for the project, there are times when it is useful to override the configuration file. The following arguments can be used to override the configuration file:

```
  --config-file  # Full path to the alternate configuration file
  --output-dir   # Directory to output the generated files
  --layers       # Comma separated list of Lambda layer ARNs to include in the function configuration
  --bundle       # Path to code to bundle into a layer. If requirements.txt present pip install will be run.
  --server-url   # Override server URL in the spec. Ignores any [server] config in picofun.toml
```

Here is an example of overriding the configuration file:

```bash

uv -m picofun --config ~/picofun-example.toml example example.json

```

Commonly the layers argument is used to provide different layer ARNs based on the target environment, region and AWS account. Here is an example of overriding the layers argument:

```bash

uv -m picofun --layers "arn:aws:lambda:us-east-1:012345678912:layer:example:1,arn:aws:lambda:us-east-1:012345678912:layer:another-example:123" example example.yaml

```

The `--server-url` overrides the default server url. This can help with testing different environments.

```bash

uv -m picofun --server-url "https://staging-api.example.com" example example.yaml

```

**Note**: When `--server-url` is provided, it takes precedence over any `[server]` configuration in `picofun.toml`.

## Bundle

PicoFun supports bundling code into a Lambda layer. The code to bundle is specified using the `bundle` entry in the configuration file or the `--bundle` argument on the command line. If a `requirements.txt` file is present in the bundle directory, `pip install` will be run by terraform before creating the layer.

The most common use case for using code bundles is to include pre and post processors.

## Endpoint Filtering

By default, PicoFun generates Lambda functions for all endpoints in the OpenAPI spec. To generate functions for only specific endpoints, create an allowlist file and reference it in your configuration.

Add to `picofun.toml`:

```toml
include_endpoints = "include-endpoints.yaml"
```

Create `include-endpoints.yaml`:

```yaml
# Include endpoints matching any of these paths
# Supports trailing wildcards: * (single segment), ** (multiple segments)
paths:
  - path: /users
    methods: [get, post]  # Optional: if omitted, all methods allowed
  - path: /orders/*
  - path: /products/**

# Include endpoints with these operationIds
operationIds:
  - getUser
  - createOrder

# Include endpoints with any of these tags
tags:
  - public
  - v2
```

Endpoints are included if they match ANY of the criteria (OR logic). If `include_endpoints` is not specified, all endpoints are generated.

The path patterns support two types of wildcards:
- `*` matches a single path segment (e.g., `/users/*` matches `/users/123` but not `/users/123/orders`)
- `**` matches multiple path segments (e.g., `/users/**` matches `/users/123` and `/users/123/orders`)

When specifying methods for a path, the matching is case-insensitive. If no methods are specified for a path entry, all HTTP methods are allowed for that path.

## Automatic Authentication

PicoFun automatically generates authentication code for APIs that define security schemes in their OpenAPI specifications. This feature eliminates the need to manually write preprocessor hooks for common authentication methods.

### Supported Authentication Methods

PicoFun supports the following OpenAPI security scheme types:

- **HTTP Bearer Token** (`http` with `scheme: bearer`) - Most common for modern APIs
- **HTTP Basic Authentication** (`http` with `scheme: basic`)
- **API Key** (`apiKey`) - Supports header, query parameter, and cookie locations
- **Mutual TLS** (`mutualTLS`) - Client certificate authentication

**Note:** OAuth2 and OpenID Connect are not yet supported and will cause an error if they are the only security schemes defined.

### How It Works

When you run PicoFun on an OpenAPI spec with security schemes:

1. PicoFun extracts all security schemes from the `components.securitySchemes` section
2. Filters to schemes referenced in the global `security` array
3. Selects the highest priority supported scheme (Bearer > Basic > API Key > mTLS)
4. Generates a `preprocessor` function in `output/layer/auth_hooks.py`
5. Creates AWS infrastructure:
   - SSM Parameter (SecureString) to store credentials
   - KMS key for encryption (or uses your provided key)
   - IAM policies for Lambda to access SSM and KMS

### SSM Parameter Naming

Credentials are stored in AWS Systems Manager Parameter Store with this pattern:

```
/picofun/<namespace>/credentials-<scheme-type>
```

Where `<scheme-type>` is:
- `http` for Bearer and Basic auth
- `api-key` for API Key auth
- `mutual-tls` for mutual TLS

Examples:
- `/picofun/myapi/credentials-http`
- `/picofun/zendesk/credentials-api-key`

### Credential Structure

Each authentication type requires specific JSON structure in the SSM parameter:

**Bearer Token:**
```json
{
  "token": "your-bearer-token-here"
}
```

**Basic Authentication:**
```json
{
  "username": "your-username",
  "password": "your-password"
}
```

**API Key:**
```json
{
  "api_key": "your-api-key-value"
}
```

**Mutual TLS:**
```json
{
  "cert": "-----BEGIN CERTIFICATE-----\n...\n-----END CERTIFICATE-----",
  "key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----"
}
```

### Setting Up Credentials

After running `terraform apply`, you must populate the SSM parameter with your actual credentials:

```bash
# Using AWS CLI
aws ssm put-parameter \
  --name "/picofun/myapi/credentials-http" \
  --type "SecureString" \
  --value '{"token":"your-actual-token"}' \
  --overwrite
```

### Configuration Options

Control authentication behavior in `picofun.toml`:

```toml
[auth]
enabled = true        # Set to false to disable automatic authentication
ttl_minutes = 5       # Cache credentials in Lambda memory (default: 5 minutes)
```

**Important:** You cannot use both automatic authentication and a custom `preprocessor`. If you need custom logic, set `auth.enabled = false` and implement your own preprocessor.

### Custom KMS Key

By default, PicoFun creates a new KMS key for encrypting credentials. To use an existing key, pass it as a Terraform variable:

```hcl
module "example_lambdas" {
  source = "./output"
  
  kms_key_arn = "arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012"
}
```

### Environment Variable

The generated Lambda functions include the `PICORUN_CREDENTIALS_TTL` environment variable, which controls how long credentials are cached in memory. This defaults to the `ttl_minutes` value from your config (converted to seconds). You can override this in Terraform:

```hcl
module "example_lambdas" {
  source = "./output"
  
  auth_credentials_ttl = 600  # 10 minutes in seconds
}
```

### Example: API with Bearer Token

OpenAPI spec excerpt:
```yaml
openapi: "3.0.0"
info:
  title: Example API
  version: "1.0"
servers:
  - url: https://api.example.com/v1
components:
  securitySchemes:
    bearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT
security:
  - bearerAuth: []
paths:
  /users:
    get:
      operationId: listUsers
      responses:
        "200":
          description: List of users
```

After running PicoFun:
- `output/layer/auth_hooks.py` contains the authentication preprocessor
- `output/main.tf` includes SSM parameter and IAM policies
- Lambda functions automatically add `Authorization: Bearer <token>` header

## Preprocessing and Postprocessing Requests

Out of the box PicoFun generates Lambda functions that make unauthenticated calls to endpoints. With automatic authentication enabled (the default), PicoFun will generate authentication hooks if your OpenAPI spec defines supported security schemes. For APIs without security schemes or when you need custom logic, you can provide preprocessing and postprocessing hooks to customize the request payload and response.

**Note:** You cannot use both automatic authentication and a custom `preprocessor`. If your OpenAPI spec has security schemes but you need custom preprocessing logic, set `auth.enabled = false` in your configuration file.

The preprocessing and postprocessing hooks allow engineers to customize the request payload and response. Common use cases include:
- Custom authentication not covered by automatic generation
- Request payload transformation
- Response data filtering or transformation
- Custom headers or query parameters

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