"""Security scheme parsing and selection from OpenAPI specifications."""

__author__ = "Dave Hall <skwashd@gmail.com>"
__copyright__ = "Copyright 2026, Dave Hall https://proactiveops.io"
__license__ = "MIT"

from dataclasses import dataclass

from picofun.errors import UnsupportedSecuritySchemeError


@dataclass
class SecurityScheme:
    """
    Represents an OpenAPI security scheme.

    Attributes:
        name: Reference name from the spec
        type: One of: apiKey, http, mutualTLS, oauth2, openIdConnect
        param_name: For apiKey: the header/query/cookie parameter name
        location: For apiKey: header, query, or cookie
        scheme: For http: basic or bearer
        bearer_format: For http bearer: optional format hint

    """

    name: str
    type: str
    param_name: str | None = None
    location: str | None = None
    scheme: str | None = None
    bearer_format: str | None = None


def extract_security_schemes(spec: dict) -> dict[str, SecurityScheme]:
    """
    Extract security schemes from an OpenAPI specification.

    Parses the components.securitySchemes section of an OpenAPI spec
    and returns a dictionary mapping scheme names to SecurityScheme objects.

    Args:
        spec: The OpenAPI specification as a dictionary

    Returns:
        Dictionary mapping scheme names to SecurityScheme objects.
        Returns empty dict if no securitySchemes are defined.

    """
    components = spec.get("components", {})
    security_schemes = components.get("securitySchemes", {})

    result = {}
    for name, scheme_def in security_schemes.items():
        scheme_type = scheme_def.get("type")

        security_scheme = SecurityScheme(
            name=name,
            type=scheme_type,
            param_name=scheme_def.get("name"),
            location=scheme_def.get("in"),
            scheme=scheme_def.get("scheme"),
            bearer_format=scheme_def.get("bearerFormat"),
        )
        result[name] = security_scheme

    return result


def get_global_security(spec: dict) -> list[str]:
    """
    Extract the top-level security array from an OpenAPI specification.

    Returns the list of security scheme names referenced in the global
    security requirement.

    Args:
        spec: The OpenAPI specification as a dictionary

    Returns:
        List of scheme names referenced in global security.
        Returns empty list if no security is defined.

    """
    security = spec.get("security", [])

    # Each item in security is a dict with scheme names as keys
    scheme_names = []
    for requirement in security:
        scheme_names.extend(requirement.keys())

    return scheme_names


def _is_supported_scheme(scheme: SecurityScheme) -> bool:
    """Check if a security scheme is supported."""
    if scheme.type == "apiKey":
        return True
    if scheme.type == "http" and scheme.scheme in ["basic", "bearer"]:
        return True
    return scheme.type == "mutualTLS"


def _is_unsupported_scheme(scheme: SecurityScheme) -> bool:
    """Check if a security scheme is unsupported (oauth2, openIdConnect)."""
    return scheme.type in ["oauth2", "openIdConnect"]


def _get_scheme_priority(scheme: SecurityScheme) -> int:
    """
    Get priority ranking for a security scheme.

    Lower number = higher priority.
    Priority order: bearer > basic > apiKey header > apiKey query > apiKey cookie > mutualTLS
    """
    if scheme.type == "http" and scheme.scheme == "bearer":
        return 1
    if scheme.type == "http" and scheme.scheme == "basic":
        return 2
    if scheme.type == "apiKey" and scheme.location == "header":
        return 3
    if scheme.type == "apiKey" and scheme.location == "query":
        return 4
    if scheme.type == "apiKey" and scheme.location == "cookie":
        return 5
    if scheme.type == "mutualTLS":
        return 6
    return 999  # Unknown scheme type


def get_scheme_type_kebab(scheme: SecurityScheme) -> str:
    """
    Convert a security scheme type to kebab-case for SSM parameter naming.

    Args:
        scheme: The security scheme

    Returns:
        The scheme type in kebab-case (e.g., 'api-key', 'http', 'mutual-tls')

    """
    type_map = {
        "apiKey": "api-key",
        "http": "http",
        "mutualTLS": "mutual-tls",
    }
    return type_map.get(scheme.type, scheme.type)


def select_security_scheme(
    schemes: dict[str, SecurityScheme], global_security: list[str]
) -> SecurityScheme | None:
    """
    Select the highest priority supported security scheme.

    Filters schemes to those referenced in global_security and supported types,
    then returns the highest priority scheme according to the priority order:
    1. http with scheme: bearer
    2. http with scheme: basic
    3. apiKey in header
    4. apiKey in query
    5. apiKey in cookie
    6. mutualTLS

    Args:
        schemes: Dictionary of available security schemes
        global_security: List of scheme names referenced in global security

    Returns:
        The highest priority SecurityScheme, or None if no schemes are defined

    Raises:
        UnsupportedSecuritySchemeError: If only unsupported schemes (oauth2,
            openIdConnect) are present in global security

    """
    if not schemes:
        return None

    # Filter to only schemes referenced in global security
    referenced_schemes = {
        name: scheme for name, scheme in schemes.items() if name in global_security
    }

    if not referenced_schemes:
        return None

    # Separate supported and unsupported schemes
    supported_schemes = [
        scheme for scheme in referenced_schemes.values() if _is_supported_scheme(scheme)
    ]

    unsupported_scheme_names = [
        name
        for name, scheme in referenced_schemes.items()
        if _is_unsupported_scheme(scheme)
    ]

    # If only unsupported schemes exist, raise error
    if unsupported_scheme_names and not supported_schemes:
        raise UnsupportedSecuritySchemeError(unsupported_scheme_names)

    # If no supported schemes, return None
    if not supported_schemes:
        return None

    # Return scheme with highest priority (lowest priority number)
    return min(supported_schemes, key=_get_scheme_priority)
