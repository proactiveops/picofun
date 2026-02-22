"""Base class for IaC generators."""

__author__ = "Dave Hall <skwashd@gmail.com>"
__copyright__ = "Copyright 2023 - 2026, Dave Hall https://proactiveops.io"
__license__ = "MIT"

import abc

import picofun.config
import picofun.template


class BaseGenerator(abc.ABC):
    """Base class for IaC generators."""

    def __init__(
        self,
        template: picofun.template.Template,
        namespace: str,
        config: picofun.config.Config,
    ) -> None:
        """Initialize the generator."""
        self._template = template
        self._namespace = namespace
        self._config = config

    @abc.abstractmethod
    def generate(
        self,
        lambdas: list[str],
        auth_enabled: bool = False,
        auth_scheme_type: str | None = None,
        auth_scheme_name: str | None = None,
        auth_ttl: int = 300,
    ) -> None:
        """Generate IaC configuration for the Lambda functions."""

    def _render_context(
        self,
        lambdas: list[str],
        auth_enabled: bool,
        auth_scheme_type: str | None,
        auth_scheme_name: str | None,
        auth_ttl: int,
    ) -> dict:
        """Build the common template rendering context."""
        return {
            "auth_enabled": auth_enabled,
            "auth_scheme_name": auth_scheme_name,
            "auth_scheme_type": auth_scheme_type,
            "auth_ttl": auth_ttl,
            "bundle": self._config.bundle,
            "iam_role_prefix": self._config.iam_role_prefix,
            "lambdas": lambdas,
            "layers": self._config.layers,
            "namespace": self._namespace,
            "role_permissions_boundary": self._config.role_permissions_boundary,
            "subnets": self._config.subnets,
            "tags": self._config.tags,
            "vpc_id": self._config.vpc_id,
            "xray_tracing": self._config.xray_tracing,
        }
