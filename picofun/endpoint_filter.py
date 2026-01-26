"""Endpoint filtering based on allowlist configuration."""

__author__ = "Dave Hall <skwashd@gmail.com>"
__copyright__ = "Copyright 2026, Dave Hall https://proactiveops.io"
__license__ = "MIT"

import logging
import os
import re
from typing import Any

import yaml

import picofun.errors

logger = logging.getLogger(__name__)


class EndpointFilter:
    """Filters OpenAPI endpoints based on allowlist configuration."""

    def __init__(self, filter_file: str | None = None) -> None:
        """
        Initialize the endpoint filter.

        :param filter_file: Path to the YAML filter file. If None, no filtering is applied.
        """
        self._paths: list[dict[str, Any]] = []
        self._operation_ids: list[str] = []
        self._tags: list[str] = []
        self._has_filters = False

        if filter_file:
            self._load(filter_file)

    def _load(self, filter_file: str) -> None:
        """
        Load and parse the filter file.

        :param filter_file: Path to the YAML filter file.
        :raises EndpointFilterFileNotFoundError: If the file does not exist.
        :raises EndpointFilterInvalidYAMLError: If the file contains invalid YAML.
        :raises EndpointFilterEmptyFileError: If the file is empty or contains no filters.
        """
        if not os.path.isfile(filter_file):
            raise picofun.errors.EndpointFilterFileNotFoundError(filter_file)

        with open(filter_file, "rb") as file:
            try:
                data = yaml.safe_load(file)
            except yaml.YAMLError as e:
                raise picofun.errors.EndpointFilterInvalidYAMLError(e) from e

        if not data:
            raise picofun.errors.EndpointFilterEmptyFileError()

        self._paths = data.get("paths", []) or []
        self._operation_ids = data.get("operationIds", []) or []
        self._tags = data.get("tags", []) or []

        # Normalize methods to lowercase
        for path_entry in self._paths:
            if path_entry.get("methods"):
                path_entry["methods"] = [m.lower() for m in path_entry["methods"]]

        self._has_filters = bool(self._paths or self._operation_ids or self._tags)

        if not self._has_filters:
            raise picofun.errors.EndpointFilterEmptyFileError()

    def _match_path(self, path: str, method: str) -> bool:
        """
        Check if a path/method combination matches any path filter.

        :param path: The OpenAPI path (e.g., "/users/{id}").
        :param method: The HTTP method (lowercase).
        :return: True if the path/method matches a filter.
        """
        for entry in self._paths:
            pattern = entry.get("path", "")
            methods = entry.get("methods")

            if self._glob_match(pattern, path):
                # If methods not specified, all methods allowed
                if not methods:
                    return True
                # If methods specified, check if this method is allowed
                if method in methods:
                    return True

        return False

    def _glob_match(self, pattern: str, path: str) -> bool:
        """
        Match a path against a glob pattern (trailing wildcards only).

        Supports:
        - * matches a single path segment
        - ** matches one or more path segments

        :param pattern: The glob pattern.
        :param path: The path to match.
        :return: True if the path matches the pattern.
        """
        # Exact match (no wildcards)
        if "*" not in pattern:
            return pattern == path

        # Convert glob to regex
        # Escape special regex characters except *
        regex = re.escape(pattern)

        # Handle ** first (must come before * handling)
        # ** matches one or more segments (at least one /)
        regex = regex.replace(r"\*\*", ".+")

        # * matches a single segment (no slashes)
        regex = regex.replace(r"\*", "[^/]+")

        regex = f"^{regex}$"

        return bool(re.match(regex, path))

    def _match_operation_id(self, operation_id: str | None) -> bool:
        """
        Check if an operationId matches the filter.

        :param operation_id: The operationId from the OpenAPI spec.
        :return: True if the operationId matches.
        """
        if not operation_id:
            return False
        return operation_id in self._operation_ids

    def _match_tags(self, endpoint_tags: list[str] | None) -> bool:
        """
        Check if any endpoint tag matches the filter.

        :param endpoint_tags: List of tags from the OpenAPI endpoint.
        :return: True if any tag matches.
        """
        if not endpoint_tags:
            return False
        return bool(set(endpoint_tags) & set(self._tags))

    def is_included(
        self,
        path: str,
        method: str,
        details: dict[str, Any],
    ) -> bool:
        """
        Determine if an endpoint should be included.

        :param path: The OpenAPI path.
        :param method: The HTTP method (will be lowercased).
        :param details: The endpoint details from the OpenAPI spec.
        :return: True if the endpoint should be included.
        """
        # No filters configured = include everything
        if not self._has_filters:
            return True

        method = method.lower()
        operation_id = details.get("operationId")
        endpoint_tags = details.get("tags")

        # OR logic: include if ANY filter matches
        return (
            self._match_path(path, method)
            or self._match_operation_id(operation_id)
            or self._match_tags(endpoint_tags)
        )
