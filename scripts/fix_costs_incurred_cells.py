#!/usr/bin/env python3
"""Mark HubSpot + Calendly as Free tier confirmed."""
from google_sheets_helper import write_values

SHEET_ID = "14VDWJwsAMRpN0kV3RPGpoV085RJIPNPEqV-Gpw4V8kg"
TAB = "Costs Already Incurred"

# HubSpot row 14, Calendly row 15
write_values(SHEET_ID, f"'{TAB}'!B14:E14",
             [[0, "Monthly", "ACTIVE", "Free tier (confirmed 2026-05-26)"]])
write_values(SHEET_ID, f"'{TAB}'!B15:E15",
             [[0, "Monthly", "ACTIVE", "Free tier (confirmed 2026-05-26)"]])

# Clear the "Pending tier confirmation" line at row 21
write_values(SHEET_ID, f"'{TAB}'!A21:B21", [["", ""]])

print("DONE — HubSpot + Calendly marked Free tier confirmed")
