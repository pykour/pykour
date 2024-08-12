import pytest

from pykour.config import Config, ConfigFileHandler, replace_placeholders


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


def test_get_int_valid_int_value():
    config = Config("config.yaml")
    config.config = {"key": 10}
    assert config.get_int("key") == 10


def test_get_int_valid_float_value():
    config = Config("config.yaml")
    config.config = {"key": 10.5}
    assert config.get_int("key") == 10


def test_get_int_valid_str_value():
    config = Config("config.yaml")
    config.config = {"key": "10"}
    assert config.get_int("key") == 10


def test_get_int_invalid_str_value():
    config = Config("config.yaml")
    config.config = {"key": "invalid"}
    with pytest.raises(ValueError):
        config.get_int("key")


def test_get_int_none_value():
    config = Config("config.yaml")
    config.config = {"key": None}
    assert config.get_int("key") is None


def test_get_int_default_value():
    config = Config("config.yaml")
    assert config.get_int("nonexistent", 5) == 5


def test_get_float_valid_int_value():
    config = Config("config.yaml")
    config.config = {"key": 10}
    assert config.get_float("key") == 10.0


def test_get_float_valid_float_value():
    config = Config("config.yaml")
    config.config = {"key": 10.5}
    assert config.get_float("key") == 10.5


def test_get_float_valid_str_value():
    config = Config("config.yaml")
    config.config = {"key": "10.5"}
    assert config.get_float("key") == 10.5


def test_get_float_invalid_str_value():
    config = Config("config.yaml")
    config.config = {"key": "invalid"}
    with pytest.raises(ValueError):
        config.get_float("key")


def test_get_float_none_value():
    config = Config("config.yaml")
    config.config = {"key": None}
    assert config.get_float("key") is None


def test_get_float_default_value():
    config = Config("config.yaml")
    assert config.get_float("nonexistent", 5.5) == 5.5


def test_get_int_invalid_type_value():
    config = Config("config.yaml")
    config.config = {"key": [1, 2, 3]}
    with pytest.raises(ValueError):
        config.get_int("key")


def test_get_float_invalid_type_value():
    config = Config("config.yaml")
    config.config = {"key": [1, 2, 3]}
    with pytest.raises(ValueError):
        config.get_float("key")


def test_load_invalid_yaml_format(mocker):
    config = Config("config.yaml")
    mocker.patch("builtins.open", mocker.mock_open(read_data="invalid_yaml"))
    mocker.patch("yaml.safe_load", return_value="not_a_dict")
    config.load()
    assert config.config == {}


def test_get_value_from_nested_keys():
    config = Config("config.yaml")
    config.config = {"level1": {"level2": {"key": "value"}}}
    assert config.get("level1.level2.key") == "value"


def test_get_value_from_nonexistent_nested_keys():
    config = Config("config.yaml")
    config.config = {"level1": {"level2": {}}}
    assert config.get("level1.level2.nonexistent") is None


def test_get_value_from_nested_keys_with_default():
    config = Config("config.yaml")
    config.config = {"level1": {"level2": {}}}
    assert config.get("level1.level2.nonexistent", "default") == "default"


def test_get_log_levels():
    config = Config()
    config.config = {"pykour": {"logging": {"level": "INFO, WARN, ERROR"}}}
    assert config.get_log_levels() == [20, 30, 40, 25]


def test_get_log_levels_unknown_error():
    config = Config()
    with pytest.raises(ValueError):
        config.config = {"pykour": {"logging": {"level": "INFO, WARN, UNKNOWN"}}}
        config.get_log_levels()


@pytest.fixture
def mock_observer(mocker):
    mock = mocker.patch("watchdog.observers.Observer")
    return mock


def test_call_del_with_mock_observer(mock_observer):
    config = Config()
    config.observer = mock_observer()
    config.__del__()
    mock_observer().stop.assert_called()
    mock_observer().join.assert_called()


@pytest.fixture
def nested_dict_with_env_vars():
    return {"outer": {"inner": "${HOME}/inner_path", "unchanged": "no_env_var"}, "env_var": "${USER}"}


def test_replace_placeholders_with_nested_dict(nested_dict_with_env_vars, monkeypatch):
    # Setup environment variables for the test
    monkeypatch.setenv("HOME", "/home/testuser")
    monkeypatch.setenv("USER", "testuser")

    expected = {"outer": {"inner": "/home/testuser/inner_path", "unchanged": "no_env_var"}, "env_var": "testuser"}

    replace_placeholders(nested_dict_with_env_vars)
    assert nested_dict_with_env_vars == expected


def test_get_datasource_type():
    config = Config()
    config.config = {"pykour": {"datasource": {"type": "sqlite"}}}
    assert config.get_datasource_type() == "sqlite"


def test_get_datasource_url():
    config = Config()
    config.config = {"pykour": {"datasource": {"db": "sqlite:///test.db"}}}
    assert config.get_datasource_db() == "sqlite:///test.db"


def test_get_datasource_host():
    config = Config()
    config.config = {"pykour": {"datasource": {"host": "localhost"}}}
    assert config.get_datasource_host() == "localhost"


def test_get_datasource_username():
    config = Config()
    config.config = {"pykour": {"datasource": {"username": "testuser"}}}
    assert config.get_datasource_username() == "testuser"


def test_get_datasource_password():
    config = Config()
    config.config = {"pykour": {"datasource": {"password": "testpassword"}}}
    assert config.get_datasource_password() == "testpassword"


def test_get_datasource_pool_max_connections():
    config = Config()
    config.config = {"pykour": {"datasource": {"pool": {"max-connections": 10}}}}
    assert config.get_datasource_pool_max_connections() == 10
