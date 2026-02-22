"""Terraform generator."""

__author__ = "Dave Hall <skwashd@gmail.com>"
__copyright__ = "Copyright 2023 - 2026, Dave Hall https://proactiveops.io"
__license__ = "MIT"

import logging
import os

import picofun.iac.base

logger = logging.getLogger(__name__)


class TerraformGenerator(picofun.iac.base.BaseGenerator):
    """Terraform generator."""

    def generate(
        self,
        lambdas: list[str],
        auth_enabled: bool = False,
        auth_scheme_type: str | None = None,
        auth_scheme_name: str | None = None,
        auth_ttl: int = 300,
    ) -> None:
        """Generate terraform configuration for the Lambda functions."""
        template = self._template.get("main.tf.j2")
        context = self._render_context(
            lambdas, auth_enabled, auth_scheme_type, auth_scheme_name, auth_ttl
        )

        terraform_content = template.render(**context)
        output_file = os.path.join(self._config.output_dir, "main.tf")
        with open(output_file, "w") as terraform_file:
            terraform_file.write(terraform_content)

        logger.info("Generated terraform: %s", output_file)
