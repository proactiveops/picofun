"""PicoFun exceptions."""

import typing

import requests


class ConfigFileNotFoundError(FileNotFoundError):

    """Exception thrown when the config file cannot be found."""

    def __init__(self, path: str) -> None:
        """
        Initialise ConfigFileNotFoundError.

        :param path: The path to the config file.
        """
        super().__init__(f"Config file not found: {path}")


class DownloadSpecError(Exception):

    """Exception thrown when requests is unable to download the spec file."""

    def __init__(self: "DownloadSpecError", arg: requests.RequestException) -> None:
        """
        Initialise DownloadSpecError.

        :param arg: The exception thrown.
        """
        super().__init__(f"Request Error: {arg}")


class DownloadSpecHTTPError(Exception):

    """Exception thrown when requests is unable to download the spec file."""

    def __init__(self, arg: requests.HTTPError) -> None:
        """
        Initialise DownloadSpecHTTPError.

        :param arg: The HTTP error thrown.
        """
        super().__init__(
            f"HTTP Error {arg.response.status_code}: {arg.response.reason}"
        )


class InvalidConfigError(Exception):

    """Exception thrown when the config file is not valid TOML."""

    def __init__(self) -> None:
        """Initialise InvalidConfigError."""
        super().__init__("The config file isn't valid TOML")


class InvalidConfigTypeError(TypeError):

    """Exception thrown when an unknown configuration type is specified."""

    def __init__(
        self,
        name: str,
        value: typing.Any,  # noqa ANN001 We need dynamic types as this generic exception.
        expected: typing.Any,  # noqa ANN401 We need dynamic types as this generic exception.
    ) -> None:
        """Initialise InvalidConfigTypeError."""
        super().__init__(
            f"Expected {expected} for {name}, but receieved {type(value)}."
        )


class InvalidSpecError(Exception):

    """Exception thrown when the spec file is not valid JSON or YAML."""

    def __init__(self) -> None:
        """Initialise InvalidSpecError."""
        super().__init__("The spec file isn't valid JSON or YAML")


class UnknownConfigValueError(AttributeError):

    """Exception thrown when an unknown configuration value is specified."""

    def __init__(self, name: str) -> None:
        """Initialise UnknownConfigValueError."""
        super().__init__(name=name, obj="Config")
