"""Tests for IR Pydantic models."""

__author__ = "Dave Hall <skwashd@gmail.com>"
__copyright__ = "Copyright 2026, Dave Hall https://proactiveops.io"
__license__ = "MIT"

import pytest
from pydantic import ValidationError

from picofun.models import (
    ApiSpec,
    Endpoint,
    Parameter,
    SecurityScheme,
    Server,
    ServerVariable,
)


def test_api_spec_required_fields_only() -> None:
    """Constructing ApiSpec with only required fields applies defaults."""
    spec = ApiSpec(source_format="openapi3")
    assert spec.source_format == "openapi3"
    assert spec.title == ""
    assert spec.version == ""
    assert spec.servers == []
    assert spec.security_schemes == []
    assert spec.global_security == []
    assert spec.endpoints == []


def test_api_spec_all_fields() -> None:
    """Constructing ApiSpec with all fields stores them correctly."""
    spec = ApiSpec(
        title="Pet Store",
        version="1.0.0",
        source_format="openapi3",
        servers=[Server(url="https://api.example.com")],
        security_schemes=[SecurityScheme(name="api_key", type="apiKey")],
        global_security=["api_key"],
        endpoints=[Endpoint(path="/pets", method="get")],
    )
    assert spec.title == "Pet Store"
    assert spec.version == "1.0.0"
    assert len(spec.servers) == 1
    assert spec.servers[0].url == "https://api.example.com"
    assert len(spec.security_schemes) == 1
    assert spec.global_security == ["api_key"]
    assert len(spec.endpoints) == 1


def test_api_spec_missing_source_format_raises() -> None:
    """Constructing ApiSpec without source_format raises ValidationError."""
    with pytest.raises(ValidationError):
        ApiSpec.model_validate({})


def test_api_spec_json_round_trip() -> None:
    """Serialize ApiSpec to JSON and back, assert equality."""
    spec = ApiSpec(
        title="Round Trip API",
        version="2.0.0",
        source_format="swagger2",
        servers=[
            Server(
                url="https://{host}/v2",
                description="Production",
                variables={"host": ServerVariable(default="api.example.com")},
            )
        ],
        security_schemes=[
            SecurityScheme(
                name="bearer_auth",
                type="http",
                scheme="bearer",
                bearer_format="JWT",
            )
        ],
        global_security=["bearer_auth"],
        endpoints=[
            Endpoint(
                path="/users",
                method="post",
                operation_id="createUser",
                summary="Create a user",
                description="Creates a new user account",
                tags=["users"],
                parameters=[
                    Parameter(
                        name="X-Request-Id",
                        location="header",
                        required=True,
                        description="Correlation ID",
                        schema_={"type": "string"},
                    )
                ],
                deprecated=False,
                extra={"x-custom": "value"},
            )
        ],
    )
    json_str = spec.model_dump_json()
    restored = ApiSpec.model_validate_json(json_str)
    assert restored == spec


def test_nested_server_with_variables() -> None:
    """ApiSpec with Server containing ServerVariable objects."""
    var = ServerVariable(
        default="v1",
        description="API version",
        enum=["v1", "v2"],
    )
    server = Server(
        url="https://api.example.com/{version}",
        description="Main server",
        variables={"version": var},
    )
    spec = ApiSpec(source_format="openapi3", servers=[server])
    assert spec.servers[0].variables["version"].default == "v1"
    assert spec.servers[0].variables["version"].enum == ["v1", "v2"]


def test_endpoint_empty_defaults() -> None:
    """Endpoint with no optional fields defaults to empty collections."""
    endpoint = Endpoint(path="/health", method="get")
    assert endpoint.tags == []
    assert endpoint.parameters == []
    assert endpoint.extra == {}
    assert endpoint.operation_id is None
    assert endpoint.summary == ""
    assert endpoint.description == ""
    assert endpoint.deprecated is False


def test_security_scheme_all_fields() -> None:
    """SecurityScheme stores all fields correctly."""
    scheme = SecurityScheme(
        name="api_key",
        type="apiKey",
        param_name="X-API-Key",
        location="header",
        scheme=None,
        bearer_format=None,
    )
    assert scheme.name == "api_key"
    assert scheme.type == "apiKey"
    assert scheme.param_name == "X-API-Key"
    assert scheme.location == "header"


def test_parameter_defaults() -> None:
    """Parameter applies defaults for optional fields."""
    param = Parameter(name="limit", location="query")
    assert param.required is False
    assert param.description == ""
    assert param.schema_ == {}


def test_server_variable_defaults() -> None:
    """ServerVariable applies defaults for optional fields."""
    var = ServerVariable(default="production")
    assert var.description == ""
    assert var.enum == []
