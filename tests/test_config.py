from watchdog.observers import Observer

from pykour.config import Config, ConfigFileHandler


def test_config_initialization():
    config = Config("config.yaml")
    assert config.filepath.endswith("config.yaml")


def test_config_load_nonexistent_file():
    config = Config("nonexistent.yaml")
    assert config.config == {}


def test_config_get_existing_key():
    config = Config("config.yaml")
    config.config = {"key": "value"}
    assert config.get("key") == "value"


def test_config_get_nonexistent_key():
    config = Config("config.yaml")
    assert config.get("nonexistent") is None


def test_config_get_with_default():
    config = Config("config.yaml")
    assert config.get("nonexistent", "default") == "default"


def test_config_reload_modified_file(mocker, tmp_path):
    test_file = tmp_path / "config.yaml"
    test_file.write_text("key: value")

    mocker.patch("os.path.getmtime", return_value=1234567890)
    config = Config(str(test_file))
    config._last_modified = 123456789
    config.reload()
    assert config._last_modified == 1234567890


def test_config_str_representation():
    config = Config("config.yaml")
    config.config = {"key": "value"}
    expected_str = "key: value\n"
    assert str(config) == expected_str


def test_config_repr_representation():
    config = Config("config.yaml")
    config.config = {"key": "value"}
    expected_repr = "key: value\n"
    assert repr(config) == expected_repr


def test_on_modified_triggers_load(mocker):
    # Arrange
    config = Config("config.yaml")
    handler = ConfigFileHandler(config)
    mocker.patch.object(config, "load")
    event = mocker.Mock()
    event.src_path = config.filepath

    # Act
    handler.on_modified(event)

    # Assert
    config.load.assert_called_once()
