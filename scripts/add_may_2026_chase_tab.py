#!/usr/bin/env python3
"""Add May 2026 tab to the Chase 3915 spreadsheet, matching the existing
Jan–Apr 2026 tab format. Source: Chase3915_Activity_20260527.csv."""
import csv
import json
import sys
from pathlib import Path
from datetime import date

sys.path.insert(0, str(Path(__file__).resolve().parent))
from google_sheets_helper import _access_token, _api, write_values

SID = "1AY161cwEj-Aq4OU74TN8m7e2YIyNoUXnyPnvE1VQ9iQ"
CSV = Path("/Users/victoria/Desktop/Chase3915_Activity_20260527.csv")
TAB = "May 2026"


def main():
    tok = _access_token()

    rows_in = []
    with CSV.open() as f:
        for r in csv.reader(f):
            if not r or r[0] == "Details":
                continue
            posting, desc, amt = r[1], r[2], r[3]
            bal = r[5].strip() if len(r) > 5 else ""
            if not posting.startswith("05/"):
                continue
            mo, dd, yyyy = posting.split("/")
            iso = f"{yyyy}-{mo}-{dd}"
            bal_v = float(bal) if bal else None
            rows_in.append((iso, f"{mo}/{dd}", desc.title(), float(amt), bal_v))

    rows_in.sort(key=lambda x: x[0])
    print(f"May rows: {len(rows_in)}")

    # ---- Create tab ----
    meta = _api("GET", f"https://sheets.googleapis.com/v4/spreadsheets/{SID}", tok)
    if any(s["properties"]["title"] == TAB for s in meta["sheets"]):
        raise SystemExit(f"tab '{TAB}' already exists — aborting")

    # Insert May tab after Apr 2026
    apr_index = next(s["properties"]["index"] for s in meta["sheets"]
                     if s["properties"]["title"] == "Apr 2026")
    add = _api("POST", f"https://sheets.googleapis.com/v4/spreadsheets/{SID}:batchUpdate", tok,
               data=json.dumps({"requests": [{"addSheet": {"properties": {
                   "title": TAB, "index": apr_index + 1,
                   "gridProperties": {"rowCount": 200, "columnCount": 25,
                                      "frozenRowCount": 1}}}}]}))
    new_sheet_id = add["replies"][0]["addSheet"]["properties"]["sheetId"]
    print(f"created tab '{TAB}' sheetId={new_sheet_id}")

    # ---- Header + data + footer ----
    header = [["Date", "MM/DD", "Description", "Amount"]]
    data = [[iso, mmdd, desc, amt] for iso, mmdd, desc, amt, _ in rows_in]
    last_row = 1 + len(data)  # row of last txn (1-indexed)
    blank = [[""]]
    footer = [
        ["", "", "Deposits (positive)",   f"=SUMIF(D2:D{last_row},\">0\")"],
        ["", "", "Withdrawals (negative)", f"=SUMIF(D2:D{last_row},\"<0\")"],
        ["", "", "Transaction count",      f"=COUNTA(A2:A{last_row})"],
    ]
    all_rows = header + data + blank + footer
    write_values(SID, f"'{TAB}'!A1", all_rows)
    print(f"wrote {len(all_rows)} rows")

    # ---- Format: bold header, currency on D, date formats on A/B ----
    fmts = [
        {"repeatCell": {
            "range": {"sheetId": new_sheet_id, "startRowIndex": 0, "endRowIndex": 1,
                      "startColumnIndex": 0, "endColumnIndex": 4},
            "cell": {"userEnteredFormat": {"textFormat": {"bold": True},
                                            "backgroundColor": {"red": 0.93, "green": 0.93, "blue": 0.93}}},
            "fields": "userEnteredFormat(textFormat,backgroundColor)"}},
        {"repeatCell": {
            "range": {"sheetId": new_sheet_id, "startRowIndex": 1, "endRowIndex": last_row,
                      "startColumnIndex": 0, "endColumnIndex": 1},
            "cell": {"userEnteredFormat": {"numberFormat": {"type": "DATE", "pattern": "yyyy-mm-dd"}}},
            "fields": "userEnteredFormat.numberFormat"}},
        {"repeatCell": {
            "range": {"sheetId": new_sheet_id, "startRowIndex": 1, "endRowIndex": last_row,
                      "startColumnIndex": 1, "endColumnIndex": 2},
            "cell": {"userEnteredFormat": {"numberFormat": {"type": "DATE", "pattern": "mm/dd"}}},
            "fields": "userEnteredFormat.numberFormat"}},
        {"repeatCell": {
            "range": {"sheetId": new_sheet_id, "startRowIndex": 1, "endRowIndex": last_row + 4,
                      "startColumnIndex": 3, "endColumnIndex": 4},
            "cell": {"userEnteredFormat": {"numberFormat": {"type": "CURRENCY", "pattern": "$#,##0.00"}}},
            "fields": "userEnteredFormat.numberFormat"}},
        {"repeatCell": {
            "range": {"sheetId": new_sheet_id, "startRowIndex": last_row + 1, "endRowIndex": last_row + 4,
                      "startColumnIndex": 2, "endColumnIndex": 4},
            "cell": {"userEnteredFormat": {"textFormat": {"bold": True}}},
            "fields": "userEnteredFormat.textFormat"}},
        {"autoResizeDimensions": {
            "dimensions": {"sheetId": new_sheet_id, "dimension": "COLUMNS",
                           "startIndex": 0, "endIndex": 4}}},
    ]
    _api("POST", f"https://sheets.googleapis.com/v4/spreadsheets/{SID}:batchUpdate", tok,
         data=json.dumps({"requests": fmts}))
    print("formatting applied")

    # ---- Update Summary tab: add May row before Total ----
    smry = _api("GET", f"https://sheets.googleapis.com/v4/spreadsheets/{SID}/values/Summary!A1:F20"
                "?valueRenderOption=FORMULA", tok).get("values", [])
    total_row_idx = next(i for i, r in enumerate(smry) if r and r[0] == "Total")  # 0-indexed
    may_row_num = total_row_idx + 1  # 1-indexed insertion row

    # Insert blank row at total_row_idx (0-indexed) → shifts Total down
    _api("POST", f"https://sheets.googleapis.com/v4/spreadsheets/{SID}:batchUpdate", tok,
         data=json.dumps({"requests": [{"insertDimension": {
             "range": {"sheetId": 0, "dimension": "ROWS",
                       "startIndex": total_row_idx, "endIndex": total_row_idx + 1},
             "inheritFromBefore": False}}]}))

    # Write May row
    may_row = [["May 2026", "April 25, 2026 through May 27, 2026 (partial)",
                "=SUMIF('May 2026'!D:D,\">0\")",
                "=SUMIF('May 2026'!D:D,\"<0\")",
                f"=C{may_row_num}+D{may_row_num}",
                ""]]
    write_values(SID, f"Summary!A{may_row_num}", may_row)

    # Fix Total SUM ranges to include new row (C5:C9, D5:D9, E5:E9)
    new_total_row = may_row_num + 1
    write_values(SID, f"Summary!C{new_total_row}:E{new_total_row}",
                 [[f"=SUM(C5:C{may_row_num})",
                   f"=SUM(D5:D{may_row_num})",
                   f"=SUM(E5:E{may_row_num})"]])
    print(f"Summary updated: May row inserted at row {may_row_num}")

    # ---- Append May to All Transactions ----
    at = _api("GET", f"https://sheets.googleapis.com/v4/spreadsheets/{SID}/values/All%20Transactions!A:A",
              tok).get("values", [])
    next_row = len(at) + 1
    # Statement key for May: 20260527 (latest activity date)
    may_rows = []
    for iso, mmdd, desc, amt, bal in rows_in:
        y, m, d = iso.split("-")
        stmt_key = int(f"{y}{m}{d}")
        may_rows.append([stmt_key, iso, mmdd, desc, amt, bal if bal is not None else ""])
    write_values(SID, f"'All Transactions'!A{next_row}", may_rows)
    print(f"appended {len(may_rows)} rows to All Transactions starting row {next_row}")

    url = f"https://docs.google.com/spreadsheets/d/{SID}/edit#gid={new_sheet_id}"
    print(f"DONE: {url}")


if __name__ == "__main__":
    main()
