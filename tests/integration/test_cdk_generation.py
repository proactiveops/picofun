"""Integration tests for full CDK generation."""

__author__ = "Dave Hall <skwashd@gmail.com>"
__copyright__ = "Copyright 2026, Dave Hall https://proactiveops.io"
__license__ = "MIT"

import os
import tempfile

from typer.testing import CliRunner

from picofun.cli import app

runner = CliRunner()


def test_generate_cdk_with_bearer_auth() -> None:
    """Test full CDK generation with http bearer scheme."""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = runner.invoke(
            app,
            [
                "testbearer",
                "tests/fixtures/spec_bearer_auth.yaml",
                "--iac",
                "cdk",
                "--output-dir",
                tmpdir,
            ],
        )

        assert result.exit_code == 0

        # Check CDK construct was generated (not Terraform)
        construct_path = os.path.join(tmpdir, "construct.py")
        assert os.path.exists(construct_path)

        main_tf_path = os.path.join(tmpdir, "main.tf")
        assert not os.path.exists(main_tf_path)

        with open(construct_path) as f:
            content = f.read()
            assert "class TestbearerFunctions(Construct):" in content
            assert "ssm.StringParameter" in content
            assert "credentials-http" in content
            assert "kms:Decrypt" in content


def test_generate_cdk_auth_disabled() -> None:
    """Test CDK generation with auth disabled."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = os.path.join(tmpdir, "picofun.toml")
        with open(config_path, "w") as f:
            f.write('iac = "cdk"\n\n[auth]\nenabled = false\n')

        result = runner.invoke(
            app,
            [
                "testnoauth",
                "tests/fixtures/spec_bearer_auth.yaml",
                "--config-file",
                config_path,
                "--output-dir",
                tmpdir,
            ],
        )

        assert result.exit_code == 0

        construct_path = os.path.join(tmpdir, "construct.py")
        assert os.path.exists(construct_path)

        with open(construct_path) as f:
            content = f.read()
            assert "ssm.StringParameter" not in content
            assert "kms:Decrypt" not in content


def test_generate_cdk_shorthand_flag() -> None:
    """Test that --cdk shorthand flag works."""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = runner.invoke(
            app,
            [
                "testcdk",
                "tests/fixtures/spec_bearer_auth.yaml",
                "--cdk",
                "--output-dir",
                tmpdir,
            ],
        )

        assert result.exit_code == 0

        construct_path = os.path.join(tmpdir, "construct.py")
        assert os.path.exists(construct_path)

        main_tf_path = os.path.join(tmpdir, "main.tf")
        assert not os.path.exists(main_tf_path)
