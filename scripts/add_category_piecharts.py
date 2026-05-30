#!/usr/bin/env python3
"""For each month tab in the Chase 3915 sheet:
  - add a Category column (E) with rule-based classifier
  - build a small per-category breakdown (F-G) using SUMIF formulas
  - embed a pie chart anchored to that area
Excludes deposits/credits (positive amounts) from the pie."""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from google_sheets_helper import _access_token, _api, write_values

SID = "1AY161cwEj-Aq4OU74TN8m7e2YIyNoUXnyPnvE1VQ9iQ"
MONTHS = ["Jan 2026", "Feb 2026", "Mar 2026", "Apr 2026", "May 2026"]

# Ordered: first match wins
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


def classify(desc: str, amt: float) -> str:
    if amt > 0:
        return "INFLOW (excluded)"
    for cat, pat in RULES:
        if pat.search(desc):
            return cat
    return "Misc Retail"


def main():
    tok = _access_token()
    meta = _api("GET", f"https://sheets.googleapis.com/v4/spreadsheets/{SID}", tok)
    sheet_ids = {s["properties"]["title"]: s["properties"]["sheetId"] for s in meta["sheets"]}

    chart_reqs = []

    for tab in MONTHS:
        # Pull existing rows
        rows = _api("GET", f"https://sheets.googleapis.com/v4/spreadsheets/{SID}"
                          f"/values/{tab.replace(' ','%20')}!A1:D200"
                          "?valueRenderOption=UNFORMATTED_VALUE", tok).get("values", [])
        # Find last txn row (first blank after header)
        last_txn = 1
        for i, r in enumerate(rows[1:], start=2):
            if not r or r[0] in ("", None):
                break
            last_txn = i

        # Build category column values
        cats = []
        for i in range(2, last_txn + 1):
            desc = rows[i - 1][2] if len(rows[i - 1]) > 2 else ""
            amt = rows[i - 1][3] if len(rows[i - 1]) > 3 else 0
            cats.append([classify(str(desc), float(amt))])

        # Write header + categories
        write_values(SID, f"'{tab}'!E1", [["Category"]])
        write_values(SID, f"'{tab}'!E2", cats)

        # Breakdown table in cols G/H starting row 1
        breakdown = [["Category", "Spent"]]
        for cat in CATEGORIES:
            breakdown.append([cat,
                f"=IFERROR(-SUMIFS(D2:D{last_txn},E2:E{last_txn},G{len(breakdown)+1}),0)"])
        total_row = len(breakdown) + 1
        breakdown.append(["TOTAL", f"=SUM(H2:H{total_row - 1})"])
        write_values(SID, f"'{tab}'!G1", breakdown)

        # Format breakdown table
        sid_int = sheet_ids[tab]
        fmt = [
            {"repeatCell": {
                "range": {"sheetId": sid_int, "startRowIndex": 0, "endRowIndex": 1,
                          "startColumnIndex": 6, "endColumnIndex": 8},
                "cell": {"userEnteredFormat": {"textFormat": {"bold": True},
                          "backgroundColor": {"red": 0.93, "green": 0.93, "blue": 0.93}}},
                "fields": "userEnteredFormat(textFormat,backgroundColor)"}},
            {"repeatCell": {
                "range": {"sheetId": sid_int, "startRowIndex": 1, "endRowIndex": total_row,
                          "startColumnIndex": 7, "endColumnIndex": 8},
                "cell": {"userEnteredFormat": {"numberFormat": {"type": "CURRENCY", "pattern": "$#,##0.00"}}},
                "fields": "userEnteredFormat.numberFormat"}},
            {"repeatCell": {
                "range": {"sheetId": sid_int, "startRowIndex": total_row - 1, "endRowIndex": total_row,
                          "startColumnIndex": 6, "endColumnIndex": 8},
                "cell": {"userEnteredFormat": {"textFormat": {"bold": True},
                          "backgroundColor": {"red": 1.0, "green": 0.93, "blue": 0.7}}},
                "fields": "userEnteredFormat(textFormat,backgroundColor)"}},
            {"autoResizeDimensions": {
                "dimensions": {"sheetId": sid_int, "dimension": "COLUMNS",
                               "startIndex": 4, "endIndex": 8}}},
        ]
        _api("POST", f"https://sheets.googleapis.com/v4/spreadsheets/{SID}:batchUpdate", tok,
             data=json.dumps({"requests": fmt}))

        # Pie chart anchored at column J (col index 9), row 0
        chart_reqs.append({"addChart": {"chart": {
            "spec": {
                "title": f"{tab} — Spending by Category",
                "pieChart": {
                    "legendPosition": "RIGHT_LEGEND",
                    "threeDimensional": False,
                    "domain": {"sourceRange": {"sources": [{
                        "sheetId": sid_int,
                        "startRowIndex": 1, "endRowIndex": total_row - 1,
                        "startColumnIndex": 6, "endColumnIndex": 7,
                    }]}},
                    "series": {"sourceRange": {"sources": [{
                        "sheetId": sid_int,
                        "startRowIndex": 1, "endRowIndex": total_row - 1,
                        "startColumnIndex": 7, "endColumnIndex": 8,
                    }]}},
                },
            },
            "position": {"overlayPosition": {"anchorCell": {
                "sheetId": sid_int, "rowIndex": 0, "columnIndex": 9
            }, "widthPixels": 640, "heightPixels": 420}}
        }}})

        print(f"  {tab}: {last_txn - 1} txns categorized, breakdown rows={total_row}")

    _api("POST", f"https://sheets.googleapis.com/v4/spreadsheets/{SID}:batchUpdate", tok,
         data=json.dumps({"requests": chart_reqs}))
    print(f"added {len(chart_reqs)} pie charts")


if __name__ == "__main__":
    main()
