from unittest.mock import patch, MagicMock
from gdrive_mcp.auth import SCOPES, build_clients

def test_build_clients_uses_scopes_and_returns_three():
    fake_creds = MagicMock()
    with patch("gdrive_mcp.auth.service_account.Credentials.from_service_account_info",
               return_value=fake_creds) as mk_creds, \
         patch("gdrive_mcp.auth.build") as mk_build, \
         patch("gdrive_mcp.auth.gspread.authorize") as mk_gspread:
        clients = build_clients({"type": "service_account"})

        mk_creds.assert_called_once()
        assert mk_creds.call_args.kwargs["scopes"] == list(SCOPES)
        assert mk_build.call_args_list[0].args == ("drive", "v3")
        assert mk_build.call_args_list[1].args == ("docs", "v1")
        mk_gspread.assert_called_once_with(fake_creds)
        assert clients.drive is not None
        assert clients.docs is not None
        assert clients.sheets is not None

def test_scopes_are_the_three_expected():
    assert SCOPES == (
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/documents",
        "https://www.googleapis.com/auth/spreadsheets",
    )
