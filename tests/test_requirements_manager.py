"""Test the requirements manager."""

import os
import tempfile

import picofun.requirements_manager


def test_load() -> None:
    """Test loading the requirements file."""
    requirements = picofun.requirements_manager.RequirementsManager(
        "tests/data/requirements.txt"
    )

    assert requirements._requirements == ["picorun==0.1.0", ""]


def test_load_no_file() -> None:
    """Test loading the requirements file."""
    requirements = picofun.requirements_manager.RequirementsManager(
        "tests/data/requirements-not-found.txt"
    )

    assert requirements._requirements == []


def test_update() -> None:
    """Test updating the requirements file."""
    requirements = picofun.requirements_manager.RequirementsManager(
        "tests/data/requirements.txt"
    )
    requirements.update("picorun", "1.0.0")

    assert requirements._requirements == ["picorun==0.1.0", ""]


def test_update_add() -> None:
    """Test updating the requirements file."""
    requirements = picofun.requirements_manager.RequirementsManager(
        "tests/data/requirements-not-found.txt"
    )
    requirements.update("picorun", "1.0.0")

    assert requirements._requirements == ["picorun==1.0.0"]


def test_save() -> None:
    """Test saving the requirements file."""
    (_, filename) = tempfile.mkstemp(".txt", "picofun_requirements")

    requirements = picofun.requirements_manager.RequirementsManager(filename)
    requirements.update("picorun", "0.1.0")
    requirements.save()

    with open(filename) as file:
        contents = file.readlines()

    assert contents == ["picorun==0.1.0"]

    os.remove(filename)
