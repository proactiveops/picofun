"""Test the template module."""

import jinja2
import pytest

import picofun.errors
import picofun.template


def test_template_load() -> None:
    """Test loading a template."""
    template = picofun.template.Template("tests/data/templates")
    file = template.get("empty.j2")
    assert type(file) == jinja2.environment.Template


def test_template_load_missing() -> None:
    """Test loading a missing template."""
    template = picofun.template.Template("tests/data")
    with pytest.raises(jinja2.exceptions.TemplateNotFound):
        template.get("missing.j2")
