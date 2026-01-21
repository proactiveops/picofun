"""Tests for the LambdaGenerator class."""

import os
import tempfile

import pytest
import yaml

import picofun.config
import picofun.endpoint_filter
import picofun.errors
import picofun.lambda_generator
import picofun.template


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
    spec = {
        "swagger": "2.0",
        "info": {"title": "Simple API overview", "version": "v2"},
        "servers": [{"url": "https://example.com"}],
        "paths": {
            "/": {
                "get": {
                    "operationId": "example",
                    "summary": "Example endpoint",
                    "produces": ["application/json"],
                    "responses": {
                        "200": {
                            "description": "OK response",
                        },
                        "404": {
                            "description": "Not found response",
                        },
                    },
                }
            },
        },
    }

    tpl = picofun.template.Template("tests/data/templates")
    config = picofun.config.Config()
    with tempfile.TemporaryDirectory() as out_dir:
        config.output_dir = out_dir
        generator = picofun.lambda_generator.LambdaGenerator(tpl, "", config)

        assert generator.generate(spec) == ["get_"]


def test_generate_empty() -> None:
    """Test generate with no lambdas."""
    spec = {
        "swagger": "2.0",
        "info": {"title": "Simple API overview", "version": "v2"},
        "servers": [{"url": "https://example.com"}],
        "paths": {
            "/": {
                "invalid": {
                    "operationId": "example",
                    "summary": "Example endpoint",
                    "produces": ["application/json"],
                    "responses": {
                        "200": {
                            "description": "OK response",
                        },
                        "404": {
                            "description": "Not found response",
                        },
                    },
                }
            },
        },
    }

    tpl = picofun.template.Template("tests/data/templates")
    config = picofun.config.Config()

    with tempfile.TemporaryDirectory() as out_dir:
        config.output_dir = out_dir
        generator = picofun.lambda_generator.LambdaGenerator(tpl, "", config)
        assert generator.generate(spec) == []


def test_generate_invalid_method() -> None:
    """Test generate with invalid HTTP method."""
    spec = {"servers": [{"url": "https://example.com"}], "paths": {}}

    tpl = picofun.template.Template("tests/data/templates")
    config = picofun.config.Config()

    with tempfile.TemporaryDirectory() as out_dir:
        config.output_dir = out_dir
        generator = picofun.lambda_generator.LambdaGenerator(tpl, "", config)
        assert generator.generate(spec) == []


def test_render() -> None:
    """Test rendering the lambda."""
    tpl = picofun.template.Template("tests/data/templates")
    config = picofun.config.Config()
    generator = picofun.lambda_generator.LambdaGenerator(tpl, "", config)

    code = generator.render("https://example.com", "get", "/path", {})

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
    spec = {
        "swagger": "2.0",
        "info": {"title": "Simple API overview", "version": "v2"},
        "servers": [{"url": "https://example.com"}],
        "paths": {
            "/users": {
                "get": {
                    "operationId": "getUsers",
                    "summary": "Get users",
                },
            },
            "/orders": {
                "get": {
                    "operationId": "getOrders",
                    "summary": "Get orders",
                },
            },
        },
    }

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
            lambdas = generator.generate(spec)

            # Only /users should be generated, /orders should be filtered out
            assert lambdas == ["get_users"]
    finally:
        os.unlink(filter_file)


def test_resolve_server_url_no_config() -> None:
    """Test resolving server URL without any config override."""
    tpl = picofun.template.Template("tests/data/templates")
    config = picofun.config.Config()
    generator = picofun.lambda_generator.LambdaGenerator(tpl, "", config)

    server_spec = {"url": "https://example.com/api"}
    result = generator._resolve_server_url(server_spec)

    assert result == "https://example.com/api"


def test_resolve_server_url_with_url_override() -> None:
    """Test resolving server URL with config URL override."""
    tpl = picofun.template.Template("tests/data/templates")
    config = picofun.config.Config(
        server=picofun.config.ServerConfig(url="https://override.example.com")
    )
    generator = picofun.lambda_generator.LambdaGenerator(tpl, "", config)

    server_spec = {"url": "https://original.example.com/api"}
    result = generator._resolve_server_url(server_spec)

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

    server_spec = {
        "url": "https://{subdomain}.example.com/api/{version}",
        "variables": {
            "subdomain": {"default": "api"},
            "version": {"default": "v1"},
        },
    }
    result = generator._resolve_server_url(server_spec)

    assert result == "https://custom.example.com/api/v2"


def test_resolve_server_url_with_partial_variables() -> None:
    """Test resolving server URL with partial variable overrides."""
    tpl = picofun.template.Template("tests/data/templates")
    config = picofun.config.Config(
        server=picofun.config.ServerConfig(variables={"subdomain": "custom"})
    )
    generator = picofun.lambda_generator.LambdaGenerator(tpl, "", config)

    server_spec = {
        "url": "https://{subdomain}.{domain}.com/api",
        "variables": {
            "subdomain": {"default": "api"},
            "domain": {"default": "example"},
        },
    }
    result = generator._resolve_server_url(server_spec)

    assert result == "https://custom.example.com/api"


def test_resolve_server_url_unknown_variable() -> None:
    """Test resolving server URL with unknown variable raises error."""
    tpl = picofun.template.Template("tests/data/templates")
    config = picofun.config.Config(
        server=picofun.config.ServerConfig(variables={"unknown": "value"})
    )
    generator = picofun.lambda_generator.LambdaGenerator(tpl, "", config)

    server_spec = {
        "url": "https://{subdomain}.example.com/api",
        "variables": {"subdomain": {"default": "api"}},
    }

    with pytest.raises(picofun.errors.UnknownServerVariableError) as exc_info:
        generator._resolve_server_url(server_spec)

    assert "unknown" in str(exc_info.value)
    assert "subdomain" in str(exc_info.value)


def test_resolve_server_url_missing_default() -> None:
    """Test resolving server URL with missing default value raises error."""
    tpl = picofun.template.Template("tests/data/templates")
    config = picofun.config.Config()
    generator = picofun.lambda_generator.LambdaGenerator(tpl, "", config)

    server_spec = {
        "url": "https://{subdomain}.example.com/api",
        "variables": {"subdomain": {"description": "The subdomain"}},
    }

    with pytest.raises(picofun.errors.MissingServerVariableError) as exc_info:
        generator._resolve_server_url(server_spec)

    assert "subdomain" in str(exc_info.value)


def test_resolve_server_url_no_variables_in_spec() -> None:
    """Test resolving server URL when spec has no variables defined."""
    tpl = picofun.template.Template("tests/data/templates")
    config = picofun.config.Config(
        server=picofun.config.ServerConfig(variables={"key": "value"})
    )
    generator = picofun.lambda_generator.LambdaGenerator(tpl, "", config)

    server_spec = {"url": "https://example.com/api"}

    with pytest.raises(picofun.errors.UnknownServerVariableError):
        generator._resolve_server_url(server_spec)


def test_generate_with_server_url_override() -> None:
    """Test generating lambda with server URL override."""
    spec = {
        "swagger": "2.0",
        "info": {"title": "Simple API", "version": "v1"},
        "servers": [{"url": "https://original.example.com"}],
        "paths": {
            "/test": {
                "get": {
                    "operationId": "getTest",
                    "summary": "Test endpoint",
                }
            }
        },
    }

    tpl = picofun.template.Template("tests/data/templates")
    config = picofun.config.Config(
        server=picofun.config.ServerConfig(url="https://override.example.com")
    )

    with tempfile.TemporaryDirectory() as out_dir:
        config.output_dir = out_dir
        generator = picofun.lambda_generator.LambdaGenerator(tpl, "", config)
        lambdas = generator.generate(spec)

        assert lambdas == ["get_test"]

        # Verify the generated file contains the overridden URL
        lambda_file = os.path.join(out_dir, "lambdas", "get_test.py")
        with open(lambda_file) as f:
            content = f.read()
            assert "https://override.example.com" in content
            assert "https://original.example.com" not in content


def test_generate_with_server_variables() -> None:
    """Test generating lambda with server variable substitution."""
    spec = {
        "swagger": "2.0",
        "info": {"title": "Simple API", "version": "v1"},
        "servers": [
            {
                "url": "https://{subdomain}.{domain}.com/api",
                "variables": {
                    "subdomain": {"default": "api"},
                    "domain": {"default": "example"},
                },
            }
        ],
        "paths": {
            "/test": {
                "get": {
                    "operationId": "getTest",
                    "summary": "Test endpoint",
                }
            }
        },
    }

    tpl = picofun.template.Template("tests/data/templates")
    config = picofun.config.Config(
        server=picofun.config.ServerConfig(
            variables={"subdomain": "custom", "domain": "test"}
        )
    )

    with tempfile.TemporaryDirectory() as out_dir:
        config.output_dir = out_dir
        generator = picofun.lambda_generator.LambdaGenerator(tpl, "", config)
        lambdas = generator.generate(spec)

        assert lambdas == ["get_test"]

        # Verify the generated file contains the resolved URL
        lambda_file = os.path.join(out_dir, "lambdas", "get_test.py")
        with open(lambda_file) as f:
            content = f.read()
            assert "https://custom.test.com/api" in content


def test_generate_with_cli_server_url_override() -> None:
    """Test generating lambda with CLI server_url override that ignores config."""
    spec = {
        "swagger": "2.0",
        "info": {"title": "Simple API", "version": "v1"},
        "servers": [{"url": "https://original.example.com"}],
        "paths": {
            "/test": {
                "get": {
                    "operationId": "getTest",
                    "summary": "Test endpoint",
                }
            }
        },
    }

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
        lambdas = generator.generate(spec)

        assert lambdas == ["get_test"]

        # Verify the generated file contains the CLI override URL, not the config or spec URL
        lambda_file = os.path.join(out_dir, "lambdas", "get_test.py")
        with open(lambda_file) as f:
            content = f.read()
            assert "https://cli-override.example.com" in content
            assert "https://original.example.com" not in content
            assert "from-config" not in content
