"""Template loader for Jinja2 templates."""
import os

from jinja2 import Environment, FileSystemLoader, Template


class Template:

    """Loads Jinja2 templates."""

    def __init__(self, base_path: str | None = "") -> None:
        """Initialise TemplateLoader."""
        if len(base_path) > 0 and base_path[0] != "/":
            base_path = os.path.join(os.getcwd(), base_path)

        path = os.path.realpath(base_path)

        self._environment = Environment(  # noqa: S701 We're not generating HTML
            loader=FileSystemLoader(path)
        )

    def get(self, filename: str) -> Template:
        """Get a template by filename."""
        return self._environment.get_template(filename)
