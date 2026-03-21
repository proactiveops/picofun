"""Tests for OpenAPI3 parser."""

import json
from pathlib import Path

import yaml

from picofun.parsers.openapi3 import OpenAPI3Parser

FIXTURES_DIR = Path(__file__).parent / "fixtures"
DATA_DIR = Path(__file__).parent / "data"


class TestCanParse:
    """Tests for OpenAPI3Parser.can_parse()."""

    def test_openapi_300(self) -> None:
        """Verify can_parse returns True for OpenAPI 3.0.0."""
        assert OpenAPI3Parser.can_parse({"openapi": "3.0.0"}) is True

    def test_openapi_310(self) -> None:
        """Verify can_parse returns True for OpenAPI 3.1.0."""
        assert OpenAPI3Parser.can_parse({"openapi": "3.1.0"}) is True

    def test_swagger_20(self) -> None:
        """Verify can_parse returns False for Swagger 2.0."""
        assert OpenAPI3Parser.can_parse({"swagger": "2.0"}) is False

    def test_empty_dict(self) -> None:
        """Verify can_parse returns False for an empty dict."""
        assert OpenAPI3Parser.can_parse({}) is False


class TestServerExtraction:
    """Tests for server extraction."""

    def test_servers_with_variables(self) -> None:
        """Verify servers and variables are extracted correctly."""
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test", "version": "1.0"},
            "servers": [
                {
                    "url": "https://{env}.example.com/v1",
                    "description": "Main server",
                    "variables": {
                        "env": {
                            "default": "prod",
                            "description": "Environment",
                            "enum": ["prod", "staging"],
                        }
                    },
                }
            ],
            "paths": {},
        }
        parser = OpenAPI3Parser()
        result = parser.parse(spec)

        assert len(result.servers) == 1
        server = result.servers[0]
        assert server.url == "https://{env}.example.com/v1"
        assert server.description == "Main server"
        assert "env" in server.variables
        var = server.variables["env"]
        assert var.default == "prod"
        assert var.description == "Environment"
        assert var.enum == ["prod", "staging"]


class TestSecuritySchemeExtraction:
    """Tests for security scheme extraction."""

    def test_bearer_auth_fixture(self) -> None:
        """Verify bearer auth security scheme is extracted from fixture."""
        spec_text = (FIXTURES_DIR / "spec_bearer_auth.yaml").read_text()
        spec = yaml.safe_load(spec_text)

        parser = OpenAPI3Parser()
        result = parser.parse(spec)

        assert len(result.security_schemes) == 1
        scheme = result.security_schemes[0]
        assert scheme.name == "bearerAuth"
        assert scheme.type == "http"
        assert scheme.scheme == "bearer"
        assert scheme.bearer_format == "JWT"


class TestGlobalSecurityExtraction:
    """Tests for global security extraction."""

    def test_global_security(self) -> None:
        """Verify global security requirements are extracted."""
        spec_text = (FIXTURES_DIR / "spec_bearer_auth.yaml").read_text()
        spec = yaml.safe_load(spec_text)

        parser = OpenAPI3Parser()
        result = parser.parse(spec)

        assert result.global_security == ["bearerAuth"]


class TestEndpointExtraction:
    """Tests for endpoint extraction."""

    def test_petstore_endpoints(self) -> None:
        """Verify petstore endpoints are parsed with correct fields."""
        spec_text = (DATA_DIR / "petstore.json").read_text()
        spec = json.loads(spec_text)

        parser = OpenAPI3Parser()
        result = parser.parse(spec)

        assert len(result.endpoints) == 3

        endpoints_by_key = {(e.path, e.method): e for e in result.endpoints}

        get_pets = endpoints_by_key[("/pets", "get")]
        assert get_pets.operation_id == "listPets"
        assert get_pets.summary == "List all pets"
        assert get_pets.tags == ["pets"]

        post_pets = endpoints_by_key[("/pets", "post")]
        assert post_pets.operation_id == "createPets"

        get_pet = endpoints_by_key[("/pets/{petId}", "get")]
        assert get_pet.operation_id == "showPetById"

    def test_extra_contains_raw_dict(self) -> None:
        """Verify endpoint extra field contains the raw operation dict."""
        spec_text = (DATA_DIR / "petstore.json").read_text()
        spec = json.loads(spec_text)

        parser = OpenAPI3Parser()
        result = parser.parse(spec)

        endpoint = result.endpoints[0]
        assert isinstance(endpoint.extra, dict)
        assert "responses" in endpoint.extra

    def test_invalid_methods_filtered(self) -> None:
        """Verify non-HTTP methods like parameters and x-custom are filtered out."""
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test", "version": "1.0"},
            "paths": {
                "/test": {
                    "get": {"operationId": "getTest", "responses": {}},
                    "parameters": [{"name": "id", "in": "query"}],
                    "x-custom": {"something": True},
                }
            },
        }
        parser = OpenAPI3Parser()
        result = parser.parse(spec)

        assert len(result.endpoints) == 1
        assert result.endpoints[0].method == "get"


class TestSourceFormat:
    """Tests for source_format field."""

    def test_source_format_is_openapi3(self) -> None:
        """Verify source_format is set to 'openapi3'."""
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test", "version": "1.0"},
            "paths": {},
        }
        parser = OpenAPI3Parser()
        result = parser.parse(spec)

        assert result.source_format == "openapi3"
