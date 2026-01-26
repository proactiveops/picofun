"""Entry point for the application script."""

__author__ = "Dave Hall <skwashd@gmail.com>"
__copyright__ = "Copyright 2023 - 2026, Dave Hall https://proactiveops.io"
__license__ = "MIT"

import logging

import picofun.cli
from picofun import __app_name__

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main() -> None:
    """Run the application."""
    picofun.cli.app(prog_name=__app_name__)


if __name__ == "__main__":
    main()
