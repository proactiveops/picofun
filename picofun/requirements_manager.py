"""Manage requirements.txt. file contents."""

import os
import re


class RequirementsManager:

    """Manage the requirements file."""

    def __init__(self, path: str) -> None:
        """Initialise the requirements manager."""
        self._path = path
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        self._requirements = self._load()

    def _load(self) -> list[str]:
        """Load the requirements file."""
        requirements = []
        if os.path.isfile(self._path):
            with open(self._path) as file:
                requirements = [line.strip() for line in file.readlines()]

        return requirements

    def save(self) -> None:
        """Save the requirements file."""
        with open(self._path, "w") as file:
            file.write("".join(self._requirements))

    def update(self, package: str, version: str) -> str:
        """Update the requirements file."""
        package = "picorun"
        # Subset of https://pip.pypa.io/en/stable/reference/requirement-specifiers/#requirement-specifiers
        regex = re.compile(rf"{package}\s?([~<>=]?=?|$)")

        found = False
        for line in self._requirements:
            if regex.match(line):
                found = True
                break

        if not found:
            self._requirements.append(f"{package}=={version}")
            self._requirements.sort()
