"""Authentication hook code generator."""

__author__ = "Dave Hall <skwashd@gmail.com>"
__copyright__ = "Copyright 2026, Dave Hall https://proactiveops.io"
__license__ = "MIT"

import re

from jinja2 import Environment, FileSystemLoader

from picofun.security import SecurityScheme


def _to_kebab_case(text: str) -> str:
    """
    Convert camelCase or PascalCase to kebab-case.

    Args:
        text: The text to convert

    Returns:
        The text in kebab-case

    """
    # Insert hyphen before uppercase letters and convert to lowercase
    return re.sub(r"(?<!^)(?=[A-Z])", "-", text).lower()


def generate_auth_hooks(
    scheme: SecurityScheme, namespace: str, template_path: str
) -> str:
    """
    Generate Python authentication hook code from a security scheme.

    Creates a preprocessor function that applies the appropriate authentication
    method based on the security scheme type (apiKey, http basic/bearer, mutualTLS).

    Args:
        scheme: The SecurityScheme to generate hooks for
        namespace: The namespace for SSM parameter paths
        template_path: Path to the templates directory

    Returns:
        Generated Python code as a string

    """
    env = Environment(
        loader=FileSystemLoader(template_path),
        autoescape=False,  # noqa: S701  We're generating Python code, not HTML
    )
    template = env.get_template("auth_hooks.py.j2")

    # Convert scheme type to kebab-case for SSM parameter naming
    scheme_type_kebab = _to_kebab_case(scheme.type)

    context = {
        "namespace": namespace,
        "scheme_name": scheme.name,
        "scheme_type": scheme.type,
        "scheme_type_kebab": scheme_type_kebab,
        "scheme_scheme": scheme.scheme,
        "scheme_location": scheme.location,
        "scheme_param_name": scheme.param_name,
        "scheme_bearer_format": scheme.bearer_format,
    }

    return template.render(**context)
