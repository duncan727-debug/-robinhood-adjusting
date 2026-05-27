#!/usr/bin/env python3
"""Replace hardcoded totals with live formulas across all three tabs."""
from google_sheets_helper import write_values

SHEET_ID = "14VDWJwsAMRpN0kV3RPGpoV085RJIPNPEqV-Gpw4V8kg"

# ============================================================
# TAB 1: "Sheet1" (default) — Firm Setup (Costs & Timeline)
# ============================================================
# Layout:
#  Row 5: header [Component, Low, High, Frequency, Notes]
#  Rows 6-14: cost items (9 items)
#    6=LLC formation, 7=EIN, 8=DFS license (one-times)
#    9-14 = annual items (bond, E&O, GL, bank, domain, LLC annual report)
#  Row 17: header [Period, Low, High]
#  Row 18: First-Year Total (all-in)         → SUM(B6:B13) / SUM(C6:C13)
#         (excludes LLC Annual Report which is year-2+ only)
#  Row 19: Recurring Annual (year 2+)        → SUM(B9:B14) / SUM(C9:C14)
#  Row 20: Attorney consult — keep hardcoded contingent values
TAB1 = "Start-up Costs"
write_values(SHEET_ID, f"'{TAB1}'!B18:C18", [["=SUM(B6:B13)", "=SUM(C6:C13)"]])
write_values(SHEET_ID, f"'{TAB1}'!B19:C19", [["=SUM(B9:B14)", "=SUM(C9:C14)"]])

# ============================================================
# TAB 2: "Costs Already Incurred"
# ============================================================
TAB2 = "Costs Already Incurred"
#  Rows 10-17 = subscription items (Namecheap annual + 7 monthly items)
#    Row 10 Namecheap = ANNUAL → exclude from monthly recurring
#    Rows 11-17 = monthly items (Netlify, GitHub, Gmail, HubSpot, Calendly, Claude, Google Places)
#  Row 20: monthly recurring total
write_values(SHEET_ID, f"'{TAB2}'!B20", [["=SUM(B11:B17)"]])

#  Today marker:
#  Rows 25-28 = 4 paid items (Computer, Namecheap, Netlify, Claude)
#  Row 29 = TOTAL SPENT TO DATE
write_values(SHEET_ID, f"'{TAB2}'!B29", [["=SUM(B25:B28)"]])

# ============================================================
# TAB 3: "12-Month Projection"
# ============================================================
TAB3 = "12-Month Projection"
#  Data rows:
#    Ops:  6-10  (5 rows)
#    Ins:  14-18 (5 rows)
#    Mkt:  22-25 (4 rows)
#    Fld:  29-32 (4 rows)
#  Columns: C..N = 12 months, O = 12mo total, P = notes
#  Row 35: monthly totals; Row 36: avg

# Per-row 12mo totals (column O)
data_rows = list(range(6, 11)) + list(range(14, 19)) + list(range(22, 26)) + list(range(29, 33))
for r in data_rows:
    write_values(SHEET_ID, f"'{TAB3}'!O{r}", [[f"=SUM(C{r}:N{r})"]])

# Row 35: monthly totals per column = sum of all 4 category data ranges
# For each column letter C..N, write =SUM(C6:C10)+SUM(C14:C18)+SUM(C22:C25)+SUM(C29:C32)
month_cols = ["C","D","E","F","G","H","I","J","K","L","M","N"]
formulas_row35 = []
for c in month_cols:
    formulas_row35.append(f"=SUM({c}6:{c}10)+SUM({c}14:{c}18)+SUM({c}22:{c}25)+SUM({c}29:{c}32)")
# Plus O35 = total of monthly totals
formulas_row35.append("=SUM(C35:N35)")
write_values(SHEET_ID, f"'{TAB3}'!C35:O35", [formulas_row35])

# Row 36 avg
write_values(SHEET_ID, f"'{TAB3}'!O36", [["=O35/12"]])

print("DONE — all totals converted to live formulas across 3 tabs")
print("  Tab 1: B18:C18 (first-year), B19:C19 (recurring)")
print(f"  Tab 2: B20 (monthly subs), B29 (today total)")
print(f"  Tab 3: O6-O32 per-row totals, C35:O35 monthly totals, O36 avg")
