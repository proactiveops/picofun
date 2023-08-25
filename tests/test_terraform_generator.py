"""Tests for the TerraformGenerator class."""
import tempfile

import picofun.config
import picofun.template
import picofun.terraform_generator


def test_generate() -> None:
    """Test generating the terraform configuration."""
    config = picofun.config.Config("tests/data/empty.toml")
    tpl = picofun.template.Template("tests/data/templates")
    with tempfile.TemporaryDirectory() as out_dir:
        config.output_dir = out_dir
        generator = picofun.terraform_generator.TerraformGenerator(tpl, "test", config)
        generator.generate([])
