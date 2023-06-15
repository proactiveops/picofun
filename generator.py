"""Open API spec file to Lambda code generator."""
import logging
import os
from typing import Annotated, Optional

import black
import typer

import picofun

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# fmt: off
# Hack to stop black and typer fighting over the type annotations
OptionalString = Optional[str]
# fmt: on


def generate_lambda(
    template_loader: picofun.Template, api_data: dict, config: str, output_dir: str
) -> list[str]:
    """Generate the lambda functions."""
    template = template_loader.get("lambda.py.j2")
    lambdas = []

    base_url = api_data["servers"][0]["url"]

    for path, path_details in api_data["paths"].items():
        for method, details in path_details.items():
            if method not in ["get", "put", "post", "delete", "patch", "head"]:
                continue

            clean_path = path.replace("{", "").replace("}", "")
            script_filename = f"{method}_{clean_path.replace('/', '_').strip('_')}.py"
            script_path = os.path.join(output_dir, script_filename)

            code = template.render(
                base_url=base_url,
                path=path,
                method=method,
                details=details,
                preprocessor=config.preprocessor,
                postprocessor=config.postprocessor,
            )
            code = black.format_str(code, mode=black.Mode())

            with open(script_path, "w") as file:
                file.write(code)

            logger.info("Generated script: %s", script_path)
            lambdas.append(script_filename)

    lambdas.sort()
    return lambdas


def generate_terraform(
    template_loader: picofun.Template,
    namespace: str,
    lambdas: list[str],
    config: dict,
    output_dir: str,
) -> None:
    """Generate terraform configuration for the Lambda functions."""
    template = template_loader.get("lambda.tf.j2")

    terraform_content = template.render(
        namespace=namespace,
        lambdas=lambdas,
        layers=config.layers,
        bundle=config.bundle,
        subnets=config.subnets,
        tags=config.tags,
    )
    output_file = os.path.join(output_dir, "terraform.tf")
    with open(output_file, "w") as terraform_file:
        terraform_file.write(terraform_content)

    logger.info("Generated terraform: %s", output_file)


def main(
    namespace: Annotated[
        str, typer.Argument(help="Namespace for the generated functions")
    ],
    spec_file: Annotated[
        str, typer.Argument(help="URL or path to the OpenAPI spec file")
    ],
    output_dir: Annotated[
        OptionalString, typer.Option(help="Directory to output the generated files")
    ] = None,
    layers: Annotated[
        OptionalString, typer.Option(help="Comma separated list of Lambda layer ARNs")
    ] = "",
    bundle: Annotated[
        OptionalString,
        typer.Option(
            help="Path to code to bundle into a layer. If requirements.txt present pip install will be run."
        ),
    ] = None,
) -> None:
    """Generate lambda functions and terraform configuration to call REST APIs."""
    config_file = os.path.join(os.getcwd(), "picofun.toml")
    config = picofun.Config(config_file)
    config.merge(
        output_dir=output_dir,
        layers=layers,
        bundle=bundle,
    )

    if not os.path.exists(config.output_dir):
        os.makedirs(config.output_dir, exist_ok=True)

    spec = picofun.Spec(spec_file)
    api_data = spec.parse()

    template_loader = picofun.Template(config.template_path)

    lambdas = generate_lambda(template_loader, api_data, config, config.output_dir)
    generate_terraform(template_loader, namespace, lambdas, config, config.output_dir)


if __name__ == "__main__":
    typer.run(main)
