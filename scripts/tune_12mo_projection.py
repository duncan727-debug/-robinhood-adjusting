#!/usr/bin/env python3
"""Adjust 12-Month Projection: ads → $350, lunches note 5→4 lunches/mo."""
from google_sheets_helper import write_values

SHEET_ID = "14VDWJwsAMRpN0kV3RPGpoV085RJIPNPEqV-Gpw4V8kg"
TAB = "12-Month Projection"

# Meta Ads row 22: amounts → 350/mo, total = 4200, note updated
write_values(SHEET_ID, f"'{TAB}'!C22:P22",
             [[350]*12 + [4200, "$350/mo target, launch 2026-06-01"]])

# Lunches row 30: keep $200/mo but change note 5→4 lunches
write_values(SHEET_ID, f"'{TAB}'!P30",
             [["~4 lunches/mo × $50 avg"]])

# Recompute monthly totals
ops_m = [119,119,119,119,119,144,144,144,144,144,144,159]
ins_m = [2100,0,0,0,0,0,0,0,0,0,0,0]
mkt_m = [550]*12   # 350 ads + 150/100 print + 50 networking + 0/50 swag
mkt_m[0] = 550     # M1: 350+150+50+0 = 550
fld_m = [455]*12   # 135+200+80+40
monthly = [ops_m[i]+ins_m[i]+mkt_m[i]+fld_m[i] for i in range(12)]
total12 = sum(monthly)
avg = round(total12/12)

write_values(SHEET_ID, f"'{TAB}'!C35:O35", [monthly + [total12]])
write_values(SHEET_ID, f"'{TAB}'!O36", [[avg]])

print(f"DONE — ads $350/mo, lunches note 5→4/mo")
print(f"  New 12-mo total: ${total12:,}  |  Avg monthly: ${avg:,}")
