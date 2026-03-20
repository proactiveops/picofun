"""Test the Spec.to_api_spec() method."""

__author__ = "Dave Hall <skwashd@gmail.com>"
__copyright__ = "Copyright 2026, Dave Hall https://proactiveops.io"
__license__ = "MIT"

import picofun.spec
from picofun.models import ApiSpec


def test_to_api_spec_json() -> None:
    """Test to_api_spec() with a JSON fixture."""
    spec = picofun.spec.Spec("tests/data/petstore.json")
    api_spec = spec.to_api_spec()

    assert isinstance(api_spec, ApiSpec)
    assert api_spec.source_format == "openapi3"
    assert api_spec.title == "Swagger Petstore"
    assert len(api_spec.servers) == 1
    assert api_spec.servers[0].url == "http://petstore.swagger.io/v1"
    assert len(api_spec.endpoints) > 0


def test_to_api_spec_yaml() -> None:
    """Test to_api_spec() with a YAML fixture."""
    spec = picofun.spec.Spec("tests/data/petstore.yaml")
    api_spec = spec.to_api_spec()

    assert isinstance(api_spec, ApiSpec)
    assert api_spec.source_format == "openapi3"
    assert api_spec.title == "Swagger Petstore"
    assert len(api_spec.servers) == 1
    assert api_spec.servers[0].url == "http://petstore.swagger.io/v1"
    assert len(api_spec.endpoints) > 0


def test_to_api_spec_auth() -> None:
    """Test to_api_spec() with bearer auth fixture."""
    spec = picofun.spec.Spec("tests/fixtures/spec_bearer_auth.yaml")
    api_spec = spec.to_api_spec()

    assert isinstance(api_spec, ApiSpec)
    assert len(api_spec.security_schemes) > 0
    assert api_spec.security_schemes[0].name == "bearerAuth"
    assert api_spec.security_schemes[0].scheme == "bearer"
    assert len(api_spec.global_security) > 0
    assert "bearerAuth" in api_spec.global_security


def test_to_api_spec_format_override() -> None:
    """Test to_api_spec() with format_override parameter."""
    spec = picofun.spec.Spec("tests/data/petstore.json")
    api_spec = spec.to_api_spec(format_override="openapi3")

    assert isinstance(api_spec, ApiSpec)
    assert api_spec.source_format == "openapi3"
    assert api_spec.title == "Swagger Petstore"


def test_parse_still_returns_dict() -> None:
    """Test that existing parse() method still returns a raw dict."""
    spec = picofun.spec.Spec("tests/data/petstore.json")
    result = spec.parse()

    assert isinstance(result, dict)
    assert not isinstance(result, ApiSpec)
    assert "openapi" in result
