"""Tests for the EndpointFilter class."""

import os
import tempfile

import pytest
import yaml

import picofun.endpoint_filter
import picofun.errors


class TestEndpointFilter:
    """Tests for EndpointFilter."""

    def test_no_filter_file_includes_all(self) -> None:
        """When no filter file is provided, all endpoints are included."""
        ef = picofun.endpoint_filter.EndpointFilter()
        assert ef.is_included("/users", "get", {}) is True
        assert ef.is_included("/anything", "post", {}) is True

    def test_missing_file_raises_error(self) -> None:
        """Missing filter file raises EndpointFilterFileNotFoundError."""
        with pytest.raises(picofun.errors.EndpointFilterFileNotFoundError):
            picofun.endpoint_filter.EndpointFilter("/nonexistent/file.yaml")

    def test_empty_file_raises_error(self) -> None:
        """Empty filter file raises EndpointFilterEmptyFileError."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("")
            f.flush()
            try:
                with pytest.raises(picofun.errors.EndpointFilterEmptyFileError):
                    picofun.endpoint_filter.EndpointFilter(f.name)
            finally:
                os.unlink(f.name)

    def test_no_filters_raises_error(self) -> None:
        """Filter file with empty sections raises EndpointFilterEmptyFileError."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("paths: []\noperationIds: []\ntags: []")
            f.flush()
            try:
                with pytest.raises(picofun.errors.EndpointFilterEmptyFileError):
                    picofun.endpoint_filter.EndpointFilter(f.name)
            finally:
                os.unlink(f.name)

    def test_invalid_yaml_raises_error(self) -> None:
        """Filter file with invalid YAML raises EndpointFilterInvalidYAMLError."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("paths:\n  - this is: [invalid yaml\n    missing bracket")
            f.flush()
            try:
                with pytest.raises(
                    picofun.errors.EndpointFilterInvalidYAMLError
                ) as exc_info:
                    picofun.endpoint_filter.EndpointFilter(f.name)
                assert "Invalid YAML" in str(exc_info.value)
            finally:
                os.unlink(f.name)


class TestPathMatching:
    """Tests for path pattern matching."""

    def _create_filter(self, paths: list) -> picofun.endpoint_filter.EndpointFilter:
        """Create a filter with path entries."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump({"paths": paths}, f)
            f.flush()
            try:
                return picofun.endpoint_filter.EndpointFilter(f.name)
            finally:
                os.unlink(f.name)

    def test_exact_path_match(self) -> None:
        """Exact path matches."""
        ef = self._create_filter([{"path": "/users"}])
        assert ef.is_included("/users", "get", {}) is True
        assert ef.is_included("/users/123", "get", {}) is False

    def test_single_wildcard(self) -> None:
        """Single wildcard matches one segment."""
        ef = self._create_filter([{"path": "/users/*"}])
        assert ef.is_included("/users/123", "get", {}) is True
        assert ef.is_included("/users/abc", "get", {}) is True
        assert ef.is_included("/users", "get", {}) is False
        assert ef.is_included("/users/123/orders", "get", {}) is False

    def test_double_wildcard(self) -> None:
        """Double wildcard matches multiple segments."""
        ef = self._create_filter([{"path": "/users/**"}])
        assert ef.is_included("/users/123", "get", {}) is True
        assert ef.is_included("/users/123/orders", "get", {}) is True
        assert ef.is_included("/users/123/orders/456", "get", {}) is True
        assert ef.is_included("/users", "get", {}) is False

    def test_method_filter(self) -> None:
        """Methods filter restricts which methods are allowed."""
        ef = self._create_filter([{"path": "/users", "methods": ["get", "post"]}])
        assert ef.is_included("/users", "get", {}) is True
        assert ef.is_included("/users", "post", {}) is True
        assert ef.is_included("/users", "delete", {}) is False

    def test_method_case_insensitive(self) -> None:
        """Method matching is case-insensitive."""
        ef = self._create_filter([{"path": "/users", "methods": ["GET", "Post"]}])
        assert ef.is_included("/users", "get", {}) is True
        assert ef.is_included("/users", "post", {}) is True

    def test_no_methods_allows_all(self) -> None:
        """Omitting methods allows all HTTP methods."""
        ef = self._create_filter([{"path": "/users"}])
        assert ef.is_included("/users", "get", {}) is True
        assert ef.is_included("/users", "post", {}) is True
        assert ef.is_included("/users", "delete", {}) is True


class TestOperationIdMatching:
    """Tests for operationId matching."""

    def _create_filter(
        self, operation_ids: list
    ) -> picofun.endpoint_filter.EndpointFilter:
        """Create a filter with operationIds."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump({"operationIds": operation_ids}, f)
            f.flush()
            try:
                return picofun.endpoint_filter.EndpointFilter(f.name)
            finally:
                os.unlink(f.name)

    def test_operation_id_match(self) -> None:
        """Matching operationId includes endpoint."""
        ef = self._create_filter(["getUser", "createUser"])
        assert ef.is_included("/users", "get", {"operationId": "getUser"}) is True
        assert ef.is_included("/users", "post", {"operationId": "createUser"}) is True
        assert (
            ef.is_included("/users", "delete", {"operationId": "deleteUser"}) is False
        )

    def test_no_operation_id_in_details(self) -> None:
        """Endpoint without operationId doesn't match operationId filter."""
        ef = self._create_filter(["getUser"])
        assert ef.is_included("/users", "get", {}) is False


class TestTagMatching:
    """Tests for tag matching."""

    def _create_filter(self, tags: list) -> picofun.endpoint_filter.EndpointFilter:
        """Create a filter with tags."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump({"tags": tags}, f)
            f.flush()
            try:
                return picofun.endpoint_filter.EndpointFilter(f.name)
            finally:
                os.unlink(f.name)

    def test_tag_match(self) -> None:
        """Matching tag includes endpoint."""
        ef = self._create_filter(["public", "v2"])
        assert ef.is_included("/users", "get", {"tags": ["public"]}) is True
        assert ef.is_included("/users", "get", {"tags": ["v2"]}) is True
        assert ef.is_included("/users", "get", {"tags": ["internal"]}) is False

    def test_multiple_tags_any_match(self) -> None:
        """Any matching tag includes the endpoint."""
        ef = self._create_filter(["public"])
        assert ef.is_included("/users", "get", {"tags": ["internal", "public"]}) is True

    def test_no_tags_in_details(self) -> None:
        """Endpoint without tags doesn't match tag filter."""
        ef = self._create_filter(["public"])
        assert ef.is_included("/users", "get", {}) is False


class TestOrLogic:
    """Tests for OR logic between filter sections."""

    def test_path_or_operation_id(self) -> None:
        """Endpoint included if path OR operationId matches."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump({"paths": [{"path": "/users"}], "operationIds": ["getOrders"]}, f)
            f.flush()
            try:
                ef = picofun.endpoint_filter.EndpointFilter(f.name)
            finally:
                os.unlink(f.name)

        # Matches path
        assert ef.is_included("/users", "get", {}) is True
        # Matches operationId
        assert ef.is_included("/orders", "get", {"operationId": "getOrders"}) is True
        # Matches neither
        assert ef.is_included("/products", "get", {}) is False

    def test_all_three_sections(self) -> None:
        """Endpoint included if path OR operationId OR tags matches."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(
                {
                    "paths": [{"path": "/users"}],
                    "operationIds": ["getOrders"],
                    "tags": ["public"],
                },
                f,
            )
            f.flush()
            try:
                ef = picofun.endpoint_filter.EndpointFilter(f.name)
            finally:
                os.unlink(f.name)

        # Matches path only
        assert ef.is_included("/users", "get", {}) is True
        # Matches operationId only
        assert ef.is_included("/orders", "get", {"operationId": "getOrders"}) is True
        # Matches tag only
        assert ef.is_included("/products", "get", {"tags": ["public"]}) is True
        # Matches nothing
        assert ef.is_included("/internal", "get", {"tags": ["internal"]}) is False
