"""Configuration handling."""

import os
import typing
from importlib.resources import files

import tomlkit
from pydantic import (
    BaseModel,
    DirectoryPath,
    ValidationError,
    field_validator,
    model_validator,
)

import picofun.errors

AWS_POWER_TOOLS_LAYER_ARN = "arn:aws:lambda:us-east-1:017000801446:layer:AWSLambdaPowertoolsPythonV3-python313-arm64:27"


class ServerConfig(BaseModel, extra="forbid"):
    """Server configuration for overriding OpenAPI spec server URLs."""

    url: str | None = None
    variables: dict[str, str] | None = None

    @model_validator(mode="after")
    def validate_mutual_exclusivity(self) -> "ServerConfig":
        """
        Ensure url and variables are mutually exclusive.

        Raises
        ------
            InvalidServerConfigError: If both url and variables are specified.

        """
        if self.url is not None and self.variables is not None:
            raise picofun.errors.InvalidServerConfigError()
        return self


class Config(BaseModel, extra="forbid", validate_assignment=True):
    """Configuration management class."""

    auth_enabled: bool = True
    auth_ttl_minutes: int = 5
    bundle: str = None
    iam_role_prefix: str = "pf-"
    include_endpoints: str = None
    layers: list[str] = [AWS_POWER_TOOLS_LAYER_ARN]
    output_dir: DirectoryPath = os.path.realpath(os.path.join(os.getcwd(), "output"))
    postprocessor: str = ""
    preprocessor: str = ""
    role_permissions_boundary: str = None
    server: ServerConfig | None = None
    subnets: list[str] = []
    tags: dict[str, typing.Any] = {}
    template_path: DirectoryPath = os.path.join(files("picofun"), "templates")
    vpc_id: str = None
    xray_tracing: bool = True

    @model_validator(mode="after")
    def validate_subnets_vpc(self) -> "Config":
        """
        Check if subnets and vpc are set together.

        Raises
        ------
            ValueError: If subnets is set without vpc.

        """
        if (self.subnets and not self.vpc_id) or (self.vpc_id and not self.subnets):
            raise ValueError("Both subnets and vpc must be set, if one is set")  # noqa TRY003 This is a valid use case for a ValueError.

        return self

    @model_validator(mode="after")
    def validate_auth_preprocessor(self) -> "Config":
        """
        Check if auth is enabled and preprocessor is set.

        Raises
        ------
            ValueError: If auth_enabled is True and preprocessor is set.

        """
        if self.auth_enabled and self.preprocessor:
            raise ValueError(  # noqa: TRY003 This is a valid use case for a ValueError.
                "Cannot use both auth_enabled and preprocessor. Set auth.enabled=false to use a custom preprocessor."
            )

        return self

    @field_validator("auth_ttl_minutes", mode="before")
    @classmethod
    def validate_auth_ttl(cls: "Config", value: int) -> int:
        """
        Check if auth_ttl_minutes is a positive integer.

        Args:
        ----
            value: The value to validate.

        Returns:
        -------
            int: The validated value.

        Raises:
        ------
            ValueError: If the value is not a positive integer.

        """
        if not isinstance(value, int) or value <= 0:
            raise ValueError("auth_ttl_minutes must be a positive integer")  # noqa TRY003 This is a valid use case for a ValueError.

        return value

    @field_validator("bundle", mode="before")
    @classmethod
    def validate_bundle(cls: "Config", value: str) -> str:
        """
        Check if bundle is a valid path.

        Args:
        ----
            value: The value to validate.

        Returns:
        -------
            str: The validated value.

        """
        if not os.path.isabs(value):
            bundle_path = os.path.realpath(os.path.join(os.getcwd(), value))
        else:
            bundle_path = os.path.realpath(value)

        if not os.path.exists(bundle_path):
            raise ValueError(f"Bundle path not found: {bundle_path}")  # noqa TRY003 This is a valid use case for a ValueError.

        return bundle_path

    @field_validator("include_endpoints", mode="before")
    @classmethod
    def validate_include_endpoints(cls: "Config", value: str) -> str:
        """
        Check if include_endpoints is a valid path.

        Args:
        ----
            value: The value to validate.

        Returns:
        -------
            str: The validated value.

        """
        if not value:
            return value

        if not os.path.isabs(value):
            include_endpoints_path = os.path.realpath(os.path.join(os.getcwd(), value))
        else:
            include_endpoints_path = os.path.realpath(value)

        return include_endpoints_path

    @field_validator("layers", mode="before")
    @classmethod
    def validate_layers(cls: "Config", value: str | list[str]) -> list[str]:
        """
        Check if layers is a list of strings.

        Convert a string to a list of strings if necessary.

        Args:
        ----
            value: The value to validate.

        Returns:
        -------
            list[str]: The validated value.

        """
        layers = []
        print(f"Type: {type(value)} Value: {value}")
        if isinstance(value, str):
            layers = [item.strip() for item in value.split(",") if item.strip()]

        if isinstance(value, list):
            layers = value

        if (
            len([layer for layer in layers if "awslambdapowertools" in layer.lower()])
            == 0
        ):
            layers.insert(0, AWS_POWER_TOOLS_LAYER_ARN)

        return layers

    @field_validator("output_dir", mode="before")
    @classmethod
    def validate_output_dir(cls: "Config", value: str) -> str:
        """
        Check if output_dir is a valid path.

        Args:
        ----
            value: The value to validate.

        Returns:
        -------
            str: The validated value.

        """
        if os.path.isabs(value):
            output_dir = os.path.realpath(value)
        else:
            output_dir = os.path.realpath(os.path.join(os.getcwd(), value))

        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        return output_dir

    @field_validator("subnets", mode="before")
    @classmethod
    def validate_subnets(cls: "Config", value: str | list[str]) -> list[str]:
        """
        Check if subnets is a list of strings.

        Convert a string to a list of strings if necessary.

        Args:
        ----
            value: The value to validate.

        Returns:
        -------
            list[str]: The validated value.

        """
        subnets = []
        if isinstance(value, str):
            subnets = [item.strip() for item in value.split(",") if item.strip()]

        if isinstance(value, list):
            subnets = value

        if len([subnet for subnet in subnets if subnet[:7] != "subnet-"]) != 0:
            raise ValueError("Subnets must be in the format 'subnet-[hex]'")  # noqa TRY003 This is a valid use case for a ValueError.

        return subnets

    @field_validator("template_path", mode="before")
    @classmethod
    def validate_template_path(cls: "Config", value: str) -> str:
        """
        Check if template is a valid path.

        Args:
        ----
            value: The value to validate.

        Returns:
        -------
            str: The validated value.

        """
        if not os.path.isabs(value):
            template_path = os.path.realpath(os.path.join(os.getcwd(), value))
        else:
            template_path = os.path.realpath(value)

        if not os.path.exists(os.path.join(template_path, "main.tf.j2")):
            raise ValueError(f"Template path not found: {template_path}")  # noqa TRY003 This is a valid use case for a ValueError.

        return template_path

    def merge(self, **kwargs: dict[str, typing.Any]) -> None:
        """
        Merge the existing configuration with a dictionary of values.

        Args:
        ----
            kwargs: The CLI arguments.

        """
        # Handle server_url CLI override - it takes precedence and ignores config file
        server_url = kwargs.get("server_url")
        if server_url:
            self.server = ServerConfig(url=server_url)
            # Don't process server_url further
            kwargs = {k: v for k, v in kwargs.items() if k != "server_url"}

        for key in kwargs:
            if kwargs[key]:
                setattr(self, key, kwargs[key])


class ConfigLoader:
    """Configuration management class."""

    def __init__(self, file_path: str | None = None) -> None:
        """
        Initialize the configuration.

        Args:
        ----
            file_path: The path to the configuration file.

        """
        self._config_file = self._get_config_file(file_path)
        self._config = self.load_from_file(self._config_file)

    def _get_config_file(self, config_file: str | None = None) -> str:
        """
        Get the path to the configuration file.

        Args:
        ----
            config_file: The path to the configuration file.

        Returns:
        -------
            The path to the configuration file.

        """
        if not config_file:
            config_file = os.getcwd()

        if os.path.isdir(config_file):
            config_file = os.path.join(config_file, "picofun.toml")

        return config_file

    def get_config(self) -> Config:
        """
        Get the configuration object.

        Returns
        -------
            The configuration object.

        """
        return self._config

    def load_from_file(self, path: str) -> None:
        """
        Load configuration from toml file.

        Args:
        ----
            path: The path to the configuration file.

        Returns:
            The configuration object.

        """
        if not os.path.isfile(path):
            raise picofun.errors.ConfigFileNotFoundError(path=path)

        with open(path, "rb") as file:
            try:
                contents = tomlkit.load(file)
            except tomlkit.exceptions.ParseError as e:
                raise picofun.errors.InvalidConfigError() from e

        # Resolve include_endpoints path relative to config file location
        if contents.get("include_endpoints"):
            include_endpoints = contents["include_endpoints"]
            if not os.path.isabs(include_endpoints):
                config_dir = os.path.dirname(path)
                contents["include_endpoints"] = os.path.join(
                    config_dir, include_endpoints
                )

        # Flatten [auth] section if present
        if "auth" in contents:
            auth_section = contents.pop("auth")
            if "enabled" in auth_section:
                contents["auth_enabled"] = auth_section["enabled"]
            if "ttl_minutes" in auth_section:
                contents["auth_ttl_minutes"] = auth_section["ttl_minutes"]

        try:
            return Config(**contents)
        except ValidationError as e:
            raise picofun.errors.UnknownConfigValueError() from e
