#!/usr/bin/env python3
"""Add a '12-Month Projection' tab to the firm-setup spreadsheet.
Period: Jun 2026 – May 2027. Month 1 = Jun 2026 (firm operational + ad launch)."""
import json
import subprocess

from google_sheets_helper import (
    _access_token, _api, write_values, batch_format,
    fmt_bold, fmt_currency, fmt_auto_resize,
)

SHEET_ID = "14VDWJwsAMRpN0kV3RPGpoV085RJIPNPEqV-Gpw4V8kg"
TAB = "12-Month Projection"

MONTHS = ["Jun '26","Jul '26","Aug '26","Sep '26","Oct '26","Nov '26",
          "Dec '26","Jan '27","Feb '27","Mar '27","Apr '27","May '27"]

def row(cat, item, vals, notes=""):
    assert len(vals) == 12
    return [cat, item] + vals + [sum(vals), notes]

# ---- Operations (recurring SaaS) ------------------------------------------
ops = []
ops.append(row("Ops", "Netlify Pro",       [19]*12, "Confirmed"))
ops.append(row("Ops", "Claude Max 5x",     [100]*12, "Confirmed"))
ops.append(row("Ops", "Namecheap domain",  [0,0,0,0,0,0,0,0,0,0,0,15], "Annual renewal"))
# HubSpot Starter ramp at month 6 (Nov 2026) — when contact count + email seq need it
ops.append(row("Ops", "HubSpot (Free → Starter $15/mo at M6)",
               [0,0,0,0,0,15,15,15,15,15,15,15], "Upgrade trigger: >1k contacts or email automation"))
# Calendly Standard ramp at month 6
ops.append(row("Ops", "Calendly (Free → Standard $10/mo at M6)",
               [0,0,0,0,0,10,10,10,10,10,10,10], "Upgrade trigger: custom branding / multi-event"))

# ---- Insurance & Compliance (firm setup recurring) -----------------------
# Bond + E&O + GL bind in Jun (M1); annual policies
ins = []
ins.append(row("Insurance", "Surety bond ($50K) — annual premium",
               [625,0,0,0,0,0,0,0,0,0,0,0], "Mid of $500-750 range; renews M13"))
ins.append(row("Insurance", "E&O ($1M/$1M) — annual premium",
               [750,0,0,0,0,0,0,0,0,0,0,0], "Mid of $500-1000 range"))
ins.append(row("Insurance", "General Liability — annual premium",
               [600,0,0,0,0,0,0,0,0,0,0,0], "Mid of $400-800 range"))
ins.append(row("Compliance", "FL LLC formation (Sunbiz)",
               [125,0,0,0,0,0,0,0,0,0,0,0], "One-time"))
ins.append(row("Compliance", "Business bank account fees",
               [0]*12, "Free biz checking assumed"))

# ---- Marketing ----------------------------------------------------------
mkt = []
mkt.append(row("Marketing", "Meta Ads (FB/IG) — local",
               [500]*12, "$500/mo target, launch 2026-06-01"))
mkt.append(row("Marketing", "Print materials / cards / signage",
               [150,100,100,100,100,100,100,100,100,100,100,100], "Heavier M1 for initial print run"))
mkt.append(row("Marketing", "Networking dues + event fees",
               [50,50,50,50,50,50,50,50,50,50,50,50], "Chamber/BNI/mixer fees; est. 4-6 events/mo"))
mkt.append(row("Marketing", "Branded swag / leave-behinds",
               [0,50,50,50,50,50,50,50,50,50,50,50], "Magnets, branded notepads for client visits"))

# ---- Field / Travel / Entertainment -------------------------------------
fld = []
fld.append(row("Field", "Mileage — free inspections",
               [135]*12, "~10 inspections/mo × 20mi RT × $0.67/mi IRS 2026"))
fld.append(row("Field", "Lunches — service providers + RE pros",
               [250]*12, "~5 lunches/mo × $50 avg"))
fld.append(row("Field", "Coffee meetings / quick meetups",
               [80]*12, "~8/mo × $10"))
fld.append(row("Field", "Parking / tolls",
               [40]*12, "Conservative estimate"))

# ---- Build the full content block ---------------------------------------
HEADER = ["Category", "Item"] + MONTHS + ["12mo Total", "Notes"]

content = []
content.append(["ROBINHOOD ADJUSTING — 12-MONTH OPERATING PROJECTION"])
content.append([f"Period: Jun 2026 – May 2027 (Month 1 = firm-operational + ad-launch month). All figures = estimates unless noted Confirmed."])
content.append([""])
content.append(["1. OPERATIONS (SaaS / Recurring)"])
content.append(HEADER)
content += ops
content.append([""])
content.append(["2. INSURANCE & COMPLIANCE"])
content.append(HEADER)
content += ins
content.append([""])
content.append(["3. MARKETING & ADVERTISING"])
content.append(HEADER)
content += mkt
content.append([""])
content.append(["4. FIELD / TRAVEL / ENTERTAINMENT"])
content.append(HEADER)
content += fld
content.append([""])

# ---- Monthly totals row -------------------------------------------------
all_data = ops + ins + mkt + fld
monthly_totals = [0]*12
for r in all_data:
    for i in range(12):
        monthly_totals[i] += r[2+i]
total_12mo = sum(monthly_totals)

content.append(["5. TOTALS"])
content.append(["", "MONTHLY TOTAL"] + monthly_totals + [total_12mo, ""])
# 3-month rolling avg
avg = total_12mo / 12
content.append(["", "Avg monthly burn", "", "", "", "", "", "", "", "", "", "", "", "", round(avg), "12-mo average"])

# ---- Create tab + write -------------------------------------------------
print(f"adding tab '{TAB}'…", flush=True)
token = _access_token()
url = f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}:batchUpdate"
res = _api("POST", url, token, data=json.dumps({"requests":[{"addSheet":{"properties":{"title":TAB}}}]}))
sheet_id = res["replies"][0]["addSheet"]["properties"]["sheetId"]
print(f"  sheetId={sheet_id}", flush=True)

a1 = f"'{TAB}'!A1"
print(f"writing {len(content)} rows…", flush=True)
write_values(SHEET_ID, a1, content)

# ---- Formatting ---------------------------------------------------------
ncols = 2 + 12 + 2  # 16
fmts = []
# title
fmts.append(fmt_bold(sheet_id, 0, 1, 0, ncols, bg=(0.12,0.12,0.14), font_size=14))
fmts.append({"repeatCell": {
    "range": {"sheetId": sheet_id, "startRowIndex": 0, "endRowIndex": 1, "startColumnIndex": 0, "endColumnIndex": ncols},
    "cell": {"userEnteredFormat": {"textFormat": {"foregroundColor": {"red":1,"green":1,"blue":1}}}},
    "fields": "userEnteredFormat.textFormat.foregroundColor",
}})

# Walk content to find section title + header rows
sec_title_color = (0.85, 0.92, 1.0)
header_color = (0.93, 0.93, 0.93)
total_color = (1.0, 0.93, 0.7)

# row indices (0-based) of section titles + their headers + their data ranges
# 0: title, 1: subtitle, 2: blank, 3: "1. OPS", 4: header, 5-9: ops (5 rows)
# 10: blank, 11: "2. INS", 12: header, 13-17: ins (5 rows)
# 18: blank, 19: "3. MKT", 20: header, 21-24: mkt (4 rows)
# 25: blank, 26: "4. FLD", 27: header, 28-31: fld (4 rows)
# 32: blank, 33: "5. TOTALS", 34: monthly total, 35: avg row
sections = [
    (3, 4, 5, 5+len(ops)),
    (3+1+len(ops)+1+1, 3+1+len(ops)+1+1+1, 3+1+len(ops)+1+1+2, 3+1+len(ops)+1+1+2+len(ins)),
]
# easier: compute on the fly
def offsets():
    r = 0
    r += 1  # title
    r += 1  # subtitle
    r += 1  # blank
    out = []
    for data in (ops, ins, mkt, fld):
        sec = r; r += 1
        hdr = r; r += 1
        ds = r; r += len(data)
        de = r
        out.append((sec, hdr, ds, de))
        r += 1  # blank
    return out, r

ranges, r = offsets()
totals_section = r        # "5. TOTALS"
totals_row = r + 1
avg_row = r + 2

for sec, hdr, ds, de in ranges:
    fmts.append(fmt_bold(sheet_id, sec, sec+1, 0, ncols, bg=sec_title_color))
    fmts.append(fmt_bold(sheet_id, hdr, hdr+1, 0, ncols, bg=header_color))
    # currency on months + total
    fmts.append({
        "repeatCell": {
            "range": {"sheetId": sheet_id, "startRowIndex": ds, "endRowIndex": de, "startColumnIndex": 2, "endColumnIndex": 15},
            "cell": {"userEnteredFormat": {"numberFormat": {"type":"CURRENCY","pattern":"$#,##0"}}},
            "fields": "userEnteredFormat.numberFormat",
        }
    })

# totals
fmts.append(fmt_bold(sheet_id, totals_section, totals_section+1, 0, ncols, bg=sec_title_color))
fmts.append(fmt_bold(sheet_id, totals_row, totals_row+1, 0, ncols, bg=total_color))
fmts.append({
    "repeatCell": {
        "range": {"sheetId": sheet_id, "startRowIndex": totals_row, "endRowIndex": avg_row+1, "startColumnIndex": 2, "endColumnIndex": 15},
        "cell": {"userEnteredFormat": {"numberFormat": {"type":"CURRENCY","pattern":"$#,##0"}}},
        "fields": "userEnteredFormat.numberFormat",
    }
})

# freeze first 2 cols + header rows
fmts.append({
    "updateSheetProperties": {
        "properties": {"sheetId": sheet_id, "gridProperties": {"frozenColumnCount": 2, "frozenRowCount": 1}},
        "fields": "gridProperties.frozenColumnCount,gridProperties.frozenRowCount",
    }
})

fmts.append(fmt_auto_resize(sheet_id, 0, ncols))

print(f"applying {len(fmts)} format requests…", flush=True)
batch_format(SHEET_ID, fmts)

opened = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit#gid={sheet_id}"
print(f"DONE: {opened}", flush=True)
print(f"12-mo total: ${total_12mo:,}  |  Avg monthly: ${round(avg):,}", flush=True)
subprocess.run(["open", "-a", "Google Chrome", opened], check=False)
