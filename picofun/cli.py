"""Command line interface for picofun."""

__author__ = "Dave Hall <skwashd@gmail.com>"
__copyright__ = "Copyright 2023 - 2026, Dave Hall https://proactiveops.io"
__license__ = "MIT"

import logging
import os
import typing

import typer

import picofun.auth_generator
import picofun.config
import picofun.endpoint_filter
import picofun.errors
import picofun.iac.cdk
import picofun.iac.terraform
import picofun.lambda_generator
import picofun.layer
import picofun.security
import picofun.spec
import picofun.template

app = typer.Typer()
logger = logging.getLogger(__name__)


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
    server_url: typing.Annotated[
        str | None,
        typer.Option(
            help="Override server URL from OpenAPI spec. Ignores any server config in picofun.toml."
        ),
    ] = None,
    iac: typing.Annotated[
        str | None,
        typer.Option(
            help="IaC tool to use for infrastructure generation (terraform, tf, cdk)"
        ),
    ] = None,
    cdk: typing.Annotated[
        bool,
        typer.Option("--cdk", help="Shorthand for --iac cdk"),
    ] = False,
    tf: typing.Annotated[
        bool,
        typer.Option("--tf", help="Shorthand for --iac terraform"),
    ] = False,
) -> None:
    """Generate lambda functions and IaC configuration to call REST APIs."""
    # Resolve IaC selection: shorthand flags take precedence over --iac
    if cdk:
        iac = "cdk"
    elif tf:
        iac = "terraform"

    config = picofun.config.ConfigLoader(config_file).get_config()
    config.merge(
        output_dir=output_dir,
        layers=layers,
        bundle=bundle,
        server_url=server_url,
        iac=iac,
    )

    spec = picofun.spec.Spec(spec_file)
    api_data = spec.parse()

    # Extract and select security scheme
    selected_scheme = None
    auth_scheme_type = None
    if config.auth_enabled:
        try:
            schemes = picofun.security.extract_security_schemes(api_data)
            global_security = picofun.security.get_global_security(api_data)
            selected_scheme = picofun.security.select_security_scheme(
                schemes, global_security
            )

            if selected_scheme:
                logger.info(
                    "Selected security scheme: %s (%s)",
                    selected_scheme.name,
                    selected_scheme.type,
                )
                auth_scheme_type = picofun.security.get_scheme_type_kebab(
                    selected_scheme
                )
            else:
                logger.warning(
                    "No supported security scheme found in OpenAPI spec. "
                    "Authentication hooks will not be generated."
                )
        except picofun.errors.UnsupportedSecuritySchemeError as e:
            logger.exception(
                "OpenAPI spec contains only unsupported security schemes: %s. "
                "Supported schemes: apiKey, http (basic/bearer), mutualTLS. "
                "OAuth2 and OpenID Connect are not yet supported.",
                ", ".join(e.unsupported_schemes),
            )
            raise typer.Exit(code=1) from e

    template = picofun.template.Template(config.template_path)

    # Create endpoint filter
    endpoint_filter = picofun.endpoint_filter.EndpointFilter(config.include_endpoints)

    layer = picofun.layer.Layer(config)
    layer.prepare()

    # Generate authentication hooks if enabled and scheme selected
    if config.auth_enabled and selected_scheme:
        auth_hooks_code = picofun.auth_generator.generate_auth_hooks(
            selected_scheme, namespace, config.template_path
        )
        auth_hooks_path = os.path.join(config.output_dir, "layer", "auth_hooks.py")
        os.makedirs(os.path.dirname(auth_hooks_path), exist_ok=True)
        with open(auth_hooks_path, "w") as f:
            f.write(auth_hooks_code)
        logger.info("Generated authentication hooks: %s", auth_hooks_path)

        object.__setattr__(config, "preprocessor", "auth_hooks.preprocessor")

    lambda_generator = picofun.lambda_generator.LambdaGenerator(
        template, namespace, config, endpoint_filter
    )
    lambdas = lambda_generator.generate(api_data)

    if config.iac == "cdk":
        iac_generator = picofun.iac.cdk.CdkGenerator(template, namespace, config)
    else:
        iac_generator = picofun.iac.terraform.TerraformGenerator(
            template, namespace, config
        )

    iac_generator.generate(
        lambdas,
        auth_enabled=config.auth_enabled and selected_scheme is not None,
        auth_scheme_type=auth_scheme_type,
        auth_scheme_name=selected_scheme.name if selected_scheme else None,
        auth_ttl=config.auth_ttl_minutes * 60,  # Convert minutes to seconds
    )
