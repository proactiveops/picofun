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


def test_invalid_config_error() -> None:
    """Test InvalidConfigError."""
    with pytest.raises(picofun.errors.InvalidConfigError):
        raise picofun.errors.InvalidConfigError()


def test_invalid_spec_error() -> None:
    """Test InvalidSpecError."""
    with pytest.raises(picofun.errors.InvalidSpecError):
        raise picofun.errors.InvalidSpecError()


def test_unknown_config_value_error() -> None:
    """Test UnknownConfigValueError."""
    with pytest.raises(picofun.errors.UnknownConfigValueError):
        raise picofun.errors.UnknownConfigValueError("missing")


def test_invalid_config_type_error() -> None:
    """Test InvalidConfigTypeError."""
    with pytest.raises(picofun.errors.InvalidConfigTypeError):
        raise picofun.errors.InvalidConfigTypeError("example", [], str)
