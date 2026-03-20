"""Tests for parser discovery and get_parser()."""

from unittest.mock import MagicMock

import pytest

from picofun.errors import (
    DuplicateParserFormatError,
    InvalidParserPluginError,
    UnsupportedSpecFormatError,
)
from picofun.parsers.base import (
    BUILTIN_PARSERS,
    discover_parsers,
    get_parser,
)
from picofun.parsers.openapi3 import OpenAPI3Parser


class TestDiscoverParsers:
    """Tests for discover_parsers()."""

    def test_builtins_include_openapi3(self) -> None:
        """Verify OpenAPI3Parser is in the built-in parsers list."""
        parsers = discover_parsers()
        parser_classes = {type(p) if not isinstance(p, type) else p for p in parsers}
        assert OpenAPI3Parser in parser_classes

    def test_duplicate_format_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verify duplicate format_name raises DuplicateParserFormatError."""
        duplicate_ep = MagicMock()
        duplicate_ep.name = "duplicate-openapi3"
        duplicate_ep.load.return_value = OpenAPI3Parser

        monkeypatch.setattr(
            "picofun.parsers.base.importlib.metadata.entry_points",
            lambda group: [duplicate_ep],
        )
        with pytest.raises(DuplicateParserFormatError):
            discover_parsers()

    def test_broken_plugin_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verify non-BaseParser plugin raises InvalidParserPluginError."""

        class NotAParser:
            pass

        broken_ep = MagicMock()
        broken_ep.name = "broken-plugin"
        broken_ep.load.return_value = NotAParser

        monkeypatch.setattr(
            "picofun.parsers.base.importlib.metadata.entry_points",
            lambda group: [broken_ep],
        )
        with pytest.raises(InvalidParserPluginError):
            discover_parsers()

    def test_valid_plugin_loaded(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verify a valid plugin parser is included in discovered parsers."""
        from picofun.parsers.base import BaseParser

        class FakeSwaggerParser(BaseParser):
            format_name = "swagger2"

            @classmethod
            def can_parse(cls, spec_dict: dict) -> bool:
                """Check for swagger field."""
                return False  # pragma: no cover

            def parse(self, spec_dict: dict) -> None:  # type: ignore[override]
                """Parse a swagger spec."""
                ...

        plugin_ep = MagicMock()
        plugin_ep.name = "swagger2-plugin"
        plugin_ep.load.return_value = FakeSwaggerParser

        monkeypatch.setattr(
            "picofun.parsers.base.importlib.metadata.entry_points",
            lambda group: [plugin_ep],
        )
        parsers = discover_parsers()
        assert FakeSwaggerParser in parsers


class TestGetParser:
    """Tests for get_parser()."""

    def test_auto_detect_openapi3(self) -> None:
        """Verify auto-detection returns OpenAPI3Parser for an OpenAPI 3 spec."""
        parser = get_parser({"openapi": "3.0.0"})
        assert isinstance(parser, OpenAPI3Parser)

    def test_format_override_openapi3(self) -> None:
        """Verify format_override selects OpenAPI3Parser."""
        parser = get_parser({}, format_override="openapi3")
        assert isinstance(parser, OpenAPI3Parser)

    def test_unknown_format_override_raises(self) -> None:
        """Verify unknown format_override raises UnsupportedSpecFormatError."""
        with pytest.raises(UnsupportedSpecFormatError):
            get_parser({}, format_override="graphql")

    def test_unrecognized_spec_raises(self) -> None:
        """Verify unrecognized spec raises UnsupportedSpecFormatError."""
        with pytest.raises(UnsupportedSpecFormatError):
            get_parser({"swagger": "2.0"})


@pytest.fixture(autouse=True)
def _reset_builtins() -> None:
    """Reset BUILTIN_PARSERS between tests to avoid pollution from lazy init."""
    BUILTIN_PARSERS.clear()
