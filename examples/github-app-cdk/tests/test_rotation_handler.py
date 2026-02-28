"""Tests for the GitHub App token rotation handler."""

import json
import time
from unittest.mock import MagicMock, patch

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from rotation.handler import (
    _generate_jwt,
    _get_installation_id,
    _get_installation_token,
    handler,
)


@pytest.fixture(scope="module")
def rsa_key_pair() -> tuple[str, str]:
    """Generate a real RSA key pair for testing."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    public_pem = (
        private_key.public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode()
    )
    return private_pem, public_pem


@pytest.fixture(scope="module")
def test_private_key(rsa_key_pair: tuple[str, str]) -> str:
    """Return the private key PEM string."""
    return rsa_key_pair[0]


def test_generate_jwt_produces_valid_token(rsa_key_pair: tuple[str, str]) -> None:
    """Test that _generate_jwt produces a valid RS256-signed JWT."""
    private_pem, public_pem = rsa_key_pair
    token = _generate_jwt("12345", private_pem)

    decoded = jwt.decode(token, public_pem, algorithms=["RS256"])
    assert decoded["iss"] == "12345"


def test_generate_jwt_has_correct_claims(rsa_key_pair: tuple[str, str]) -> None:
    """Test that the JWT has correct iat, exp, and iss claims."""
    private_pem, public_pem = rsa_key_pair
    before = int(time.time())
    token = _generate_jwt("99999", private_pem)
    after = int(time.time())

    decoded = jwt.decode(
        token, public_pem, algorithms=["RS256"], options={"verify_exp": False}
    )

    assert decoded["iss"] == "99999"
    # iat should be ~60 seconds before now
    assert before - 61 <= decoded["iat"] <= after - 59
    # exp should be ~10 minutes from now
    assert before + 599 <= decoded["exp"] <= after + 601


@patch("rotation.handler.http")
def test_get_installation_id_success(mock_http: MagicMock) -> None:
    """Test successful installation ID discovery."""
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.data = json.dumps([{"id": 789, "app_id": 12345}]).encode()
    mock_http.request.return_value = mock_response

    result = _get_installation_id("jwt_token_here")

    assert result == "789"
    mock_http.request.assert_called_once_with(
        "GET",
        "https://api.github.com/app/installations",
        headers={
            "Authorization": "Bearer jwt_token_here",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )


@patch("rotation.handler.http")
def test_get_installation_id_raises_on_empty(mock_http: MagicMock) -> None:
    """Test that _get_installation_id raises when no installations found."""
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.data = json.dumps([]).encode()
    mock_http.request.return_value = mock_response

    with pytest.raises(RuntimeError, match="No installations found"):
        _get_installation_id("jwt_token_here")


@patch("rotation.handler.http")
def test_get_installation_id_raises_on_error(mock_http: MagicMock) -> None:
    """Test that _get_installation_id raises on non-200 responses."""
    mock_response = MagicMock()
    mock_response.status = 401
    mock_response.data = b"Unauthorized"
    mock_http.request.return_value = mock_response

    with pytest.raises(RuntimeError, match="Failed to list installations"):
        _get_installation_id("bad_jwt")


@patch("rotation.handler.http")
def test_get_installation_token_success(mock_http: MagicMock) -> None:
    """Test successful installation token retrieval."""
    mock_response = MagicMock()
    mock_response.status = 201
    mock_response.data = json.dumps({"token": "ghs_abc123"}).encode()
    mock_http.request.return_value = mock_response

    result = _get_installation_token("jwt_token_here", "456")

    assert result == "ghs_abc123"
    mock_http.request.assert_called_once_with(
        "POST",
        "https://api.github.com/app/installations/456/access_tokens",
        headers={
            "Authorization": "Bearer jwt_token_here",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )


@patch("rotation.handler.http")
def test_get_installation_token_raises_on_error(mock_http: MagicMock) -> None:
    """Test that _get_installation_token raises on non-201 responses."""
    mock_response = MagicMock()
    mock_response.status = 401
    mock_response.data = b"Unauthorized"
    mock_http.request.return_value = mock_response

    with pytest.raises(RuntimeError, match="Failed to get installation token"):
        _get_installation_token("bad_jwt", "456")


@patch("rotation.handler.sm_client")
@patch("rotation.handler.http")
def test_handler_end_to_end(
    mock_http: MagicMock, mock_sm: MagicMock, test_private_key: str
) -> None:
    """Test the handler orchestrates the full token rotation flow."""
    mock_sm.get_secret_value.return_value = {
        "SecretString": json.dumps(
            {
                "private_key": test_private_key,
                "app_id": "12345",
                "installation_id": "789",
            }
        )
    }

    mock_response = MagicMock()
    mock_response.status = 201
    mock_response.data = json.dumps({"token": "ghs_new_token"}).encode()
    mock_http.request.return_value = mock_response

    result = handler({}, None)

    assert result == {"status": "ok"}

    # Verify secret read
    mock_sm.get_secret_value.assert_called_once_with(
        SecretId="picofun/githubapp/app-credentials"
    )

    # Verify token written to Secrets Manager
    mock_sm.put_secret_value.assert_called_once_with(
        SecretId="picofun/githubapp/token",
        SecretString="ghs_new_token",
    )


@patch("rotation.handler.sm_client")
@patch("rotation.handler.http")
def test_handler_auto_discovers_installation_id(
    mock_http: MagicMock, mock_sm: MagicMock, test_private_key: str
) -> None:
    """Test the handler auto-discovers installation_id when not in creds."""
    mock_sm.get_secret_value.return_value = {
        "SecretString": json.dumps(
            {
                "private_key": test_private_key,
                "app_id": "12345",
            }
        )
    }

    # First call: GET /app/installations (discovery)
    installations_response = MagicMock()
    installations_response.status = 200
    installations_response.data = json.dumps([{"id": 789}]).encode()

    # Second call: POST /app/installations/789/access_tokens
    token_response = MagicMock()
    token_response.status = 201
    token_response.data = json.dumps({"token": "ghs_discovered"}).encode()

    mock_http.request.side_effect = [installations_response, token_response]

    result = handler({}, None)

    assert result == {"status": "ok"}
    assert mock_http.request.call_count == 2
    mock_sm.put_secret_value.assert_called_once_with(
        SecretId="picofun/githubapp/token",
        SecretString="ghs_discovered",
    )
