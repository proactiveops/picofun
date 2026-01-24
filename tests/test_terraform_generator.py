"""Tests for the TerraformGenerator class."""

import os
import tempfile

import picofun.config
import picofun.template
import picofun.terraform_generator


def test_generate() -> None:
    """Test generating the terraform configuration."""
    config = picofun.config.Config()
    tpl = picofun.template.Template("tests/data/templates")
    with tempfile.TemporaryDirectory() as out_dir:
        config.output_dir = out_dir
        generator = picofun.terraform_generator.TerraformGenerator(tpl, "test", config)
        generator.generate([])


def test_generate_iam_statements_included() -> None:
    """Test that auth IAM statements are present when auth is enabled."""
    config = picofun.config.Config()
    tpl = picofun.template.Template("picofun/templates")
    with tempfile.TemporaryDirectory() as out_dir:
        config.output_dir = out_dir
        generator = picofun.terraform_generator.TerraformGenerator(
            tpl, "testauth", config
        )
        generator.generate(
            ["test_lambda"],
            auth_enabled=True,
            auth_scheme_type="http",
            auth_scheme_name="bearerAuth",
            auth_ttl=300,
        )

        output_file = os.path.join(out_dir, "main.tf")
        with open(output_file) as f:
            content = f.read()

        assert "ssm:GetParameter" in content
        assert "kms:Decrypt" in content
        assert "aws_iam_policy_document" in content
        assert "lambda_auth" in content


def test_generate_iam_statements_excluded() -> None:
    """Test that auth IAM statements are absent when auth is disabled."""
    config = picofun.config.Config()
    tpl = picofun.template.Template("picofun/templates")
    with tempfile.TemporaryDirectory() as out_dir:
        config.output_dir = out_dir
        generator = picofun.terraform_generator.TerraformGenerator(
            tpl, "testnoauth", config
        )
        generator.generate(["test_lambda"], auth_enabled=False)

        output_file = os.path.join(out_dir, "main.tf")
        with open(output_file) as f:
            content = f.read()

        assert "ssm:GetParameter" not in content
        assert "lambda_auth" not in content
        assert "aws_kms_key" not in content


def test_generate_ssm_correct_path() -> None:
    """Test that SSM parameter has correct path pattern."""
    config = picofun.config.Config()
    tpl = picofun.template.Template("picofun/templates")
    with tempfile.TemporaryDirectory() as out_dir:
        config.output_dir = out_dir
        generator = picofun.terraform_generator.TerraformGenerator(
            tpl, "zendesk", config
        )
        generator.generate(
            ["test_lambda"],
            auth_enabled=True,
            auth_scheme_type="api-key",
            auth_scheme_name="apiKeyAuth",
        )

        output_file = os.path.join(out_dir, "main.tf")
        with open(output_file) as f:
            content = f.read()

        assert "/picofun/zendesk/credentials-api-key" in content
        assert "parameter/picofun/zendesk/credentials-*" in content


def test_generate_ssm_secure_string() -> None:
    """Test that SSM parameter type is SecureString."""
    config = picofun.config.Config()
    tpl = picofun.template.Template("picofun/templates")
    with tempfile.TemporaryDirectory() as out_dir:
        config.output_dir = out_dir
        generator = picofun.terraform_generator.TerraformGenerator(
            tpl, "testauth", config
        )
        generator.generate(
            ["test_lambda"],
            auth_enabled=True,
            auth_scheme_type="http",
            auth_scheme_name="bearerAuth",
        )

        output_file = os.path.join(out_dir, "main.tf")
        with open(output_file) as f:
            content = f.read()

        assert 'type        = "SecureString"' in content
        assert "ignore_changes = [value]" in content


def test_generate_kms_conditional() -> None:
    """Test that KMS key is created conditionally."""
    config = picofun.config.Config()
    tpl = picofun.template.Template("picofun/templates")
    with tempfile.TemporaryDirectory() as out_dir:
        config.output_dir = out_dir
        generator = picofun.terraform_generator.TerraformGenerator(
            tpl, "testauth", config
        )
        generator.generate(
            ["test_lambda"],
            auth_enabled=True,
            auth_scheme_type="http",
            auth_scheme_name="bearerAuth",
        )

        output_file = os.path.join(out_dir, "main.tf")
        with open(output_file) as f:
            content = f.read()

        assert "aws_kms_key" in content
        assert "count = var.kms_key_arn == null ? 1 : 0" in content
        assert "count = var.kms_key_arn != null ? 1 : 0" in content
        assert "data.aws_kms_key.existing" in content
        assert "alias/picorun-testauth" in content


def test_generate_variables_kms_optional() -> None:
    """Test that kms_key_arn variable has default null."""
    config = picofun.config.Config()
    tpl = picofun.template.Template("picofun/templates")
    with tempfile.TemporaryDirectory() as out_dir:
        config.output_dir = out_dir
        generator = picofun.terraform_generator.TerraformGenerator(
            tpl, "testauth", config
        )
        generator.generate(
            ["test_lambda"],
            auth_enabled=True,
            auth_scheme_type="http",
            auth_scheme_name="bearerAuth",
        )

        output_file = os.path.join(out_dir, "main.tf")
        with open(output_file) as f:
            content = f.read()

        assert 'variable "kms_key_arn"' in content
        assert "default     = null" in content


def test_generate_lambda_env_ttl() -> None:
    """Test that Lambda has PICORUN_CREDENTIALS_TTL env var."""
    config = picofun.config.Config()
    tpl = picofun.template.Template("picofun/templates")
    with tempfile.TemporaryDirectory() as out_dir:
        config.output_dir = out_dir
        generator = picofun.terraform_generator.TerraformGenerator(
            tpl, "testauth", config
        )
        generator.generate(
            ["test_lambda"],
            auth_enabled=True,
            auth_scheme_type="http",
            auth_scheme_name="bearerAuth",
            auth_ttl=600,
        )

        output_file = os.path.join(out_dir, "main.tf")
        with open(output_file) as f:
            content = f.read()

        assert "PICORUN_CREDENTIALS_TTL" in content
        assert "var.auth_credentials_ttl" in content
        assert "default     = 600" in content


def test_generate_auth_credentials_ttl_variable() -> None:
    """Test that auth_credentials_ttl variable is created with correct default."""
    config = picofun.config.Config()
    tpl = picofun.template.Template("picofun/templates")
    with tempfile.TemporaryDirectory() as out_dir:
        config.output_dir = out_dir
        generator = picofun.terraform_generator.TerraformGenerator(
            tpl, "testauth", config
        )
        generator.generate(
            ["test_lambda"],
            auth_enabled=True,
            auth_scheme_type="http",
            auth_scheme_name="bearerAuth",
            auth_ttl=300,
        )

        output_file = os.path.join(out_dir, "main.tf")
        with open(output_file) as f:
            content = f.read()

        assert 'variable "auth_credentials_ttl"' in content
        assert "default     = 300" in content
