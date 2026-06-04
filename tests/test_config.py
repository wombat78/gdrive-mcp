import json
import pytest
from gdrive_mcp.config import Config, ConfigError

def test_inline_json_and_folders():
    cfg = Config.from_env({
        "SERVICE_ACCOUNT_JSON": '{"type": "service_account"}',
        "ALLOWED_FOLDER_IDS": "abc, def",
    })
    assert cfg.service_account_info == {"type": "service_account"}
    assert cfg.allowed_folder_ids == ("abc", "def")
    assert cfg.port == 8080
    assert cfg.host == "0.0.0.0"

def test_path_is_read(tmp_path):
    p = tmp_path / "sa.json"
    p.write_text(json.dumps({"type": "service_account", "k": 1}))
    cfg = Config.from_env({
        "SERVICE_ACCOUNT_PATH": str(p),
        "ALLOWED_FOLDER_IDS": "abc",
        "GDRIVE_MCP_PORT": "9000",
    })
    assert cfg.service_account_info["k"] == 1
    assert cfg.port == 9000

def test_missing_creds_raises():
    with pytest.raises(ConfigError, match="SERVICE_ACCOUNT"):
        Config.from_env({"ALLOWED_FOLDER_IDS": "abc"})

def test_missing_folders_raises():
    with pytest.raises(ConfigError, match="ALLOWED_FOLDER_IDS or ALLOWED_DRIVE_IDS"):
        Config.from_env({"SERVICE_ACCOUNT_JSON": "{}"})

def test_enabled_tools_default_none_means_all():
    cfg = Config.from_env({"SERVICE_ACCOUNT_JSON": "{}", "ALLOWED_FOLDER_IDS": "a"})
    assert cfg.enabled_tools is None

def test_empty_folder_ids_after_strip_raises():
    """ALLOWED_FOLDER_IDS with only whitespace/commas (no valid IDs) must raise ConfigError."""
    with pytest.raises(ConfigError, match="ALLOWED_FOLDER_IDS contains no valid folder IDs"):
        Config.from_env({"SERVICE_ACCOUNT_JSON": "{}", "ALLOWED_FOLDER_IDS": ", ,"})


def test_allowed_drive_ids_parsed():
    cfg = Config.from_env({"SERVICE_ACCOUNT_JSON": "{}", "ALLOWED_DRIVE_IDS": "D1, D2"})
    assert cfg.allowed_drive_ids == ("D1", "D2")
    assert cfg.allowed_folder_ids == ()  # folders optional when drives given

def test_folders_optional_when_drives_present():
    cfg = Config.from_env({"SERVICE_ACCOUNT_JSON": "{}", "ALLOWED_DRIVE_IDS": "D1"})
    assert cfg.allowed_drive_ids == ("D1",)

def test_requires_at_least_one_scope():
    import pytest
    with pytest.raises(ConfigError, match="ALLOWED_FOLDER_IDS or ALLOWED_DRIVE_IDS"):
        Config.from_env({"SERVICE_ACCOUNT_JSON": "{}"})

def test_folders_only_still_valid():
    cfg = Config.from_env({"SERVICE_ACCOUNT_JSON": "{}", "ALLOWED_FOLDER_IDS": "F1"})
    assert cfg.allowed_folder_ids == ("F1",)
    assert cfg.allowed_drive_ids == ()
