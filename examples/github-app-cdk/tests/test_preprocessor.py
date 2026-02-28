"""Tests for the GitHub App preprocessor."""

import sys
from types import ModuleType
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture


@pytest.fixture(autouse=True)
def _mock_picorun(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mock the picorun module so the preprocessor can be imported without it installed."""
    picorun_mock = ModuleType("picorun")
    picorun_mock.ApiRequestArgs = type("ApiRequestArgs", (), {})
    monkeypatch.setitem(sys.modules, "picorun", picorun_mock)


@pytest.fixture
def mock_get_secret(mocker: MockerFixture) -> MagicMock:
    """Mock aws_lambda_powertools.utilities.parameters.get_secret."""
    return mocker.patch(
        "aws_lambda_powertools.utilities.parameters.get_secret",
        return_value="ghs_test_installation_token_123",
    )


@pytest.fixture
def api_request_args() -> MagicMock:
    """Create a mock ApiRequestArgs object."""
    args = MagicMock()
    args.headers = {}
    return args


def test_preprocess_sets_authorization_header(
    mock_get_secret: MagicMock, api_request_args: MagicMock
) -> None:
    """Test that preprocess sets the correct Authorization header."""
    from helpers.github_auth.preprocessor import preprocess

    result = preprocess(api_request_args)

    assert result.headers["Authorization"] == "Bearer ghs_test_installation_token_123"


def test_preprocess_sets_accept_header(
    mock_get_secret: MagicMock, api_request_args: MagicMock
) -> None:
    """Test that preprocess sets the Accept header."""
    from helpers.github_auth.preprocessor import preprocess

    result = preprocess(api_request_args)

    assert result.headers["Accept"] == "application/vnd.github+json"


def test_preprocess_sets_api_version_header(
    mock_get_secret: MagicMock, api_request_args: MagicMock
) -> None:
    """Test that preprocess sets the X-GitHub-Api-Version header."""
    from helpers.github_auth.preprocessor import preprocess

    result = preprocess(api_request_args)

    assert result.headers["X-GitHub-Api-Version"] == "2022-11-28"


def test_preprocess_reads_correct_secret(
    mock_get_secret: MagicMock, api_request_args: MagicMock
) -> None:
    """Test that preprocess reads from the correct Secrets Manager secret."""
    from helpers.github_auth.preprocessor import preprocess

    preprocess(api_request_args)

    mock_get_secret.assert_called_once_with("picofun/githubapp/token", max_age=300)


def test_preprocess_uses_cache_ttl(
    mock_get_secret: MagicMock, api_request_args: MagicMock
) -> None:
    """Test that preprocess passes max_age=300 for 5-minute caching."""
    from helpers.github_auth.preprocessor import preprocess

    preprocess(api_request_args)

    call_kwargs = mock_get_secret.call_args
    assert call_kwargs[1]["max_age"] == 300


def test_preprocess_returns_args(
    mock_get_secret: MagicMock, api_request_args: MagicMock
) -> None:
    """Test that preprocess returns the modified args object."""
    from helpers.github_auth.preprocessor import preprocess

    result = preprocess(api_request_args)

    assert result is api_request_args
