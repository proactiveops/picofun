"""Preprocessor for Zendesk API requests."""

import base64

import aws_lambda_powertools.utilities.parameters
import picorun


def preprocess(args: picorun.ApiRequestArgs) -> picorun.ApiRequestArgs:
    """Preprocess the request arguments."""
    creds = aws_lambda_powertools.utilities.parameters.get_parameter(
        "/picorun_zendesk/creds", max_age=60, decrypt=True, transform="json"
    )
    auth = base64.b64encode(
        f"{creds['email']}/token:{creds['token']}".encode()
    ).decode()
    args.headers["Authorization"] = f"Basic {auth}"

    subdomain = aws_lambda_powertools.utilities.parameters.get_parameter(
        "/picorun_zendesk/subdomain", max_age=60
    )
    args.path["subdomain"] = subdomain
    args.path["domain"] = "zendesk"
    return args
