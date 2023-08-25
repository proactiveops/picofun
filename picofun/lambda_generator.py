"""Lambda generator."""
import logging
import os
import random
import string
import typing

import black

import picofun.config
import picofun.template

logger = logging.getLogger(__name__)

LAMBDA_MAX_LENGTH = 64
LAMBDA_PREFIX_LENGTH = LAMBDA_MAX_LENGTH - 7
LAMBDA_SUFFIX_LENGTH = 6


class LambdaGenerator:

    """Lambda generator."""

    def __init__(
        self, template: picofun.template.Template, config: picofun.config.Config
    ) -> None:
        """Initialize the lambda generator."""
        self._template = template
        self._config = config

    def _get_name(self, method: str, path: str) -> str:
        clean_path = path.replace("{", "").replace("}", "")
        lambda_name = f"{method}_{clean_path.replace('/', '_').strip('_')}"

        if len(lambda_name) > LAMBDA_MAX_LENGTH:
            suffix = "".join(
                random.sample(string.ascii_lowercase, LAMBDA_SUFFIX_LENGTH)
            )
            lambda_name = f"{lambda_name[:LAMBDA_PREFIX_LENGTH]}_{suffix}"

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
        code = self._template.render(
            "lambda.py.j2",
            base_url=base_url,
            method=method,
            path=path,
            details=details,
            preprocessor=self._config.preprocessor,
            postprocessor=self._config.postprocessor,
        )
        return black.format_str(code, mode=black.Mode())
