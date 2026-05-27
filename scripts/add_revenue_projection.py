#!/usr/bin/env python3
"""Add '12-Month Revenue Projection' tab — pessimistic / realistic / optimistic
scenarios broken down by lead source. All totals are live formulas.

Assumptions baked in:
- Avg PA fee = 10% of settlement (FL standard non-emergency cap is 20%; market is 10%)
- Avg residential settlement: $25K realistic ($15K pessimistic, $35K optimistic)
- Conversion (lead → signed claim): 25% real / 15% pess / 35% opt
- Settlement lag (sign → revenue): ~2 months avg (so M1-M2 = $0)
- Ad launch + firm operational = M1 (Jun 2026)
"""
import json
import subprocess

from google_sheets_helper import (
    _access_token, _api, write_values, batch_write_values, batch_format,
    fmt_bold, fmt_auto_resize,
)

SHEET_ID = "14VDWJwsAMRpN0kV3RPGpoV085RJIPNPEqV-Gpw4V8kg"
TAB = "12-Month Revenue Projection"

MONTHS = ["Jun '26","Jul '26","Aug '26","Sep '26","Oct '26","Nov '26",
          "Dec '26","Jan '27","Feb '27","Mar '27","Apr '27","May '27"]

# ------------------- Realistic ----------------------------------------------
real = {
    "Meta Ads (paid)":              [0,0, 800,1000,1500,1800,2200,2700,3100,3500,3600,3500],
    "Newsletter / website inbound": [0,0, 300, 400, 700, 800,1100,1300,1500,1700,1700,1800],
    "Real-estate referrals":        [0,0, 400, 500, 900,1000,1300,1500,1800,2100,2200,2200],
    "Service-provider referrals":   [0,0, 300, 400, 700, 800,1000,1200,1400,1600,1600,1600],
    "Networking groups (Chamber/BNI)":[0,0, 300, 300, 600, 700, 900,1100,1300,1500,1500,1500],
    "Direct / field-met":           [0,0, 400, 400, 600, 900,1000,1200,1400,1600,1900,2400],
}
# ------------------- Pessimistic --------------------------------------------
pess = {
    "Meta Ads (paid)":              [0,0, 150, 200, 300, 350, 500, 600, 700, 800, 900,1000],
    "Newsletter / website inbound": [0,0, 100, 150, 200, 250, 350, 400, 500, 550, 600, 650],
    "Real-estate referrals":        [0,0, 250, 400, 500, 650, 900,1000,1300,1400,1500,1700],
    "Service-provider referrals":   [0,0, 200, 300, 400, 500, 700, 800,1000,1100,1200,1300],
    "Networking groups (Chamber/BNI)":[0,0, 150, 250, 300, 400, 550, 600, 750, 850, 900, 950],
    "Direct / field-met":           [0,0, 150, 200, 300, 350, 500, 600, 750, 800, 900, 900],
}
# ------------------- Optimistic ---------------------------------------------
opt = {
    "Meta Ads (paid)":              [0,0, 2000,3000,4000,4500,5500,6500,7000,8500,9000,9500],
    "Newsletter / website inbound": [0,0,  700,1000,1500,1800,2200,2500,3000,3800,4000,5000],
    "Real-estate referrals":        [0,0, 1000,1500,2000,2500,3000,3500,4000,5000,5500,6000],
    "Service-provider referrals":   [0,0,  600, 900,1200,1500,1800,2100,2400,3000,3300,3500],
    "Networking groups (Chamber/BNI)":[0,0,400, 600, 800,1000,1200,1400,1600,2000,2200,2500],
    "Direct / field-met":           [0,0,  300, 500, 500,1200,1300,1500,2000,2700,3500,3500],
}

# Common header row for scenario blocks
HDR = ["Lead source"] + MONTHS + ["12mo Total", "Notes"]

ASSUMPTIONS = [
    ["PA fee % of settlement",          "10%",   "10%",   "10%",   "FL market standard"],
    ["Avg claim settlement",            "$15K",  "$25K",  "$35K",  "Residential mix"],
    ["Avg fee per signed claim",        "$1,500","$2,500","$3,500","= settlement × 10%"],
    ["Lead → signed conversion",        "15%",   "25%",   "35%",   "Warm (referral) converts higher than cold (ads)"],
    ["Settlement lag (sign → revenue)", "~2 mo", "~2 mo", "~2 mo", "M1-M2 revenue = $0 by design"],
    ["Ad spend (driving Meta leads)",   "$450",  "$450",  "$450",  "Per /month; see Operating Costs tab"],
    ["12-mo claims signed (approx)",    "~25",   "~32",   "~50",   "Implied from monthly $ ÷ avg fee"],
]

def scenario_section(num, label, data):
    rows = []
    rows.append([f"{num}. {label}"])
    rows.append(HDR)
    for src, vals in data.items():
        rows.append([src] + vals + [None, ""])  # 12mo total placeholder (formula later)
    rows.append(["TOTAL"] + [None]*12 + [None, ""])
    return rows

def main():
    print(f"adding tab '{TAB}'…", flush=True)
    tok = _access_token()
    # If tab already exists from a prior partial run, delete it first
    import requests as _rq
    meta = _rq.get(f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}",
                   headers={"Authorization": f"Bearer {tok}"}).json()
    for s in meta.get("sheets", []):
        if s["properties"]["title"] == TAB:
            _api("POST",
                 f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}:batchUpdate",
                 tok,
                 data=json.dumps({"requests":[{"deleteSheet":{"sheetId":s["properties"]["sheetId"]}}]}))
            print(f"  (removed existing partial tab)", flush=True)
            break
    res = _api("POST",
               f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}:batchUpdate",
               tok,
               data=json.dumps({"requests":[{"addSheet":{"properties":{"title":TAB}}}]}))
    sheet_id = res["replies"][0]["addSheet"]["properties"]["sheetId"]
    print(f"  sheetId={sheet_id}", flush=True)

    content = []
    content.append(["ROBINHOOD ADJUSTING — 12-MONTH REVENUE PROJECTION"])
    content.append(["Period: Jun 2026 – May 2027 (M1 = firm-operational month). $ shown = PA fees received. Lead source = where the prospect originated."])
    content.append([""])

    # 1. Assumptions
    content.append(["1. KEY ASSUMPTIONS"])
    content.append(["Parameter", "Pessimistic", "Realistic", "Optimistic", "Notes"])
    content += ASSUMPTIONS
    content.append([""])

    # 2-4. Scenarios
    content += scenario_section(2, "REALISTIC SCENARIO", real)
    content.append([""])
    content += scenario_section(3, "PESSIMISTIC SCENARIO", pess)
    content.append([""])
    content += scenario_section(4, "OPTIMISTIC SCENARIO", opt)
    content.append([""])

    # 5. Summary
    content.append(["5. SUMMARY"])
    content.append(["Scenario", "12mo Revenue", "Avg Monthly", "vs $150K goal", "Notes"])
    content.append(["Pessimistic", None, None, None, "Slow ramp, smaller claims, ads underperform"])
    content.append(["Realistic",    None, None, None, "Industry-baseline growth curve"])
    content.append(["Optimistic",   None, None, None, "Larger claims + paid ads convert hot"])

    write_values(SHEET_ID, f"'{TAB}'!A1", content)

    # ----- Add formulas now that rows are placed -----
    # Layout (1-indexed):
    #  Row 1: title
    #  Row 2: subtitle
    #  Row 3: blank
    #  Row 4: "1. KEY ASSUMPTIONS"
    #  Row 5: header
    #  Rows 6-12: 7 assumption rows
    #  Row 13: blank
    #  Row 14: "2. REALISTIC SCENARIO"
    #  Row 15: scenario header
    #  Rows 16-21: 6 source rows
    #  Row 22: TOTAL row
    #  Row 23: blank
    #  Row 24: "3. PESSIMISTIC SCENARIO"
    #  Row 25: header
    #  Rows 26-31: 6 sources
    #  Row 32: TOTAL
    #  Row 33: blank
    #  Row 34: "4. OPTIMISTIC SCENARIO"
    #  Row 35: header
    #  Rows 36-41: 6 sources
    #  Row 42: TOTAL
    #  Row 43: blank
    #  Row 44: "5. SUMMARY"
    #  Row 45: header
    #  Row 46-48: scenarios

    # Per-source 12mo totals in column N (col 14)
    # Wait — header has: Lead source(A) + 12 months(B-M) + 12mo Total(N) + Notes(O)
    # So months are B..M, total is N, notes is O.
    month_cols = ["B","C","D","E","F","G","H","I","J","K","L","M"]
    formulas = []

    for scenario_total_row, source_rows in [(22, range(16,22)),
                                            (32, range(26,32)),
                                            (42, range(36,42))]:
        # Per-source 12mo total in column N
        for r in source_rows:
            formulas.append((f"'{TAB}'!N{r}", f"=SUM(B{r}:M{r})"))
        # Total row: per-month formula + 12mo total
        first, last = min(source_rows), max(source_rows)
        for c in month_cols:
            formulas.append((f"'{TAB}'!{c}{scenario_total_row}", f"=SUM({c}{first}:{c}{last})"))
        formulas.append((f"'{TAB}'!N{scenario_total_row}", f"=SUM(B{scenario_total_row}:M{scenario_total_row})"))

    # Summary block: pull from scenario totals
    # Row 46 = Pessimistic (totals row 32)
    # Row 47 = Realistic (totals row 22)
    # Row 48 = Optimistic (totals row 42)
    formulas.append((f"'{TAB}'!B46", "=N32"))
    formulas.append((f"'{TAB}'!C46", "=B46/12"))
    formulas.append((f"'{TAB}'!D46", "=B46/150000"))
    formulas.append((f"'{TAB}'!B47", "=N22"))
    formulas.append((f"'{TAB}'!C47", "=B47/12"))
    formulas.append((f"'{TAB}'!D47", "=B47/150000"))
    formulas.append((f"'{TAB}'!B48", "=N42"))
    formulas.append((f"'{TAB}'!C48", "=B48/12"))
    formulas.append((f"'{TAB}'!D48", "=B48/150000"))

    # Push all formulas in a single batched call
    batch_write_values(SHEET_ID, [(rng, [[fml]]) for rng, fml in formulas])

    # ----- Formatting -----
    ncols = 16  # A..P
    fmts = []
    # Title
    fmts.append(fmt_bold(sheet_id, 0, 1, 0, ncols, bg=(0.10,0.30,0.15), font_size=14))
    fmts.append({"repeatCell":{
        "range":{"sheetId":sheet_id,"startRowIndex":0,"endRowIndex":1,"startColumnIndex":0,"endColumnIndex":ncols},
        "cell":{"userEnteredFormat":{"textFormat":{"foregroundColor":{"red":1,"green":1,"blue":1}}}},
        "fields":"userEnteredFormat.textFormat.foregroundColor",
    }})

    sec_color = (0.85, 0.92, 1.0)
    hdr_color = (0.93, 0.93, 0.93)
    total_color = (1.0, 0.93, 0.7)

    # Assumptions block: section title row 3 (0-idx), header row 4
    fmts.append(fmt_bold(sheet_id, 3, 4, 0, ncols, bg=sec_color))
    fmts.append(fmt_bold(sheet_id, 4, 5, 0, ncols, bg=hdr_color))

    # Scenario blocks: section title row, header, total row
    scenarios = [
        (13, 14, 15, 21),  # 0-idx: realistic — sec 13, hdr 14, data 15-20, total 21
        (23, 24, 25, 31),  # pessimistic — sec 23, hdr 24, data 25-30, total 31
        (33, 34, 35, 41),  # optimistic — sec 33, hdr 34, data 35-40, total 41
    ]
    for sec, hdr, ds, tot in scenarios:
        fmts.append(fmt_bold(sheet_id, sec, sec+1, 0, ncols, bg=sec_color))
        fmts.append(fmt_bold(sheet_id, hdr, hdr+1, 0, ncols, bg=hdr_color))
        fmts.append(fmt_bold(sheet_id, tot, tot+1, 0, ncols, bg=total_color))
        # Currency on data + total rows, cols B..N (1..13)
        fmts.append({"repeatCell":{
            "range":{"sheetId":sheet_id,"startRowIndex":ds,"endRowIndex":tot+1,"startColumnIndex":1,"endColumnIndex":14},
            "cell":{"userEnteredFormat":{"numberFormat":{"type":"CURRENCY","pattern":"$#,##0"}}},
            "fields":"userEnteredFormat.numberFormat",
        }})

    # Summary block (0-idx 43-47): section title, header, 3 rows
    fmts.append(fmt_bold(sheet_id, 43, 44, 0, ncols, bg=sec_color))
    fmts.append(fmt_bold(sheet_id, 44, 45, 0, ncols, bg=hdr_color))
    fmts.append(fmt_bold(sheet_id, 45, 48, 0, ncols, bg=total_color))
    # B and C as currency, D as percent
    fmts.append({"repeatCell":{
        "range":{"sheetId":sheet_id,"startRowIndex":45,"endRowIndex":48,"startColumnIndex":1,"endColumnIndex":3},
        "cell":{"userEnteredFormat":{"numberFormat":{"type":"CURRENCY","pattern":"$#,##0"}}},
        "fields":"userEnteredFormat.numberFormat",
    }})
    fmts.append({"repeatCell":{
        "range":{"sheetId":sheet_id,"startRowIndex":45,"endRowIndex":48,"startColumnIndex":3,"endColumnIndex":4},
        "cell":{"userEnteredFormat":{"numberFormat":{"type":"PERCENT","pattern":"0%"}}},
        "fields":"userEnteredFormat.numberFormat",
    }})

    # Freeze header
    fmts.append({"updateSheetProperties":{
        "properties":{"sheetId":sheet_id,"gridProperties":{"frozenColumnCount":1,"frozenRowCount":1}},
        "fields":"gridProperties.frozenColumnCount,gridProperties.frozenRowCount",
    }})

    fmts.append(fmt_auto_resize(sheet_id, 0, ncols))

    print(f"applying {len(fmts)} format requests…", flush=True)
    batch_format(SHEET_ID, fmts)

    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit#gid={sheet_id}"
    print(f"DONE: {url}", flush=True)
    subprocess.run(["open", "-a", "Google Chrome", url], check=False)

if __name__ == "__main__":
    main()
