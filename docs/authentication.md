# PicoFun Authentication Guide

This guide provides detailed information about PicoFun's automatic authentication feature, including setup instructions, troubleshooting, and advanced usage patterns.

## Overview

PicoFun automatically generates authentication code for APIs that define security schemes in their OpenAPI specifications. This eliminates the need to manually write preprocessor hooks for common authentication methods.

### How It Works

1. **Parsing**: PicoFun reads security schemes from your OpenAPI spec's `components.securitySchemes` section
2. **Selection**: It identifies schemes referenced in the global `security` array and selects the highest priority supported scheme
3. **Code Generation**: Creates a Python preprocessor function that implements the authentication logic
4. **Infrastructure**: Generates Terraform resources for storing and accessing credentials securely
5. **Runtime**: Lambda functions automatically authenticate requests using cached credentials from SSM Parameter Store

### Architecture

```
OpenAPI Spec → PicoFun
                 ↓
           [Parsing & Selection]
                 ↓
        ┌────────┴────────┐
        ↓                 ↓
   auth_hooks.py      main.tf
   (preprocessor)    (SSM + KMS + IAM)
        ↓                 ↓
    Lambda Layer    Terraform Apply
        ↓                 ↓
   Lambda Function → SSM Parameter
        ↓                 ↓
   API Request      (credentials)
```

## Supported Authentication Methods

### Priority Order

When multiple security schemes are defined, PicoFun selects one based on this priority:

1. **HTTP Bearer** (`http` with `scheme: bearer`) - JWT, OAuth tokens
2. **HTTP Basic** (`http` with `scheme: basic`) - Username/password
3. **API Key in Header** (`apiKey` with `in: header`)
4. **API Key in Query** (`apiKey` with `in: query`)
5. **API Key in Cookie** (`apiKey` with `in: cookie`)
6. **Mutual TLS** (`mutualTLS`) - Client certificates

### Unsupported Schemes

- **OAuth2 flows** (authorization code, client credentials, etc.)
- **OpenID Connect**

If your spec only contains unsupported schemes, PicoFun will exit with an error. You'll need to use a custom preprocessor for these cases.

## Step-by-Step Setup

### 1. Prepare Your OpenAPI Spec

Ensure your OpenAPI spec defines security schemes. Example:

```yaml
openapi: "3.0.0"
info:
  title: My API
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
      operationId: getUsers
      responses:
        "200":
          description: Success
```

### 2. Configure PicoFun (Optional)

Create or update `picofun.toml`:

```toml
[auth]
enabled = true        # Default: true
ttl_minutes = 5       # Default: 5 minutes
```

### 3. Generate Code

Run PicoFun:

```bash
uvx picofun myapi spec.yaml
```

PicoFun will:
- Log which security scheme was selected
- Generate `output/layer/auth_hooks.py`
- Generate Terraform with SSM parameter and IAM policies

### 4. Review Generated Files

**output/layer/auth_hooks.py:**
```python
"""Auto-generated authentication hooks."""

import os
from aws_lambda_powertools.utilities import parameters

def get_credentials(scheme_type):
    """Retrieve credentials from SSM Parameter Store."""
    ttl = int(os.environ.get("PICORUN_CREDENTIALS_TTL", "300"))
    param_name = f"/picorun/myapi/credentials-{scheme_type}"
    return parameters.get_parameter(param_name, transform="json", max_age=ttl)

def preprocessor(request):
    """Add authentication to the request."""
    creds = get_credentials("http")
    request.headers["Authorization"] = f"Bearer {creds['token']}"
    return request
```

**output/main.tf (excerpt):**
```hcl
resource "aws_ssm_parameter" "credentials" {
  name        = "/picorun/myapi/credentials-http"
  type        = "SecureString"
  key_id      = local.kms_key_arn
  value       = jsonencode({})
  
  lifecycle {
    ignore_changes = [value]
  }
}

resource "aws_kms_key" "this" {
  description             = "KMS key for picorun myapi SSM parameter encryption"
  enable_key_rotation     = true
}
```

### 5. Deploy Infrastructure

```bash
cd output
terraform init
terraform apply
```

### 6. Populate Credentials

After Terraform creates the infrastructure, add your actual credentials:

```bash
# Bearer Token
aws ssm put-parameter \
  --name "/picorun/myapi/credentials-http" \
  --type "SecureString" \
  --value '{"token":"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."}' \
  --overwrite

# Basic Auth
aws ssm put-parameter \
  --name "/picorun/myapi/credentials-http" \
  --type "SecureString" \
  --value '{"username":"admin","password":"secret123"}' \
  --overwrite

# API Key
aws ssm put-parameter \
  --name "/picorun/myapi/credentials-api-key" \
  --type "SecureString" \
  --value '{"api_key":"abc123def456"}' \
  --overwrite

# Mutual TLS
aws ssm put-parameter \
  --name "/picorun/myapi/credentials-mutual-tls" \
  --type "SecureString" \
  --value '{"cert":"-----BEGIN CERTIFICATE-----\n...\n","key":"-----BEGIN PRIVATE KEY-----\n...\n"}' \
  --overwrite
```

### 7. Test Your Lambda

Invoke a Lambda function to test authentication:

```bash
aws lambda invoke \
  --function-name myapi_getUsers \
  --payload '{}' \
  response.json

cat response.json
```

## Advanced Configuration

### Using an Existing KMS Key

Instead of creating a new KMS key, you can use an existing one:

```hcl
module "myapi_lambdas" {
  source = "./output"
  
  kms_key_arn = "arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012"
}
```

### Adjusting Credential Cache TTL

Control how long credentials are cached in Lambda memory:

**Via Configuration (affects default):**
```toml
[auth]
ttl_minutes = 10  # 10 minutes
```

**Via Terraform Variable (per deployment):**
```hcl
module "myapi_lambdas" {
  source = "./output"
  
  auth_credentials_ttl = 600  # 10 minutes in seconds
}
```

**Why caching matters:**
- Reduces SSM API calls (cost savings)
- Improves Lambda performance (fewer network calls)
- Balance between security and performance

### Disabling Automatic Authentication

If your OpenAPI spec has security schemes but you need custom logic:

```toml
[auth]
enabled = false

preprocessor = "my_package.custom_auth.preprocessor"
```

## Credential Rotation

### Manual Rotation

Update the SSM parameter value:

```bash
aws ssm put-parameter \
  --name "/picorun/myapi/credentials-http" \
  --type "SecureString" \
  --value '{"token":"new-token-value"}' \
  --overwrite
```

Lambda functions will pick up the new value after the TTL expires (default 5 minutes).

### Automatic Rotation

For automated credential rotation, consider:

1. **AWS Secrets Manager** (instead of SSM Parameter Store)
   - Native rotation support
   - Requires custom preprocessor (set `auth.enabled = false`)

2. **Scheduled Lambda** to update SSM parameters
   - Rotates credentials periodically
   - Updates both API provider and SSM parameter

## Troubleshooting

### No Security Scheme Found

**Symptom:**
```
WARNING: No supported security scheme found in OpenAPI spec.
Authentication hooks will not be generated.
```

**Causes:**
- OpenAPI spec has no `components.securitySchemes` section
- Security schemes defined but not referenced in global `security` array
- All schemes are unsupported (OAuth2, OpenID Connect)

**Solution:**
- Verify `components.securitySchemes` exists in your spec
- Ensure schemes are referenced in top-level `security: []` array
- If using OAuth2, implement a custom preprocessor

### Only Unsupported Schemes Error

**Symptom:**
```
ERROR: OpenAPI spec contains only unsupported security schemes: oauth2.
Supported schemes: apiKey, http (basic/bearer), mutualTLS.
```

**Solution:**
Use a custom preprocessor for OAuth2/OIDC:

```toml
[auth]
enabled = false

preprocessor = "my_auth.oauth2_handler.preprocessor"
```

### Authentication Not Working

**Symptom:** API returns 401 Unauthorized

**Checklist:**
1. **Credentials populated?**
   ```bash
   aws ssm get-parameter --name "/picorun/myapi/credentials-http" --with-decryption
   ```

2. **Correct JSON structure?**
   - Bearer: `{"token":"..."}`
   - Basic: `{"username":"...","password":"..."}`
   - API Key: `{"api_key":"..."}`

3. **IAM permissions?**
   - Lambda execution role needs `ssm:GetParameter`
   - Lambda execution role needs `kms:Decrypt` on KMS key

4. **Parameter name correct?**
   - Check generated Terraform for exact parameter name
   - Verify namespace matches

5. **Credentials expired?**
   - Tokens may have expiration
   - Check with API provider

### Custom Preprocessor Conflicts

**Symptom:**
```
ERROR: Cannot use both auth_enabled and preprocessor.
Set auth.enabled=false to use a custom preprocessor.
```

**Solution:**
Choose one approach:
- Use automatic authentication (remove `preprocessor` config)
- Use custom preprocessor (set `auth.enabled = false`)

### KMS Encryption Errors

**Symptom:** Lambda can't decrypt SSM parameter

**Solution:**
Ensure Lambda execution role has KMS decrypt permission:

```hcl
# Already included in generated Terraform
data "aws_iam_policy_document" "lambda_auth" {
  statement {
    actions   = ["kms:Decrypt"]
    resources = [local.kms_key_arn]
  }
}
```

### High SSM API Costs

**Symptom:** Unexpected AWS costs from SSM GetParameter calls

**Solution:**
Increase TTL to reduce API calls:

```toml
[auth]
ttl_minutes = 15  # Cache for 15 minutes instead of 5
```

**Note:** Longer TTL means longer delay before rotated credentials take effect.

## Best Practices

### Security

1. **Use KMS encryption** (enabled by default)
2. **Rotate credentials regularly**
3. **Use short-lived tokens** when possible
4. **Monitor SSM parameter access** via CloudTrail
5. **Apply least-privilege IAM** policies

### Performance

1. **Tune TTL** based on your rotation frequency
   - More frequent rotation → shorter TTL
   - Less frequent rotation → longer TTL
2. **Use regional endpoints** for lower latency
3. **Consider credential size** (mTLS certs can be large)

### Operations

1. **Document credential sources** (where to get fresh tokens)
2. **Set up alerts** for authentication failures
3. **Test credential rotation** before production
4. **Include credentials** in disaster recovery plans
5. **Use Terraform workspaces** for multi-environment deployments

## Migration from Custom Preprocessor

If you currently use a custom preprocessor for authentication:

### Before (Custom Preprocessor)

```python
# custom_auth.py
import os
from aws_lambda_powertools.utilities import parameters

def preprocessor(request):
    token = parameters.get_parameter("/myapp/api-token")
    request.headers["Authorization"] = f"Bearer {token}"
    return request
```

```toml
# picofun.toml
preprocessor = "custom_auth.preprocessor"
bundle = "/path/to/custom_auth"
```

### After (Automatic Authentication)

1. Add security scheme to OpenAPI spec:
```yaml
components:
  securitySchemes:
    bearerAuth:
      type: http
      scheme: bearer
security:
  - bearerAuth: []
```

2. Update configuration:
```toml
# picofun.toml
[auth]
enabled = true  # Can omit, true is default

# Remove preprocessor and bundle
```

3. Regenerate:
```bash
uvx picofun myapi spec.yaml
```

4. Migrate SSM parameter:
```bash
# Rename and restructure parameter
aws ssm put-parameter \
  --name "/picorun/myapi/credentials-http" \
  --type "SecureString" \
  --value "{\"token\":\"$(aws ssm get-parameter --name /myapp/api-token --with-decryption --query Parameter.Value --output text)\"}" \
  --overwrite
```

5. Deploy and test

## Examples by Authentication Type

### Bearer Token (JWT)

**OpenAPI Spec:**
```yaml
components:
  securitySchemes:
    jwtAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT
security:
  - jwtAuth: []
```

**SSM Parameter:**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
}
```

**Generated Request:**
```
GET /api/users HTTP/1.1
Host: api.example.com
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Basic Authentication

**OpenAPI Spec:**
```yaml
components:
  securitySchemes:
    basicAuth:
      type: http
      scheme: basic
security:
  - basicAuth: []
```

**SSM Parameter:**
```json
{
  "username": "admin",
  "password": "P@ssw0rd123"
}
```

**Generated Request:**
```
GET /api/users HTTP/1.1
Host: api.example.com
Authorization: Basic YWRtaW46UEBzc3cwcmQxMjM=
```

### API Key in Header

**OpenAPI Spec:**
```yaml
components:
  securitySchemes:
    apiKeyAuth:
      type: apiKey
      in: header
      name: X-API-Key
security:
  - apiKeyAuth: []
```

**SSM Parameter:**
```json
{
  "api_key": "sk_live_abc123def456ghi789"
}
```

**Generated Request:**
```
GET /api/users HTTP/1.1
Host: api.example.com
X-API-Key: sk_live_abc123def456ghi789
```

### API Key in Query Parameter

**OpenAPI Spec:**
```yaml
components:
  securitySchemes:
    apiKeyAuth:
      type: apiKey
      in: query
      name: api_key
security:
  - apiKeyAuth: []
```

**SSM Parameter:**
```json
{
  "api_key": "abc123def456"
}
```

**Generated Request:**
```
GET /api/users?api_key=abc123def456 HTTP/1.1
Host: api.example.com
```

### Mutual TLS

**OpenAPI Spec:**
```yaml
components:
  securitySchemes:
    mtlsAuth:
      type: mutualTLS
security:
  - mtlsAuth: []
```

**SSM Parameter:**
```json
{
  "cert": "-----BEGIN CERTIFICATE-----\nMIIDXTCCAkWgAwIBAgIJAKL...\n-----END CERTIFICATE-----",
  "key": "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w...\n-----END PRIVATE KEY-----"
}
```

**Generated Behavior:**
- Writes cert and key to `/tmp/picorun_cert.pem` and `/tmp/picorun_key.pem`
- Configures requests library to use client certificates

## Further Reading

- [OpenAPI Security Schemes](https://swagger.io/docs/specification/authentication/)
- [AWS Systems Manager Parameter Store](https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-parameter-store.html)
- [AWS Lambda Powertools Parameters](https://docs.powertools.aws.dev/lambda/python/latest/utilities/parameters/)
- [AWS KMS Key Management](https://docs.aws.amazon.com/kms/latest/developerguide/overview.html)
