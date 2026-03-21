"""Security scheme parsing and selection from OpenAPI specifications."""

__author__ = "Dave Hall <skwashd@gmail.com>"
__copyright__ = "Copyright 2026, Dave Hall https://proactiveops.io"
__license__ = "MIT"

from picofun.errors import UnsupportedSecuritySchemeError
from picofun.models import SecurityScheme


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
    schemes: list[SecurityScheme], global_security: list[str]
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
        schemes: List of available security schemes
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
    referenced_schemes = [s for s in schemes if s.name in global_security]

    if not referenced_schemes:
        return None

    # Separate supported and unsupported schemes
    supported_schemes = [
        scheme for scheme in referenced_schemes if _is_supported_scheme(scheme)
    ]

    unsupported_scheme_names = [
        scheme.name for scheme in referenced_schemes if _is_unsupported_scheme(scheme)
    ]

    # If only unsupported schemes exist, raise error
    if unsupported_scheme_names and not supported_schemes:
        raise UnsupportedSecuritySchemeError(unsupported_scheme_names)

    # If no supported schemes, return None
    if not supported_schemes:
        return None

    # Return scheme with highest priority (lowest priority number)
    return min(supported_schemes, key=_get_scheme_priority)
