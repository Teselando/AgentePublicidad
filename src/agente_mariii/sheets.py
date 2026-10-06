"""Acceso de alcance mínimo a la hoja existente mediante cuenta de servicio."""

from __future__ import annotations

import json
import os
from urllib.parse import quote

from google.auth.transport.requests import AuthorizedSession
from google.oauth2 import service_account

SCOPE = "https://www.googleapis.com/auth/spreadsheets"
BASE = "https://sheets.googleapis.com/v4/spreadsheets"


class Sheet:
    def __init__(self) -> None:
        self.spreadsheet_id = os.environ["SPREADSHEET_ID"]
        info = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"])
        credentials = service_account.Credentials.from_service_account_info(info, scopes=[SCOPE])
        self.session = AuthorizedSession(credentials)

    def rows(self, tab: str, a1: str) -> list[list[str]]:
        range_name = quote(f"'{tab}'!{a1}", safe="")
        response = self.session.get(f"{BASE}/{self.spreadsheet_id}/values/{range_name}", timeout=30)
        response.raise_for_status()
        return response.json().get("values", [])

    def append(self, tab: str, a1: str, rows: list[list[str | int]]) -> None:
        if not rows:
            return
        range_name = quote(f"'{tab}'!{a1}", safe="")
        response = self.session.post(
            f"{BASE}/{self.spreadsheet_id}/values/{range_name}:append",
            # RAW prevents an untrusted group title or search snippet beginning
            # with '=' from becoming a spreadsheet formula.
            params={"valueInputOption": "RAW", "insertDataOption": "OVERWRITE"},
            json={"majorDimension": "ROWS", "values": rows}, timeout=30,
        )
        response.raise_for_status()
