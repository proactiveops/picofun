"""Tests for picofun exceptions."""

import pytest
import requests.exceptions
import requests.models

import picofun.errors


def test_config_file_not_found_error() -> None:
    """Test ConfigFileError."""
    with pytest.raises(picofun.errors.ConfigFileNotFoundError):
        raise picofun.errors.ConfigFileNotFoundError("missing.toml")


def test_download_spec_error() -> None:
    """Test DownloadSpecError."""
    exception = requests.exceptions.RequestException()
    with pytest.raises(picofun.errors.DownloadSpecError):
        raise picofun.errors.DownloadSpecError(exception)


def test_download_spec_http_error() -> None:
    """Test DownloadSpecHTTPError."""
    response = requests.models.Response()
    response.status_code = 404
    response.reason = "Not Found"

    exception = requests.exceptions.HTTPError(response=response)

    with pytest.raises(picofun.errors.DownloadSpecHTTPError):
        raise picofun.errors.DownloadSpecHTTPError(exception)


def test_endpoint_filter_empty_file_error() -> None:
    """Test EndpointFilterEmptyFileError."""
    with pytest.raises(picofun.errors.EndpointFilterEmptyFileError):
        raise picofun.errors.EndpointFilterEmptyFileError()


def test_endpoint_filter_file_not_found_error() -> None:
    """Test EndpointFilterFileNotFoundError."""
    with pytest.raises(picofun.errors.EndpointFilterFileNotFoundError):
        raise picofun.errors.EndpointFilterFileNotFoundError("/path/to/filter.yaml")


def test_endpoint_filter_invalid_yaml_error() -> None:
    """Test EndpointFilterInvalidYAMLError."""
    yaml_error = Exception("could not determine a constructor")
    with pytest.raises(picofun.errors.EndpointFilterInvalidYAMLError):
        raise picofun.errors.EndpointFilterInvalidYAMLError(yaml_error)


def test_invalid_config_error() -> None:
    """Test InvalidConfigError."""
    with pytest.raises(picofun.errors.InvalidConfigError):
        raise picofun.errors.InvalidConfigError()


def test_invalid_config_type_error() -> None:
    """Test InvalidConfigTypeError."""
    with pytest.raises(picofun.errors.InvalidConfigTypeError):
        raise picofun.errors.InvalidConfigTypeError("example", [], str)


def test_invalid_spec_error() -> None:
    """Test InvalidSpecError."""
    with pytest.raises(picofun.errors.InvalidSpecError):
        raise picofun.errors.InvalidSpecError()


def test_unknown_config_value_error() -> None:
    """Test UnknownConfigValueError."""
    with pytest.raises(picofun.errors.UnknownConfigValueError):
        raise picofun.errors.UnknownConfigValueError()
