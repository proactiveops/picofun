"""Entry point for the application script."""
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
