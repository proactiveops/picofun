"""Lambda generator."""

__author__ = "Dave Hall <skwashd@gmail.com>"
__copyright__ = "Copyright 2023 - 2026, Dave Hall https://proactiveops.io"
__license__ = "MIT"

import hashlib
import logging
import os
import typing

import black

import picofun.config
import picofun.endpoint_filter
import picofun.errors
import picofun.template
from picofun.models import ApiSpec, Endpoint, Server, ServerVariable

logger = logging.getLogger(__name__)

LAMBDA_SUFFIX_LENGTH = 4


class LambdaGenerator:
    """Lambda generator."""

    def __init__(
        self,
        template: picofun.template.Template,
        namespace: str,
        config: picofun.config.Config,
        endpoint_filter: picofun.endpoint_filter.EndpointFilter | None = None,
    ) -> None:
        """Initialize the lambda generator."""
        self._template = template
        self._config = config
        self._config_dict = config.model_dump()
        self._endpoint_filter = (
            endpoint_filter or picofun.endpoint_filter.EndpointFilter()
        )

        self.max_length = 64 - len(f"{namespace}_")
        # Remove one for the underscore between the prefix and the suffix.
        self.prefix_length = self.max_length - LAMBDA_SUFFIX_LENGTH - 1

    def _get_name(self, method: str, path: str) -> str:
        clean_path = path.replace("{", "").replace("}", "")
        lambda_name = f"{method}_{clean_path.replace('/', '_').replace('.', '_').replace('-', '_').strip('_')}"

        if len(lambda_name) > self.max_length:
            suffix = hashlib.sha512(lambda_name.encode()).hexdigest()[
                :LAMBDA_SUFFIX_LENGTH
            ]
            # The underscire adds another character to the length.
            lambda_name = f"{lambda_name[: self.prefix_length]}_{suffix}"

        return lambda_name

    def _validate_config_variables(self, spec_variables: dict[str, ServerVariable]) -> None:
        """
        Validate that config variables exist in spec.

        :param spec_variables: The variables from the Server model.
        :raises UnknownServerVariableError: If a config variable is not in spec.
        """
        if not self._config.server or not self._config.server.variables:
            return

        available_vars = list(spec_variables.keys())
        for var_name in self._config.server.variables:
            if var_name not in spec_variables:
                raise picofun.errors.UnknownServerVariableError(
                    var_name, available_vars
                )

    def _build_variable_values(
        self, spec_variables: dict[str, ServerVariable]
    ) -> dict[str, str]:
        """
        Build final variable values from spec defaults and config overrides.

        :param spec_variables: The variables from the Server model.
        :return: Dictionary of variable names to values.
        """
        final_variables = {}
        for var_name, var_spec in spec_variables.items():
            if (
                self._config.server
                and self._config.server.variables
                and var_name in self._config.server.variables
            ):
                final_variables[var_name] = self._config.server.variables[var_name]
            else:
                # ServerVariable.default is required, so it always exists
                final_variables[var_name] = var_spec.default
        return final_variables

    def _resolve_server_url(self, server: Server) -> str:
        """
        Resolve server URL from spec with config overrides.

        :param server: The Server model from ApiSpec.
        :return: The resolved server URL.
        :raises UnknownServerVariableError: If a config variable is not in spec.
        """
        if self._config.server and self._config.server.url:
            return self._config.server.url

        base_url = server.url
        spec_variables = server.variables

        if not spec_variables:
            if self._config.server and self._config.server.variables:
                raise picofun.errors.UnknownServerVariableError(
                    next(iter(self._config.server.variables.keys())), []
                )
            return base_url

        self._validate_config_variables(spec_variables)
        final_variables = self._build_variable_values(spec_variables)

        resolved_url = base_url
        for var_name, var_value in final_variables.items():
            token = f"{{{var_name}}}"
            resolved_url = resolved_url.replace(token, var_value)

        return resolved_url

    def generate(
        self,
        api_spec: ApiSpec,
    ) -> list[str]:
        """Generate the lambda functions."""
        output_dir = self._config_dict["output_dir"]

        lambda_dir = os.path.join(output_dir, "lambdas")
        if not os.path.exists(lambda_dir):
            os.makedirs(lambda_dir, exist_ok=True)

        base_url = self._resolve_server_url(api_spec.servers[0])

        lambdas = []
        for endpoint in api_spec.endpoints:
            if not self._endpoint_filter.is_included(endpoint):
                logger.debug(
                    "Skipping excluded endpoint: %s %s",
                    endpoint.method.upper(),
                    endpoint.path,
                )
                continue

            lambda_name = self._get_name(endpoint.method, endpoint.path)

            code = self.render(base_url, endpoint)

            script_filename = f"{lambda_name}.py"
            script_path = os.path.join(lambda_dir, script_filename)
            with open(script_path, "w") as file:
                file.write(code)

            logger.info("Generated function: %s", script_path)
            lambdas.append(lambda_name)

        lambdas.sort()
        return lambdas

    def render(self, base_url: str, endpoint: Endpoint) -> str:
        """Render the lambda function."""
        preprocessor_handler = self._config_dict["preprocessor"]
        preprocessor = (
            ".".join(preprocessor_handler.split(".")[:-1])
            if preprocessor_handler
            else None
        )

        postprocessor_handler = self._config_dict["postprocessor"]
        postprocessor = (
            ".".join(postprocessor_handler.split(".")[:-1])
            if postprocessor_handler
            else None
        )

        code = self._template.render(
            "lambda.py.j2",
            base_url=base_url,
            method=endpoint.method,
            path=endpoint.path,
            summary=endpoint.summary,
            details=endpoint.extra,
            preprocessor=preprocessor,
            preprocessor_handler=preprocessor_handler,
            postprocessor=postprocessor,
            postprocessor_handler=postprocessor_handler,
            xray_tracing=self._config_dict["xray_tracing"],
        )
        return black.format_str(code, mode=black.Mode())
