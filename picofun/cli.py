"""Command line interface for picofun."""

import typing

import typer

import picofun.config
import picofun.endpoint_filter
import picofun.lambda_generator
import picofun.layer
import picofun.spec
import picofun.template
import picofun.terraform_generator

app = typer.Typer()


@app.command()
def main(
    namespace: typing.Annotated[
        str, typer.Argument(help="Namespace for the generated functions")
    ],
    spec_file: typing.Annotated[
        str, typer.Argument(help="URL or path to the OpenAPI spec file")
    ],
    config_file: typing.Annotated[
        str | None, typer.Option(help="Full path to the configuration file")
    ] = None,
    output_dir: typing.Annotated[
        str | None,
        typer.Option(help="Directory to output the generated files"),
    ] = None,
    layers: typing.Annotated[
        str | None,
        typer.Option(help="Comma separated list of Lambda layer ARNs"),
    ] = "",
    bundle: typing.Annotated[
        str | None,
        typer.Option(
            help="Path to code to bundle into a layer. If pyproject.toml present uv sync will be run."
        ),
    ] = None,
) -> None:
    """Generate lambda functions and terraform configuration to call REST APIs."""
    config = picofun.config.ConfigLoader(config_file).get_config()
    config.merge(
        output_dir=output_dir,
        layers=layers,
        bundle=bundle,
    )

    spec = picofun.spec.Spec(spec_file)
    api_data = spec.parse()

    template = picofun.template.Template(config.template_path)

    # Create endpoint filter
    endpoint_filter = picofun.endpoint_filter.EndpointFilter(config.include_endpoints)

    lambda_generator = picofun.lambda_generator.LambdaGenerator(
        template, namespace, config, endpoint_filter
    )
    lambdas = lambda_generator.generate(api_data)

    layer = picofun.layer.Layer(config)
    layer.prepare()

    terraform_generator = picofun.terraform_generator.TerraformGenerator(
        template, namespace, config
    )
    terraform_generator.generate(lambdas)
