#!/usr/bin/env python3
from __future__ import annotations
"""Reusable Google Sheets writer. Creates a new spreadsheet, writes rows,
applies basic formatting (bold headers, frozen rows, auto-resize columns,
currency on $ columns).

Usage (module):
    from google_sheets_helper import create_sheet, write_block
    sid = create_sheet("My Title")
    write_block(sid, "A1", rows)
"""
import json
import os
import pathlib
import sys
import time

import requests

REPO = pathlib.Path(__file__).resolve().parents[1]
TOKEN_PATH = REPO / "config" / "google_sheets_token.json"


def _access_token() -> str:
    if not TOKEN_PATH.exists():
        raise SystemExit(f"missing {TOKEN_PATH} — run scripts/google_sheets_oauth.py first")
    tok = json.loads(TOKEN_PATH.read_text())
    resp = requests.post(
        tok["token_uri"],
        data={
            "client_id": tok["client_id"],
            "client_secret": tok["client_secret"],
            "refresh_token": tok["refresh_token"],
            "grant_type": "refresh_token",
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def _api(method: str, url: str, access_token: str, **kw) -> dict:
    headers = kw.pop("headers", {})
    headers["Authorization"] = f"Bearer {access_token}"
    headers["Content-Type"] = "application/json"
    resp = requests.request(method, url, headers=headers, timeout=30, **kw)
    if not resp.ok:
        raise RuntimeError(f"{method} {url} -> {resp.status_code}: {resp.text}")
    return resp.json() if resp.text else {}


def create_sheet(title: str) -> tuple[str, str]:
    """Create a new spreadsheet. Returns (spreadsheet_id, url)."""
    token = _access_token()
    body = {"properties": {"title": title}}
    res = _api(
        "POST",
        "https://sheets.googleapis.com/v4/spreadsheets",
        token,
        data=json.dumps(body),
    )
    return res["spreadsheetId"], res["spreadsheetUrl"]


def write_values(spreadsheet_id: str, range_a1: str, rows: list[list]) -> None:
    """Write rows starting at range_a1 (e.g. 'Sheet1!A1'). Overwrites cells."""
    token = _access_token()
    url = (
        f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}"
        f"/values/{requests.utils.quote(range_a1, safe='!')}"
        "?valueInputOption=USER_ENTERED"
    )
    _api("PUT", url, token, data=json.dumps({"values": rows}))


def batch_write_values(spreadsheet_id: str, ranges_and_values: list[tuple]) -> None:
    """Write multiple ranges in one API call. ranges_and_values: list of (a1_range, rows_2d_list)."""
    token = _access_token()
    url = (
        f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}"
        "/values:batchUpdate"
    )
    body = {
        "valueInputOption": "USER_ENTERED",
        "data": [{"range": r, "values": v} for r, v in ranges_and_values],
    }
    _api("POST", url, token, data=json.dumps(body))


def batch_format(spreadsheet_id: str, requests_list: list[dict]) -> None:
    """Apply formatting via batchUpdate."""
    token = _access_token()
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}:batchUpdate"
    _api("POST", url, token, data=json.dumps({"requests": requests_list}))


# --- Convenience: build common formatting requests ----------------------------

def fmt_bold(sheet_id: int, start_row: int, end_row: int,
             start_col: int = 0, end_col: int = 26,
             bg: tuple[float, float, float] | None = None,
             font_size: int | None = None) -> dict:
    text_format = {"bold": True}
    if font_size:
        text_format["fontSize"] = font_size
    fields = "userEnteredFormat.textFormat.bold,userEnteredFormat.textFormat.fontSize"
    cell_format = {"textFormat": text_format}
    if bg:
        cell_format["backgroundColor"] = {"red": bg[0], "green": bg[1], "blue": bg[2]}
        fields += ",userEnteredFormat.backgroundColor"
    return {
        "repeatCell": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": start_row, "endRowIndex": end_row,
                "startColumnIndex": start_col, "endColumnIndex": end_col,
            },
            "cell": {"userEnteredFormat": cell_format},
            "fields": fields,
        }
    }


def fmt_currency(sheet_id: int, start_row: int, end_row: int,
                 start_col: int, end_col: int) -> dict:
    return {
        "repeatCell": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": start_row, "endRowIndex": end_row,
                "startColumnIndex": start_col, "endColumnIndex": end_col,
            },
            "cell": {"userEnteredFormat": {
                "numberFormat": {"type": "CURRENCY", "pattern": "$#,##0"}
            }},
            "fields": "userEnteredFormat.numberFormat",
        }
    }


def fmt_auto_resize(sheet_id: int, start_col: int = 0, end_col: int = 10) -> dict:
    return {
        "autoResizeDimensions": {
            "dimensions": {
                "sheetId": sheet_id,
                "dimension": "COLUMNS",
                "startIndex": start_col, "endIndex": end_col,
            }
        }
    }


def fmt_freeze(sheet_id: int, frozen_rows: int = 1) -> dict:
    return {
        "updateSheetProperties": {
            "properties": {"sheetId": sheet_id, "gridProperties": {"frozenRowCount": frozen_rows}},
            "fields": "gridProperties.frozenRowCount",
        }
    }


if __name__ == "__main__":
    # Smoke test
    sid, url = create_sheet(f"helper smoke test {int(time.time())}")
    write_values(sid, "A1", [["hello", "world"]])
    print(f"created: {url}")
