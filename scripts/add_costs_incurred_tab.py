#!/usr/bin/env python3
"""Add a 'Costs Already Incurred' tab to the firm-setup spreadsheet."""
import sys

from google_sheets_helper import (
    _access_token, _api, write_values, batch_format,
    fmt_bold, fmt_currency, fmt_auto_resize,
)

SHEET_ID = "14VDWJwsAMRpN0kV3RPGpoV085RJIPNPEqV-Gpw4V8kg"
TAB_TITLE = "Costs Already Incurred"

ROWS_HEADER = [["Item", "Cost ($)", "Frequency", "Status", "Notes"]]

ROWS_ONE_TIME = [
    ["Computer (work laptop)", 500, "One-time", "PAID", "Already incurred"],
]

ROWS_SUBS = [
    ["Namecheap — robinhoodadjusting.com",   15,  "Annual",   "ACTIVE",  ".com renewal, ~$13-15/yr"],
    ["Netlify — website hosting",             0,  "Monthly",  "ACTIVE",  "Free tier (low traffic)"],
    ["GitHub — code repo",                    0,  "Monthly",  "ACTIVE",  "Free tier (public repo)"],
    ["Gmail — duncanlittlejohn727@gmail.com", 0,  "Monthly",  "ACTIVE",  "Free Gmail account"],
    ["HubSpot — CRM + native email",          0,  "Monthly",  "ACTIVE",  "Tier TBD — confirm Free vs Starter ($15/mo) vs Pro ($90/mo)"],
    ["Calendly — booking links",              0,  "Monthly",  "ACTIVE",  "Tier TBD — Free or Standard ($10/mo)"],
    ["Claude (Anthropic) — AI assistant",     0,  "Monthly",  "ACTIVE",  "Tier TBD — upgraded 2026-05-15; confirm Max plan ($100 or $200/mo)"],
    ["Google Places API",                     0,  "Monthly",  "ACTIVE",  "Within $200/mo free credit (~$0.24 actual usage)"],
]

ROWS_PLANNED_HEADER = [["Item", "Cost ($)", "Frequency", "Status", "Notes"]]
ROWS_PLANNED = [
    ["Meta Ads (FB/IG)", 500, "Monthly", "PLANNED",  "Launch target: 2026-06-01"],
]


def add_sheet(spreadsheet_id: str, title: str) -> int:
    token = _access_token()
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}:batchUpdate"
    body = {"requests": [{"addSheet": {"properties": {"title": title}}}]}
    import json
    res = _api("POST", url, token, data=json.dumps(body))
    return res["replies"][0]["addSheet"]["properties"]["sheetId"]


def section_title(text):
    return [[text]]


def main():
    print(f"adding tab '{TAB_TITLE}'…", flush=True)
    sheet_id = add_sheet(SHEET_ID, TAB_TITLE)
    print(f"  sheetId={sheet_id}", flush=True)

    blank = [[""]]
    content = []
    content += section_title("ROBINHOOD ADJUSTING — COSTS ALREADY INCURRED")
    content += [["As of 2026-05-26"]]
    content += blank
    content += section_title("1. ONE-TIME COSTS PAID")
    content += ROWS_HEADER + ROWS_ONE_TIME
    content += blank
    content += section_title("2. ONGOING SUBSCRIPTIONS")
    content += ROWS_HEADER + ROWS_SUBS
    content += blank
    content += section_title("3. PLANNED (NOT YET INCURRED)")
    content += ROWS_PLANNED_HEADER + ROWS_PLANNED
    content += blank
    content += section_title("4. MONTHLY SUBSCRIPTION TOTAL (current)")
    content += [["Confirmed monthly recurring", "$0 + TBD tiers"]]
    content += [["Once HubSpot/Calendly/Claude tiers confirmed, fill in actuals", ""]]

    a1 = f"'{TAB_TITLE}'!A1"
    print(f"writing {len(content)} rows…", flush=True)
    write_values(SHEET_ID, a1, content)

    fmts = []
    row = 0
    # title
    fmts.append(fmt_bold(sheet_id, row, row + 1, 0, 6, bg=(0.12, 0.12, 0.14), font_size=14))
    fmts.append({
        "repeatCell": {
            "range": {"sheetId": sheet_id, "startRowIndex": row, "endRowIndex": row + 1, "startColumnIndex": 0, "endColumnIndex": 6},
            "cell": {"userEnteredFormat": {"textFormat": {"foregroundColor": {"red": 1, "green": 1, "blue": 1}}}},
            "fields": "userEnteredFormat.textFormat.foregroundColor",
        }
    })
    row += 1  # subtitle
    row += 1
    row += 1  # blank
    # Section 1
    fmts.append(fmt_bold(sheet_id, row, row + 1, 0, 5, bg=(0.85, 0.92, 1.0)))
    row += 1
    fmts.append(fmt_bold(sheet_id, row, row + 1, 0, 5, bg=(0.93, 0.93, 0.93)))
    row += 1
    s1_start = row
    row += len(ROWS_ONE_TIME)
    s1_end = row
    fmts.append(fmt_currency(sheet_id, s1_start, s1_end, 1, 2))

    row += 1  # blank
    # Section 2
    fmts.append(fmt_bold(sheet_id, row, row + 1, 0, 5, bg=(0.85, 0.92, 1.0)))
    row += 1
    fmts.append(fmt_bold(sheet_id, row, row + 1, 0, 5, bg=(0.93, 0.93, 0.93)))
    row += 1
    s2_start = row
    row += len(ROWS_SUBS)
    s2_end = row
    fmts.append(fmt_currency(sheet_id, s2_start, s2_end, 1, 2))

    row += 1  # blank
    # Section 3
    fmts.append(fmt_bold(sheet_id, row, row + 1, 0, 5, bg=(1.0, 0.95, 0.85)))
    row += 1
    fmts.append(fmt_bold(sheet_id, row, row + 1, 0, 5, bg=(0.93, 0.93, 0.93)))
    row += 1
    s3_start = row
    row += len(ROWS_PLANNED)
    s3_end = row
    fmts.append(fmt_currency(sheet_id, s3_start, s3_end, 1, 2))

    row += 1  # blank
    # Section 4
    fmts.append(fmt_bold(sheet_id, row, row + 1, 0, 5, bg=(0.85, 0.92, 1.0)))

    fmts.append(fmt_auto_resize(sheet_id, 0, 6))

    print(f"applying {len(fmts)} format requests…", flush=True)
    batch_format(SHEET_ID, fmts)

    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit#gid={sheet_id}"
    print(f"DONE: {url}", flush=True)
    import subprocess
    subprocess.run(["open", "-a", "Google Chrome", url], check=False)


if __name__ == "__main__":
    main()
