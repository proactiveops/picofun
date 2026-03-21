"""Tests for the LambdaGenerator class."""

__author__ = "Dave Hall <skwashd@gmail.com>"
__copyright__ = "Copyright 2023 - 2026, Dave Hall https://proactiveops.io"
__license__ = "MIT"

import os
import tempfile
from typing import Any

import pydantic
import pytest
import yaml

import picofun.config
import picofun.endpoint_filter
import picofun.errors
import picofun.lambda_generator
import picofun.template
from picofun.models import ApiSpec, Endpoint, Server, ServerVariable


def test_get_name() -> None:
    """Test getting the name of the lambda."""
    tpl = picofun.template.Template("tests/data/templates")
    generator = picofun.lambda_generator.LambdaGenerator(
        tpl, "", picofun.config.Config()
    )

    assert generator._get_name("method", "path") == "method_path"


def test_get_name_with_dot() -> None:
    """Test getting the name of the lambda when path contains a dot (.)."""
    tpl = picofun.template.Template("tests/data/templates")
    generator = picofun.lambda_generator.LambdaGenerator(
        tpl, "", picofun.config.Config()
    )

    assert generator._get_name("method", "path.json") == "method_path_json"


def test_get_name_with_dash() -> None:
    """Test getting the name of the lambda when path contains a dash (-)."""
    tpl = picofun.template.Template("tests/data/templates")
    generator = picofun.lambda_generator.LambdaGenerator(
        tpl, "", picofun.config.Config()
    )

    assert (
        generator._get_name("get", "/actions/secrets/public-key")
        == "get_actions_secrets_public_key"
    )


def test_get_name_too_long() -> None:
    """Test getting the name of the lambda."""
    tpl = picofun.template.Template("tests/data/templates")
    generator = picofun.lambda_generator.LambdaGenerator(
        tpl, "prefix", picofun.config.Config()
    )

    path = "how_long_does_this_string_need_to_be_before_it_is_truncated_by_get_name"

    name = generator._get_name("get", path)
    assert len(name) == 57  # 64 - "prefix_" = 57
    assert name[:52] == "get_how_long_does_this_string_need_to_be_before_it_i"


def test_generate() -> None:
    """Test generating the lambda functions."""
    api_spec = ApiSpec(
        source_format="openapi3",
        servers=[Server(url="https://example.com")],
        endpoints=[
            Endpoint(
                path="/",
                method="get",
                operation_id="example",
                summary="Example endpoint",
                extra={
                    "operationId": "example",
                    "summary": "Example endpoint",
                    "produces": ["application/json"],
                    "responses": {
                        "200": {"description": "OK response"},
                        "404": {"description": "Not found response"},
                    },
                },
            )
        ],
    )

    tpl = picofun.template.Template("tests/data/templates")
    config = picofun.config.Config()
    with tempfile.TemporaryDirectory() as out_dir:
        config.output_dir = out_dir
        generator = picofun.lambda_generator.LambdaGenerator(tpl, "", config)

        assert generator.generate(api_spec) == ["get_"]


def test_generate_empty() -> None:
    """Test generate with no lambdas."""
    api_spec = ApiSpec(
        source_format="openapi3",
        servers=[Server(url="https://example.com")],
        endpoints=[],
    )

    tpl = picofun.template.Template("tests/data/templates")
    config = picofun.config.Config()

    with tempfile.TemporaryDirectory() as out_dir:
        config.output_dir = out_dir
        generator = picofun.lambda_generator.LambdaGenerator(tpl, "", config)
        assert generator.generate(api_spec) == []


def test_generate_invalid_method() -> None:
    """Test generate with invalid HTTP method."""
    api_spec = ApiSpec(
        source_format="openapi3",
        servers=[Server(url="https://example.com")],
        endpoints=[],
    )

    tpl = picofun.template.Template("tests/data/templates")
    config = picofun.config.Config()

    with tempfile.TemporaryDirectory() as out_dir:
        config.output_dir = out_dir
        generator = picofun.lambda_generator.LambdaGenerator(tpl, "", config)
        assert generator.generate(api_spec) == []


def test_render() -> None:
    """Test rendering the lambda."""
    tpl = picofun.template.Template("tests/data/templates")
    config = picofun.config.Config()
    generator = picofun.lambda_generator.LambdaGenerator(tpl, "", config)

    endpoint = Endpoint(path="/path", method="get", extra={})
    code = generator.render("https://example.com", endpoint)

    assert (
        code
        == """\"\"\"Generated AWS Lambda function for making an API call.\"\"\"

from typing import Any

import requests
from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext

import picorun

logger = Logger()


@logger.inject_lambda_context
def handler(event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
    \"\"\".\"\"\"
    properties = picorun.ApiRequestArgs(**event)

    url = "https://example.com/path".format(**properties.path)

    timeout = context.get_remaining_time_in_millis() - 1000
    response = requests.get(url, timeout=timeout, **properties.to_kwargs())
    out = picorun.ApiResponse(response)

    if response.status_code >= 400:
        logger.error("Error %d: %s", response.status_code, response.text)
        raise picorun.ApiError(response.text, response.status_code)

    return out.asdict()
"""
    )


def test_generate_with_filter() -> None:
    """Test generating lambda functions with endpoint filter."""
    api_spec = ApiSpec(
        source_format="openapi3",
        servers=[Server(url="https://example.com")],
        endpoints=[
            Endpoint(
                path="/users",
                method="get",
                operation_id="getUsers",
                summary="Get users",
            ),
            Endpoint(
                path="/orders",
                method="get",
                operation_id="getOrders",
                summary="Get orders",
            ),
        ],
    )

    # Create a filter that only includes /users
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump({"paths": [{"path": "/users"}]}, f)
        f.flush()
        filter_file = f.name

    try:
        endpoint_filter = picofun.endpoint_filter.EndpointFilter(filter_file)
        tpl = picofun.template.Template("tests/data/templates")
        config = picofun.config.Config()

        with tempfile.TemporaryDirectory() as out_dir:
            config.output_dir = out_dir
            generator = picofun.lambda_generator.LambdaGenerator(
                tpl, "", config, endpoint_filter
            )
            lambdas = generator.generate(api_spec)

            # Only /users should be generated, /orders should be filtered out
            assert lambdas == ["get_users"]
    finally:
        os.unlink(filter_file)


def test_resolve_server_url_no_config() -> None:
    """Test resolving server URL without any config override."""
    tpl = picofun.template.Template("tests/data/templates")
    config = picofun.config.Config()
    generator = picofun.lambda_generator.LambdaGenerator(tpl, "", config)

    server = Server(url="https://example.com/api")
    result = generator._resolve_server_url(server)

    assert result == "https://example.com/api"


def test_resolve_server_url_no_config_with_spec_variables() -> None:
    """Test resolving server URL uses spec defaults when config has no server."""
    tpl = picofun.template.Template("tests/data/templates")
    config = picofun.config.Config()
    generator = picofun.lambda_generator.LambdaGenerator(tpl, "", config)

    server = Server(
        url="https://{subdomain}.example.com/api",
        variables={"subdomain": ServerVariable(default="api")},
    )
    result = generator._resolve_server_url(server)

    assert result == "https://api.example.com/api"


def test_resolve_server_url_with_url_override() -> None:
    """Test resolving server URL with config URL override."""
    tpl = picofun.template.Template("tests/data/templates")
    config = picofun.config.Config(
        server=picofun.config.ServerConfig(url="https://override.example.com")
    )
    generator = picofun.lambda_generator.LambdaGenerator(tpl, "", config)

    server = Server(url="https://original.example.com/api")
    result = generator._resolve_server_url(server)

    assert result == "https://override.example.com"


def test_resolve_server_url_with_variables() -> None:
    """Test resolving server URL with variable substitution."""
    tpl = picofun.template.Template("tests/data/templates")
    config = picofun.config.Config(
        server=picofun.config.ServerConfig(
            variables={"subdomain": "custom", "version": "v2"}
        )
    )
    generator = picofun.lambda_generator.LambdaGenerator(tpl, "", config)

    server = Server(
        url="https://{subdomain}.example.com/api/{version}",
        variables={
            "subdomain": ServerVariable(default="api"),
            "version": ServerVariable(default="v1"),
        },
    )
    result = generator._resolve_server_url(server)

    assert result == "https://custom.example.com/api/v2"


def test_resolve_server_url_with_partial_variables() -> None:
    """Test resolving server URL with partial variable overrides."""
    tpl = picofun.template.Template("tests/data/templates")
    config = picofun.config.Config(
        server=picofun.config.ServerConfig(variables={"subdomain": "custom"})
    )
    generator = picofun.lambda_generator.LambdaGenerator(tpl, "", config)

    server = Server(
        url="https://{subdomain}.{domain}.com/api",
        variables={
            "subdomain": ServerVariable(default="api"),
            "domain": ServerVariable(default="example"),
        },
    )
    result = generator._resolve_server_url(server)

    assert result == "https://custom.example.com/api"


def test_resolve_server_url_unknown_variable() -> None:
    """Test resolving server URL with unknown variable raises error."""
    tpl = picofun.template.Template("tests/data/templates")
    config = picofun.config.Config(
        server=picofun.config.ServerConfig(variables={"unknown": "value"})
    )
    generator = picofun.lambda_generator.LambdaGenerator(tpl, "", config)

    server = Server(
        url="https://{subdomain}.example.com/api",
        variables={"subdomain": ServerVariable(default="api")},
    )

    with pytest.raises(picofun.errors.UnknownServerVariableError) as exc_info:
        generator._resolve_server_url(server)

    assert "unknown" in str(exc_info.value)
    assert "subdomain" in str(exc_info.value)


def test_resolve_server_url_missing_default() -> None:
    """Test that ServerVariable without default fails at model construction."""
    kwargs: dict[str, Any] = {"description": "The subdomain"}
    with pytest.raises(pydantic.ValidationError):
        ServerVariable(**kwargs)


def test_resolve_server_url_no_variables_in_spec() -> None:
    """Test resolving server URL when spec has no variables defined."""
    tpl = picofun.template.Template("tests/data/templates")
    config = picofun.config.Config(
        server=picofun.config.ServerConfig(variables={"key": "value"})
    )
    generator = picofun.lambda_generator.LambdaGenerator(tpl, "", config)

    server = Server(url="https://example.com/api")

    with pytest.raises(picofun.errors.UnknownServerVariableError):
        generator._resolve_server_url(server)


def test_generate_with_server_url_override() -> None:
    """Test generating lambda with server URL override."""
    api_spec = ApiSpec(
        source_format="openapi3",
        servers=[Server(url="https://original.example.com")],
        endpoints=[
            Endpoint(
                path="/test",
                method="get",
                operation_id="getTest",
                summary="Test endpoint",
            )
        ],
    )

    tpl = picofun.template.Template("tests/data/templates")
    config = picofun.config.Config(
        server=picofun.config.ServerConfig(url="https://override.example.com")
    )

    with tempfile.TemporaryDirectory() as out_dir:
        config.output_dir = out_dir
        generator = picofun.lambda_generator.LambdaGenerator(tpl, "", config)
        lambdas = generator.generate(api_spec)

        assert lambdas == ["get_test"]

        # Verify the generated file contains the overridden URL
        lambda_file = os.path.join(out_dir, "lambdas", "get_test.py")
        with open(lambda_file) as f:
            content = f.read()
            assert "https://override.example.com" in content
            assert "https://original.example.com" not in content


def test_generate_with_server_variables() -> None:
    """Test generating lambda with server variable substitution."""
    api_spec = ApiSpec(
        source_format="openapi3",
        servers=[
            Server(
                url="https://{subdomain}.{domain}.com/api",
                variables={
                    "subdomain": ServerVariable(default="api"),
                    "domain": ServerVariable(default="example"),
                },
            )
        ],
        endpoints=[
            Endpoint(
                path="/test",
                method="get",
                operation_id="getTest",
                summary="Test endpoint",
            )
        ],
    )

    tpl = picofun.template.Template("tests/data/templates")
    config = picofun.config.Config(
        server=picofun.config.ServerConfig(
            variables={"subdomain": "custom", "domain": "test"}
        )
    )

    with tempfile.TemporaryDirectory() as out_dir:
        config.output_dir = out_dir
        generator = picofun.lambda_generator.LambdaGenerator(tpl, "", config)
        lambdas = generator.generate(api_spec)

        assert lambdas == ["get_test"]

        # Verify the generated file contains the resolved URL
        lambda_file = os.path.join(out_dir, "lambdas", "get_test.py")
        with open(lambda_file) as f:
            content = f.read()
            assert "https://custom.test.com/api" in content


def test_generate_with_cli_server_url_override() -> None:
    """Test generating lambda with CLI server_url override that ignores config."""
    api_spec = ApiSpec(
        source_format="openapi3",
        servers=[Server(url="https://original.example.com")],
        endpoints=[
            Endpoint(
                path="/test",
                method="get",
                operation_id="getTest",
                summary="Test endpoint",
            )
        ],
    )

    tpl = picofun.template.Template("tests/data/templates")
    # Config has server variables, but CLI override should ignore it
    config = picofun.config.Config(
        server=picofun.config.ServerConfig(
            variables={"subdomain": "from-config", "domain": "ignored"}
        )
    )

    # Simulate CLI merge with server_url
    config.merge(server_url="https://cli-override.example.com")

    with tempfile.TemporaryDirectory() as out_dir:
        config.output_dir = out_dir
        generator = picofun.lambda_generator.LambdaGenerator(tpl, "", config)
        lambdas = generator.generate(api_spec)

        assert lambdas == ["get_test"]

        # Verify the generated file contains the CLI override URL, not the config or spec URL
        lambda_file = os.path.join(out_dir, "lambdas", "get_test.py")
        with open(lambda_file) as f:
            content = f.read()
            assert "https://cli-override.example.com" in content
            assert "https://original.example.com" not in content
            assert "from-config" not in content
