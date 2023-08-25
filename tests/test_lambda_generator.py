"""Tests for the LambdaGenerator class."""

import tempfile

import picofun.config
import picofun.lambda_generator
import picofun.template


def test_get_name() -> None:
    """Test getting the name of the lambda."""
    tpl = picofun.template.Template("tests/data/templates")
    generator = picofun.lambda_generator.LambdaGenerator(tpl, "tests/data/lambda")

    assert generator._get_name("method", "path") == "method_path"


def test_get_name_too_long() -> None:
    """Test getting the name of the lambda."""
    tpl = picofun.template.Template("tests/data/templates")
    generator = picofun.lambda_generator.LambdaGenerator(tpl, "tests/data/lambda")

    path = "how_long_does_this_string_need_to_be_before_it_is_truncated_by_get_name"

    name = generator._get_name("get", path)
    assert len(name) == 64
    assert name[:58] == "get_how_long_does_this_string_need_to_be_before_it_is_tru_"


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
    config = picofun.config.Config("tests/data/empty.toml")
    with tempfile.TemporaryDirectory() as out_dir:
        config.output_dir = out_dir
        generator = picofun.lambda_generator.LambdaGenerator(tpl, config)

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
    config = picofun.config.Config("tests/data/empty.toml")

    with tempfile.TemporaryDirectory() as out_dir:
        config.output_dir = out_dir
        generator = picofun.lambda_generator.LambdaGenerator(tpl, config)
        assert generator.generate(spec) == []


def test_generate_invalid_method() -> None:
    """Test generate with invalid HTTP method."""
    spec = {"servers": [{"url": "https://example.com"}], "paths": {}}

    tpl = picofun.template.Template("tests/data/templates")
    config = picofun.config.Config("tests/data/empty.toml")

    with tempfile.TemporaryDirectory() as out_dir:
        config.output_dir = out_dir
        generator = picofun.lambda_generator.LambdaGenerator(tpl, config)
        assert generator.generate(spec) == []


def test_render() -> None:
    """Test rendering the lambda."""
    tpl = picofun.template.Template("tests/data/templates")
    config = picofun.config.Config("tests/data/empty.toml")
    generator = picofun.lambda_generator.LambdaGenerator(tpl, config)

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
