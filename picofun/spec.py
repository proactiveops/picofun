"""Spec file handler."""
import abc
import errno
import json
import os

import requests
import yaml

import picofun.errors


class SpecLoader(abc.ABC):  # pragma: no cover

    """Loads an OpenAPI spec file."""

    @abc.abstractmethod
    def load(self, location: str) -> str:
        """
        Load a spec file.

        :param location: The location of the file.
        :return: The contents of the file.
        """
        pass


class FileSpecLoader(SpecLoader):

    """Loads an OpenAPI spec file from disk."""

    def load(self, location: str) -> str:
        """
        Load a spec file from disk.

        :param location: The location of the file.
        :raises FileNotFoundError: If the file does not exist.
        :return: The contents of the file.
        """
        if not os.path.exists(location):
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), location)

        with open(location, "rb") as file:
            return file.read()


class HTTPSpecLoader(SpecLoader):

    """Loads an OpenAPI spec file from a URL."""

    def load(self, location: str) -> str:
        """
        Load a spec file from a URL.

        :param location: The location of the file.
        :raises DownloadSpecError: If the file cannot be downloaded.
        :return: The contents of the file.
        """
        try:
            response = requests.get(location, timeout=30)
            response.raise_for_status()
        except requests.HTTPError as e:
            raise picofun.errors.DownloadSpecError(e) from e
        except requests.RequestException as e:
            raise picofun.errors.DownloadSpecError(e) from e

        return response.content


class SpecParser(abc.ABC):  # pragma: no cover

    """Parses an OpenAPI spec file."""

    @abc.abstractmethod
    def parse(self, content: str) -> dict:
        """
        Parse the contents of the spec file.

        :param content: The raw string containing the spec file.
        :raises InvalidSpecError: If the spec file is not valid.
        :return: The contents of the spec file as a dict.
        """
        pass


class JSONSpecParser(SpecParser):

    """Parses an OpenAPI spec file in JSON format."""

    def parse(self, content: str) -> dict:
        """
        Parse the contents of the spec file.

        :param content: The raw string containing the spec file.
        :raises InvalidSpecError: If the spec file is not valid JSON.
        :return: The contents of the spec file as a dict.
        """
        try:
            return json.loads(content)
        except ValueError as e:
            raise picofun.errors.InvalidSpecError() from e


class YAMLSpecParser(SpecParser):

    """Parses an OpenAPI spec file in YAML format."""

    def parse(self, content: str) -> dict:
        """
        Parse the contents of the spec file.

        :param content: The raw string containing the spec file.
        :raises InvalidSpecError: If the spec file is not valid YAML.
        :return: The contents of the spec file as a dict.
        """
        try:
            return yaml.safe_load(content)
        except yaml.YAMLError as e:
            raise picofun.errors.InvalidSpecError() from e


class Spec:

    """Spec file handler."""

    def __init__(self, location: str) -> None:
        """
        Initialise Spec.

        :param source: The location of the spec file. Can be a URL or a path to a file.
        """
        self._content = self._load(location)

    def _load(self, location: str) -> str:
        """
        Load a spec file.

        :param location: The location of the spec file. Can be a URL or a path to a file.
        :return: The contents of the spec file as a string.
        """
        loader = HTTPSpecLoader() if location.startswith("http") else FileSpecLoader()

        return loader.load(location)

    def parse(self) -> dict:
        """
        Parse the contents of the spec file.

        :param content: The raw string containing the spec file
        :raises InvalidSpecError: If the spec file is not valid JSON or YAML
        :return: The contents of the spec file as a dict
        """
        try:
            return JSONSpecParser().parse(self._content)
        except picofun.errors.InvalidSpecError:
            # Try YAML parser if JSON parser fails
            pass

        try:
            return YAMLSpecParser().parse(self._content)
        except picofun.errors.InvalidSpecError as e:
            raise picofun.errors.InvalidSpecError() from e
