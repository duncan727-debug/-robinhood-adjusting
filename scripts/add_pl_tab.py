#!/usr/bin/env python3
"""Add '12-Month P&L' tab combining revenue (3 scenarios) with operating costs
and one-time start-up costs. All cells are live cross-tab references / formulas
so updates propagate automatically.

Sources referenced:
  - '12-Month Revenue Projection': totals row 22 (Realistic), 32 (Pess), 42 (Opt)
      months in cols B..M, total col N
  - '12-Month Projection' (costs): totals row 27, months C..N, total O
  - 'Start-up Costs': B18 = low, C18 = high; we use midpoint for one-time M1 hit
"""
import json
import subprocess

from google_sheets_helper import (
    _access_token, _api, write_values, batch_write_values, batch_format,
    fmt_bold, fmt_auto_resize,
)

SHEET_ID = "14VDWJwsAMRpN0kV3RPGpoV085RJIPNPEqV-Gpw4V8kg"
TAB = "12-Month P&L"
MONTHS = ["Jun '26","Jul '26","Aug '26","Sep '26","Oct '26","Nov '26",
          "Dec '26","Jan '27","Feb '27","Mar '27","Apr '27","May '27"]

# Source tab row numbers (1-indexed)
REV_PESS_ROW, REV_REAL_ROW, REV_OPT_ROW = 32, 22, 42
COST_TOT_ROW = 27   # in '12-Month Projection'

def main():
    tok = _access_token()

    # remove existing P&L tab if present (idempotent)
    import requests as _rq
    meta = _rq.get(f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}",
                   headers={"Authorization": f"Bearer {tok}"}).json()
    for s in meta.get("sheets", []):
        if s["properties"]["title"] == TAB:
            _api("POST", f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}:batchUpdate",
                 tok, data=json.dumps({"requests":[{"deleteSheet":{"sheetId":s["properties"]["sheetId"]}}]}))
            break

    res = _api("POST",
               f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}:batchUpdate",
               tok,
               data=json.dumps({"requests":[{"addSheet":{"properties":{"title":TAB}}}]}))
    sheet_id = res["replies"][0]["addSheet"]["properties"]["sheetId"]
    print(f"sheetId={sheet_id}", flush=True)

    # Helper: build a row of N cells: label + 12 placeholders + total placeholder
    blank = [""] * 14

    # ---------- Layout ----------
    # Cols: A=Label, B..M = 12 months, N = 12mo Total
    HDR = ["Scenario"] + MONTHS + ["12mo Total"]

    content = []
    content.append(["ROBINHOOD ADJUSTING — 12-MONTH P&L"])
    content.append(["Combines Revenue scenarios with Operating Costs and Start-Up Costs. All values are live formulas referencing the other tabs."])
    content.append([""])
    content.append(["1. REVENUE BY SCENARIO"])
    content.append(HDR)
    content.append(["Pessimistic"] + blank[:13])   # row 6, formulas filled below
    content.append(["Realistic"]   + blank[:13])
    content.append(["Optimistic"]  + blank[:13])
    content.append([""])
    content.append(["2. OPERATING COSTS (same across scenarios)"])
    content.append(HDR)
    content.append(["Monthly opex"] + blank[:13])  # row 12
    content.append([""])
    content.append(["3. ONE-TIME START-UP COSTS (M1 only — bond, E&O, GL, LLC)"])
    content.append(HDR)
    content.append(["Start-up hit"] + blank[:13])  # row 16
    content.append([""])
    content.append(["4. NET P&L BY SCENARIO (= Revenue − Opex − Start-Up)"])
    content.append(HDR)
    content.append(["Pessimistic NET"] + blank[:13])  # row 20
    content.append(["Realistic NET"]   + blank[:13])
    content.append(["Optimistic NET"]  + blank[:13])
    content.append([""])
    content.append(["5. SUMMARY (12-month)"])
    content.append(["Scenario", "Revenue", "Operating Costs", "Start-Up Costs", "NET P&L", "Net Margin %"])
    content.append(["Pessimistic"] + [""]*5)   # row 26
    content.append(["Realistic"]   + [""]*5)
    content.append(["Optimistic"]  + [""]*5)

    write_values(SHEET_ID, f"'{TAB}'!A1", content)

    # ---------- Build formulas ----------
    REV_TAB = "'12-Month Revenue Projection'"
    COST_TAB = "'12-Month Projection'"
    START_TAB = "'Start-up Costs'"

    # rev tab months are cols B..M (12 months); use offset i = 0..11
    # P&L tab months are cols B..M as well — same column letters
    cols = ["B","C","D","E","F","G","H","I","J","K","L","M"]

    formulas = []

    # ---- Section 1: Revenue rows 6,7,8 ----
    for tgt_row, src_row in [(6, REV_PESS_ROW), (7, REV_REAL_ROW), (8, REV_OPT_ROW)]:
        for c in cols:
            formulas.append((f"'{TAB}'!{c}{tgt_row}", f"={REV_TAB}!{c}{src_row}"))
        formulas.append((f"'{TAB}'!N{tgt_row}", f"=SUM(B{tgt_row}:M{tgt_row})"))

    # ---- Section 2: Opex row 12 ----
    # Cost tab months in cols C..N; map: P&L B → cost C, P&L M → cost N
    cost_cols = ["C","D","E","F","G","H","I","J","K","L","M","N"]
    for i, c in enumerate(cols):
        formulas.append((f"'{TAB}'!{c}12", f"={COST_TAB}!{cost_cols[i]}{COST_TOT_ROW}"))
    formulas.append((f"'{TAB}'!N12", f"=SUM(B12:M12)"))

    # ---- Section 3: Start-Up row 16 (M1 only) ----
    # midpoint of low/high
    formulas.append((f"'{TAB}'!B16", f"=({START_TAB}!B18 + {START_TAB}!C18)/2"))
    for c in cols[1:]:  # C..M
        formulas.append((f"'{TAB}'!{c}16", "=0"))
    formulas.append((f"'{TAB}'!N16", "=SUM(B16:M16)"))

    # ---- Section 4: Net rows 20,21,22 = Rev - Opex - StartUp ----
    for tgt_row, rev_row in [(20, 6), (21, 7), (22, 8)]:
        for c in cols:
            formulas.append((f"'{TAB}'!{c}{tgt_row}",
                             f"={c}{rev_row}-{c}$12-{c}$16"))
        formulas.append((f"'{TAB}'!N{tgt_row}", f"=SUM(B{tgt_row}:M{tgt_row})"))

    # ---- Section 5: Summary rows 26,27,28 ----
    for tgt_row, rev_row, net_row in [(26, 6, 20), (27, 7, 21), (28, 8, 22)]:
        formulas.append((f"'{TAB}'!B{tgt_row}", f"=N{rev_row}"))     # revenue
        formulas.append((f"'{TAB}'!C{tgt_row}", "=N12"))             # opex
        formulas.append((f"'{TAB}'!D{tgt_row}", "=N16"))             # start-up
        formulas.append((f"'{TAB}'!E{tgt_row}", f"=N{net_row}"))     # net
        formulas.append((f"'{TAB}'!F{tgt_row}", f"=IFERROR(E{tgt_row}/B{tgt_row},0)"))  # margin

    batch_write_values(SHEET_ID, [(rng, [[fml]]) for rng, fml in formulas])

    # ---------- Formatting ----------
    ncols = 14  # A..N
    fmts = []
    # Title
    fmts.append(fmt_bold(sheet_id, 0, 1, 0, ncols, bg=(0.10,0.20,0.30), font_size=14))
    fmts.append({"repeatCell":{
        "range":{"sheetId":sheet_id,"startRowIndex":0,"endRowIndex":1,"startColumnIndex":0,"endColumnIndex":ncols},
        "cell":{"userEnteredFormat":{"textFormat":{"foregroundColor":{"red":1,"green":1,"blue":1}}}},
        "fields":"userEnteredFormat.textFormat.foregroundColor",
    }})

    sec_color = (0.85, 0.92, 1.0)
    hdr_color = (0.93, 0.93, 0.93)
    total_color = (1.0, 0.93, 0.7)
    net_color   = (0.82, 0.92, 0.82)   # light green for net rows

    # Section markers (0-idx): 3 = "1. REVENUE", 9 = "2. OPEX", 13 = "3. START-UP",
    #   17 = "4. NET P&L", 23 = "5. SUMMARY"
    # Headers (0-idx): 4, 10, 14, 18, 24
    # Data ranges:
    #   Rev rows 5-7 (0-idx)
    #   Opex row 11
    #   Start-up row 15
    #   Net rows 19-21
    #   Summary rows 25-27
    for sec, hdr in [(3,4), (9,10), (13,14), (17,18), (23,24)]:
        fmts.append(fmt_bold(sheet_id, sec, sec+1, 0, ncols, bg=sec_color))
        fmts.append(fmt_bold(sheet_id, hdr, hdr+1, 0, ncols, bg=hdr_color))

    # Net rows green
    fmts.append(fmt_bold(sheet_id, 19, 22, 0, ncols, bg=net_color))
    # Summary highlight
    fmts.append(fmt_bold(sheet_id, 25, 28, 0, ncols, bg=total_color))

    # Currency on data + summary cells (B..N range for the various rows)
    currency_ranges = [(5, 8), (11, 12), (15, 16), (19, 22)]
    for s, e in currency_ranges:
        fmts.append({"repeatCell":{
            "range":{"sheetId":sheet_id,"startRowIndex":s,"endRowIndex":e,"startColumnIndex":1,"endColumnIndex":14},
            "cell":{"userEnteredFormat":{"numberFormat":{"type":"CURRENCY","pattern":"$#,##0"}}},
            "fields":"userEnteredFormat.numberFormat",
        }})
    # Summary B..E currency
    fmts.append({"repeatCell":{
        "range":{"sheetId":sheet_id,"startRowIndex":25,"endRowIndex":28,"startColumnIndex":1,"endColumnIndex":5},
        "cell":{"userEnteredFormat":{"numberFormat":{"type":"CURRENCY","pattern":"$#,##0"}}},
        "fields":"userEnteredFormat.numberFormat",
    }})
    # Summary F = percent
    fmts.append({"repeatCell":{
        "range":{"sheetId":sheet_id,"startRowIndex":25,"endRowIndex":28,"startColumnIndex":5,"endColumnIndex":6},
        "cell":{"userEnteredFormat":{"numberFormat":{"type":"PERCENT","pattern":"0%"}}},
        "fields":"userEnteredFormat.numberFormat",
    }})

    # Freeze
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
