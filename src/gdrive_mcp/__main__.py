from __future__ import annotations

from gdrive_mcp.config import Config
from gdrive_mcp.auth import build_clients
from gdrive_mcp.service import GDriveService
from gdrive_mcp.server import build_mcp


def main() -> None:
    cfg = Config.from_env()
    clients = build_clients(cfg.service_account_info)
    service = GDriveService(clients, cfg.allowed_folder_ids)
    mcp = build_mcp(service, cfg.enabled_tools, host=cfg.host, port=cfg.port)
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
