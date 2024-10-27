"""Configuration handling."""

import os
import typing
from importlib.resources import files

import tomli as toml

import picofun.errors

AWS_POWER_TOOLS_LAYER_ARN = "arn:aws:lambda:us-east-1:017000801446:layer:AWSLambdaPowertoolsPythonV3-python312-arm64:2"


class Config:
    """Configuration management class."""

    _attrs: typing.ClassVar[dict[str : typing.Any]] = {
        "_config_file": str,
        "bundle": str,
        "iam_role_prefix": str,
        "layers": list,
        "output_dir": str,
        "postprocessor": str,
        "preprocessor": str,
        "role_permissions_boundary": str,
        "subnets": list,
        "tags": dict,
        "template_path": str,
        "xray_tracing": bool,
    }

    def __init__(self, file_path: typing.Optional[str] = None) -> None:
        """
        Initialize the configuration.

        :param file_path: The path to the configuration file.
        """
        self.set_defaults()
        self._config_file = self._get_config_file(file_path)
        self.load_from_file(self._config_file)

    def _get_config_file(self, config_file: typing.Optional[str] = None) -> str:
        """Get the path to the configuration file."""
        if not config_file:
            config_file = os.getcwd()

        if os.path.isdir(config_file):
            config_file = os.path.join(config_file, "picofun.toml")

        if os.path.isfile(config_file):
            return config_file

        raise picofun.errors.ConfigFileNotFoundError(config_file)

    def __getattr__(self, name: str) -> str | list | dict[str, typing.Any]:
        """
        Get a configuration value.

        :param name: The name of the configuration value.
        :return: The configuration value.
        """
        if name not in self._attrs:
            raise picofun.errors.UnknownConfigValueError(name)

    def __setattr__(self, name: str, value: str | list | dict[str, typing.Any]) -> None:
        """
        Set a configuration value.

        :param name: The name of the configuration value.
        :param value: The value to set.
        """
        if name not in self._attrs:
            raise picofun.errors.UnknownConfigValueError(name)

        # First allow layers to be set as a comma separated string and convert it to a list
        if name == "layers":
            if isinstance(value, str):
                value = [raw.strip() for raw in value.split(",")]
                if value == [""]:
                    value = []

            if (
                len([item for item in value if "awslambdapowertools" in item.lower()])
                == 0
            ):
                value.append(AWS_POWER_TOOLS_LAYER_ARN)

        if not isinstance(value, self._attrs[name]):
            raise picofun.errors.InvalidConfigTypeError(name, value, self._attrs[name])

        if name == "bundle" and value:
            value = self._fix_bundle_path(value)

        if name == "output_dir":
            value = self._fix_target_path(value)
            # Ensure the path exists
            if not os.path.exists(value):
                os.makedirs(value, exist_ok=True)

        self.__dict__[name] = value

    def _fix_bundle_path(self, bundle_path: str) -> str:
        """
        Fix the bundle path to ensure it is absolute.

        :param bundle_path: The path to the bundle.
        :return: The absolute path to the bundle.
        """
        if not os.path.isabs(bundle_path):
            bundle_path = os.path.join(os.path.dirname(self._config_file), bundle_path)

        return os.path.realpath(bundle_path)

    def _fix_target_path(self, output_dir: str = "") -> str:
        """
        Fix the target path to ensure it is absolute.

        :param output_dir: The name of the output directory
        :return: The absolute path to the output directory
        """
        if os.path.isabs(output_dir):
            return os.path.realpath(output_dir)

        return os.path.realpath(os.path.join(os.getcwd(), output_dir))

    def load_from_file(self, path: str) -> None:
        """
        Load configuration from toml file.

        :param path: The path to the configuration file.
        :return: The configuration.
        """
        if not os.path.isfile(path):
            raise picofun.errors.ConfigFileNotFoundError(path=path)

        with open(path, "rb") as file:
            try:
                file_config = toml.load(file)
            except toml.TOMLDecodeError as e:
                raise picofun.errors.InvalidConfigError() from e

        self.merge(**file_config)

    def merge(self, **kwargs: dict[str, typing.Any]) -> None:
        """
        Merge the configuration with the CLI arguments.

        :param kwargs: The CLI arguments.
        """
        for key in kwargs:
            if key not in self._attrs:
                raise picofun.errors.UnknownConfigValueError(key)

            if kwargs[key]:
                setattr(self, key, kwargs[key])

    def set_defaults(self) -> None:
        """Set the default values for the configuration."""
        defaults = {
            "_config_file": "",
            "bundle": None,
            "iam_role_prefix": "pf-",
            "layers": [AWS_POWER_TOOLS_LAYER_ARN],
            "output_dir": os.path.realpath(os.path.join(os.getcwd(), "output")),
            "postprocessor": "",
            "preprocessor": "",
            "role_permissions_boundary": None,
            "subnets": [],
            "tags": {},
            "template_path": os.path.join(files("picofun"), "templates"),
            "xray_tracing": True,
        }

        for key in defaults:
            self.__dict__[key] = defaults[key]

    def asdict(self) -> dict[str, typing.Any]:
        """
        Convert the configuration to a dictionary.

        :return: The configuration dictionary.
        """
        return self.__dict__
