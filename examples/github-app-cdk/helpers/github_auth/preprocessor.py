"""Preprocessor for GitHub API requests using GitHub App authentication."""

__author__ = "Dave Hall <skwashd@gmail.com>"
__copyright__ = "Copyright 2024 - 2026, Dave Hall https://proactiveops.io"
__license__ = "MIT"

import aws_lambda_powertools.utilities.parameters
import picorun


def get_token(force_fetch: bool = False) -> str:
    """
    Fetch the GitHub App installation token from Secrets Manager.

    Args:
        force_fetch: If True, bypass cache and fetch fresh token

    Returns:
        The installation token

    """
    return aws_lambda_powertools.utilities.parameters.get_secret(
        "picofun/githubapp/token", max_age=300, force_fetch=force_fetch
    )


def preprocess(
    args: picorun.ApiRequestArgs, force_fetch: bool = False
) -> picorun.ApiRequestArgs:
    """
    Preprocess the request arguments with GitHub App installation token.

    Args:
        args: The API request arguments
        force_fetch: If True, bypass cache and fetch fresh token

    Returns:
        Modified request arguments with authentication headers

    """
    token = get_token(force_fetch=force_fetch)
    args.headers["Authorization"] = f"Bearer {token}"
    args.headers["Accept"] = "application/vnd.github+json"
    args.headers["X-GitHub-Api-Version"] = "2022-11-28"
    return args
