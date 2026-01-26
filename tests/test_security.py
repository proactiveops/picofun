"""Tests for security scheme parsing and selection."""

__author__ = "Dave Hall <skwashd@gmail.com>"
__copyright__ = "Copyright 2026, Dave Hall https://proactiveops.io"
__license__ = "MIT"

import pytest

from picofun.errors import UnsupportedSecuritySchemeError
from picofun.security import (
    SecurityScheme,
    extract_security_schemes,
    get_global_security,
    get_scheme_type_kebab,
    select_security_scheme,
)


def test_extract_api_key_cookie_scheme() -> None:
    """Parse apiKey in cookie."""
    spec = {
        "components": {
            "securitySchemes": {
                "cookieAuth": {
                    "type": "apiKey",
                    "in": "cookie",
                    "name": "session_id",
                }
            }
        }
    }

    schemes = extract_security_schemes(spec)

    assert len(schemes) == 1
    assert "cookieAuth" in schemes
    scheme = schemes["cookieAuth"]
    assert scheme.name == "cookieAuth"
    assert scheme.type == "apiKey"
    assert scheme.location == "cookie"
    assert scheme.param_name == "session_id"


def test_extract_api_key_header_scheme() -> None:
    """Parse apiKey in header."""
    spec = {
        "components": {
            "securitySchemes": {
                "apiKeyAuth": {
                    "type": "apiKey",
                    "in": "header",
                    "name": "X-API-Key",
                }
            }
        }
    }

    schemes = extract_security_schemes(spec)

    assert len(schemes) == 1
    assert "apiKeyAuth" in schemes
    scheme = schemes["apiKeyAuth"]
    assert scheme.name == "apiKeyAuth"
    assert scheme.type == "apiKey"
    assert scheme.location == "header"
    assert scheme.param_name == "X-API-Key"


def test_extract_api_key_query_scheme() -> None:
    """Parse apiKey in query."""
    spec = {
        "components": {
            "securitySchemes": {
                "apiKeyQuery": {
                    "type": "apiKey",
                    "in": "query",
                    "name": "api_key",
                }
            }
        }
    }

    schemes = extract_security_schemes(spec)

    assert len(schemes) == 1
    assert "apiKeyQuery" in schemes
    scheme = schemes["apiKeyQuery"]
    assert scheme.name == "apiKeyQuery"
    assert scheme.type == "apiKey"
    assert scheme.location == "query"
    assert scheme.param_name == "api_key"


def test_extract_http_basic_scheme() -> None:
    """Parse http basic."""
    spec = {
        "components": {
            "securitySchemes": {"basicAuth": {"type": "http", "scheme": "basic"}}
        }
    }

    schemes = extract_security_schemes(spec)

    assert len(schemes) == 1
    assert "basicAuth" in schemes
    scheme = schemes["basicAuth"]
    assert scheme.name == "basicAuth"
    assert scheme.type == "http"
    assert scheme.scheme == "basic"


def test_extract_http_bearer_scheme() -> None:
    """Parse http bearer with format."""
    spec = {
        "components": {
            "securitySchemes": {
                "bearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT",
                }
            }
        }
    }

    schemes = extract_security_schemes(spec)

    assert len(schemes) == 1
    assert "bearerAuth" in schemes
    scheme = schemes["bearerAuth"]
    assert scheme.name == "bearerAuth"
    assert scheme.type == "http"
    assert scheme.scheme == "bearer"
    assert scheme.bearer_format == "JWT"


def test_extract_multiple_schemes() -> None:
    """Parse spec with multiple schemes."""
    spec = {
        "components": {
            "securitySchemes": {
                "bearerAuth": {"type": "http", "scheme": "bearer"},
                "apiKeyAuth": {
                    "type": "apiKey",
                    "in": "header",
                    "name": "X-API-Key",
                },
                "oauth2": {
                    "type": "oauth2",
                    "flows": {
                        "clientCredentials": {
                            "tokenUrl": "https://auth.example.com/token",
                            "scopes": {},
                        }
                    },
                },
            }
        }
    }

    schemes = extract_security_schemes(spec)

    assert len(schemes) == 3
    assert "bearerAuth" in schemes
    assert "apiKeyAuth" in schemes
    assert "oauth2" in schemes


def test_extract_mutual_tls_scheme() -> None:
    """Parse mutualTLS."""
    spec = {"components": {"securitySchemes": {"mtlsAuth": {"type": "mutualTLS"}}}}

    schemes = extract_security_schemes(spec)

    assert len(schemes) == 1
    assert "mtlsAuth" in schemes
    scheme = schemes["mtlsAuth"]
    assert scheme.name == "mtlsAuth"
    assert scheme.type == "mutualTLS"


def test_extract_no_schemes() -> None:
    """Handle spec without securitySchemes."""
    spec = {"components": {}}

    schemes = extract_security_schemes(spec)

    assert len(schemes) == 0
    assert schemes == {}


def test_get_global_security_empty() -> None:
    """Handle missing security array."""
    spec = {"openapi": "3.0.0"}

    security = get_global_security(spec)

    assert security == []


def test_get_global_security() -> None:
    """Extract global security array."""
    spec = {"security": [{"bearerAuth": []}, {"apiKeyAuth": []}, {"oauth2": []}]}

    security = get_global_security(spec)

    assert len(security) == 3
    assert "bearerAuth" in security
    assert "apiKeyAuth" in security
    assert "oauth2" in security


def test_select_scheme_filters_unreferenced() -> None:
    """Schemes not in global security ignored."""
    schemes = {
        "bearerAuth": SecurityScheme(name="bearerAuth", type="http", scheme="bearer"),
        "apiKeyAuth": SecurityScheme(
            name="apiKeyAuth",
            type="apiKey",
            location="header",
            param_name="X-API-Key",
        ),
    }
    global_security = ["bearerAuth"]

    selected = select_security_scheme(schemes, global_security)

    assert selected is not None
    assert selected.name == "bearerAuth"


def test_select_scheme_filters_unsupported() -> None:
    """oauth2/oidc schemes trigger fatal error."""
    schemes = {
        "oauth2": SecurityScheme(name="oauth2", type="oauth2"),
        "oidc": SecurityScheme(name="oidc", type="openIdConnect"),
    }
    global_security = ["oauth2", "oidc"]

    with pytest.raises(UnsupportedSecuritySchemeError) as exc_info:
        select_security_scheme(schemes, global_security)

    assert "oauth2" in str(exc_info.value)
    assert "oidc" in str(exc_info.value)


def test_select_scheme_priority_apikey_header_over_query() -> None:
    """Header apiKey over query."""
    schemes = {
        "apiKeyHeader": SecurityScheme(
            name="apiKeyHeader",
            type="apiKey",
            location="header",
            param_name="X-API-Key",
        ),
        "apiKeyQuery": SecurityScheme(
            name="apiKeyQuery",
            type="apiKey",
            location="query",
            param_name="api_key",
        ),
    }
    global_security = ["apiKeyHeader", "apiKeyQuery"]

    selected = select_security_scheme(schemes, global_security)

    assert selected is not None
    assert selected.name == "apiKeyHeader"
    assert selected.location == "header"


def test_select_scheme_priority_basic_over_apikey() -> None:
    """Basic selected over apiKey."""
    schemes = {
        "basicAuth": SecurityScheme(name="basicAuth", type="http", scheme="basic"),
        "apiKeyAuth": SecurityScheme(
            name="apiKeyAuth",
            type="apiKey",
            location="header",
            param_name="X-API-Key",
        ),
    }
    global_security = ["basicAuth", "apiKeyAuth"]

    selected = select_security_scheme(schemes, global_security)

    assert selected is not None
    assert selected.name == "basicAuth"


def test_select_scheme_priority_bearer_first() -> None:
    """Bearer selected over basic."""
    schemes = {
        "bearerAuth": SecurityScheme(name="bearerAuth", type="http", scheme="bearer"),
        "basicAuth": SecurityScheme(name="basicAuth", type="http", scheme="basic"),
    }
    global_security = ["bearerAuth", "basicAuth"]

    selected = select_security_scheme(schemes, global_security)

    assert selected is not None
    assert selected.name == "bearerAuth"


def test_select_scheme_raises_unsupported_error() -> None:
    """Verify exception is raised with appropriate message when only oauth2/oidc schemes exist."""
    schemes = {
        "oauth2Auth": SecurityScheme(name="oauth2Auth", type="oauth2"),
        "apiKeyAuth": SecurityScheme(
            name="apiKeyAuth",
            type="apiKey",
            location="header",
            param_name="X-API-Key",
        ),
    }
    # Only reference oauth2 in global security
    global_security = ["oauth2Auth"]

    with pytest.raises(UnsupportedSecuritySchemeError) as exc_info:
        select_security_scheme(schemes, global_security)

    error_message = str(exc_info.value)
    assert "oauth2Auth" in error_message
    assert "Supported types are" in error_message


def test_select_scheme_no_schemes_defined() -> None:
    """Return None when no security schemes are defined."""
    schemes = {}
    global_security = []

    selected = select_security_scheme(schemes, global_security)

    assert selected is None


def test_select_scheme_no_global_security() -> None:
    """Return None when no global security is defined."""
    schemes = {
        "bearerAuth": SecurityScheme(name="bearerAuth", type="http", scheme="bearer")
    }
    global_security = []

    selected = select_security_scheme(schemes, global_security)

    assert selected is None


def test_select_scheme_priority_query_over_cookie() -> None:
    """Query apiKey over cookie."""
    schemes = {
        "apiKeyCookie": SecurityScheme(
            name="apiKeyCookie",
            type="apiKey",
            location="cookie",
            param_name="session",
        ),
        "apiKeyQuery": SecurityScheme(
            name="apiKeyQuery",
            type="apiKey",
            location="query",
            param_name="api_key",
        ),
    }
    global_security = ["apiKeyCookie", "apiKeyQuery"]

    selected = select_security_scheme(schemes, global_security)

    assert selected is not None
    assert selected.name == "apiKeyQuery"
    assert selected.location == "query"


def test_select_scheme_priority_cookie_over_mutual_tls() -> None:
    """Cookie apiKey over mutualTLS."""
    schemes = {
        "apiKeyCookie": SecurityScheme(
            name="apiKeyCookie",
            type="apiKey",
            location="cookie",
            param_name="session",
        ),
        "mtlsAuth": SecurityScheme(name="mtlsAuth", type="mutualTLS"),
    }
    global_security = ["apiKeyCookie", "mtlsAuth"]

    selected = select_security_scheme(schemes, global_security)

    assert selected is not None
    assert selected.name == "apiKeyCookie"
    assert selected.location == "cookie"


def test_select_scheme_mutual_tls_selected() -> None:
    """MutualTLS selected when it's the only option."""
    schemes = {"mtlsAuth": SecurityScheme(name="mtlsAuth", type="mutualTLS")}
    global_security = ["mtlsAuth"]

    selected = select_security_scheme(schemes, global_security)

    assert selected is not None
    assert selected.name == "mtlsAuth"
    assert selected.type == "mutualTLS"


def test_select_scheme_no_supported_schemes() -> None:
    """Return None when spec has schemes but none are supported or referenced."""
    schemes = {
        "digestAuth": SecurityScheme(name="digestAuth", type="http", scheme="digest"),
        "oauth2": SecurityScheme(name="oauth2", type="oauth2"),
    }
    global_security = ["digestAuth"]

    selected = select_security_scheme(schemes, global_security)

    assert selected is None


def test_get_scheme_priority_unknown_type() -> None:
    """Test that unknown scheme types get lowest priority."""
    from picofun.security import _get_scheme_priority

    unknown_scheme = SecurityScheme(name="unknownAuth", type="unknown", scheme="digest")

    priority = _get_scheme_priority(unknown_scheme)

    assert priority == 999


def test_get_scheme_type_kebab_api_key() -> None:
    """Convert apiKey type to kebab-case."""
    scheme = SecurityScheme(
        name="apiKeyAuth", type="apiKey", location="header", param_name="X-API-Key"
    )

    result = get_scheme_type_kebab(scheme)

    assert result == "api-key"


def test_get_scheme_type_kebab_mutual_tls() -> None:
    """Convert mutualTLS type to kebab-case with special handling."""
    scheme = SecurityScheme(name="mtlsAuth", type="mutualTLS")

    result = get_scheme_type_kebab(scheme)

    assert result == "mutual-tls"


def test_get_scheme_type_kebab_http() -> None:
    """Convert http type (already lowercase) to kebab-case."""
    scheme = SecurityScheme(name="bearerAuth", type="http", scheme="bearer")

    result = get_scheme_type_kebab(scheme)

    assert result == "http"


def test_get_scheme_type_kebab_oauth2() -> None:
    """Convert oauth2 type to kebab-case."""
    scheme = SecurityScheme(name="oauth", type="oauth2")

    result = get_scheme_type_kebab(scheme)

    assert result == "oauth2"
