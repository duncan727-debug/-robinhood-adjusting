#!/usr/bin/env python3
"""
One-time enrichment: pattern-match trade category from company name,
write to HubSpot `description` field for any company missing it.
Also sets `industry` (HubSpot enum) if missing.
"""

import json
import re
import time
import urllib.request
import urllib.error
from pathlib import Path

WORKSPACE = Path("/Users/victoria/.openclaw/workspace")
LOG_PATH = WORKSPACE / "crm" / "enrich_categories.log"

TOKEN_RE = re.compile(r'TOKEN\s*=\s*"([^"]+)"')
token = TOKEN_RE.search((WORKSPACE / "scripts" / "setup-hubspot-lists.py").read_text()).group(1)

# Priority order matters — more specific patterns first
PATTERNS = [
    ("Roofing",             re.compile(r"roof|shingle|metal roof", re.I)),
    ("Restoration",         re.compile(r"restor|mitigation|mold|remediat|water damage|flood", re.I)),
    ("Plumbing",            re.compile(r"plumb|pipe|drain|sewer", re.I)),
    ("HVAC",                re.compile(r"hvac|air condition|cooling|heating|\bac\b|a/c|refriger|mechanical", re.I)),
    ("Property Management", re.compile(r"property manag|property mgmt|prop mgmt|asset manag", re.I)),
    ("Real Estate",         re.compile(r"real estate|realty|realtor|realtors", re.I)),
    ("General Contractor",  re.compile(r"contractor|construction|builders?|building|renovation|remodel|home improve", re.I)),
]

INDUSTRY_MAP = {
    "Roofing":             "CONSTRUCTION",
    "Restoration":         "CONSTRUCTION",
    "Plumbing":            "CONSTRUCTION",
    "HVAC":                "CONSTRUCTION",
    "General Contractor":  "CONSTRUCTION",
    "Property Management": "REAL_ESTATE",
    "Real Estate":         "REAL_ESTATE",
}


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
            body_text = e.read().decode()
            if e.code == 429:
                time.sleep(2 ** attempt)
                continue
            return e.code, {"error": body_text}
    return 0, {}


def guess_category(name):
    for label, pat in PATTERNS:
        if pat.search(name):
            return label
    return None


def log(msg):
    print(msg)
    with open(LOG_PATH, "a") as f:
        f.write(msg + "\n")


def get_all_companies():
    companies = []
    after = None
    while True:
        url = "/crm/v3/objects/companies/search"
        payload = {
            "filterGroups": [{"filters": [{"propertyName": "hs_lastmodifieddate", "operator": "GT", "value": "0"}]}],
            "properties": ["name", "description", "industry"],
            "limit": 100,
        }
        if after:
            payload["after"] = after
        status, data = hs("POST", url, payload)
        if status not in (200, 201):
            log(f"ERROR fetching companies: {status} {data}")
            break
        companies.extend(data.get("results", []))
        after = data.get("paging", {}).get("next", {}).get("after")
        if not after:
            break
        time.sleep(0.2)
    return companies


def main():
    log("=== enrich_company_categories start ===")
    companies = get_all_companies()
    log(f"Total companies fetched: {len(companies)}")

    needs_update = []
    for c in companies:
        p = c["properties"]
        name = p.get("name") or ""
        desc = p.get("description") or ""
        ind  = p.get("industry") or ""
        if not desc:
            needs_update.append((c["id"], name, ind))

    log(f"Companies missing description: {len(needs_update)}")

    updated = 0
    flagged = []

    for company_id, name, existing_industry in needs_update:
        category = guess_category(name)
        if not category:
            flagged.append(name)
            continue

        industry = INDUSTRY_MAP.get(category, "CONSTRUCTION")
        props = {"description": category}
        if not existing_industry:
            props["industry"] = industry

        status, _ = hs("PATCH", f"/crm/v3/objects/companies/{company_id}", {"properties": props})
        if status in (200, 201):
            log(f"  ✓  {name:45s} → {category}")
            updated += 1
        else:
            log(f"  ✗  {name:45s} → ERROR {status}")
        time.sleep(0.07)

    log(f"\n=== Done — updated: {updated} | needs manual review: {len(flagged)} ===")
    if flagged:
        log("\nNeeds manual review (name didn't match any pattern):")
        for name in flagged:
            log(f"  - {name}")


if __name__ == "__main__":
    main()
