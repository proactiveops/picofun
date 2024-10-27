"""Terraform generator."""

import logging
import os

import picofun.config
import picofun.template

logger = logging.getLogger(__name__)


class TerraformGenerator:
    """Terraform generator."""

    def __init__(
        self,
        template: picofun.template.Template,
        namespace: str,
        config: picofun.config.Config,
    ) -> None:
        """Initialize the terraform generator."""
        self._template = template
        self._namespace = namespace
        self._config = config

    def generate(
        self,
        lambdas: list[str],
    ) -> None:
        """Generate terraform configuration for the Lambda functions."""
        output_dir = self._config.output_dir

        template = self._template.get("main.tf.j2")

        terraform_content = template.render(
            bundle=self._config.bundle,
            iam_role_prefix=self._config.iam_role_prefix,
            lambdas=lambdas,
            layers=self._config.layers,
            namespace=self._namespace,
            role_permissions_boundary=self._config.role_permissions_boundary,
            subnets=self._config.subnets,
            tags=self._config.tags,
            xray_tracing=self._config.xray_tracing,
        )
        output_file = os.path.join(output_dir, "main.tf")
        with open(output_file, "w") as terraform_file:
            terraform_file.write(terraform_content)

        logger.info("Generated terraform: %s", output_file)
