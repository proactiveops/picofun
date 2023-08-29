"""Test picofun Configuration loader."""

import os
import random
import string
import tempfile

import pytest

import picofun.config


def test_config_load() -> None:
    """Test loading a configuration file."""
    config = picofun.config.Config("tests/data/config.toml")

    assert config.output_dir == os.path.realpath("tests/data/output")
    assert config.layers == ["arn:aws:lambda:us-east-1:012345678910:layer:example:1"]
    assert config.template_path == "tests/data/templates"


def test_config_load_empty() -> None:
    """Test loading an empty configuration file."""
    config = picofun.config.Config("tests/data/empty.toml")

    assert config.output_dir == os.path.realpath(f"{os.getcwd()}/output")
    assert config.layers == []


def test_config_load_missing() -> None:
    """Test loading a missing configuration file."""
    with pytest.raises(picofun.errors.ConfigFileNotFoundError):
        picofun.config.Config("tests/data/missing.toml")


def test_config_load_invalid() -> None:
    """Test loading an invalid configuration file."""
    with pytest.raises(picofun.errors.InvalidConfigError):
        picofun.config.Config("tests/data/invalid.toml")


def test_config_load_invalid_value() -> None:
    """Test loading an invalid configuration file."""
    with pytest.raises(picofun.errors.UnknownConfigValueError):
        picofun.config.Config("tests/data/invalid_type.toml")


def test_config_load_relative_path() -> None:
    """Test loading a configuration file with a relative path."""
    config = picofun.config.Config("tests/data/config_relative.toml")

    assert config.output_dir == os.path.realpath("tests/data/output")


def test_config_load_relative_path_missing() -> None:
    """Test loading a configuration file with a relative path."""
    with pytest.raises(picofun.errors.ConfigFileNotFoundError):
        picofun.config.Config("tests/data/missing.toml")


def test_config_load_absolute_path_missing() -> None:
    """Test loading a configuration file with an absolute path."""
    with pytest.raises(picofun.errors.ConfigFileNotFoundError):
        picofun.config.Config(
            "/tmp/invalid/config/file/location/45c5391e-6e9a-496e-8694-9ef1a03addb3.toml"
        )


def test_config_getattr() -> None:
    """Test loading a configuration file."""
    config = picofun.config.Config("tests/data/config.toml")

    assert config.layers == ["arn:aws:lambda:us-east-1:012345678910:layer:example:1"]


def test_config_getattr_invalid() -> None:
    """Test __getattr__ with an invalid property."""
    config = picofun.config.Config("tests/data/config.toml")
    with pytest.raises(picofun.errors.UnknownConfigValueError):
        _ = config.invalid


def test_config_setattr_invalid() -> None:
    """Test splitting layers string into a list."""
    config = picofun.config.Config("tests/data/empty.toml")

    with pytest.raises(picofun.errors.UnknownConfigValueError):
        config.invalid = "invalid"


def test_config_setattr_layers_empty() -> None:
    """Test splitting layers string into a list."""
    config = picofun.config.Config("tests/data/empty.toml")

    config.layers = ""
    assert config.layers == []


def test_config_setattr_layers() -> None:
    """Test splitting layers string into a list."""
    layers = [
        "arn:aws:lambda:us-east-1:012345678910:layer:example:1",
        "arn:aws:lambda:us-east-1:012345678910:layer:anotherexample:123",
    ]

    config = picofun.config.Config("tests/data/empty.toml")
    assert config.layers == []

    config.layers = ", ".join(layers)
    assert config.layers == layers


def test_config_load_absolute_path() -> None:
    """Test loading a configuration file with an absolute path."""
    config = picofun.config.Config(os.path.realpath("tests/data/config.toml"))

    assert config.output_dir == os.path.realpath("tests/data/output")


def test_fix_target_path_relative() -> None:
    """Test fixing the target path with a realtive path."""
    config = picofun.config.Config("tests/data/config.toml")

    assert config._fix_target_path("tests/data") == os.path.realpath("tests/data")


def test_fix_target_path_absolute() -> None:
    """Test fixing the target path with an absolute path."""
    config = picofun.config.Config("tests/data/config.toml")

    assert config._fix_target_path("/tmp") == os.path.realpath("/tmp")


def test_fix_target_path_dots() -> None:
    """Test fixing the target path containing dots."""
    config = picofun.config.Config("tests/data/config.toml")

    assert config._fix_target_path("tests/../tests/data") == os.path.realpath(
        "tests/data"
    )


def test_fix_target_path_empty() -> None:
    """Test fixing the target path with an empty path."""
    config = picofun.config.Config("tests/data/config.toml")

    assert config._fix_target_path("") == os.path.realpath(os.getcwd())


def test_fix_target_path_none() -> None:
    """Test fixing the target path with an empty path."""
    config = picofun.config.Config("tests/data/config.toml")

    assert config._fix_target_path() == os.path.realpath(os.getcwd())


def test_fix_target_path_missing() -> None:
    """Test fixing the target path with an empty path."""
    config = picofun.config.Config("tests/data/config.toml")

    assert config._fix_target_path("missing") == os.path.realpath(
        os.path.join(os.getcwd(), "missing")
    )


def test_fix_target_path_missing_absolute() -> None:
    """Test fixing the target path with an empty path."""
    config = picofun.config.Config("tests/data/config.toml")

    assert config._fix_target_path("/missing") == os.path.realpath("/missing")


def test_fix_target_path_missing_relative() -> None:
    """Test fixing the target path with an empty path."""
    config = picofun.config.Config("tests/data/config.toml")

    assert config._fix_target_path("missing") == os.path.realpath(
        os.path.join(os.getcwd(), "missing")
    )


def test_load_from_file() -> None:
    """Test loading a configuration file."""
    config = picofun.config.Config("tests/data/config.toml")

    with tempfile.NamedTemporaryFile() as tmp:
        tmp.write(b"output_dir = 'tests/data/output'")
        tmp.seek(0)

        config.load_from_file(tmp.name)

        assert config.output_dir == os.path.realpath("tests/data/output")


def test_load_from_file_missing() -> None:
    """Test loading a configuration file."""
    config = picofun.config.Config("tests/data/config.toml")

    with pytest.raises(picofun.errors.ConfigFileNotFoundError):
        config.load_from_file(
            "/tmp/invalid/config/file/location/45c5391e-6e9a-496e-8694-9ef1a03addb3.toml"
        )


def test_load_from_file_invalid() -> None:
    """Test loading a configuration file."""
    config = picofun.config.Config("tests/data/config.toml")

    with tempfile.NamedTemporaryFile() as tmp:
        tmp.write(b"this = invalid = toml")
        tmp.seek(0)

        with pytest.raises(picofun.errors.InvalidConfigError):
            config.load_from_file(tmp.name)


def test_merge() -> None:
    """Test merging two configurations."""
    config = picofun.config.Config("tests/data/config.toml")

    config.merge(output_dir="tests/output")

    assert config.output_dir == os.path.realpath("tests/output")


def test_merge_invalid() -> None:
    """Test merging two configurations."""
    config = picofun.config.Config("tests/data/config.toml")

    with pytest.raises(picofun.errors.UnknownConfigValueError):
        config.merge(invalid="invalid")


def test_merge_invalid_type() -> None:
    """Test merging two configurations."""
    config = picofun.config.Config("tests/data/config.toml")

    with pytest.raises(picofun.errors.InvalidConfigTypeError):
        config.merge(output_dir=1234)


def test_set_defaults() -> None:
    """Test setting defaults."""
    config = picofun.config.Config("tests/data/empty.toml")

    config.set_defaults()

    assert config.bundle is None
    assert config.layers == []


def test_asdict() -> None:
    """Test converting the config to a dictionary."""
    config = picofun.config.Config("tests/data/config.toml")

    config_dict = config.asdict()

    assert isinstance(config_dict, dict)
    assert config_dict["output_dir"] == os.path.realpath("tests/data/output")


def test_asdict_empty() -> None:
    """Test converting the config to a dictionary."""
    config = picofun.config.Config("tests/data/empty.toml")

    assert config.asdict()["layers"] == []


def test_get_config_file() -> None:
    """Test getting the path to the config file."""
    path = os.path.join(os.path.dirname(__file__), "data")
    config = picofun.config.Config(path)
    assert config._config_file == f"{path}/picofun.toml"


def test_get_config_file_empty() -> None:
    """Test getting the path to the config file with an empty argument."""
    path = os.getcwd()
    config = picofun.config.Config()
    assert config._config_file == f"{path}/picofun.toml"


def test_get_config_file_invalid() -> None:
    """Test not getting the config file from an invalid path."""
    with pytest.raises(picofun.errors.ConfigFileNotFoundError):
        picofun.config.Config("/invalid/")


def test_setattr_output_dir_mkdir() -> None:
    """Test creating the output directory."""
    config = picofun.config.Config("tests/data/empty.toml")

    tmp = os.path.realpath(
        f'/tmp/picofun_tests_{"".join(random.sample(string.ascii_letters + string.digits, 16))}'
    )

    assert not os.path.exists(tmp)
    config.output_dir = tmp
    assert os.path.exists(tmp)

    os.rmdir(tmp)
