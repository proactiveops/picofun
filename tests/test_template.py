"""Test the template module."""

__author__ = "Dave Hall <skwashd@gmail.com>"
__copyright__ = "Copyright 2023 - 2026, Dave Hall https://proactiveops.io"
__license__ = "MIT"

import jinja2
import pytest

import picofun.errors
import picofun.template


def test_template_load() -> None:
    """Test loading a template."""
    template = picofun.template.Template("tests/data/templates")
    file = template.get("empty.j2")
    assert isinstance(file, jinja2.environment.Template)


def test_template_load_missing() -> None:
    """Test loading a missing template."""
    template = picofun.template.Template("tests/data")
    with pytest.raises(FileNotFoundError):
        template.get("missing.j2")


def test_template_render() -> None:
    """Test rendering a template."""
    template = picofun.template.Template("tests/data/templates")
    assert template.render("empty.j2") == ""


def test_template_fallback_uses_override() -> None:
    """Test that override template is used when present."""
    template = picofun.template.Template(
        "tests/data/templates_override", "tests/data/templates"
    )
    # empty.j2 exists in both, should use the override version
    assert template.render("empty.j2") == "Override of empty template"


def test_template_fallback_uses_default() -> None:
    """Test that default template is used when not in override directory."""
    template = picofun.template.Template(
        "tests/data/templates_override", "tests/data/templates"
    )
    # lambda.py.j2 only exists in default, should fall back to it
    file = template.get("lambda.py.j2")
    assert isinstance(file, jinja2.environment.Template)


def test_template_fallback_custom_only() -> None:
    """Test template that exists only in override directory."""
    template = picofun.template.Template(
        "tests/data/templates_override", "tests/data/templates"
    )
    # custom.j2 only exists in override, should use it
    assert template.render("custom.j2") == "This is a custom template"


def test_template_fallback_missing_both() -> None:
    """Test error when template is missing from both directories."""
    template = picofun.template.Template(
        "tests/data/templates_override", "tests/data/templates"
    )
    # missing.j2 doesn't exist in either directory
    with pytest.raises(FileNotFoundError):
        template.get("missing.j2")


def test_template_without_fallback() -> None:
    """Test that single path still works (backwards compatibility)."""
    template = picofun.template.Template("tests/data/templates")
    file = template.get("empty.j2")
    assert isinstance(file, jinja2.environment.Template)
    assert template.render("empty.j2") == ""
