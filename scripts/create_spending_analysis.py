#!/usr/bin/env python3
"""Build a Google Sheet analyzing Chase statement Mar 26 - Apr 24, 2026
(account ending 3915, Robert Littlejohn). Includes:
  - Tab 1: Summary (statement-level)
  - Tab 2: Transactions (every line, categorized)
  - Tab 3: Category Analysis (pivot + pie chart + bar chart)
"""
import json
import subprocess

from google_sheets_helper import (
    _access_token, _api, create_sheet, write_values,
    batch_write_values, batch_format,
    fmt_bold, fmt_auto_resize,
)

TITLE = "Chase Spending Analysis — Mar–Apr 2026 (Acct 3915)"

# ----- Transactions: (date, description, amount, category) -----------------
# Positive = deposit/credit, Negative = withdrawal
TXNS = [
    # Date,    Description,                              Amount,   Category
    ("03/26", "Apple.com/Bill (subscription)",            -4.99,   "Subscriptions"),
    ("03/26", "Chevron — gas",                            -45.51,  "Gas"),
    ("03/27", "Zelle From Ashley Clark",                 893.75,   "Deposit (Zelle In)"),
    ("03/27", "Vagaro Face/Body",                         -48.00,  "Personal Care"),
    ("03/29", "Ulta.com",                                 -140.56, "Personal Care"),
    ("03/27", "Amazon Prime",                             -15.16,  "Subscriptions"),
    ("03/28", "Toi Spa",                                  -125.00, "Personal Care"),
    ("03/30", "Zelle To Lydia Mani",                      -20.00,  "Zelle Out"),
    ("03/28", "Costco Whse #0623",                        -213.99, "Costco"),
    ("03/28", "Costco Whse #0623",                        -13.25,  "Costco"),
    ("03/29", "Everglades Petro — gas",                   -45.63,  "Gas"),
    ("03/29", "Publix Super Market",                      -86.19,  "Groceries"),
    ("03/29", "Publix Super Market",                      -12.19,  "Groceries"),
    ("04/01", "Zelle From Ashley Clark",                 781.75,   "Deposit (Zelle In)"),
    ("03/31", "Sushi Yama",                               -25.28,  "Dining Out"),
    ("03/31", "Sushi Yama",                               -64.63,  "Dining Out"),
    ("04/02", "Zelle To R2D2",                            -900.00, "Zelle Out"),
    ("04/03", "Zelle From Ashley Clark",                 456.50,   "Deposit (Zelle In)"),
    ("04/02", "Amazon Marketplace",                       -39.99,  "Amazon Shopping"),
    ("04/02", "Amazon Marketplace",                       -21.00,  "Amazon Shopping"),
    ("04/02", "Amazon Marketplace",                       -29.95,  "Amazon Shopping"),
    ("04/02", "Spotify",                                  -21.39,  "Subscriptions"),
    ("04/06", "Zelle From Brittany Garcia",               10.00,   "Deposit (Zelle In)"),
    ("04/04", "Google YouTube Membership",                -4.99,   "Subscriptions"),
    ("04/04", "Schumacher VW (service)",                  -210.82, "Auto"),
    ("04/04", "Marathon — gas",                           -57.07,  "Gas"),
    ("04/04", "Chick-Fil-A",                              -6.27,   "Dining Out"),
    ("04/04", "Walgreens",                                -13.57,  "Misc Retail"),
    ("04/05", "Trader Joe's",                             -72.10,  "Groceries"),
    ("04/05", "Wal-Mart",                                 -57.09,  "Groceries"),
    ("04/06", "Zelle To Brittany Garcia",                 -10.00,  "Zelle Out"),
    ("04/06", "Eb*Jetset On The Mat",                     -28.52,  "Misc Retail"),
    ("04/07", "Amazon Marketplace",                       -47.89,  "Amazon Shopping"),
    ("04/10", "Zelle From Ashley Clark",                 1069.31,  "Deposit (Zelle In)"),
    ("04/10", "Zelle From Ashley Clark",                  30.00,   "Deposit (Zelle In)"),
    ("04/13", "Zelle From Robert Littlejohn",            1000.00,  "Deposit (Zelle In)"),
    ("04/11", "Sephora Boynton Beach",                    -23.86,  "Personal Care"),
    ("04/12", "Trader Joe's",                             -86.55,  "Groceries"),
    ("04/12", "Everglades Petro — gas",                   -51.91,  "Gas"),
    ("04/12", "Publix",                                   -64.70,  "Groceries"),
    ("04/13", "Online Transfer To Chk 2205",              -125.00, "Transfer Out"),
    ("04/14", "Citi Card Online Payment",                 -586.42, "Credit Card Payment"),
    ("04/14", "Walgreens",                                -17.56,  "Misc Retail"),
    ("04/14", "Florida Woman Care Lab",                   -75.00,  "Healthcare"),
    ("04/14", "Season Women's Care",                      -120.00, "Healthcare"),
    ("04/15", "Children's Museum",                        -10.00,  "Misc Retail"),
    ("04/16", "Apple.com/Bill",                           -9.99,   "Subscriptions"),
    ("04/17", "Zelle From Ashley Clark",                  848.20,  "Deposit (Zelle In)"),
    ("04/17", "Target",                                   -21.29,  "Misc Retail"),
    ("04/17", "Target",                                   -4.89,   "Misc Retail"),
    ("04/20", "VW Credit Auto Debit",                     -318.81, "Auto"),
    ("04/20", "VW Credit Auto Debit",                     -299.60, "Auto"),
    ("04/18", "MDNow Royal Palm Beach",                   -75.00,  "Healthcare"),
    ("04/18", "Publix",                                   -67.43,  "Groceries"),
    ("04/19", "Trader Joe's",                             -34.44,  "Groceries"),
    ("04/20", "ATM Withdrawal — Lake Worth",              -160.00, "Cash / ATM"),
    ("04/21", "Seed.com",                                 -49.99,  "Subscriptions"),
    ("04/21", "Withdrawal (Official Check)",              -300.00, "Official Checks"),
    ("04/21", "Withdrawal (Official Check)",              -50.00,  "Official Checks"),
    ("04/21", "Official Checks Charge",                   -10.00,  "Bank Fees"),
    ("04/21", "Official Checks Charge",                   -10.00,  "Bank Fees"),
    ("04/22", "Amazon Return (credit)",                    72.42,  "Amazon Return"),
    ("04/22", "Amazon Return (credit)",                    72.42,  "Amazon Return"),
    ("04/22", "Zelle From Robert Littlejohn",             500.00,  "Deposit (Zelle In)"),
    ("04/22", "Amazon Marketplace",                       -173.68, "Amazon Shopping"),
    ("04/22", "Sephora Boynton Beach",                    -67.74,  "Personal Care"),
    ("04/22", "Sephora Boynton Beach",                    -30.89,  "Personal Care"),
    ("04/22", "Whole Foods",                              -70.11,  "Groceries"),
    ("04/22", "Wawa — gas",                               -51.92,  "Gas"),
    ("04/23", "Amazon.com",                               -17.00,  "Amazon Shopping"),
    ("04/23", "AT&T Bill Payment",                        -205.81, "Bills / Utilities"),
    ("04/22", "Amazon Marketplace",                       -14.09,  "Amazon Shopping"),
    ("04/23", "Zelle To Silver",                          -15.00,  "Zelle Out"),
    ("04/24", "Zelle From Ashley Clark",                 1217.42,  "Deposit (Zelle In)"),
    ("04/24", "Quest Diagnostics",                        -75.00,  "Healthcare"),
    ("04/23", "MJ's Jewelry And Watch",                   -85.20,  "Misc Retail"),
    ("04/24", "Monthly Service Fee",                      -15.00,  "Bank Fees"),
]

def main():
    print("creating spreadsheet…", flush=True)
    sid, url = create_sheet(TITLE)
    print(f"  id={sid}\n  url={url}", flush=True)
    tok = _access_token()

    # ------- Tab 1: Summary ---------------------------------------------
    SUMMARY_TAB = "Summary"
    # Rename default Sheet1 → Summary
    _api("POST", f"https://sheets.googleapis.com/v4/spreadsheets/{sid}:batchUpdate", tok,
         data=json.dumps({"requests":[{"updateSheetProperties":{
             "properties":{"sheetId":0,"title":SUMMARY_TAB},
             "fields":"title"}}]}))

    summary = [
        ["CHASE TOTAL CHECKING — STATEMENT SUMMARY"],
        ["Account ending 3915  |  Robert Littlejohn / Gabriela Rigo Bussotti"],
        ["Statement period: March 26, 2026 — April 24, 2026 (30 days)"],
        [""],
        ["Metric", "Amount"],
        ["Beginning Balance",       245.70],
        ["Deposits & Additions",   6951.77],
        ["ATM & Debit Withdrawals",-3115.08],
        ["Electronic Withdrawals", -2274.83],
        ["Other Withdrawals",       -350.00],
        ["Fees",                     -35.00],
        ["Ending Balance",         1422.56],
        [""],
        ["Net change this period", None],  # formula
        ["Total inflows",          None],
        ["Total outflows",         None],
        ["Daily avg spend",        None],
    ]
    write_values(sid, f"'{SUMMARY_TAB}'!A1", summary)

    # ------- Tab 2: Transactions -----------------------------------------
    TXN_TAB = "Transactions"
    _api("POST", f"https://sheets.googleapis.com/v4/spreadsheets/{sid}:batchUpdate", tok,
         data=json.dumps({"requests":[{"addSheet":{"properties":{"title":TXN_TAB}}}]}))

    txn_rows = [["Date", "Description", "Amount", "Category"]] + [list(t) for t in TXNS]
    write_values(sid, f"'{TXN_TAB}'!A1", txn_rows)

    # ------- Tab 3: Category Analysis (pivot via formulas) ---------------
    CAT_TAB = "Category Analysis"
    add = _api("POST", f"https://sheets.googleapis.com/v4/spreadsheets/{sid}:batchUpdate", tok,
         data=json.dumps({"requests":[{"addSheet":{"properties":{"title":CAT_TAB}}}]}))
    cat_sheet_id = add["replies"][0]["addSheet"]["properties"]["sheetId"]

    # Ordered categories (spending only — exclude deposits/returns)
    spending_categories = [
        "Auto",
        "Zelle Out",
        "Credit Card Payment",
        "Groceries",
        "Personal Care",
        "Healthcare",
        "Official Checks",
        "Cash / ATM",
        "Gas",
        "Amazon Shopping",
        "Costco",
        "Bills / Utilities",
        "Misc Retail",
        "Transfer Out",
        "Subscriptions",
        "Dining Out",
        "Bank Fees",
    ]

    cat_rows = []
    cat_rows.append(["SPENDING BY CATEGORY — Mar 26 to Apr 24, 2026"])
    cat_rows.append(["(Excludes Zelle Deposits In and Amazon Returns)"])
    cat_rows.append([""])
    cat_rows.append(["Category", "Amount Spent", "% of Total"])
    last_data_row = 4 + len(spending_categories)
    for cat in spending_categories:
        cat_rows.append([
            cat,
            f"=ABS(SUMIF(Transactions!D:D,A{4 + len(cat_rows) - 3},Transactions!C:C))",
            None,  # formula filled below
        ])
    cat_rows.append([
        "TOTAL SPENDING",
        f"=SUM(B5:B{last_data_row})",
        f"=SUM(C5:C{last_data_row})",
    ])
    cat_rows.append([""])
    cat_rows.append(["DEPOSITS (inflows)", f"=SUMIF(Transactions!D:D,\"Deposit (Zelle In)\",Transactions!C:C)"])
    cat_rows.append(["AMAZON RETURNS",      f"=SUMIF(Transactions!D:D,\"Amazon Return\",Transactions!C:C)"])
    cat_rows.append(["NET CASH FLOW", f"=B{last_data_row+3} + B{last_data_row+4} - B{last_data_row+1}"])

    write_values(sid, f"'{CAT_TAB}'!A1", cat_rows)

    # Fix the SUMIF references — when I built `cat_rows` I miscomputed the A-column reference
    # Re-write the per-category formulas cleanly now that we know the rows
    fix_updates = []
    for i, cat in enumerate(spending_categories):
        row = 5 + i
        fix_updates.append((f"'{CAT_TAB}'!B{row}",
                            [[f'=ABS(SUMIF(Transactions!D:D,A{row},Transactions!C:C))']]))
        fix_updates.append((f"'{CAT_TAB}'!C{row}",
                            [[f'=B{row}/$B${last_data_row+1}']]))
    batch_write_values(sid, fix_updates)

    # ------- Summary tab formulas ----------------------------------------
    s_formulas = [
        (f"'{SUMMARY_TAB}'!B14", [["=B12-B6"]]),                      # net change = end - begin
        (f"'{SUMMARY_TAB}'!B15", [["=B7"]]),                          # total inflows
        (f"'{SUMMARY_TAB}'!B16", [["=B8+B9+B10+B11"]]),               # total outflows (sum negatives)
        (f"'{SUMMARY_TAB}'!B17", [["=ABS(B16)/30"]]),                 # daily avg spend (30 days)
    ]
    batch_write_values(sid, s_formulas)

    # ------- Formatting --------------------------------------------------
    fmts = []
    # Summary tab
    fmts.append(fmt_bold(0, 0, 1, 0, 6, bg=(0.10,0.20,0.30), font_size=14))
    fmts.append({"repeatCell":{
        "range":{"sheetId":0,"startRowIndex":0,"endRowIndex":1,"startColumnIndex":0,"endColumnIndex":6},
        "cell":{"userEnteredFormat":{"textFormat":{"foregroundColor":{"red":1,"green":1,"blue":1}}}},
        "fields":"userEnteredFormat.textFormat.foregroundColor"}})
    fmts.append(fmt_bold(0, 4, 5, 0, 2, bg=(0.93,0.93,0.93)))
    fmts.append({"repeatCell":{
        "range":{"sheetId":0,"startRowIndex":5,"endRowIndex":17,"startColumnIndex":1,"endColumnIndex":2},
        "cell":{"userEnteredFormat":{"numberFormat":{"type":"CURRENCY","pattern":"$#,##0.00"}}},
        "fields":"userEnteredFormat.numberFormat"}})
    fmts.append(fmt_bold(0, 11, 12, 0, 2, bg=(1.0,0.93,0.7)))      # ending balance row
    fmts.append(fmt_bold(0, 13, 17, 0, 2, bg=(0.82,0.92,0.82)))    # computed metrics
    fmts.append(fmt_auto_resize(0, 0, 6))

    # Transactions tab (sheetId TBD — let's get it)
    meta = _api("GET", f"https://sheets.googleapis.com/v4/spreadsheets/{sid}", tok)
    txn_sheet_id = next(s["properties"]["sheetId"] for s in meta["sheets"] if s["properties"]["title"]==TXN_TAB)
    fmts.append(fmt_bold(txn_sheet_id, 0, 1, 0, 4, bg=(0.93,0.93,0.93)))
    fmts.append({"repeatCell":{
        "range":{"sheetId":txn_sheet_id,"startRowIndex":1,"endRowIndex":1+len(TXNS),"startColumnIndex":2,"endColumnIndex":3},
        "cell":{"userEnteredFormat":{"numberFormat":{"type":"CURRENCY","pattern":"$#,##0.00"}}},
        "fields":"userEnteredFormat.numberFormat"}})
    fmts.append({"updateSheetProperties":{
        "properties":{"sheetId":txn_sheet_id,"gridProperties":{"frozenRowCount":1}},
        "fields":"gridProperties.frozenRowCount"}})
    fmts.append(fmt_auto_resize(txn_sheet_id, 0, 4))

    # Category Analysis tab
    fmts.append(fmt_bold(cat_sheet_id, 0, 1, 0, 4, bg=(0.10,0.30,0.15), font_size=14))
    fmts.append({"repeatCell":{
        "range":{"sheetId":cat_sheet_id,"startRowIndex":0,"endRowIndex":1,"startColumnIndex":0,"endColumnIndex":4},
        "cell":{"userEnteredFormat":{"textFormat":{"foregroundColor":{"red":1,"green":1,"blue":1}}}},
        "fields":"userEnteredFormat.textFormat.foregroundColor"}})
    fmts.append(fmt_bold(cat_sheet_id, 3, 4, 0, 3, bg=(0.93,0.93,0.93)))
    fmts.append({"repeatCell":{
        "range":{"sheetId":cat_sheet_id,"startRowIndex":4,"endRowIndex":last_data_row+1,"startColumnIndex":1,"endColumnIndex":2},
        "cell":{"userEnteredFormat":{"numberFormat":{"type":"CURRENCY","pattern":"$#,##0.00"}}},
        "fields":"userEnteredFormat.numberFormat"}})
    fmts.append({"repeatCell":{
        "range":{"sheetId":cat_sheet_id,"startRowIndex":4,"endRowIndex":last_data_row+1,"startColumnIndex":2,"endColumnIndex":3},
        "cell":{"userEnteredFormat":{"numberFormat":{"type":"PERCENT","pattern":"0.0%"}}},
        "fields":"userEnteredFormat.numberFormat"}})
    fmts.append(fmt_bold(cat_sheet_id, last_data_row, last_data_row+1, 0, 3, bg=(1.0,0.93,0.7)))  # TOTAL row
    # Net cash flow + inflows rows
    fmts.append({"repeatCell":{
        "range":{"sheetId":cat_sheet_id,"startRowIndex":last_data_row+2,"endRowIndex":last_data_row+5,"startColumnIndex":1,"endColumnIndex":2},
        "cell":{"userEnteredFormat":{"numberFormat":{"type":"CURRENCY","pattern":"$#,##0.00"}}},
        "fields":"userEnteredFormat.numberFormat"}})
    fmts.append(fmt_bold(cat_sheet_id, last_data_row+4, last_data_row+5, 0, 2, bg=(0.82,0.92,0.82)))
    fmts.append(fmt_auto_resize(cat_sheet_id, 0, 4))

    # ------- Charts ------------------------------------------------------
    # Pie chart: spending by category
    chart_reqs = []
    chart_reqs.append({"addChart": {"chart": {
        "spec": {
            "title": "Spending by Category — Mar/Apr 2026",
            "pieChart": {
                "legendPosition": "RIGHT_LEGEND",
                "threeDimensional": False,
                "domain": {"sourceRange": {"sources":[{
                    "sheetId": cat_sheet_id,
                    "startRowIndex": 4, "endRowIndex": last_data_row,
                    "startColumnIndex": 0, "endColumnIndex": 1,
                }]}},
                "series": {"sourceRange": {"sources":[{
                    "sheetId": cat_sheet_id,
                    "startRowIndex": 4, "endRowIndex": last_data_row,
                    "startColumnIndex": 1, "endColumnIndex": 2,
                }]}},
            },
        },
        "position": {"overlayPosition": {"anchorCell": {
            "sheetId": cat_sheet_id, "rowIndex": 3, "columnIndex": 4
        }, "widthPixels": 600, "heightPixels": 400}}
    }}})

    # Bar chart: top categories sorted
    chart_reqs.append({"addChart": {"chart": {
        "spec": {
            "title": "Top Spending Categories",
            "basicChart": {
                "chartType": "BAR",
                "legendPosition": "NO_LEGEND",
                "domains": [{"domain": {"sourceRange": {"sources":[{
                    "sheetId": cat_sheet_id,
                    "startRowIndex": 4, "endRowIndex": last_data_row,
                    "startColumnIndex": 0, "endColumnIndex": 1,
                }]}}}],
                "series": [{"series": {"sourceRange": {"sources":[{
                    "sheetId": cat_sheet_id,
                    "startRowIndex": 4, "endRowIndex": last_data_row,
                    "startColumnIndex": 1, "endColumnIndex": 2,
                }]}}, "targetAxis": "BOTTOM_AXIS"}],
            },
        },
        "position": {"overlayPosition": {"anchorCell": {
            "sheetId": cat_sheet_id, "rowIndex": 23, "columnIndex": 4
        }, "widthPixels": 600, "heightPixels": 400}}
    }}})

    print(f"applying {len(fmts)} formatting + {len(chart_reqs)} chart requests…", flush=True)
    batch_format(sid, fmts + chart_reqs)

    print(f"DONE: {url}", flush=True)
    subprocess.run(["open", "-a", "Google Chrome", url], check=False)

if __name__ == "__main__":
    main()
