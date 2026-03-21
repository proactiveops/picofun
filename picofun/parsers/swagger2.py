"""Swagger 2.0 parser."""

__author__ = "Dave Hall <skwashd@gmail.com>"
__copyright__ = "Copyright 2026, Dave Hall https://proactiveops.io"
__license__ = "MIT"

from picofun.models import (
    ApiSpec,
    Endpoint,
    SecurityScheme,
    Server,
)
from picofun.parsers.base import BaseParser
from picofun.parsers.ref_resolver import resolve_refs

_VALID_METHODS = {"get", "put", "post", "delete", "patch", "head"}


class Swagger2Parser(BaseParser):
    """Parser for Swagger 2.0 specifications."""

    format_name = "swagger2"

    @classmethod
    def can_parse(cls, spec_dict: dict) -> bool:
        """Check for swagger field starting with '2.'."""
        return str(spec_dict.get("swagger", "")).startswith("2.")

    def parse(self, spec_dict: dict) -> ApiSpec:
        """Parse a Swagger 2.0 spec dict into an ApiSpec."""
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
        """Build server URLs from host, basePath, and schemes."""
        host = spec.get("host", "") or "localhost"
        base_path = spec.get("basePath", "/")
        schemes = spec.get("schemes", ["https"])

        servers = []
        for scheme in schemes:
            url = f"{scheme}://{host}{base_path}"
            # Strip trailing slash only if basePath is "/" to avoid double slash
            if url.endswith("/") and url.count("/") > 3:
                url = url.rstrip("/")
            servers.append(Server(url=url))
        return servers

    def _extract_security_schemes(self, spec: dict) -> list[SecurityScheme]:
        """Extract and normalize security definitions."""
        security_defs = spec.get("securityDefinitions", {})

        result = []
        for name, scheme_def in security_defs.items():
            scheme_type = scheme_def.get("type", "")

            # Normalize Swagger 2.0 "basic" type to IR "http" type
            if scheme_type == "basic":
                result.append(
                    SecurityScheme(
                        name=name,
                        type="http",
                        scheme="basic",
                    )
                )
            else:
                result.append(
                    SecurityScheme(
                        name=name,
                        type=scheme_type,
                        param_name=scheme_def.get("name"),
                        location=scheme_def.get("in"),
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
