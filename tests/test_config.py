"""Test picofun Configuration loader."""

import os
import random
import string
import tempfile

import pydantic
import pytest

import picofun.config


def test_config_getattr() -> None:
    """Test loading a configuration file."""
    params = {"layers": ["arn:aws:lambda:us-east-1:012345678910:layer:example:1"]}
    config = picofun.config.Config(**params)

    assert config.layers == [
        picofun.config.AWS_POWER_TOOLS_LAYER_ARN,
        "arn:aws:lambda:us-east-1:012345678910:layer:example:1",
    ]


def test_config_getattr_invalid() -> None:
    """Test __getattr__ with an invalid property."""
    config = picofun.config.Config()
    with pytest.raises(
        AttributeError, match="'Config' object has no attribute 'invalid'"
    ):
        _ = config.invalid


def test_config_setattr_invalid() -> None:
    """Test setting invalid attribute."""
    config = picofun.config.Config()

    with pytest.raises(pydantic.ValidationError):
        config.invalid = "invalid"


def test_config_setattr_layers_powertools() -> None:
    """Test splitting layers string into a list."""
    layers = [
        "arn:aws:lambda:us-east-1:017000801446:layer:AWSLambdaPowertoolsPythonV2:79"
    ]

    config = picofun.config.Config()
    assert config.layers == [picofun.config.AWS_POWER_TOOLS_LAYER_ARN]

    config.layers = layers
    assert config.layers == layers


def test_config_setattr_output_dir_mkdir() -> None:
    """Test creating the output directory."""
    config = picofun.config.Config()

    # Can't use tempfile.mkdtemp as it creates the directory
    tmp = os.path.realpath(
        f"/tmp/picofun_tests_{''.join(random.sample(string.ascii_letters + string.digits, 16))}"
    )

    assert not os.path.exists(tmp)
    config.output_dir = tmp
    assert os.path.exists(tmp)

    os.rmdir(tmp)


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("tests/data", "tests/data"),
        ("/tmp", "/tmp"),
        ("tests/data/../data", "tests/data"),
    ],
)
def test_config_bundle_validation(path: str, expected: str) -> None:
    """Test bundle validation."""
    assert picofun.config.Config.validate_bundle(path) == os.path.realpath(expected)


def test_config_bundle_validation_not_found() -> None:
    """Test bundle validation."""
    with pytest.raises(
        ValueError, match="Bundle path not found: /this/path/does/not/exist"
    ):
        assert picofun.config.Config.validate_bundle("/this/path/does/not/exist")


@pytest.mark.parametrize(
    ("layers", "expected"),
    [
        ("", [picofun.config.AWS_POWER_TOOLS_LAYER_ARN]),
        (
            "arn:aws:lambda:us-east-1:012345678910:layer:example:1",
            [
                picofun.config.AWS_POWER_TOOLS_LAYER_ARN,
                "arn:aws:lambda:us-east-1:012345678910:layer:example:1",
            ],
        ),
        (
            ["arn:aws:lambda:us-east-1:012345678910:layer:example:1"],
            [
                picofun.config.AWS_POWER_TOOLS_LAYER_ARN,
                "arn:aws:lambda:us-east-1:012345678910:layer:example:1",
            ],
        ),
        (
            [
                "arn:aws:lambda:us-east-1:012345678910:layer:example:1",
                picofun.config.AWS_POWER_TOOLS_LAYER_ARN,
            ],
            [
                "arn:aws:lambda:us-east-1:012345678910:layer:example:1",
                picofun.config.AWS_POWER_TOOLS_LAYER_ARN,
            ],
        ),
        (
            "arn:aws:lambda:us-east-1:012345678910:layer:example:1, arn:aws:lambda:us-east-1:012345678910:layer:example:2",
            [
                picofun.config.AWS_POWER_TOOLS_LAYER_ARN,
                "arn:aws:lambda:us-east-1:012345678910:layer:example:1",
                "arn:aws:lambda:us-east-1:012345678910:layer:example:2",
            ],
        ),
    ],
)
def test_config_validate_layers(layers: list, expected: list) -> None:
    """Test layers validation."""
    assert picofun.config.Config.validate_layers(layers) == expected


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("tests/data", "tests/data"),
        ("/tmp", "/tmp"),
        ("tests/data/../data", "tests/data"),
        ("", os.getcwd()),
    ],
)
def test_config_output_dir_validator(path: str, expected: str) -> None:
    """Test the outpath validator."""
    assert picofun.config.Config.validate_output_dir(path) == os.path.realpath(expected)


@pytest.mark.parametrize(
    ("subnets", "expected"),
    [
        ("", []),
        ("subnet-12345678", ["subnet-12345678"]),
        (["subnet-12345678"], ["subnet-12345678"]),
        (
            ["subnet-12345678", "subnet-87654321"],
            ["subnet-12345678", "subnet-87654321"],
        ),
        ("subnet-12345678, subnet-87654321", ["subnet-12345678", "subnet-87654321"]),
    ],
)
def test_config_validate_subnets(subnets: list, expected: list) -> None:
    """Test subnets validation."""
    assert picofun.config.Config.validate_subnets(subnets) == expected


def test_config_validate_subnets_invalid() -> None:
    """Test subnets validation with invalid subnet id."""
    with pytest.raises(
        ValueError, match=r"Subnets must be in the format 'subnet-\[hex\]'"
    ):
        picofun.config.Config.validate_subnets("invalid")


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("tests/data/templates", "tests/data/templates"),
        (os.path.realpath("tests/data/templates"), "tests/data/templates"),
    ],
)
def test_config_validate_template_path(path: str, expected: str) -> None:
    """Test the template path validator."""
    assert picofun.config.Config.validate_template_path(path) == os.path.realpath(
        expected
    )


def test_config_validate_template_path_not_found() -> None:
    """Test the template path validator."""
    with pytest.raises(
        ValueError, match="Template path not found: /this/path/does/not/exist"
    ):
        picofun.config.Config.validate_template_path("/this/path/does/not/exist")


@pytest.mark.parametrize(
    ("vpc_id", "subnets", "expected"),
    [
        (
            "vpc-12345678",
            "subnet-12345678",
            {"vpc_id": "vpc-12345678", "subnets": ["subnet-12345678"]},
        ),
        (
            "vpc-12345678",
            ["subnet-12345678"],
            {"vpc_id": "vpc-12345678", "subnets": ["subnet-12345678"]},
        ),
        (
            "vpc-12345678",
            ["subnet-12345678", "subnet-87654321"],
            {
                "vpc_id": "vpc-12345678",
                "subnets": ["subnet-12345678", "subnet-87654321"],
            },
        ),
        (
            "vpc-12345678",
            "subnet-12345678, subnet-87654321",
            {
                "vpc_id": "vpc-12345678",
                "subnets": ["subnet-12345678", "subnet-87654321"],
            },
        ),
    ],
)
def test_config_validate_subnets_vpc(
    vpc_id: str, subnets: list, expected: dict[str : str | list]
) -> None:
    """Test subnets VPC validation."""
    params = {"vpc_id": vpc_id, "subnets": subnets}
    config = picofun.config.Config(**params)

    assert config.vpc_id == expected["vpc_id"]
    assert config.subnets == expected["subnets"]


@pytest.mark.parametrize(
    ("vpc_id", "subnets"),
    [
        ("vpc-12345678", ""),
        ("vpc-12345678", []),
        ("", "subnet-12345678"),
        ("", "subnet-12345678, subnet-87654321"),
    ],
)
def test_config_validate_subnets_vpc_invalid(vpc_id: str, subnets: list) -> None:
    """Test subnets VPC validation with invalid configuration."""
    params = {"vpc_id": vpc_id, "subnets": subnets}
    with pytest.raises(
        ValueError, match="Both subnets and vpc must be set, if one is set"
    ):
        picofun.config.Config(**params)


def test_config_merge() -> None:
    """Test merging two configurations."""
    config = picofun.config.Config()

    config.merge(output_dir="tests/output")

    assert str(config.output_dir) == os.path.realpath("tests/output")


def test_config_merge_invalid() -> None:
    """Test merging configuration with an invalid property."""
    config = picofun.config.Config()

    with pytest.raises(pydantic.ValidationError, match="1 validation error for Config"):
        config.merge(output_dir="tests/output", invalid="invalid")


def test_config_merge_invalid_type() -> None:
    """Test merging configurations with invalid data type for the property."""
    config = picofun.config.Config()

    with pytest.raises(
        TypeError, match="expected str, bytes or os\\.PathLike object, not int"
    ):
        config.merge(output_dir=1234)


def test_config_dump_model() -> None:
    """Test converting the config to a dictionary."""
    config = picofun.config.Config()

    config_dict = config.model_dump()

    assert isinstance(config_dict, dict)

    assert config_dict["output_dir"] == os.path.realpath("output")


def test_configloader() -> None:
    """Test getting the path to the config file with an empty argument."""
    path = os.getcwd()
    loader = picofun.config.ConfigLoader()

    assert loader._config_file == f"{path}/picofun.toml"
    assert isinstance(loader._config, picofun.config.Config)
    assert len(loader._config.layers) == 1


def test_configloader_with_file() -> None:
    """Test loading a configuration file."""
    loader = picofun.config.ConfigLoader("tests/data/config.toml")

    assert loader._config_file == "tests/data/config.toml"
    assert len(loader._config.layers) == 2


def test_configloader_empty_file() -> None:
    """Test loading an empty configuration file."""
    loader = picofun.config.ConfigLoader("tests/data/empty.toml")

    assert loader._config.output_dir == os.path.realpath(f"{os.getcwd()}/output")
    assert loader._config.layers == [picofun.config.AWS_POWER_TOOLS_LAYER_ARN]


@pytest.mark.parametrize(
    ("config_file", "exception_type"),
    [
        ("tests/data/missing.toml", picofun.errors.ConfigFileNotFoundError),
        ("tests/data/invalid.toml", picofun.errors.InvalidConfigError),
        ("tests/data/invalid_type.toml", picofun.errors.UnknownConfigValueError),
        ("/this/file/doesnt/exist.toml", picofun.errors.ConfigFileNotFoundError),
    ],
)
def test_configloader_errors(config_file: str, exception_type: Exception) -> None:
    """Test loading a missing configuration file."""
    with pytest.raises(exception_type):
        picofun.config.ConfigLoader(os.path.realpath(config_file))


def test_configloader_relative_path() -> None:
    """Test loading a configuration file with a relative path."""
    loader = picofun.config.ConfigLoader("tests/data/config_relative.toml")

    assert str(loader._config.output_dir) == os.path.realpath("tests/data/output")


def test_configloader_absolute_path() -> None:
    """Test loading a configuration file with an absolute path."""
    path = os.path.join(os.path.dirname(__file__), "data")
    loader = picofun.config.ConfigLoader(path)
    assert loader._config_file == f"{path}/picofun.toml"


def test_configloader_from_file_invalid() -> None:
    """Test loading a configuration file."""
    loader = picofun.config.ConfigLoader("tests/data/config.toml")

    with tempfile.NamedTemporaryFile() as tmp:
        tmp.write(b"this = invalid = toml")
        tmp.seek(0)

        with pytest.raises(picofun.errors.InvalidConfigError):
            loader.load_from_file(tmp.name)


def test_configloader_get_config() -> None:
    """Test getting the configuration object."""
    loader = picofun.config.ConfigLoader("tests/data/config.toml")

    config = loader.get_config()

    assert isinstance(config, picofun.config.Config)
    assert len(config.layers) == 2
    assert str(config.output_dir) == os.path.realpath("tests/data/output")
