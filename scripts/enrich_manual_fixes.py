#!/usr/bin/env python3
"""
Manual category fixes:
 - Set description + industry for obvious-trade companies the pattern matcher missed
 - Mark adjuster/insurance companies as UNQUALIFIED so they're excluded from provider outreach
"""

import json
import re
import time
import urllib.request
import urllib.error
from pathlib import Path

WORKSPACE = Path("/Users/victoria/.openclaw/workspace")
TOKEN_RE = re.compile(r'TOKEN\s*=\s*"([^"]+)"')
token = TOKEN_RE.search((WORKSPACE / "scripts" / "setup-hubspot-lists.py").read_text()).group(1)

# (company name fragment, description, industry)
TRADE_FIXES = [
    ("Air Rightaway",             "HVAC",                "CONSTRUCTION"),
    ("SERVPRO",                   "Restoration",         "CONSTRUCTION"),
    ("HOA Advocates",             "Property Management", "REAL_ESTATE"),
    ("Hopkins Air",               "HVAC",                "CONSTRUCTION"),
    ("Elite General Contracting", "General Contractor",  "CONSTRUCTION"),
    ("Jilsa Management",          "Property Management", "REAL_ESTATE"),
    ("Coral Condos",              "Property Management", "REAL_ESTATE"),
    ("JMA Community Management",  "Property Management", "REAL_ESTATE"),
    ("Trident Management",        "Property Management", "REAL_ESTATE"),
]

# Companies to mark unqualified — not service provider targets
SKIP_NAMES = [
    "Parker Public Adjusters",
    "Ocean Point Claims",
    "Reliant Adjusters Group",
    "Robinhood Adjusting",
    "Florida Insurance Partners",
    "SafeHaven Property Consulting",
    "Damelecia Inc.",
]


def hs(method, path, body=None):
    url = f"https://api.hubapi.com{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(2 ** attempt)
                continue
            return e.code, {"error": e.read().decode()}
    return 0, {}


def find_company(name_fragment):
    status, data = hs("POST", "/crm/v3/objects/companies/search", {
        "filterGroups": [{"filters": [{"propertyName": "name", "operator": "CONTAINS_TOKEN", "value": name_fragment}]}],
        "properties": ["name", "description", "industry"],
        "limit": 5,
    })
    return data.get("results", [])


def update_company(company_id, props):
    return hs("PATCH", f"/crm/v3/objects/companies/{company_id}", {"properties": props})


def get_company_contacts(company_id):
    status, data = hs("GET", f"/crm/v3/objects/companies/{company_id}/associations/contacts")
    return [r["id"] for r in data.get("results", [])]


def unqualify_contact(contact_id):
    return hs("PATCH", f"/crm/v3/objects/contacts/{contact_id}", {
        "properties": {"hs_lead_status": "UNQUALIFIED"}
    })


def log(msg):
    print(msg)


def main():
    log("=== Manual category fixes ===\n")

    # --- Fix obvious trades ---
    log("--- Updating trade categories ---")
    for name_fragment, category, industry in TRADE_FIXES:
        results = find_company(name_fragment)
        if not results:
            log(f"  ? Not found: {name_fragment}")
            continue
        for company in results:
            cid = company["id"]
            cname = company["properties"].get("name", "?")
            existing_desc = company["properties"].get("description", "")
            if existing_desc:
                log(f"  ~ Already set: {cname} ({existing_desc}) — skipping")
                continue
            status, _ = update_company(cid, {"description": category, "industry": industry})
            mark = "✓" if status in (200, 201) else f"✗ ({status})"
            log(f"  {mark}  {cname:45s} → {category}")
            time.sleep(0.07)

    log("\n--- Marking non-targets as Unqualified ---")
    for name_fragment in SKIP_NAMES:
        results = find_company(name_fragment)
        if not results:
            log(f"  ? Not found: {name_fragment}")
            continue
        for company in results:
            cid = company["id"]
            cname = company["properties"].get("name", "?")
            # Tag company itself
            update_company(cid, {"description": "Non-Target — Adjuster/Insurance"})
            # Unqualify all associated contacts
            contact_ids = get_company_contacts(cid)
            for ctid in contact_ids:
                unqualify_contact(ctid)
                time.sleep(0.05)
            log(f"  ✓  {cname} — marked unqualified ({len(contact_ids)} contact(s))")
            time.sleep(0.07)

    log("\n=== Done ===")


if __name__ == "__main__":
    main()
