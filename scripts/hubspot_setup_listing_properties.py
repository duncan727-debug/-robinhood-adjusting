#!/usr/bin/env python3
"""Create HubSpot contact custom properties for directory-listing qualifying-questions data.

Idempotent: if a property already exists, skip it. Run once after deploying the
listing-reply template. Run again any time the question set changes.
"""
import json
import sys
import urllib.request
import urllib.error
from pathlib import Path

WORKSPACE = Path("/Users/victoria/.openclaw/workspace")
SECRETS = WORKSPACE / "config" / ".secrets"


def get_token():
    for line in SECRETS.read_text().splitlines():
        if line.strip().startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.replace("export", "").strip()
        if k == "HUBSPOT_API_KEY":
            return v.strip().strip('"').strip("'")
    sys.exit("HUBSPOT_API_KEY missing")


TOKEN = get_token()


def hs(method, path, payload=None):
    url = f"https://api.hubapi.com{path}"
    data = json.dumps(payload).encode() if payload else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {TOKEN}")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read() or b"{}")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


GROUP_NAME = "contactinformation"

PROPERTIES = [
    {
        "name": "service_counties",
        "label": "Service Counties",
        "type": "enumeration",
        "fieldType": "checkbox",
        "description": "Counties where this provider actively takes jobs",
        "options": [
            {"label": "Palm Beach", "value": "palm_beach"},
            {"label": "Martin", "value": "martin"},
            {"label": "St. Lucie", "value": "st_lucie"},
            {"label": "Broward", "value": "broward"},
            {"label": "Miami-Dade", "value": "miami_dade"},
        ],
    },
    {
        "name": "primary_trade",
        "label": "Primary Trade",
        "type": "enumeration",
        "fieldType": "select",
        "description": "Primary directory category for this provider",
        "options": [
            {"label": "General Contractor", "value": "general_contractor"},
            {"label": "Roofing", "value": "roofing"},
            {"label": "HVAC", "value": "hvac"},
            {"label": "Plumbing", "value": "plumbing"},
            {"label": "Restoration", "value": "restoration"},
            {"label": "Property Management", "value": "property_management"},
            {"label": "Real Estate", "value": "real_estate"},
            {"label": "Other", "value": "other"},
        ],
    },
    {
        "name": "secondary_trades",
        "label": "Secondary Trades (Cross-Listed)",
        "type": "enumeration",
        "fieldType": "checkbox",
        "description": "Additional trades this provider is licensed/qualified for",
        "options": [
            {"label": "General Contractor", "value": "general_contractor"},
            {"label": "Roofing", "value": "roofing"},
            {"label": "HVAC", "value": "hvac"},
            {"label": "Plumbing", "value": "plumbing"},
            {"label": "Restoration", "value": "restoration"},
            {"label": "Property Management", "value": "property_management"},
            {"label": "Real Estate", "value": "real_estate"},
        ],
    },
    {
        "name": "job_size_focus",
        "label": "Job Size Focus",
        "type": "enumeration",
        "fieldType": "select",
        "description": "What type of jobs this provider prefers",
        "options": [
            {"label": "Residential only", "value": "residential"},
            {"label": "Commercial only", "value": "commercial"},
            {"label": "Both", "value": "both"},
            {"label": "Insurance-claim repairs", "value": "insurance_claim"},
        ],
    },
    {
        "name": "emergency_availability",
        "label": "Emergency / 24-7 Available",
        "type": "enumeration",
        "fieldType": "booleancheckbox",
        "description": "Will take emergency / after-hours calls",
        "options": [
            {"label": "Yes", "value": "true"},
            {"label": "No", "value": "false"},
        ],
    },
    {
        "name": "referral_channel_pref",
        "label": "Preferred Referral Channel",
        "type": "enumeration",
        "fieldType": "select",
        "description": "How this provider wants to receive hot referrals",
        "options": [
            {"label": "Text", "value": "text"},
            {"label": "Phone call", "value": "phone"},
            {"label": "Email", "value": "email"},
            {"label": "Anything works", "value": "any"},
        ],
    },
    {
        "name": "directory_listing_status",
        "label": "Directory Listing Status",
        "type": "enumeration",
        "fieldType": "select",
        "description": "Whether this provider is live on the public directory (gates the auto-confirmation email so we don't tell them they're listed before the page is updated)",
        "options": [
            {"label": "Pending add", "value": "pending_add"},
            {"label": "Listed (live)", "value": "listed"},
            {"label": "Declined / unfit", "value": "declined"},
        ],
    },
    {
        "name": "directory_listed_date",
        "label": "Directory Listed Date",
        "type": "date",
        "fieldType": "date",
        "description": "Date this provider's listing went live on the public directory",
    },
    {
        "name": "partner_type",
        "label": "Partner Type",
        "type": "enumeration",
        "fieldType": "select",
        "description": "Audience segment — drives which 30-day/quarterly template is used by partner_lifecycle.py. Defaults to 'provider' when unset.",
        "options": [
            {"label": "Directory Provider", "value": "provider"},
            {"label": "Field-Met Service Provider", "value": "field_met"},
            {"label": "Chamber / Networking Contact", "value": "chamber"},
            {"label": "BNI / Referral Group", "value": "bni"},
            {"label": "Real Estate Pro", "value": "real_estate_pro"},
            {"label": "Other", "value": "other"},
        ],
    },
    {
        "name": "partner_onboarded_at",
        "label": "Partner Onboarded At",
        "type": "date",
        "fieldType": "date",
        "description": "Date qualifying-questions answers were received and welcome email sent. Anchors 30-day check-in and quarterly pulse cadence.",
    },
    {
        "name": "partner_30day_sent_at",
        "label": "Partner 30-Day Check-in Sent",
        "type": "date",
        "fieldType": "date",
        "description": "Date the 30-day check-in email was sent (set by partner_lifecycle.py)",
    },
    {
        "name": "partner_last_pulse_at",
        "label": "Partner Last Quarterly Pulse",
        "type": "date",
        "fieldType": "date",
        "description": "Date of most recent quarterly pulse email (set by partner_lifecycle.py)",
    },
    {
        "name": "partner_referral_count",
        "label": "Referrals Sent (Lifetime)",
        "type": "number",
        "fieldType": "number",
        "description": "Total referrals Duncan has sent this partner. Incremented by the referral-handoff workflow.",
    },
    {
        "name": "chamber_event_name",
        "label": "Met at (event name)",
        "type": "string",
        "fieldType": "text",
        "description": "For chamber/networking contacts: exact event where Duncan met them (e.g. 'Wellington Chamber Connections 2026-05-19'). Substituted into templates.",
    },
    {
        "name": "met_context",
        "label": "Met Context (field providers)",
        "type": "string",
        "fieldType": "text",
        "description": "For field-met providers: short reminder of where/how Duncan met them (e.g. 'on the Smith roof claim'). Substituted into templates.",
    },
    {
        "name": "partner_referral_count_quarter",
        "label": "Referrals Sent (This Quarter)",
        "type": "number",
        "fieldType": "number",
        "description": "Referrals sent since the last quarterly pulse. Reset to 0 by partner_lifecycle.py when pulse fires.",
    },
]


def ensure(prop):
    status, _ = hs("GET", f"/crm/v3/properties/contacts/{prop['name']}")
    if status == 200:
        print(f"  · exists: {prop['name']}")
        return
    payload = {**prop, "groupName": GROUP_NAME}
    status, body = hs("POST", "/crm/v3/properties/contacts", payload)
    if status in (200, 201):
        print(f"  ✓ created: {prop['name']}")
    else:
        print(f"  ✗ create failed {prop['name']}: {status} {json.dumps(body)[:200]}")


def main():
    print(f"Ensuring {len(PROPERTIES)} HubSpot contact properties…")
    for p in PROPERTIES:
        ensure(p)
    print("Done.")


if __name__ == "__main__":
    main()
