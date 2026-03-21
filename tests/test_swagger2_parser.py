"""Tests for Swagger 2.0 parser."""

import json
from pathlib import Path

import yaml

from picofun.parsers.openapi3 import OpenAPI3Parser
from picofun.parsers.swagger2 import Swagger2Parser

FIXTURES_DIR = Path(__file__).parent / "fixtures"
DATA_DIR = Path(__file__).parent / "data"


class TestCanParse:
    """Tests for Swagger2Parser.can_parse()."""

    def test_swagger_20(self) -> None:
        """Verify can_parse returns True for Swagger 2.0."""
        assert Swagger2Parser.can_parse({"swagger": "2.0"}) is True

    def test_openapi_30(self) -> None:
        """Verify can_parse returns False for OpenAPI 3.0.0."""
        assert Swagger2Parser.can_parse({"openapi": "3.0.0"}) is False

    def test_empty_dict(self) -> None:
        """Verify can_parse returns False for an empty dict."""
        assert Swagger2Parser.can_parse({}) is False


class TestServerURLConstruction:
    """Tests for server URL construction from host/basePath/schemes."""

    def test_full_server_url(self) -> None:
        """Verify host + basePath + scheme produces correct URL."""
        spec = {
            "swagger": "2.0",
            "info": {"title": "Test", "version": "1.0"},
            "host": "api.example.com",
            "basePath": "/v1",
            "schemes": ["https"],
            "paths": {},
        }
        parser = Swagger2Parser()
        result = parser.parse(spec)

        assert len(result.servers) == 1
        assert result.servers[0].url == "https://api.example.com/v1"

    def test_missing_host_defaults_to_localhost(self) -> None:
        """Verify missing host defaults to localhost."""
        spec = {
            "swagger": "2.0",
            "info": {"title": "Test", "version": "1.0"},
            "basePath": "/v1",
            "schemes": ["https"],
            "paths": {},
        }
        parser = Swagger2Parser()
        result = parser.parse(spec)

        assert result.servers[0].url == "https://localhost/v1"

    def test_missing_base_path_defaults_to_slash(self) -> None:
        """Verify missing basePath defaults to /."""
        spec = {
            "swagger": "2.0",
            "info": {"title": "Test", "version": "1.0"},
            "host": "api.example.com",
            "schemes": ["https"],
            "paths": {},
        }
        parser = Swagger2Parser()
        result = parser.parse(spec)

        assert result.servers[0].url == "https://api.example.com/"

    def test_missing_schemes_defaults_to_https(self) -> None:
        """Verify missing schemes defaults to https."""
        spec = {
            "swagger": "2.0",
            "info": {"title": "Test", "version": "1.0"},
            "host": "api.example.com",
            "basePath": "/v1",
            "paths": {},
        }
        parser = Swagger2Parser()
        result = parser.parse(spec)

        assert result.servers[0].url == "https://api.example.com/v1"

    def test_multiple_schemes(self) -> None:
        """Verify multiple schemes create multiple Server objects."""
        spec = {
            "swagger": "2.0",
            "info": {"title": "Test", "version": "1.0"},
            "host": "api.example.com",
            "basePath": "/v1",
            "schemes": ["http", "https"],
            "paths": {},
        }
        parser = Swagger2Parser()
        result = parser.parse(spec)

        assert len(result.servers) == 2
        assert result.servers[0].url == "http://api.example.com/v1"
        assert result.servers[1].url == "https://api.example.com/v1"

    def test_no_double_slash_with_root_base_path(self) -> None:
        """Verify basePath of / doesn't produce double slash."""
        spec = {
            "swagger": "2.0",
            "info": {"title": "Test", "version": "1.0"},
            "host": "api.example.com",
            "basePath": "/",
            "schemes": ["https"],
            "paths": {},
        }
        parser = Swagger2Parser()
        result = parser.parse(spec)

        assert result.servers[0].url == "https://api.example.com/"

    def test_trailing_slash_stripped_from_base_path(self) -> None:
        """Verify trailing slash is stripped from basePath like /v1/."""
        spec = {
            "swagger": "2.0",
            "info": {"title": "Test", "version": "1.0"},
            "host": "api.example.com",
            "basePath": "/v1/",
            "schemes": ["https"],
            "paths": {},
        }
        parser = Swagger2Parser()
        result = parser.parse(spec)

        assert result.servers[0].url == "https://api.example.com/v1"


class TestSecurityDefinitionNormalization:
    """Tests for security definition extraction and normalization."""

    def test_basic_auth_normalized_to_http(self) -> None:
        """Verify type: basic is normalized to type: http, scheme: basic."""
        spec_text = (FIXTURES_DIR / "swagger2_basic_auth.yaml").read_text()
        spec = yaml.safe_load(spec_text)

        parser = Swagger2Parser()
        result = parser.parse(spec)

        assert len(result.security_schemes) == 1
        scheme = result.security_schemes[0]
        assert scheme.name == "basicAuth"
        assert scheme.type == "http"
        assert scheme.scheme == "basic"

    def test_apikey_auth(self) -> None:
        """Verify apiKey auth is extracted correctly."""
        spec_text = (FIXTURES_DIR / "swagger2_apikey_auth.yaml").read_text()
        spec = yaml.safe_load(spec_text)

        parser = Swagger2Parser()
        result = parser.parse(spec)

        assert len(result.security_schemes) == 1
        scheme = result.security_schemes[0]
        assert scheme.name == "apiKeyAuth"
        assert scheme.type == "apiKey"
        assert scheme.location == "header"
        assert scheme.param_name == "X-API-Key"


class TestEndpointExtraction:
    """Tests for endpoint extraction."""

    def test_petstore_endpoints(self) -> None:
        """Verify petstore endpoints are parsed with correct fields."""
        spec_text = (FIXTURES_DIR / "swagger2_petstore.json").read_text()
        spec = json.loads(spec_text)

        parser = Swagger2Parser()
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

    def test_invalid_methods_are_skipped(self) -> None:
        """Verify non-HTTP-method keys in path items are ignored."""
        spec = {
            "swagger": "2.0",
            "info": {"title": "Test", "version": "1.0"},
            "paths": {
                "/test": {
                    "get": {
                        "operationId": "getTest",
                        "responses": {"200": {"description": "OK"}},
                    },
                    "parameters": [
                        {"name": "id", "in": "query", "type": "string"},
                    ],
                    "x-custom-extension": {"foo": "bar"},
                },
            },
        }
        parser = Swagger2Parser()
        result = parser.parse(spec)

        assert len(result.endpoints) == 1
        assert result.endpoints[0].method == "get"


class TestEquivalence:
    """Tests for equivalence between Swagger 2.0 and OpenAPI 3.0 parsing."""

    def test_petstore_endpoints_match(self) -> None:
        """Verify Swagger 2.0 and OpenAPI 3.0 petstore produce matching endpoints."""
        swagger_text = (FIXTURES_DIR / "swagger2_petstore.json").read_text()
        swagger_spec = json.loads(swagger_text)
        swagger_result = Swagger2Parser().parse(swagger_spec)

        openapi_text = (DATA_DIR / "petstore.json").read_text()
        openapi_spec = json.loads(openapi_text)
        openapi_result = OpenAPI3Parser().parse(openapi_spec)

        assert len(swagger_result.endpoints) == len(openapi_result.endpoints)

        swagger_keys = {
            (e.path, e.method, e.operation_id, e.summary, tuple(e.tags))
            for e in swagger_result.endpoints
        }
        openapi_keys = {
            (e.path, e.method, e.operation_id, e.summary, tuple(e.tags))
            for e in openapi_result.endpoints
        }
        assert swagger_keys == openapi_keys

    def test_petstore_server_url_equivalent(self) -> None:
        """Verify server URLs are functionally equivalent."""
        swagger_text = (FIXTURES_DIR / "swagger2_petstore.json").read_text()
        swagger_spec = json.loads(swagger_text)
        swagger_result = Swagger2Parser().parse(swagger_spec)

        openapi_text = (DATA_DIR / "petstore.json").read_text()
        openapi_spec = json.loads(openapi_text)
        openapi_result = OpenAPI3Parser().parse(openapi_spec)

        assert swagger_result.servers[0].url == "http://petstore.swagger.io/v1"
        assert openapi_result.servers[0].url == "http://petstore.swagger.io/v1"


class TestSourceFormat:
    """Tests for source_format field."""

    def test_source_format_is_swagger2(self) -> None:
        """Verify source_format is set to 'swagger2'."""
        spec = {
            "swagger": "2.0",
            "info": {"title": "Test", "version": "1.0"},
            "paths": {},
        }
        parser = Swagger2Parser()
        result = parser.parse(spec)

        assert result.source_format == "swagger2"


class TestGlobalSecurity:
    """Tests for global security extraction."""

    def test_global_security_from_apikey_fixture(self) -> None:
        """Verify global security requirements are extracted."""
        spec_text = (FIXTURES_DIR / "swagger2_apikey_auth.yaml").read_text()
        spec = yaml.safe_load(spec_text)

        parser = Swagger2Parser()
        result = parser.parse(spec)

        assert result.global_security == ["apiKeyAuth"]

    def test_global_security_from_basic_auth_fixture(self) -> None:
        """Verify global security requirements are extracted from basic auth fixture."""
        spec_text = (FIXTURES_DIR / "swagger2_basic_auth.yaml").read_text()
        spec = yaml.safe_load(spec_text)

        parser = Swagger2Parser()
        result = parser.parse(spec)

        assert result.global_security == ["basicAuth"]
