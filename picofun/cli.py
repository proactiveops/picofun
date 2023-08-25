"""Command line interface for picofun."""
import typing

import typer

import picofun.config
import picofun.lambda_generator
import picofun.layer
import picofun.spec
import picofun.template
import picofun.terraform_generator

# fmt: off
# Hack to stop black and typer fighting over the type annotations
OptionalString = typing.Optional[str]
# fmt: on

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
        OptionalString, typer.Option(help="Full path to the configuration file")
    ] = None,
    output_dir: typing.Annotated[
        OptionalString, typer.Option(help="Directory to output the generated files")
    ] = None,
    layers: typing.Annotated[
        OptionalString, typer.Option(help="Comma separated list of Lambda layer ARNs")
    ] = "",
    bundle: typing.Annotated[
        OptionalString,
        typer.Option(
            help="Path to code to bundle into a layer. If requirements.txt present pip install will be run."
        ),
    ] = None,
) -> None:
    """Generate lambda functions and terraform configuration to call REST APIs."""
    config = picofun.config.Config(config_file)
    config.merge(
        output_dir=output_dir,
        layers=layers,
        bundle=bundle,
    )

    spec = picofun.spec.Spec(spec_file)
    api_data = spec.parse()

    template = picofun.template.Template(config.template_path)

    lambda_generator = picofun.lambda_generator.LambdaGenerator(template, config)
    lambdas = lambda_generator.generate(api_data)

    layer = picofun.layer.Layer(config)
    layer.prepare()

    terraform_generator = picofun.terraform_generator.TerraformGenerator(
        template, namespace, config
    )
    terraform_generator.generate(lambdas)
