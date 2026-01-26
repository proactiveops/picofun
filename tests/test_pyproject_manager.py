"""Test the pyproject manager."""

__author__ = "Dave Hall <skwashd@gmail.com>"
__copyright__ = "Copyright 2025 - 2026, Dave Hall https://proactiveops.io"
__license__ = "MIT"

import os
import tempfile

import picofun.pyproject_manager


def test_load() -> None:
    """Test loading the requirements file."""
    pyproject = picofun.pyproject_manager.PyProjectManager("tests/data/pyproject.toml")

    assert pyproject._toml["project"]["dependencies"] == ["picorun==0.1.0"]


def test_load_no_file() -> None:
    """Test loading the requirements file."""
    pyproject = picofun.pyproject_manager.PyProjectManager(
        "tests/data/pyproject-not-found.toml"
    )

    assert pyproject._toml["project"]["dependencies"] == []


def test_update() -> None:
    """Test updating the requirements file."""
    pyproject = picofun.pyproject_manager.PyProjectManager("tests/data/pyproject.toml")
    pyproject.update("picorun", "1.0.0")

    assert pyproject._toml["project"]["dependencies"] == ["picorun==0.1.0"]


def test_update_add() -> None:
    """Test updating the requirements file."""
    pyproject = picofun.pyproject_manager.PyProjectManager(
        "tests/data/pyproject-not-found.toml"
    )
    pyproject.update("picorun", "1.0.0")

    assert pyproject._toml["project"]["dependencies"] == ["picorun==1.0.0"]


def test_save() -> None:
    """Test saving the requirements file."""
    (_, filename) = tempfile.mkstemp(".toml", "pyproject")

    pyproject = picofun.pyproject_manager.PyProjectManager(filename)
    pyproject.update("picorun", "0.1.0")
    pyproject.save()

    with open(filename) as file:
        contents = file.readlines()

    assert 'dependencies = ["picorun==0.1.0"]\n' in contents

    os.remove(filename)
