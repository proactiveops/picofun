"""CDK generator."""

__author__ = "Dave Hall <skwashd@gmail.com>"
__copyright__ = "Copyright 2023 - 2026, Dave Hall https://proactiveops.io"
__license__ = "MIT"

import logging
import os

import picofun.iac.base

logger = logging.getLogger(__name__)


class CdkGenerator(picofun.iac.base.BaseGenerator):
    """CDK generator."""

    def generate(
        self,
        lambdas: list[str],
        auth_enabled: bool = False,
        auth_scheme_type: str | None = None,
        auth_scheme_name: str | None = None,
        auth_ttl: int = 300,
    ) -> None:
        """Generate CDK construct for the Lambda functions."""
        template = self._template.get("construct.py.j2")
        context = self._render_context(
            lambdas, auth_enabled, auth_scheme_type, auth_scheme_name, auth_ttl
        )

        cdk_content = template.render(**context)
        output_file = os.path.join(self._config.output_dir, "construct.py")
        with open(output_file, "w") as cdk_file:
            cdk_file.write(cdk_content)

        logger.info("Generated CDK construct: %s", output_file)
