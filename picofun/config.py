"""Configuration handling."""

import os
from typing import Any, ClassVar

import tomli as toml

import picofun.errors


class Config:

    """Configuration management class."""

    _attrs: ClassVar[dict[str:Any]] = {
        "bundle": str,
        "layers": list,
        "output_dir": str,
        "postprocessor": str,
        "preprocessor": str,
        "subnets": list,
        "tags": dict,
        "template_path": str,
    }

    def __init__(self, file_path: str) -> None:
        """
        Initialize the configuration.

        :param file_path: The path to the configuration file.
        """
        self.set_defaults()
        self.load_from_file(file_path)

    def __getattr__(self, name: str) -> str | list | dict[str, Any]:
        """
        Get a configuration value.

        :param name: The name of the configuration value.
        :return: The configuration value.
        """
        if name not in self._attrs:
            raise picofun.errors.UnknownConfigValueError(name)

    def __setattr__(self, name: str, value: str | list | dict[str, Any]) -> None:
        """
        Set a configuration value.

        :param name: The name of the configuration value.
        :param value: The value to set.
        """
        if name not in self._attrs:
            raise picofun.errors.UnknownConfigValueError(name)

        if name == "layers" and isinstance(value, str):
            value = [raw.strip() for raw in value.split(",")]
            if value == [""]:
                value = []

        # First allow layers to be set as a comma separated string and convert it to a list
        if not isinstance(value, self._attrs[name]):
            raise picofun.errors.InvalidConfigTypeError(name, value, self._attrs[name])

        if name == "output_dir":
            value = self._fix_target_path(value)

        self.__dict__[name] = value

    def _fix_target_path(self, output_dir: str = "") -> str:
        """
        Fix the target path to ensure it is absolute.

        :param output_dir: The name of the output directory
        :return: The absolute path to the output directory
        """
        if not output_dir:
            output_dir = ""

        if output_dir.startswith("/"):
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

    def merge(self, **kwargs: dict[str, Any]) -> None:
        """
        Merge the configuration with the CLI arguments.

        :param kwargs: The CLI arguments.
        """
        for key in kwargs:
            if key not in self._attrs:
                raise picofun.errors.UnknownConfigValueError(key)

            if kwargs[key] is not None:
                setattr(self, key, kwargs[key])

    def set_defaults(self) -> None:
        """Set the default values for the configuration."""
        defaults = {
            "bundle": None,
            "layers": [],
            "output_dir": os.path.realpath(os.path.join(os.getcwd(), "output")),
            "postprocessor": "",
            "preprocessor": "",
            "subnets": [],
            "tags": {},
            "template_path": "templates",
        }

        for key in defaults:
            self.__dict__[key] = defaults[key]

    def asdict(self) -> dict[str, Any]:
        """
        Convert the configuration to a dictionary.

        :return: The configuration dictionary.
        """
        return self.__dict__
