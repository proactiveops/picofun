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

AWS_POWER_TOOLS_LAYER_ARN = "arn:aws:lambda:us-east-1:017000801446:layer:AWSLambdaPowertoolsPythonV3-python313-arm64:7"


class Config(BaseModel, extra="forbid", validate_assignment=True):
    """Configuration management class."""

    bundle: str = None
    iam_role_prefix: str = "pf-"
    layers: list[str] = [AWS_POWER_TOOLS_LAYER_ARN]
    output_dir: DirectoryPath = os.path.realpath(os.path.join(os.getcwd(), "output"))
    postprocessor: str = ""
    preprocessor: str = ""
    role_permissions_boundary: str = None
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

        try:
            return Config(**contents)
        except ValidationError as e:
            raise picofun.errors.UnknownConfigValueError() from e
