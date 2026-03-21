"""Intermediate Representation models for parsed API specifications."""

__author__ = "Dave Hall <skwashd@gmail.com>"
__copyright__ = "Copyright 2026, Dave Hall https://proactiveops.io"
__license__ = "MIT"

from typing import Any

from pydantic import BaseModel


class ServerVariable(BaseModel):
    """A server URL template variable."""

    default: str
    description: str = ""
    enum: list[str] = []


class Server(BaseModel):
    """An API server definition."""

    url: str
    description: str = ""
    variables: dict[str, ServerVariable] = {}


class SecurityScheme(BaseModel):
    """
    A security scheme definition.

    Fields match the existing dataclass in security.py.
    """

    name: str
    type: str
    param_name: str | None = None
    location: str | None = None
    scheme: str | None = None
    bearer_format: str | None = None


class Parameter(BaseModel):
    """An API operation parameter."""

    name: str
    location: str  # "query", "header", "path", "cookie"
    required: bool = False
    description: str = ""
    schema_: dict[str, Any] = {}


class Endpoint(BaseModel):
    """A single API endpoint (one HTTP method on one path)."""

    path: str
    method: str
    operation_id: str | None = None
    summary: str = ""
    description: str = ""
    tags: list[str] = []
    parameters: list[Parameter] = []
    deprecated: bool = False
    extra: dict[str, Any] = {}


class ApiSpec(BaseModel):
    """
    Canonical IR for a parsed API specification.

    Produced by parsers, consumed by generators.
    """

    title: str = ""
    version: str = ""
    source_format: str  # "openapi3", "swagger2", etc.
    servers: list[Server] = []
    security_schemes: list[SecurityScheme] = []
    global_security: list[str] = []
    endpoints: list[Endpoint] = []
