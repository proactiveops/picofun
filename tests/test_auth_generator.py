"""Tests for authentication hook code generator."""

import ast

from picofun.auth_generator import _to_kebab_case, generate_auth_hooks
from picofun.security import SecurityScheme


def test_to_kebab_case_camel() -> None:
    """Test converting camelCase to kebab-case."""
    assert _to_kebab_case("apiKey") == "api-key"
    assert _to_kebab_case("mutualTLS") == "mutual-t-l-s"


def test_to_kebab_case_pascal() -> None:
    """Test converting PascalCase to kebab-case."""
    assert _to_kebab_case("ApiKey") == "api-key"


def test_to_kebab_case_already_lowercase() -> None:
    """Test text that's already lowercase."""
    assert _to_kebab_case("http") == "http"


def test_generate_apikey_header() -> None:
    """Generates correct code for apiKey header."""
    scheme = SecurityScheme(
        name="apiKeyAuth",
        type="apiKey",
        location="header",
        param_name="X-API-Key",
    )

    # Get template path
    from picofun.config import Config
    config = Config()
    template_path = str(config.template_path)

    code = generate_auth_hooks(scheme, "test-namespace", template_path)

    assert "def get_credentials(scheme_name: str) -> dict:" in code
    assert "def preprocessor(request):" in code
    assert '/picorun/test-namespace/credentials-' in code
    assert 'request.headers["X-API-Key"]' in code
    assert 'creds["api_key"]' in code


def test_generate_apikey_query() -> None:
    """Generates correct code for apiKey query."""
    scheme = SecurityScheme(
        name="apiKeyQuery",
        type="apiKey",
        location="query",
        param_name="api_key",
    )

    from picofun.config import Config
    config = Config()
    template_path = str(config.template_path)

    code = generate_auth_hooks(scheme, "test-namespace", template_path)

    assert 'request.params["api_key"]' in code
    assert 'creds["api_key"]' in code


def test_generate_apikey_cookie() -> None:
    """Generates correct code for apiKey cookie."""
    scheme = SecurityScheme(
        name="cookieAuth",
        type="apiKey",
        location="cookie",
        param_name="session_id",
    )

    from picofun.config import Config
    config = Config()
    template_path = str(config.template_path)

    code = generate_auth_hooks(scheme, "test-namespace", template_path)

    assert 'request.cookies["session_id"]' in code
    assert 'creds["api_key"]' in code


def test_generate_http_basic() -> None:
    """Generates correct code for http basic."""
    scheme = SecurityScheme(
        name="basicAuth",
        type="http",
        scheme="basic",
    )

    from picofun.config import Config
    config = Config()
    template_path = str(config.template_path)

    code = generate_auth_hooks(scheme, "test-namespace", template_path)

    assert "import base64" in code
    assert "base64.b64encode" in code
    assert 'creds[\'username\']' in code or 'creds["username"]' in code
    assert 'creds[\'password\']' in code or 'creds["password"]' in code
    assert 'Authorization' in code
    assert 'Basic' in code


def test_generate_http_bearer() -> None:
    """Generates correct code for http bearer."""
    scheme = SecurityScheme(
        name="bearerAuth",
        type="http",
        scheme="bearer",
        bearer_format="JWT",
    )

    from picofun.config import Config
    config = Config()
    template_path = str(config.template_path)

    code = generate_auth_hooks(scheme, "test-namespace", template_path)

    assert 'Authorization' in code
    assert 'Bearer' in code
    assert 'creds[\'token\']' in code or 'creds["token"]' in code


def test_generate_mutual_tls() -> None:
    """Generates correct code for mutualTLS."""
    scheme = SecurityScheme(
        name="mtlsAuth",
        type="mutualTLS",
    )

    from picofun.config import Config
    config = Config()
    template_path = str(config.template_path)

    code = generate_auth_hooks(scheme, "test-namespace", template_path)

    assert '/tmp/picorun_cert.pem' in code
    assert '/tmp/picorun_key.pem' in code
    assert 'request.cert' in code
    assert 'creds["cert"]' in code
    assert 'creds["key"]' in code


def test_generated_code_syntax_valid() -> None:
    """Generated code parses without SyntaxError."""
    scheme = SecurityScheme(
        name="bearerAuth",
        type="http",
        scheme="bearer",
    )

    from picofun.config import Config
    config = Config()
    template_path = str(config.template_path)

    code = generate_auth_hooks(scheme, "test-namespace", template_path)

    # This will raise SyntaxError if code is invalid
    ast.parse(code)


def test_generated_code_has_preprocessor() -> None:
    """Generated code defines preprocessor function."""
    scheme = SecurityScheme(
        name="apiKeyAuth",
        type="apiKey",
        location="header",
        param_name="X-API-Key",
    )

    from picofun.config import Config
    config = Config()
    template_path = str(config.template_path)

    code = generate_auth_hooks(scheme, "test-namespace", template_path)

    tree = ast.parse(code)
    function_names = [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]

    assert 'preprocessor' in function_names
    assert 'get_credentials' in function_names


def test_generated_code_namespace_substitution() -> None:
    """Namespace correctly injected."""
    scheme = SecurityScheme(
        name="testAuth",
        type="apiKey",
        location="header",
        param_name="X-Test",
    )

    from picofun.config import Config
    config = Config()
    template_path = str(config.template_path)

    code = generate_auth_hooks(scheme, "my-service", template_path)

    assert '/picorun/my-service/credentials-' in code


def test_generated_code_scheme_name_substitution() -> None:
    """Scheme name correctly injected."""
    scheme = SecurityScheme(
        name="myCustomAuth",
        type="apiKey",
        location="header",
        param_name="X-Custom",
    )

    from picofun.config import Config
    config = Config()
    template_path = str(config.template_path)

    code = generate_auth_hooks(scheme, "test", template_path)

    assert 'myCustomAuth' in code


def test_generated_code_param_name_substitution() -> None:
    """API key param name correctly injected."""
    scheme = SecurityScheme(
        name="apiKeyAuth",
        type="apiKey",
        location="header",
        param_name="X-Custom-Key",
    )

    from picofun.config import Config
    config = Config()
    template_path = str(config.template_path)

    code = generate_auth_hooks(scheme, "test", template_path)

    assert 'X-Custom-Key' in code
