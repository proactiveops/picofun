"""Tests for the CdkGenerator class."""

__author__ = "Dave Hall <skwashd@gmail.com>"
__copyright__ = "Copyright 2023 - 2026, Dave Hall https://proactiveops.io"
__license__ = "MIT"

import os
import tempfile

import picofun.config
import picofun.iac.cdk
import picofun.template


def test_generate() -> None:
    """Test generating the CDK construct."""
    config = picofun.config.Config()
    tpl = picofun.template.Template("tests/data/templates")
    with tempfile.TemporaryDirectory() as out_dir:
        config.output_dir = out_dir
        generator = picofun.iac.cdk.CdkGenerator(tpl, "test", config)
        generator.generate([])

        output_file = os.path.join(out_dir, "construct.py")
        assert os.path.exists(output_file)


def test_generate_contains_construct_class() -> None:
    """Test that output contains Construct class with correct name."""
    config = picofun.config.Config()
    tpl = picofun.template.Template("picofun/templates")
    with tempfile.TemporaryDirectory() as out_dir:
        config.output_dir = out_dir
        generator = picofun.iac.cdk.CdkGenerator(tpl, "testns", config)
        generator.generate(["get_users"])

        output_file = os.path.join(out_dir, "construct.py")
        with open(output_file) as f:
            content = f.read()

        assert "class TestnsFunctions(Construct):" in content


def test_generate_lambda_functions() -> None:
    """Test that function names appear in output."""
    config = picofun.config.Config()
    tpl = picofun.template.Template("picofun/templates")
    with tempfile.TemporaryDirectory() as out_dir:
        config.output_dir = out_dir
        generator = picofun.iac.cdk.CdkGenerator(tpl, "myapi", config)
        generator.generate(["get_users", "create_order"])

        output_file = os.path.join(out_dir, "construct.py")
        with open(output_file) as f:
            content = f.read()

        assert "get_users" in content
        assert "create_order" in content


def test_generate_auth_resources_included() -> None:
    """Test that KMS, SSM, IAM policies present when auth enabled."""
    config = picofun.config.Config()
    tpl = picofun.template.Template("picofun/templates")
    with tempfile.TemporaryDirectory() as out_dir:
        config.output_dir = out_dir
        generator = picofun.iac.cdk.CdkGenerator(tpl, "testauth", config)
        generator.generate(
            ["test_lambda"],
            auth_enabled=True,
            auth_scheme_type="http",
            auth_scheme_name="bearerAuth",
            auth_ttl=300,
        )

        output_file = os.path.join(out_dir, "construct.py")
        with open(output_file) as f:
            content = f.read()

        assert "kms.Key" in content
        assert "ssm.StringParameter" in content
        assert "ssm:GetParameter" in content
        assert "kms:Decrypt" in content
        assert "credentials-http" in content
        assert "PICORUN_CREDENTIALS_TTL" in content


def test_generate_auth_resources_excluded() -> None:
    """Test that auth resources absent when disabled."""
    config = picofun.config.Config()
    tpl = picofun.template.Template("picofun/templates")
    with tempfile.TemporaryDirectory() as out_dir:
        config.output_dir = out_dir
        generator = picofun.iac.cdk.CdkGenerator(tpl, "testnoauth", config)
        generator.generate(["test_lambda"], auth_enabled=False)

        output_file = os.path.join(out_dir, "construct.py")
        with open(output_file) as f:
            content = f.read()

        assert "kms.Key" not in content
        assert "ssm.StringParameter" not in content
        assert "ssm:GetParameter" not in content
        assert "PICORUN_CREDENTIALS_TTL" not in content


def test_generate_xray_tracing() -> None:
    """Test that X-Ray config present when enabled."""
    config = picofun.config.Config()
    tpl = picofun.template.Template("picofun/templates")
    with tempfile.TemporaryDirectory() as out_dir:
        config.output_dir = out_dir
        generator = picofun.iac.cdk.CdkGenerator(tpl, "testxray", config)
        generator.generate(["test_lambda"])

        output_file = os.path.join(out_dir, "construct.py")
        with open(output_file) as f:
            content = f.read()

        assert "Tracing.ACTIVE" in content
        assert "AWSXRayDaemonWriteAccess" in content


def test_generate_exposes_functions_property() -> None:
    """Test that functions and role properties exist."""
    config = picofun.config.Config()
    tpl = picofun.template.Template("picofun/templates")
    with tempfile.TemporaryDirectory() as out_dir:
        config.output_dir = out_dir
        generator = picofun.iac.cdk.CdkGenerator(tpl, "testprops", config)
        generator.generate(["test_lambda"])

        output_file = os.path.join(out_dir, "construct.py")
        with open(output_file) as f:
            content = f.read()

        assert "def functions(self)" in content
        assert "def role(self)" in content
        assert "self._functions" in content
        assert "self._role" in content
