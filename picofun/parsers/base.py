"""Base parser class and discovery utilities."""

__author__ = "Dave Hall <skwashd@gmail.com>"
__copyright__ = "Copyright 2026, Dave Hall https://proactiveops.io"
__license__ = "MIT"

import abc
import importlib.metadata

from picofun.errors import (
    DuplicateParserFormatError,
    InvalidParserPluginError,
    UnsupportedSpecFormatError,
)
from picofun.models import ApiSpec


class BaseParser(abc.ABC):
    """Abstract base class for API spec parsers."""

    format_name: str  # "openapi3", "swagger2", etc.

    @classmethod
    @abc.abstractmethod
    def can_parse(cls, spec_dict: dict) -> bool:
        """Check if this parser can handle the given spec dict."""
        ...

    @abc.abstractmethod
    def parse(self, spec_dict: dict) -> ApiSpec:
        """Parse a spec dict into an ApiSpec IR."""
        ...


BUILTIN_PARSERS: list[type[BaseParser]] = []


def _ensure_builtins() -> None:
    """Lazily populate BUILTIN_PARSERS to avoid circular imports."""
    if not BUILTIN_PARSERS:
        from picofun.parsers.openapi3 import OpenAPI3Parser
        from picofun.parsers.swagger2 import Swagger2Parser

        BUILTIN_PARSERS.append(OpenAPI3Parser)
        BUILTIN_PARSERS.append(Swagger2Parser)


def discover_parsers() -> list[type[BaseParser]]:
    """
    Return all available parsers: built-ins + plugins.

    Plugins are discovered via importlib.metadata entry_points
    with group="picofun.parsers". Each entry point must resolve
    to a BaseParser subclass with a unique format_name.

    Raises:
        InvalidParserPluginError: For broken plugins (not a BaseParser subclass).
        DuplicateParserFormatError: For duplicate format_name.

    """
    _ensure_builtins()
    parsers: list[type[BaseParser]] = list(BUILTIN_PARSERS)
    seen_formats: set[str] = {p.format_name for p in parsers}

    eps = importlib.metadata.entry_points(group="picofun.parsers")
    for ep in eps:
        cls = ep.load()
        if not isinstance(cls, type) or not issubclass(cls, BaseParser):
            raise InvalidParserPluginError(ep.name)
        if cls.format_name in seen_formats:
            raise DuplicateParserFormatError(cls.format_name)
        seen_formats.add(cls.format_name)
        parsers.append(cls)

    return parsers


def get_parser(spec_dict: dict, format_override: str | None = None) -> BaseParser:
    """
    Get the appropriate parser for a spec dict.

    If format_override is set, find the parser with that format_name.
    Otherwise, auto-detect by calling can_parse() on each parser
    (built-ins first).

    Args:
        spec_dict: The raw parsed spec dictionary.
        format_override: Optional format name to force a specific parser.

    Returns:
        An instantiated parser.

    Raises:
        UnsupportedSpecFormatError: If no parser can handle the spec.

    """
    parsers = discover_parsers()
    available = [p.format_name for p in parsers]

    if format_override is not None:
        for parser_cls in parsers:
            if parser_cls.format_name == format_override:
                return parser_cls()
        raise UnsupportedSpecFormatError(
            format_name=format_override, available=available
        )

    for parser_cls in parsers:
        if parser_cls.can_parse(spec_dict):
            return parser_cls()

    raise UnsupportedSpecFormatError(available=available)
