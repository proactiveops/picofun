"""Lambda layer manager."""

import logging
import os
import shutil

import picofun.pyproject_manager

logger = logging.getLogger(__name__)

PICORUN_VERSION = "0.2.1"


class Layer:
    """Manage the contents of a Lambda layer."""

    def __init__(self, config: dict) -> None:
        """Initialise the layer."""
        self._config = config

    def prepare(self) -> None:
        """Prepare the contents of a Lambda layer."""
        output_dir = self._config.output_dir
        layer_dir = os.path.join(output_dir, "layer")

        if self._config.bundle and os.path.isdir(self._config.bundle):
            shutil.copytree(self._config.bundle, layer_dir)

        # Handle pyproject.toml updates
        toml_file = os.path.join(layer_dir, "pyproject.toml")
        requirements = picofun.pyproject_manager.PyProjectManager(toml_file)
        requirements.update("picorun", PICORUN_VERSION)
        requirements.save()

        logger.info("Prepared layer contents: %s", layer_dir)
