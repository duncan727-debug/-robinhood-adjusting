#!/usr/bin/env python3
"""Append a 'TODAY MARKER — total spent to date' section to the
Costs Already Incurred tab. As of 2026-05-26."""
import json
from google_sheets_helper import _access_token, _api, write_values, batch_format, fmt_bold

SHEET_ID = "14VDWJwsAMRpN0kV3RPGpoV085RJIPNPEqV-Gpw4V8kg"
TAB_GID = 310656859
TAB = "Costs Already Incurred"

# After the deleteDimension done earlier:
#  rows 19 = "4. MONTHLY SUBSCRIPTION TOTAL (current)"
#  row 20 = "Confirmed monthly recurring | $119/mo..."
#  row 21 = (cleared)
# We'll append starting row 23.

# Conservative ledger as of 2026-05-26:
# - Computer $500 (one-time, already paid)
# - Namecheap $15 (1 yr already paid on robinhoodadjusting.com)
# - Netlify Pro: account created 2026-04-25, upgrade detected 2026-05-06.
#     ~3 weeks active → 1 month billed = $19
# - Claude Max 5x: upgraded 2026-05-15 → 1 month billed = $100
# - HubSpot/Calendly/GitHub/Gmail/Google Places: $0 (free tier)

ROWS = [
    ["TODAY MARKER — TOTAL SPENT TO DATE (2026-05-26)", "", "", "", ""],
    ["Item", "Amount ($)", "Period covered", "Source", "Notes"],
    ["Computer (work laptop)",            500, "One-time",          "Out of pocket", "Paid"],
    ["Namecheap — robinhoodadjusting.com", 15, "1 yr",               "Card on file",  "Annual renewal already paid"],
    ["Netlify Pro",                        19, "~1 mo (upgraded 5/6)", "Card on file", "Pro tier active since 2026-05-06"],
    ["Claude Max 5x",                     100, "~1 mo (upgraded 5/15)", "Card on file", "Upgraded 2026-05-15"],
    ["TOTAL SPENT TO DATE",               634, "",                   "",              "Sum of confirmed paid items above"],
]

a1 = f"'{TAB}'!A23"
write_values(SHEET_ID, a1, ROWS)

# Format: title row, header row, total row
fmts = []
# Section title row 23 (0-indexed 22)
fmts.append(fmt_bold(TAB_GID, 22, 23, 0, 5, bg=(1.0, 0.85, 0.5)))   # amber/orange
# Header row 24 (0-indexed 23)
fmts.append(fmt_bold(TAB_GID, 23, 24, 0, 5, bg=(0.93, 0.93, 0.93)))
# Data rows 25-28 (0-indexed 24-28) currency on col B
fmts.append({
    "repeatCell": {
        "range": {"sheetId": TAB_GID, "startRowIndex": 24, "endRowIndex": 29, "startColumnIndex": 1, "endColumnIndex": 2},
        "cell": {"userEnteredFormat": {"numberFormat": {"type":"CURRENCY","pattern":"$#,##0"}}},
        "fields": "userEnteredFormat.numberFormat",
    }
})
# Total row 29 (0-indexed 28) — bold + amber
fmts.append(fmt_bold(TAB_GID, 28, 29, 0, 5, bg=(1.0, 0.93, 0.7)))

batch_format(SHEET_ID, fmts)
print("DONE — Today marker added; total spent to date = $634")
