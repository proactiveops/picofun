"""Template loader for Jinja2 templates."""

__author__ = "Dave Hall <skwashd@gmail.com>"
__copyright__ = "Copyright 2023 - 2026, Dave Hall https://proactiveops.io"
__license__ = "MIT"

import os

import jinja2


class Template:
    """Manages Jinja2 templates."""

    def __init__(self, base_path: str = "") -> None:
        """Initialise TemplateLoader."""
        if not os.path.isabs(base_path):
            base_path = os.path.join(os.getcwd(), base_path)

        path = os.path.realpath(base_path)
        loader = jinja2.FileSystemLoader(path)
        self._environment = jinja2.Environment(loader=loader)  # noqa: S701 We're not generating HTML # nosec

        self.templates = {}

    def get(self, filename: str) -> jinja2.Template:
        """Get a template by filename."""
        if filename not in self.templates:
            try:
                self.templates[filename] = self._environment.get_template(filename)
            except jinja2.exceptions.TemplateNotFound as e:
                raise FileNotFoundError(e.name) from e

        return self.templates[filename]

    def render(self, filename: str, **kwargs: object) -> str:
        """Render a template by filename."""
        return self.get(filename).render(**kwargs)
