# Zendesk Example

This example PicoFun project demonstrates generating Lambdas for the [Zendesk Ticketing API](https://developer.zendesk.com/api-reference/ticketing/introduction/).

## Generating Lambdas

To generate the Lambda functions and associated Terraform, you can run the following commmand:

```sh
picofun --config-file example/picofun.toml zendesk https://developer.zendesk.com/zendesk/oas.yaml
```
The output of the command should look something like this:

```
INFO:picofun.cli:Selected security scheme: basicAuth (http)
INFO:picofun.layer:Prepared layer contents: /path/to/output/layer
INFO:picofun.cli:Generated authentication hooks: /path/to/output/layer/auth_hooks.py
INFO:picofun.lambda_generator:Generated function: /path/to/output/lambdas/post_api_v2_tickets.py
[...]
INFO:picofun.lambda_generator:Generated function: /path/to/output/lambdas/get_api_v2_users_user_id.py
INFO:picofun.terraform_generator:Generated terraform: /path/to/output/main.tf
```

## Deployment

Before we deploy all of our Lambda functions we need to copy `extra.tf` to `output/` so we have the additional policy attached to the Lambdas execution role. This allows it to read the SSM params we created earlier. To do this, run:

```sh
cp example/extra.tf output
```

To run the deployment we need to change into the output directory by running:

```sh
cd output
```

Now we need to install the Terraform dependencies. We do that by running the following command:

```sh
terraform init
```

If you wish to restrict the versions of Terraform or the providers used, create a `providers.tf` file. Include the versions you wish to use. Copy this file into the output directory before runing `init`.

I assume you have your AWS credentials properly configured. If not, [do that now](https://registry.terraform.io/providers/hashicorp/aws/latest/docs#authentication-and-configuration).

**Finally** we're ready to deploy our Lambdas. To do this, run:

```sh
terraform apply
```

It will take a bit to calculate the change set. Wait for the confirmation prompt:

```
Do you want to perform these actions?
  Terraform will perform the actions described above.
  Only 'yes' will be accepted to approve.

  Enter a value:
```

Review scrollback to ensure everything looks in order. When you're confident things look ok, type `yes` and hit [enter]. Go make a cup of tea, then bake a cake, make another cup of tea, eat the cake, drink both cups of tea, and then your lambda should have deployed.

## Credentials

The project depends on credentials being available in [SSM Parameter Store](https://www.davehall.com.au/blog/2021/02/22/parameter-store-vs-secrets-manager/). The pipeline creates the parameter, but you will need to update it after deploying the project.

### `/picorun/zendesk/credentials-http`

These are the credentials used to access your Zendesk instance. *These are sensitive values, so you must encrypt them.** Set the type to `SecureString`. 

The IAM policy assumes that you're using the AWS managed key `alias/aws/ssm`. You can use a Customer Managed Key for encrypting the creds, but if you do so you will need to adjust override the template to adjust the policy.

Set the value to `{"email":"[email]","token":"[token]"}`. Replace `[email]` with the email address of the agent or administrator who the Lambdas will act on behalf of. Use your [Zendesk API token](https://support.zendesk.com/hc/en-us/articles/4408889192858-Managing-access-to-the-Zendesk-API#topic_bsw_lfg_mmb) instead of `[token]`.

If my agent email address was user.name@example.com the JSON would look like so:

```json
{
  "username": "user.name@example.com/token",
  "password": "get_your_own_api_token_using_the_docs_linked_above"
}
```

This is a once off action.

## GitHub Action

There is a full GitHub Actions deployment pipeline included in the project. It is designed to update the deployment once a week or when code is pushed to the main branch.

To use the workflow you must create a repository level environment variable `AWS_ROLE_ARN` and set the value to the ARN of the role that will perform the deployments. Follow the [AWS documentation for setting up the role using OIDC](https://aws.amazon.com/blogs/security/use-iam-roles-to-connect-github-actions-to-actions-in-aws/).

The role must have access to manage IAM roles and policies, lambda functions, and CloudWatch log groups along with the ability to read and write to the Terraform backend resources.

The workflow also needs a backend defined. Add a file called `backend.tf` with the following contents:

```hcl
terraform {
  backend "s3" {
    region = "us-east-1"
    bucket = "your-state-bucket" # Change to a bucket in your account
    key    = "picofun-zendesk/terraform.tfstate"
    dynamodb_table = "terraform-lock" # Make sure this table exists
  }
}
```

For more information on the configuration, [refer to the Terraform S3 backend documentation](https://developer.hashicorp.com/terraform/language/backend/s3).