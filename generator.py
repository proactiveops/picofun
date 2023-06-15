"""Open API spec file to Lambda code generator."""
import errno
import json
import logging
import os
from typing import Annotated, Optional

import black
import requests
import tomli as toml
import typer
import yaml
from jinja2 import Environment, FileSystemLoader, Template

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# fmt: off
# Hack to stop black and typer fighting over the type annotations
OptionalString = Optional[str]
# fmt: on


class DownloadSpecError(Exception):

    """Exception thrown when requests is unable to download the spec file."""

    def __init__(self: "DownloadSpecError", arg: requests.RequestException) -> None:
        """
        Initialise DownloadSpecError.

        :param arg: The exception thrown.
        """
        super().__init__(f"Request Error: {arg}")


class DownloadSpecHTTPError(Exception):

    """Exception thrown when requests is unable to download the spec file."""

    def __init__(self, arg: requests.HTTPError) -> None:
        """
        Initialise DownloadSpecHTTPError.

        :param arg: The HTTO error thrown.
        """
        super().__init__(
            f"HTTP Error {arg.response.status_code}: {arg.response.reason}"
        )


class InvalidSpecError(Exception):

    """Exception thrown when the spec file is not valid JSON or YAML."""

    def __init__(self) -> None:
        """Initialise InvalidSpecError."""
        super().__init__("The spec file isn't valid JSON or YAML")


class TemplateLoader:

    """Loads Jinja2 templates."""

    def __init__(self, base_path: str | None = "") -> None:
        """Initialise TemplateLoader."""

        if not base_path:
            base_path = os.path.join(
                os.path.dirname(os.path.realpath(__file__)), "templates"
            )

        if base_path[0] != "/":
            base_path = os.path.join(os.getcwd(), base_path)

        self.environment = Environment(  # noqa: S701 We're not generating HTML
            loader=FileSystemLoader(base_path)
        )

    def get_template(self, filename: str) -> Template:
        """Get a template by filename."""
        return self.environment.get_template(filename)


def download_spec(url: str) -> str:
    """Download the spec file from a URL."""
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
    except requests.HTTPError as e:
        raise DownloadSpecError(e) from e
    except requests.RequestException as e:
        raise DownloadSpecError(e) from e

    return response.content


def generate_lambda(
    template_loader: TemplateLoader, api_data: dict, config: str, output_dir: str
) -> list[str]:
    """Generate the lambda functions."""
    template = template_loader.get_template("lambda.py.j2")
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
                preprocessor=config["preprocessor"],
                postprocessor=config["postprocessor"],
            )
            code = black.format_str(code, mode=black.Mode())

            with open(script_path, "w") as file:
                file.write(code)

            logger.info("Generated script: %s", script_path)
            lambdas.append(script_filename)

    lambdas.sort()
    return lambdas


def generate_terraform(
    template_loader: TemplateLoader, namespace: str, lambdas: list[str], config: dict, output_dir: str
) -> None:
    """Generate terraform configuration for the Lambda functions."""
    template = template_loader.get_template("lambda.tf.j2")

    terraform_content = template.render(
        namespace=namespace,
        lambdas=lambdas,
        layers=config["layers"],
        bundle=config["bundle"],
        subnets=config["subnets"],
        tags=config["tags"],
    )
    output_file = os.path.join(output_dir, "terraform.tf")
    with open(output_file, "w") as terraform_file:
        terraform_file.write(terraform_content)

    logger.info("Generated terraform: %s", output_file)


def get_target_path(output_dir: str) -> str:
    """
    Get the target path for the generated files.

    :param output_dir: The name of the output directory
    :return: The absolute path to the output directory
    """
    cwd = os.getcwd()

    if not output_dir:
        return os.path.join(cwd, "output")

    if output_dir.startswith("/"):
        return os.path.realpath(output_dir)

    return os.path.realpath(os.path.join(cwd, output_dir))


def load_configuration(config_path: str) -> dict:
    """Load configuration from TOML file."""
    if not os.path.isfile(config_path):
        return {}

    with open(config_path) as file:
        return toml.load(file)


def merge_config(
    config: dict,
    output_dir: str,
    preprocessor: str,
    postprocessor: str,
    layers: list[str],
    bundle: str,
) -> dict:
    """Merge the configuration from the TOML file with the CLI arguments."""
    if output_dir:
        config["output_dir"] = output_dir
    elif "output_dir" not in config:
        config["output_dir"] = os.path.join(os.getcwd(), "output")

    if preprocessor:
        config["preprocessor"] = preprocessor

    if "preprocessor" not in config:
        config["preprocessor"] = ""

    if postprocessor:
        config["postprocessor"] = postprocessor

    if "postprocessor" not in config:
        config["postprocessor"] = ""

    if layers:
        config["layers"] = layers

    if "layers" not in config:
        config["layers"] = []

    if bundle:
        config["bundle"] = bundle

    if "bundle" not in config:
        config["bundle"] = ""

    if "subnets" not in config:
        config["subnets"] = []

    if "tags" not in config:
        config["tags"] = {}

    return config


def load_spec(spec_file: str) -> str:
    """
    Load a spec file from disk or a URL.

    :param spec_file: The location of the spec file. Can be a URL or a path to a file.
    :raises FileNotFoundError: _description_
    :return: The contents of the spec file as a string.
    """
    if spec_file.startswith("http"):
        return download_spec(spec_file)

    if not os.path.exists(spec_file):
        raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), spec_file)

    with open(spec_file) as file:
        return file.read()


def parse_spec(content: str) -> dict:
    """
    Parse the contents of the spec file.

    :param content: The raw string containing the spec file
    :raises InvalidSpecError: If the spec file is not valid JSON or YAML
    :return: The contents of the spec file as a dict
    """
    try:
        spec = json.loads(content)
    except json.JSONDecodeError:
        try:
            spec = yaml.safe_load(content)
        except yaml.YAMLError as e:
            raise InvalidSpecError() from e

    return spec


def main(
    namespace: Annotated[
        OptionalString, typer.Option(help="Namespace for the generated functions")
    ],
    spec_file: Annotated[
        OptionalString, typer.Option(help="URL or path to the OpenAPI spec file")
    ],
    output_dir: Annotated[
        OptionalString, typer.Option(help="Directory to output the generated files")
    ] = None,
    preprocessor: Annotated[
        OptionalString, typer.Option(help="Request preprocessor function")
    ] = None,
    postprocessor: Annotated[
        OptionalString, typer.Option(help="Request postprocessor function")
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
    layers_list = [raw.strip() for raw in layers.split(",")]

    config_file = os.path.join(os.getcwd(), "picofun.toml")
    config = merge_config(
        load_configuration(config_file),
        output_dir,
        preprocessor,
        postprocessor,
        layers_list,
        bundle,
    )

    target_path = get_target_path(output_dir)
    if not os.path.exists(target_path):
        os.makedirs(target_path, exist_ok=True)

    spec = load_spec(spec_file)
    api_data = parse_spec(spec)

    template_loader = TemplateLoader()

    lambdas = generate_lambda(template_loader, api_data, config, target_path)
    generate_terraform(template_loader, namespace, lambdas, config, target_path)


if __name__ == "__main__":
    typer.run(main)
