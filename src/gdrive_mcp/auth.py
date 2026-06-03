from __future__ import annotations
from dataclasses import dataclass
from typing import Any

import gspread
from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = (
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/spreadsheets",
)


@dataclass(frozen=True)
class Clients:
    drive: Any
    docs: Any
    sheets: Any  # gspread.Client


def build_clients(service_account_info: dict) -> Clients:
    creds = service_account.Credentials.from_service_account_info(
        service_account_info, scopes=list(SCOPES)
    )
    drive = build("drive", "v3", credentials=creds, cache_discovery=False)
    docs = build("docs", "v1", credentials=creds, cache_discovery=False)
    sheets = gspread.authorize(creds)
    return Clients(drive=drive, docs=docs, sheets=sheets)
