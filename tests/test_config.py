from pykour.config import Config


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
