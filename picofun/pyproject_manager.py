"""Manage contents of pyproject.toml."""

import os
import re
import textwrap

import tomlkit


class PyProjectManager:
    """Manage the pyproject file."""

    def __init__(self, path: str) -> None:
        """Initialise the pyproject manager."""
        self._path = path
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        self._toml = self._load()

    def _load(self) -> tomlkit.TOMLDocument:
        """
        Load the toml file.

        Returns
        -------
            toml: The parsed toml file.

        """
        toml = None

        if os.path.isfile(self._path):
            with open(self._path) as file:
                toml = tomlkit.load(file)

        if not toml:
            raw = textwrap.dedent("""\
                [project]
                name = "picofun-layer"
                version = "0.1.0"
                description = ""
                requires-python = ">=3.13"
                dependencies = []
                """)

            toml = tomlkit.parse(raw)

        return toml

    def save(self) -> None:
        """Save the toml file."""
        with open(self._path, "w") as file:
            tomlkit.dump(self._toml, file)

    def update(self, package: str, version: str) -> None:
        """
        Update the project dependencies.

        We need PicoRun is installed in the lambda layer. Here we
        check if it is already in the pyproject.toml file. If not, we
        add it with the default version.

        Args:
        ----
            package: The name of the package to update.
            version: The version to set for the package.

        """
        # Subset of https://pip.pypa.io/en/stable/reference/requirement-specifiers/#requirement-specifiers
        regex = re.compile(rf"{package}\s?([~<>=]?=?|$)")

        dependencies = self._toml["project"]["dependencies"]

        matches = list(filter(regex.match, dependencies))

        if len(matches) == 0:
            dependencies.append(f"{package}=={version}")
            dependencies.sort()

        self._toml["project"]["dependencies"] = dependencies
