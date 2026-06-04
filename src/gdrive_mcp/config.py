from __future__ import annotations
import json
import os
from dataclasses import dataclass


class ConfigError(Exception):
    """Raised when required configuration is missing or invalid."""


@dataclass(frozen=True)
class Config:
    service_account_info: dict
    allowed_folder_ids: tuple[str, ...]
    allowed_drive_ids: tuple[str, ...] = ()
    host: str = "0.0.0.0"
    port: int = 8080
    enabled_tools: tuple[str, ...] | None = None

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> "Config":
        env = dict(os.environ if env is None else env)

        if env.get("SERVICE_ACCOUNT_JSON"):
            info = json.loads(env["SERVICE_ACCOUNT_JSON"])
        elif env.get("SERVICE_ACCOUNT_PATH"):
            with open(env["SERVICE_ACCOUNT_PATH"], encoding="utf-8") as fh:
                info = json.load(fh)
        else:
            raise ConfigError("SERVICE_ACCOUNT_JSON or SERVICE_ACCOUNT_PATH is required")

        raw_folders = env.get("ALLOWED_FOLDER_IDS", "").strip()
        folders = tuple(f.strip() for f in raw_folders.split(",") if f.strip())
        if raw_folders and not folders:
            raise ConfigError("ALLOWED_FOLDER_IDS contains no valid folder IDs")

        raw_drives = env.get("ALLOWED_DRIVE_IDS", "").strip()
        drives = tuple(d.strip() for d in raw_drives.split(",") if d.strip())

        if not folders and not drives:
            raise ConfigError("ALLOWED_FOLDER_IDS or ALLOWED_DRIVE_IDS is required")

        tools_raw = env.get("ENABLED_TOOLS", "").strip()
        enabled = tuple(t.strip() for t in tools_raw.split(",") if t.strip()) or None

        return cls(
            service_account_info=info,
            allowed_folder_ids=folders,
            allowed_drive_ids=drives,
            host=env.get("GDRIVE_MCP_HOST", "0.0.0.0"),
            port=int(env.get("GDRIVE_MCP_PORT", "8080")),
            enabled_tools=enabled,
        )
