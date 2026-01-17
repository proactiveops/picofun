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


class EndpointFilterEmptyFileError(Exception):
    """Exception thrown when the endpoint filter file is empty or contains no filters."""

    def __init__(self) -> None:
        """Initialise EndpointFilterEmptyFileError."""
        super().__init__(
            "Endpoint filter file is empty or contains no filters (paths, operationIds, or tags)"
        )


class EndpointFilterFileNotFoundError(FileNotFoundError):
    """Exception thrown when the endpoint filter file cannot be found."""

    def __init__(self, path: str) -> None:
        """
        Initialise EndpointFilterFileNotFoundError.

        :param path: The path to the filter file.
        """
        super().__init__(f"Endpoint filter file not found: {path}")


class EndpointFilterInvalidYAMLError(Exception):
    """Exception thrown when the endpoint filter file contains invalid YAML."""

    def __init__(self, error: Exception) -> None:
        """
        Initialise EndpointFilterInvalidYAMLError.

        :param error: The YAML parsing error.
        """
        super().__init__(f"Invalid YAML in endpoint filter file: {error}")


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


class InvalidServerConfigError(ValueError):
    """Exception thrown when server config has both url and variables specified."""

    def __init__(self) -> None:
        """Initialise InvalidServerConfigError."""
        super().__init__(
            "Server configuration cannot have both 'url' and 'variables' specified. They are mutually exclusive."
        )


class InvalidSpecError(Exception):
    """Exception thrown when the spec file is not valid JSON or YAML."""

    def __init__(self) -> None:
        """Initialise InvalidSpecError."""
        super().__init__("The spec file isn't valid JSON or YAML")


class MissingServerVariableError(ValueError):
    """Exception thrown when a server variable lacks a default value."""

    def __init__(self, variable: str) -> None:
        """
        Initialise MissingServerVariableError.

        :param variable: The name of the variable missing a default value.
        """
        super().__init__(
            f"Server variable '{variable}' does not have a default value in the spec and was not provided in config."
        )


class UnknownConfigValueError(AttributeError):
    """Exception thrown when an unknown configuration value is specified."""

    def __init__(self) -> None:
        """Initialise UnknownConfigValueError."""
        super().__init__("Invalid property found in config file.")


class UnsupportedSecuritySchemeError(Exception):
    """Exception thrown when only unsupported security schemes are found."""

    def __init__(self, schemes: list[str]) -> None:
        """
        Initialise UnsupportedSecuritySchemeError.

        :param schemes: List of unsupported scheme names found.
        """
        scheme_list = ", ".join(schemes)
        super().__init__(
            f"Only unsupported security schemes found: {scheme_list}. "
            f"Supported types are: apiKey, http (basic/bearer), mutualTLS."
        )


class UnknownServerVariableError(ValueError):
    """Exception thrown when a config variable is not in the spec's server object."""

    def __init__(self, variable: str, available_variables: list[str]) -> None:
        """
        Initialise UnknownServerVariableError.

        :param variable: The unknown variable name.
        :param available_variables: List of available variables in the spec.
        """
        available = ", ".join(available_variables) if available_variables else "none"
        super().__init__(
            f"Server variable '{variable}' in config is not defined in the spec. Available variables: {available}"
        )
