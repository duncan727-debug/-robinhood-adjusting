#!/usr/bin/env python3
"""Rewrite the May 2026 tab from CSV: full 68 txns + categories + footer.
Then rebuild the breakdown/pie. Uses batchUpdate with updateCells (atomic)."""
import csv
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from google_sheets_helper import _access_token, _api

SID = "1AY161cwEj-Aq4OU74TN8m7e2YIyNoUXnyPnvE1VQ9iQ"
CSV = Path("/Users/victoria/Desktop/Chase3915_Activity_20260527.csv")
TAB = "May 2026"

RULES = [
    ("Auto / VW Loan",     re.compile(r"vw credit|schumacher|el car wash|car wash", re.I)),
    ("Gas",                re.compile(r"chevron|wawa|marathon|everglades petr|shell|exxon|mobil", re.I)),
    ("Groceries",          re.compile(r"trader joe|publix|whole foods|wal-?mart|whlfds|wholefds|costco", re.I)),
    ("Dining Out",         re.compile(r"sushi yama|shingo|chick-fil-a|first watch|willy cafe|elisabetta|pura vida|cousins maine|world of brigade|brigadeiro|restaur|cafe", re.I)),
    ("Personal Care",      re.compile(r"vagaro|toi spa|ulta|sephora|european wax|hbk co|brazilian wax", re.I)),
    ("Healthcare",         re.compile(r"smile design|rayus|md now|mdnow|quest diag|florida woman|seasons women|season women|childrens museum", re.I)),
    ("Bills / Utilities",  re.compile(r"at&t|att\*bill|fpl|fl power|comcast|xfinity|t-mobile|verizon", re.I)),
    ("Credit Card Payment",re.compile(r"citi card|amex|chase card|capital one online", re.I)),
    ("Subscriptions",      re.compile(r"apple\.com/bill|spotify|youtube|amazon prime|seed\.com|netflix", re.I)),
    ("Amazon Shopping",    re.compile(r"amazon mktpl|amazonmktplc|amazon marketplace|amazon\.com|amzn", re.I)),
    ("Target",             re.compile(r"target", re.I)),
    ("T J Maxx / Marshalls",re.compile(r"t ?j ?maxx|marshalls|hollister", re.I)),
    ("Zelle Out",          re.compile(r"zelle payment to|zelle to", re.I)),
    ("Transfer Out",       re.compile(r"online transfer to|transfer to chk", re.I)),
    ("ATM / Cash",         re.compile(r"atm withdrawal|cash withdrawal", re.I)),
    ("Bank Fees",          re.compile(r"monthly service fee|official checks charge|service fee", re.I)),
    ("Official Checks",    re.compile(r"official check|withdrawal \(official", re.I)),
]
CATEGORIES = [r[0] for r in RULES] + ["Misc Retail"]


def classify(desc, amt):
    if amt > 0:
        return "INFLOW (excluded)"
    for cat, pat in RULES:
        if pat.search(desc):
            return cat
    return "Misc Retail"


def clean(s):
    return re.sub(r"\s+", " ", s).strip().title()


def main():
    tok = _access_token()

    rows = []
    with CSV.open() as f:
        for r in csv.reader(f):
            if not r or r[0] == "Details":
                continue
            posting, desc, amt = r[1], r[2], r[3]
            if not posting.startswith("05/"):
                continue
            mo, dd, yyyy = posting.split("/")
            iso = f"{yyyy}-{mo}-{dd}"
            rows.append((iso, f"{mo}/{dd}", clean(desc), float(amt)))
    rows.sort(key=lambda x: x[0])
    print(f"CSV May rows: {len(rows)}")

    # Find sheet
    meta = _api("GET", f"https://sheets.googleapis.com/v4/spreadsheets/{SID}", tok)
    sheet_id = next(s["properties"]["sheetId"] for s in meta["sheets"]
                    if s["properties"]["title"] == TAB)

    last_txn = 1 + len(rows)  # 1-indexed
    blank_row = last_txn + 1
    dep_row = blank_row + 1
    wd_row = dep_row + 1
    cnt_row = wd_row + 1

    # Build values for cols A-E in one PUT
    out = [["Date", "MM/DD", "Description", "Amount", "Category"]]
    for iso, mmdd, desc, amt in rows:
        out.append([iso, mmdd, desc, amt, classify(desc, amt)])
    out.append(["", "", "", "", ""])
    out.append(["", "", "Deposits (positive)",   f"=SUMIF(D2:D{last_txn},\">0\")", ""])
    out.append(["", "", "Withdrawals (negative)", f"=SUMIF(D2:D{last_txn},\"<0\")", ""])
    out.append(["", "", "Transaction count",      f"=COUNTA(A2:A{last_txn})",      ""])

    # Clear A:H first, then write
    _api("POST", f"https://sheets.googleapis.com/v4/spreadsheets/{SID}/values/{TAB.replace(' ','%20')}!A1:Z200:clear",
         tok, data="{}")

    import requests
    url = (f"https://sheets.googleapis.com/v4/spreadsheets/{SID}"
           f"/values/{requests.utils.quote(TAB+'!A1', safe='!')}"
           "?valueInputOption=USER_ENTERED")
    _api("PUT", url, tok, data=json.dumps({"values": out}))
    print(f"wrote {len(out)} rows to {TAB}")

    # Build breakdown G/H
    bd = [["Category", "Spent"]]
    for cat in CATEGORIES:
        bd.append([cat, f"=IFERROR(-SUMIFS(D2:D{last_txn},E2:E{last_txn},G{len(bd)+1}),0)"])
    total_row = len(bd) + 1
    bd.append(["TOTAL", f"=SUM(H2:H{total_row-1})"])

    url = (f"https://sheets.googleapis.com/v4/spreadsheets/{SID}"
           f"/values/{requests.utils.quote(TAB+'!G1', safe='!')}"
           "?valueInputOption=USER_ENTERED")
    _api("PUT", url, tok, data=json.dumps({"values": bd}))
    print(f"wrote breakdown {len(bd)} rows")

    # Format cells
    fmts = [
        {"repeatCell": {
            "range": {"sheetId": sheet_id, "startRowIndex": 0, "endRowIndex": 1,
                      "startColumnIndex": 0, "endColumnIndex": 5},
            "cell": {"userEnteredFormat": {"textFormat": {"bold": True},
                      "backgroundColor": {"red":0.93,"green":0.93,"blue":0.93}}},
            "fields": "userEnteredFormat(textFormat,backgroundColor)"}},
        {"repeatCell": {
            "range": {"sheetId": sheet_id, "startRowIndex": 1, "endRowIndex": last_txn,
                      "startColumnIndex": 0, "endColumnIndex": 1},
            "cell": {"userEnteredFormat": {"numberFormat": {"type":"DATE","pattern":"yyyy-mm-dd"}}},
            "fields": "userEnteredFormat.numberFormat"}},
        {"repeatCell": {
            "range": {"sheetId": sheet_id, "startRowIndex": 1, "endRowIndex": last_txn,
                      "startColumnIndex": 1, "endColumnIndex": 2},
            "cell": {"userEnteredFormat": {"numberFormat": {"type":"DATE","pattern":"mm/dd"}}},
            "fields": "userEnteredFormat.numberFormat"}},
        # Amount currency: only rows 2..last_txn AND dep_row..wd_row (NOT cnt_row)
        {"repeatCell": {
            "range": {"sheetId": sheet_id, "startRowIndex": 1, "endRowIndex": last_txn,
                      "startColumnIndex": 3, "endColumnIndex": 4},
            "cell": {"userEnteredFormat": {"numberFormat": {"type":"CURRENCY","pattern":"$#,##0.00"}}},
            "fields": "userEnteredFormat.numberFormat"}},
        {"repeatCell": {
            "range": {"sheetId": sheet_id, "startRowIndex": dep_row-1, "endRowIndex": wd_row,
                      "startColumnIndex": 3, "endColumnIndex": 4},
            "cell": {"userEnteredFormat": {"numberFormat": {"type":"CURRENCY","pattern":"$#,##0.00"}}},
            "fields": "userEnteredFormat.numberFormat"}},
        {"repeatCell": {
            "range": {"sheetId": sheet_id, "startRowIndex": cnt_row-1, "endRowIndex": cnt_row,
                      "startColumnIndex": 3, "endColumnIndex": 4},
            "cell": {"userEnteredFormat": {"numberFormat": {"type":"NUMBER","pattern":"0"}}},
            "fields": "userEnteredFormat.numberFormat"}},
        {"repeatCell": {
            "range": {"sheetId": sheet_id, "startRowIndex": dep_row-1, "endRowIndex": cnt_row,
                      "startColumnIndex": 2, "endColumnIndex": 4},
            "cell": {"userEnteredFormat": {"textFormat": {"bold": True}}},
            "fields": "userEnteredFormat.textFormat"}},
        # Breakdown table
        {"repeatCell": {
            "range": {"sheetId": sheet_id, "startRowIndex": 0, "endRowIndex": 1,
                      "startColumnIndex": 6, "endColumnIndex": 8},
            "cell": {"userEnteredFormat": {"textFormat": {"bold": True},
                      "backgroundColor": {"red":0.93,"green":0.93,"blue":0.93}}},
            "fields": "userEnteredFormat(textFormat,backgroundColor)"}},
        {"repeatCell": {
            "range": {"sheetId": sheet_id, "startRowIndex": 1, "endRowIndex": total_row,
                      "startColumnIndex": 7, "endColumnIndex": 8},
            "cell": {"userEnteredFormat": {"numberFormat": {"type":"CURRENCY","pattern":"$#,##0.00"}}},
            "fields": "userEnteredFormat.numberFormat"}},
        {"repeatCell": {
            "range": {"sheetId": sheet_id, "startRowIndex": total_row-1, "endRowIndex": total_row,
                      "startColumnIndex": 6, "endColumnIndex": 8},
            "cell": {"userEnteredFormat": {"textFormat": {"bold": True},
                      "backgroundColor": {"red":1.0,"green":0.93,"blue":0.7}}},
            "fields": "userEnteredFormat(textFormat,backgroundColor)"}},
        {"autoResizeDimensions": {
            "dimensions": {"sheetId": sheet_id, "dimension": "COLUMNS",
                           "startIndex": 0, "endIndex": 8}}},
    ]
    _api("POST", f"https://sheets.googleapis.com/v4/spreadsheets/{SID}:batchUpdate", tok,
         data=json.dumps({"requests": fmts}))
    print("formatted")

    # No new chart needed (existing pie was added by prior script and may be stale —
    # since chart sources reference rows 2..(prev total_row-1), they may overshoot.
    # Re-create the chart cleanly: delete existing charts on this sheet first.
    m2 = _api("GET", f"https://sheets.googleapis.com/v4/spreadsheets/{SID}?fields=sheets(properties,charts)", tok)
    chart_ids = []
    for s in m2["sheets"]:
        if s["properties"]["sheetId"] == sheet_id:
            for c in s.get("charts", []):
                chart_ids.append(c["chartId"])
    del_reqs = [{"deleteEmbeddedObject": {"objectId": cid}} for cid in chart_ids]
    if del_reqs:
        _api("POST", f"https://sheets.googleapis.com/v4/spreadsheets/{SID}:batchUpdate", tok,
             data=json.dumps({"requests": del_reqs}))
        print(f"deleted {len(del_reqs)} stale chart(s)")

    chart_req = {"addChart": {"chart": {
        "spec": {
            "title": f"{TAB} — Spending by Category",
            "pieChart": {
                "legendPosition": "RIGHT_LEGEND",
                "threeDimensional": False,
                "domain": {"sourceRange": {"sources": [{
                    "sheetId": sheet_id,
                    "startRowIndex": 1, "endRowIndex": total_row - 1,
                    "startColumnIndex": 6, "endColumnIndex": 7}]}},
                "series": {"sourceRange": {"sources": [{
                    "sheetId": sheet_id,
                    "startRowIndex": 1, "endRowIndex": total_row - 1,
                    "startColumnIndex": 7, "endColumnIndex": 8}]}},
            },
        },
        "position": {"overlayPosition": {"anchorCell": {
            "sheetId": sheet_id, "rowIndex": 0, "columnIndex": 9
        }, "widthPixels": 640, "heightPixels": 420}}}}}
    _api("POST", f"https://sheets.googleapis.com/v4/spreadsheets/{SID}:batchUpdate", tok,
         data=json.dumps({"requests": [chart_req]}))
    print("re-added pie chart")
    print(f"DONE: https://docs.google.com/spreadsheets/d/{SID}/edit#gid={sheet_id}")


if __name__ == "__main__":
    main()
