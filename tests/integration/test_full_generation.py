"""Integration tests for full generation with authentication."""

__author__ = "Dave Hall <skwashd@gmail.com>"
__copyright__ = "Copyright 2026, Dave Hall https://proactiveops.io"
__license__ = "MIT"

import os
import tempfile

from typer.testing import CliRunner

from picofun.cli import app

runner = CliRunner()


def test_generate_with_bearer_auth() -> None:
    """Test full generation with http bearer scheme."""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = runner.invoke(
            app,
            [
                "testbearer",
                "tests/fixtures/spec_bearer_auth.yaml",
                "--output-dir",
                tmpdir,
            ],
        )

        assert result.exit_code == 0

        # Check auth hooks were generated
        auth_hooks_path = os.path.join(tmpdir, "layer", "auth_hooks.py")
        assert os.path.exists(auth_hooks_path)

        with open(auth_hooks_path) as f:
            content = f.read()
            assert "def preprocessor(request):" in content
            assert "def get_credentials" in content
            assert "Bearer" in content

        # Check Terraform includes auth resources
        main_tf_path = os.path.join(tmpdir, "main.tf")
        assert os.path.exists(main_tf_path)

        with open(main_tf_path) as f:
            content = f.read()
            assert "aws_ssm_parameter" in content
            assert "credentials-http" in content
            assert "ssm:GetParameter" in content
            assert "kms:Decrypt" in content


def test_generate_with_apikey_auth() -> None:
    """Test full generation with apiKey scheme."""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = runner.invoke(
            app,
            [
                "testapikey",
                "tests/fixtures/spec_apikey_auth.yaml",
                "--output-dir",
                tmpdir,
            ],
        )

        assert result.exit_code == 0

        # Check auth hooks were generated
        auth_hooks_path = os.path.join(tmpdir, "layer", "auth_hooks.py")
        assert os.path.exists(auth_hooks_path)

        with open(auth_hooks_path) as f:
            content = f.read()
            assert "def preprocessor(request):" in content
            assert "X-API-Key" in content

        # Check Terraform includes auth resources
        main_tf_path = os.path.join(tmpdir, "main.tf")
        assert os.path.exists(main_tf_path)

        with open(main_tf_path) as f:
            content = f.read()
            assert "aws_ssm_parameter" in content
            assert "credentials-api-key" in content


def test_generate_auth_disabled() -> None:
    """Test no auth files when auth is disabled."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create config file with auth disabled
        config_path = os.path.join(tmpdir, "picofun.toml")
        with open(config_path, "w") as f:
            f.write("[auth]\nenabled = false\n")

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

        # Check auth hooks were NOT generated
        auth_hooks_path = os.path.join(tmpdir, "layer", "auth_hooks.py")
        assert not os.path.exists(auth_hooks_path)

        # Check Terraform does NOT include auth resources
        main_tf_path = os.path.join(tmpdir, "main.tf")
        assert os.path.exists(main_tf_path)

        with open(main_tf_path) as f:
            content = f.read()
            assert "aws_ssm_parameter" not in content
            assert "ssm:GetParameter" not in content


def test_generate_no_security_schemes() -> None:
    """Test graceful handling when spec has no security."""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = runner.invoke(
            app,
            [
                "testnosec",
                "tests/fixtures/spec_no_auth.yaml",
                "--output-dir",
                tmpdir,
            ],
        )

        assert result.exit_code == 0

        # Check auth hooks were NOT generated
        auth_hooks_path = os.path.join(tmpdir, "layer", "auth_hooks.py")
        assert not os.path.exists(auth_hooks_path)

        # Check Terraform does NOT include auth resources
        main_tf_path = os.path.join(tmpdir, "main.tf")
        assert os.path.exists(main_tf_path)

        with open(main_tf_path) as f:
            content = f.read()
            assert "aws_ssm_parameter" not in content


def test_generate_unsupported_schemes_only() -> None:
    """Test error when only oauth2 in spec."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a spec with only oauth2
        spec_path = os.path.join(tmpdir, "spec_oauth2_only.yaml")
        with open(spec_path, "w") as f:
            f.write("""openapi: "3.0.0"
info:
  title: Test API
  version: "1.0"
servers:
  - url: https://api.example.com/v1
components:
  securitySchemes:
    oauth2:
      type: oauth2
      flows:
        clientCredentials:
          tokenUrl: https://auth.example.com/token
          scopes: {}
security:
  - oauth2: []
paths:
  /test:
    get:
      operationId: getTest
      responses:
        "200":
          description: OK
""")

        result = runner.invoke(
            app,
            [
                "testoauth",
                spec_path,
                "--output-dir",
                tmpdir,
            ],
        )

        assert result.exit_code == 1


def test_regeneration_overwrites() -> None:
    """Test running twice overwrites auth_hooks.py."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # First run
        result1 = runner.invoke(
            app,
            [
                "testoverwrite",
                "tests/fixtures/spec_bearer_auth.yaml",
                "--output-dir",
                tmpdir,
            ],
        )
        assert result1.exit_code == 0

        auth_hooks_path = os.path.join(tmpdir, "layer", "auth_hooks.py")
        assert os.path.exists(auth_hooks_path)

        # Modify the file
        with open(auth_hooks_path, "a") as f:
            f.write("\n# This should be overwritten\n")

        # Second run
        result2 = runner.invoke(
            app,
            [
                "testoverwrite",
                "tests/fixtures/spec_bearer_auth.yaml",
                "--output-dir",
                tmpdir,
            ],
        )
        assert result2.exit_code == 0

        # Check the modification was overwritten
        with open(auth_hooks_path) as f:
            content = f.read()
            assert "This should be overwritten" not in content
            assert "def preprocessor(request):" in content
