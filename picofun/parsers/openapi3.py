"""OpenAPI 3.x parser."""

__author__ = "Dave Hall <skwashd@gmail.com>"
__copyright__ = "Copyright 2026, Dave Hall https://proactiveops.io"
__license__ = "MIT"

from picofun.models import (
    ApiSpec,
    Endpoint,
    SecurityScheme,
    Server,
    ServerVariable,
)
from picofun.parsers.base import BaseParser
from picofun.parsers.ref_resolver import resolve_refs

_VALID_METHODS = {"get", "put", "post", "delete", "patch", "head"}


class OpenAPI3Parser(BaseParser):
    """Parser for OpenAPI 3.x specifications."""

    format_name = "openapi3"

    @classmethod
    def can_parse(cls, spec_dict: dict) -> bool:
        """Check for openapi field starting with '3.'."""
        return str(spec_dict.get("openapi", "")).startswith("3.")

    def parse(self, spec_dict: dict) -> ApiSpec:
        """Parse an OpenAPI 3.x spec dict into an ApiSpec."""
        resolved = resolve_refs(spec_dict)

        info = resolved.get("info", {})
        title = info.get("title", "")
        version = info.get("version", "")

        servers = self._extract_servers(resolved)
        security_schemes = self._extract_security_schemes(resolved)
        global_security = self._extract_global_security(resolved)
        endpoints = self._extract_endpoints(resolved)

        return ApiSpec(
            title=title,
            version=version,
            source_format=self.format_name,
            servers=servers,
            security_schemes=security_schemes,
            global_security=global_security,
            endpoints=endpoints,
        )

    def _extract_servers(self, spec: dict) -> list[Server]:
        """Extract server definitions from the spec."""
        servers = []
        for server_def in spec.get("servers", []):
            variables = {}
            for var_name, var_def in server_def.get("variables", {}).items():
                variables[var_name] = ServerVariable(
                    default=var_def.get("default", ""),
                    description=var_def.get("description", ""),
                    enum=var_def.get("enum", []),
                )
            servers.append(
                Server(
                    url=server_def.get("url", ""),
                    description=server_def.get("description", ""),
                    variables=variables,
                )
            )
        return servers

    def _extract_security_schemes(self, spec: dict) -> list[SecurityScheme]:
        """Extract security scheme definitions from components."""
        components = spec.get("components", {})
        security_schemes = components.get("securitySchemes", {})

        result = []
        for name, scheme_def in security_schemes.items():
            result.append(
                SecurityScheme(
                    name=name,
                    type=scheme_def.get("type", ""),
                    param_name=scheme_def.get("name"),
                    location=scheme_def.get("in"),
                    scheme=scheme_def.get("scheme"),
                    bearer_format=scheme_def.get("bearerFormat"),
                )
            )
        return result

    def _extract_global_security(self, spec: dict) -> list[str]:
        """Extract global security requirement names."""
        security = spec.get("security", [])
        scheme_names = []
        for requirement in security:
            scheme_names.extend(requirement.keys())
        return scheme_names

    def _extract_endpoints(self, spec: dict) -> list[Endpoint]:
        """Extract endpoints from paths."""
        endpoints = []
        for path, path_details in spec.get("paths", {}).items():
            for method, details in path_details.items():
                if method not in _VALID_METHODS:
                    continue
                endpoints.append(
                    Endpoint(
                        path=path,
                        method=method,
                        operation_id=details.get("operationId"),
                        summary=details.get("summary", ""),
                        description=details.get("description", ""),
                        tags=details.get("tags", []),
                        deprecated=details.get("deprecated", False),
                        extra=details,
                    )
                )
        return endpoints
