"""GitHub App installation token rotation Lambda handler."""

__author__ = "Dave Hall <skwashd@gmail.com>"
__copyright__ = "Copyright 2024 - 2026, Dave Hall https://proactiveops.io"
__license__ = "MIT"

import json
import logging
import time

import boto3
import jwt
import urllib3

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

SECRET_PREFIX = "picofun/githubapp"  # noqa: S105

sm_client = boto3.client("secretsmanager")
http = urllib3.PoolManager()


def _generate_jwt(app_id: str, private_key: str) -> str:
    """Generate a JWT for GitHub App authentication."""
    now = int(time.time())
    payload = {
        "iat": now - 60,
        "exp": now + (10 * 60),
        "iss": app_id,
    }
    return jwt.encode(payload, private_key, algorithm="RS256")


def _get_installation_id(jwt_token: str) -> str:
    """Discover the installation ID via the GitHub API."""
    response = http.request(
        "GET",
        "https://api.github.com/app/installations",
        headers={
            "Authorization": f"Bearer {jwt_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    if response.status != 200:
        msg = (
            f"Failed to list installations: {response.status} {response.data.decode()}"
        )
        raise RuntimeError(msg)

    installations = json.loads(response.data.decode())
    if not installations:
        msg = "No installations found for this GitHub App"
        raise RuntimeError(msg)

    return str(installations[0]["id"])


def _get_installation_token(jwt_token: str, installation_id: str) -> str:
    """Exchange a JWT for a GitHub App installation access token."""
    url = f"https://api.github.com/app/installations/{installation_id}/access_tokens"
    response = http.request(
        "POST",
        url,
        headers={
            "Authorization": f"Bearer {jwt_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    if response.status != 201:
        msg = f"Failed to get installation token: {response.status} {response.data.decode()}"
        raise RuntimeError(msg)

    data = json.loads(response.data.decode())
    return data["token"]


def handler(event: dict, context: object) -> dict:
    """Rotate the GitHub App installation token."""
    logger.info("Starting token rotation")

    creds_response = sm_client.get_secret_value(
        SecretId=f"{SECRET_PREFIX}/app-credentials"
    )
    creds = json.loads(creds_response["SecretString"])

    app_id = creds["app_id"]
    private_key = creds["private_key"]

    jwt_token = _generate_jwt(app_id, private_key)

    installation_id = creds.get("installation_id") or _get_installation_id(jwt_token)
    token = _get_installation_token(jwt_token, installation_id)

    sm_client.put_secret_value(
        SecretId=f"{SECRET_PREFIX}/token",
        SecretString=token,
    )

    logger.info("Token rotation complete")
    return {"status": "ok"}
