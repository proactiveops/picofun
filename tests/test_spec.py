"""Test the spec file handler."""


import pytest
import requests

import picofun.errors
import picofun.spec


def mock_requests_get_spec(
    *args: list, **kwargs: dict
) -> "MockResponse":  # noqa: F821 class defined in this function
    """
    Mock requests.get() responses.

    :param args: The positional arguments passed to requests.get().
    :param kwargs: The keyword arguments passed to requests.get().

    :return: A MockResponse object.
    """

    class MockResponse:
        def __init__(self, content: str, status_code: int) -> None:
            """
            Initialise MockResponse.

            :param content: The content of the response.
            :param status_code: The status code of the response.
            """
            self.content = content
            self.status_code = status_code

        def raise_for_status(self) -> None:
            if self.status_code != 200:
                raise requests.HTTPError(self.status_code)

            return

    if args[0] == "https://petstore3.swagger.io/api/v3/openapi.yaml":
        with open("tests/data/petstore.yaml") as file:
            return MockResponse(file.read(), 200)

    if args[0] == "httpinvalid://example.com/":
        raise requests.RequestException()

    return MockResponse("", 404)


def test_spec_parser() -> None:
    """Test the SpecParser interface."""
    with pytest.raises(TypeError):
        picofun.spec.SpecParser()


def test_json_spec_parser() -> None:
    """Test the JSONSpecParser class."""
    parser = picofun.spec.JSONSpecParser()
    assert parser.parse('{"foo": "bar"}') == {"foo": "bar"}


def test_json_spec_parser_invalid_json() -> None:
    """Test the JSONSpecParser class with invalid JSON."""
    parser = picofun.spec.JSONSpecParser()
    with pytest.raises(picofun.errors.InvalidSpecError):
        parser.parse('{"foo": "bar"')


def test_yaml_spec_parser() -> None:
    """Test the YAMLSpecParser class."""
    parser = picofun.spec.YAMLSpecParser()
    assert parser.parse("foo: bar") == {"foo": "bar"}


def test_yaml_spec_parser_invalid_yaml() -> None:
    """Test the YAMLSpecParser class with invalid YAML."""
    parser = picofun.spec.YAMLSpecParser()
    with pytest.raises(picofun.errors.InvalidSpecError):
        parser.parse("foo: b: a: r")


def test_spec_json() -> None:
    """Test the Spec class with JSON."""
    spec = picofun.spec.Spec("tests/data/petstore.json")
    assert spec.parse()["servers"][0]["url"] == "http://petstore.swagger.io/v1"


def test_spec_json_invalid_json() -> None:
    """Test the Spec class with invalid JSON."""
    spec = picofun.spec.Spec("tests/data/broken.json")
    with pytest.raises(picofun.errors.InvalidSpecError):
        spec.parse()


def test_spec_yaml() -> None:
    """Test the Spec class with YAML."""
    spec = picofun.spec.Spec("tests/data/petstore.yaml")
    assert spec.parse()["servers"][0]["url"] == "http://petstore.swagger.io/v1"


def test_spec_yaml_invalid_yaml() -> None:
    """Test the Spec class with invalid YAML."""
    spec = picofun.spec.Spec("tests/data/broken.yaml")
    with pytest.raises(picofun.errors.InvalidSpecError):
        spec.parse()


def test_spec_unknown_file_type() -> None:
    """Test the Spec class with an unknown file type."""
    spec = picofun.spec.Spec("tests/data/lambda.png")
    with pytest.raises(picofun.errors.InvalidSpecError):
        spec.parse()


def test_spec_unknown_file() -> None:
    """Test the Spec class with an unknown file."""
    with pytest.raises(FileNotFoundError):
        picofun.spec.Spec("tests/data/unknown")


def test_spec_http() -> None:
    """Test the Spec class with a URL."""
    import requests

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(requests, "get", mock_requests_get_spec)

    spec = picofun.spec.Spec("https://petstore3.swagger.io/api/v3/openapi.yaml")
    assert spec.parse()["servers"][0]["url"] == "http://petstore.swagger.io/v1"


def test_spec_http_missing() -> None:
    """Test the Spec class with a missing URL."""
    import requests

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(requests, "get", mock_requests_get_spec)

    with pytest.raises(picofun.errors.DownloadSpecError):
        picofun.spec.Spec("https://example.swagger.io/api/v3/missing.json")


def test_spec_http_invalid() -> None:
    """Test the Spec class with a missing URL."""
    import requests

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(requests, "get", mock_requests_get_spec)

    with pytest.raises(picofun.errors.DownloadSpecError):
        picofun.spec.Spec("httpinvalid://example.com/")
