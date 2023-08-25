"""Tests for the LayerGenerator class."""

import os
import tempfile

import picofun.config
import picofun.layer


def test_prepare() -> None:
    """Test generating the layer."""
    config = picofun.config.Config("tests/data/empty.toml")
    with tempfile.TemporaryDirectory() as out_dir:
        config.output_dir = out_dir
        layer = picofun.layer.Layer(config)
        layer.prepare()

        assert os.path.isfile(os.path.join(out_dir, "layer", "requirements.txt"))


def test_prepare_with_bundle() -> None:
    """Test generating the layer."""
    config = picofun.config.Config("tests/data/empty.toml")

    with tempfile.TemporaryDirectory() as bundle_dir:
        config.bundle = bundle_dir

        with tempfile.TemporaryDirectory() as out_dir:
            (fp, filename) = tempfile.mkstemp(dir=bundle_dir)
            config.output_dir = out_dir

            assert os.path.isfile(filename)
            layer = picofun.layer.Layer(config)
            layer.prepare()

            basename = os.path.basename(filename)
            assert os.path.isfile(os.path.join(out_dir, "layer", basename))
