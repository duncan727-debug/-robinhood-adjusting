#!/usr/bin/env python3
"""Push the Robinhood firm-setup costs + timeline into a fresh, well-formatted
Google Sheet. Opens it in Chrome when done."""
import subprocess
import sys

from google_sheets_helper import (
    create_sheet, write_values, batch_format,
    fmt_bold, fmt_currency, fmt_auto_resize, fmt_freeze,
)

TITLE = "Robinhood Adjusting — Firm Setup (Costs & Timeline)"

# Each block is (a1_anchor, rows). Rows are lists of cell values.
ROWS_COSTS_HEADER = [["Component", "Low ($)", "High ($)", "Frequency", "Notes"]]
ROWS_COSTS = [
    ["FL LLC formation (Sunbiz)",           125,  125,  "One-time", "Same-day file; Duncan is registered agent"],
    ["EIN (IRS)",                             0,    0,  "One-time", "Free online, instant"],
    ["FL Adjusting Firm License (DFS)",       0,    0,  "One-time", "No application fee; perpetual if primary adjuster designated"],
    ["$50K Surety Bond premium",            500,  750,  "Annual",   "Existing individual bond may transfer; credit-dependent"],
    ["E&O Insurance ($1M / $1M)",           500, 1000,  "Annual",   "Solo PA firm typical range; ~$750 midpoint"],
    ["General Liability Insurance",         400,  800,  "Annual",   "Optional but standard for client visits"],
    ["Business Bank Account",                 0,  300,  "Annual",   "$0 if free biz checking; up to $25/mo otherwise"],
    ["Domain / website / email",              0,    0,  "Annual",   "robinhoodadjusting.com already live"],
    ["FL LLC Annual Report (year 2+)",      138,  138,  "Annual",   "Filed via Sunbiz"],
]

ROWS_TOTALS_HEADER = [["Period", "Low ($)", "High ($)"]]
ROWS_TOTALS = [
    ["First-Year Total (all-in)",          1525, 2975],
    ["Recurring Annual (year 2+)",         1538, 2688],
    ["Attorney consult (contingent)",       150,  300],
]

ROWS_TIMELINE_HEADER = [["Day", "Action", "Owner", "Status", "Notes"]]
ROWS_TIMELINE = [
    ["D1 (Tue 2026-05-26)", "Re-read Barclays contract for non-compete/non-solicit", "Duncan", "OPEN",  "Blocks everything below if a restriction exists"],
    ["D1",                  "File FL LLC on Sunbiz",                                    "Duncan", "OPEN",  "Smith to prep filing language"],
    ["D1",                  "Apply for EIN online (IRS.gov)",                           "Duncan", "OPEN",  "Instant"],
    ["D1",                  "Request bond + E&O quotes",                                "Smith",  "OPEN",  "3 carrier quotes target"],
    ["D2-3",                "Review quotes",                                            "Both",   "—",     ""],
    ["D2-3",                "Bind bond + E&O policies",                                 "Duncan", "—",     "Pay first premium"],
    ["D5-7",                "LLC confirmation received",                                "—",      "—",     "Required before bank account"],
    ["D5-7",                "Open business bank account",                               "Duncan", "—",     "Chase / BoA / local CU"],
    ["D7-10",               "File FL DFS Adjusting Firm License application",           "Smith drafts; Duncan signs", "—", "Designate self as primary adjuster"],
    ["D21-35",              "DFS approval (typical 2-4 weeks)",                         "—",      "—",     "License # issued"],
    ["~July 1, 2026",       "Firm operational",                                         "—",      "TARGET","Aligned with Barclays exit"],
]

ROWS_RISKS_HEADER = [["Risk", "Severity", "Mitigation"]]
ROWS_RISKS = [
    ["Barclays non-compete or non-solicit clause",         "HIGH",   "Re-read contract TODAY; $150-300 attorney consult if any clause unclear"],
    ["Existing surety bond not transferable to firm",      "LOW",    "Confirm with bond carrier; new bond ~$500"],
    ["DFS application requires fingerprinting (re-do)",    "LOW",    "Already on file from initial license; verify not required again"],
    ["Barclays-originated claims stay with Barclays",      "HIGH",   "Plan to retain only new claims post-firm-license"],
    ["DFS approval slower than 4 weeks",                   "MEDIUM", "File D7 to give 4-week buffer before July 1"],
]

ROWS_ACTIONS_HEADER = [["#", "Action", "Owner", "Due"]]
ROWS_ACTIONS = [
    [1, "Locate + read Barclays contract",          "Duncan", "EOD Tue 5/26"],
    [2, "Prep Sunbiz LLC filing form draft",        "Smith",  "Wed 5/27 AM"],
    [3, "Request 3 surety bond quotes",             "Smith",  "Wed 5/27 AM"],
    [4, "Request 3 E&O quotes",                     "Smith",  "Wed 5/27 AM"],
    [5, "Sign + submit LLC + EIN",                  "Duncan", "Wed 5/27 PM (after #1 clears)"],
]


def section_title(text):
    return [[text]]


def main():
    print("creating spreadsheet…", flush=True)
    sid, url = create_sheet(TITLE)
    print(f"  id={sid}", flush=True)

    # Build the full sheet content as one contiguous write to A1, with blank
    # spacer rows between sections.
    blank = [[""]]
    content = []
    content += section_title("ROBINHOOD ADJUSTING — FIRM SETUP")
    content += [["Prepared by Smith, 2026-05-26"]]
    content += blank
    content += section_title("1. ONE-TIME + RECURRING COSTS")
    content += ROWS_COSTS_HEADER + ROWS_COSTS
    content += blank
    content += section_title("2. TOTALS")
    content += ROWS_TOTALS_HEADER + ROWS_TOTALS
    content += blank
    content += section_title("3. TIMELINE")
    content += ROWS_TIMELINE_HEADER + ROWS_TIMELINE
    content += blank
    content += section_title("4. RISKS / UNKNOWNS")
    content += ROWS_RISKS_HEADER + ROWS_RISKS
    content += blank
    content += section_title("5. NEXT IMMEDIATE ACTIONS")
    content += ROWS_ACTIONS_HEADER + ROWS_ACTIONS

    print(f"writing {len(content)} rows…", flush=True)
    write_values(sid, "A1", content)

    # Compute row indices for formatting (0-based).
    # title=row 0 (TITLE), subtitle row 1, blank row 2.
    # Section 1 header at row 3, costs header row 4 + 9 cost rows = rows 4..14
    # We'll compute by walking the same structure.
    fmts = []
    sheet_id = 0  # first/default sheet

    row = 0
    # title block
    fmts.append(fmt_bold(sheet_id, row, row + 1, 0, 6, bg=(0.12, 0.12, 0.14), font_size=14))
    # text color for title: needs a separate request — we'll just rely on bold + bg, then color cell text white
    fmts.append({
        "repeatCell": {
            "range": {"sheetId": sheet_id, "startRowIndex": row, "endRowIndex": row + 1, "startColumnIndex": 0, "endColumnIndex": 6},
            "cell": {"userEnteredFormat": {"textFormat": {"foregroundColor": {"red": 1, "green": 1, "blue": 1}}}},
            "fields": "userEnteredFormat.textFormat.foregroundColor",
        }
    })
    row += 1  # subtitle row
    row += 1  # subtitle done
    row += 1  # blank
    # Section 1 title
    fmts.append(fmt_bold(sheet_id, row, row + 1, 0, 5, bg=(0.85, 0.92, 1.0)))
    sec1_title_row = row
    row += 1
    sec1_header_row = row
    fmts.append(fmt_bold(sheet_id, row, row + 1, 0, 5, bg=(0.93, 0.93, 0.93)))
    row += 1
    sec1_data_start = row
    row += len(ROWS_COSTS)
    sec1_data_end = row
    # currency on cols B+C of costs
    fmts.append(fmt_currency(sheet_id, sec1_data_start, sec1_data_end, 1, 3))

    row += 1  # blank
    fmts.append(fmt_bold(sheet_id, row, row + 1, 0, 3, bg=(0.85, 0.92, 1.0)))
    row += 1
    fmts.append(fmt_bold(sheet_id, row, row + 1, 0, 3, bg=(0.93, 0.93, 0.93)))
    row += 1
    sec2_data_start = row
    row += len(ROWS_TOTALS)
    sec2_data_end = row
    fmts.append(fmt_currency(sheet_id, sec2_data_start, sec2_data_end, 1, 3))

    row += 1  # blank
    fmts.append(fmt_bold(sheet_id, row, row + 1, 0, 5, bg=(0.85, 0.92, 1.0)))
    row += 1
    fmts.append(fmt_bold(sheet_id, row, row + 1, 0, 5, bg=(0.93, 0.93, 0.93)))
    row += 1
    row += len(ROWS_TIMELINE)

    row += 1  # blank
    fmts.append(fmt_bold(sheet_id, row, row + 1, 0, 3, bg=(0.85, 0.92, 1.0)))
    row += 1
    fmts.append(fmt_bold(sheet_id, row, row + 1, 0, 3, bg=(0.93, 0.93, 0.93)))
    row += 1
    row += len(ROWS_RISKS)

    row += 1  # blank
    fmts.append(fmt_bold(sheet_id, row, row + 1, 0, 4, bg=(0.85, 0.92, 1.0)))
    row += 1
    fmts.append(fmt_bold(sheet_id, row, row + 1, 0, 4, bg=(0.93, 0.93, 0.93)))
    row += 1
    row += len(ROWS_ACTIONS)

    # auto-resize all columns
    fmts.append(fmt_auto_resize(sheet_id, 0, 6))

    print(f"applying {len(fmts)} format requests…", flush=True)
    batch_format(sid, fmts)

    print(f"DONE: {url}", flush=True)
    # open in Chrome
    try:
        subprocess.run(["open", "-a", "Google Chrome", url], check=False)
    except Exception as e:
        print(f"(open failed: {e})", flush=True)


if __name__ == "__main__":
    main()
