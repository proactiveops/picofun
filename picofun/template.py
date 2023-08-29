"""Template loader for Jinja2 templates."""
import os
import typing

import jinja2


class Template:

    """Manages Jinja2 templates."""

    def __init__(self, base_path: str | None = "") -> None:
        """Initialise TemplateLoader."""
        if not os.path.isabs(base_path):
            base_path = os.path.join(os.getcwd(), base_path)

        path = os.path.realpath(base_path)

        self._environment = (
            jinja2.Environment(  # noqa: S701 We're not generating HTML # nosec
                loader=jinja2.FileSystemLoader(path)
            )
        )

        self.templates = {}

    def get(self, filename: str) -> jinja2.Template:
        """Get a template by filename."""
        if filename not in self.templates:
            try:
                self.templates[filename] = self._environment.get_template(filename)
            except jinja2.exceptions.TemplateNotFound as e:
                raise FileNotFoundError(e.name) from e

        return self.templates[filename]

    def render(self, filename: str, **kwargs: dict[str : typing.Any]) -> str:
        """Render a template by filename."""
        return self.get(filename).render(**kwargs)
