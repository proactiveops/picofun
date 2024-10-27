"""Lambda generator."""

import hashlib
import logging
import os
import typing

import black

import picofun.config
import picofun.template

logger = logging.getLogger(__name__)

LAMBDA_SUFFIX_LENGTH = 4


class LambdaGenerator:
    """Lambda generator."""

    def __init__(
        self,
        template: picofun.template.Template,
        namespace: str,
        config: picofun.config.Config,
    ) -> None:
        """Initialize the lambda generator."""
        self._template = template
        self._config = config

        self.max_length = 64 - len(f"{namespace}_")
        # Remove one for the underscore between the prefix and the suffix.
        self.prefix_length = self.max_length - LAMBDA_SUFFIX_LENGTH - 1

    def _get_name(self, method: str, path: str) -> str:
        clean_path = path.replace("{", "").replace("}", "")
        lambda_name = (
            f"{method}_{clean_path.replace('/', '_').replace('.', '_').strip('_')}"
        )

        if len(lambda_name) > self.max_length:
            suffix = hashlib.sha512(lambda_name.encode()).hexdigest()[
                :LAMBDA_SUFFIX_LENGTH
            ]
            # The underscire adds another character to the length.
            lambda_name = f"{lambda_name[:self.prefix_length]}_{suffix}"

        return lambda_name

    def generate(
        self,
        api_data: dict[str : typing.Any],
    ) -> list[str]:
        """Generate the lambda functions."""
        output_dir = self._config.output_dir

        lambda_dir = os.path.join(output_dir, "lambdas")
        if not os.path.exists(lambda_dir):
            os.makedirs(lambda_dir, exist_ok=True)

        base_url = api_data["servers"][0]["url"]

        lambdas = []
        for path, path_details in api_data["paths"].items():
            for method, details in path_details.items():
                if method not in ["get", "put", "post", "delete", "patch", "head"]:
                    continue

                lambda_name = self._get_name(method, path)

                code = self.render(
                    base_url,
                    method,
                    path,
                    details,
                )

                script_filename = f"{lambda_name}.py"
                script_path = os.path.join(lambda_dir, script_filename)
                with open(script_path, "w") as file:
                    file.write(code)

                logger.info("Generated function: %s", script_path)
                lambdas.append(lambda_name)

        lambdas.sort()
        return lambdas

    def render(
        self, base_url: str, method: str, path: str, details: dict[str : typing.Any]
    ) -> str:
        """Render the lambda function."""
        preprocessor_handler = self._config.preprocessor
        preprocessor = (
            ".".join(preprocessor_handler.split(".")[:-1])
            if preprocessor_handler
            else None
        )

        postprocessor_handler = self._config.postprocessor
        postprocessor = (
            ".".join(postprocessor_handler.split(".")[:-1])
            if postprocessor_handler
            else None
        )

        code = self._template.render(
            "lambda.py.j2",
            base_url=base_url,
            method=method,
            path=path,
            details=details,
            preprocessor=preprocessor,
            preprocessor_handler=preprocessor_handler,
            postprocessor=postprocessor,
            postprocessor_handler=postprocessor_handler,
            xray_tracing=self._config.xray_tracing,
        )
        return black.format_str(code, mode=black.Mode())
