#!/usr/bin/env python3
"""
Enrich HubSpot contacts with data from local CRM files.
Fields updated: phone, email, city, state, website, industry, jobtitle, company

Sources (in priority order):
  1. organizations.csv  — named contacts with full details
  2. Draft .md files    — phone numbers in body text
  3. Intelligence .md   — additional context

Usage:
  python3 enrich_hubspot_contacts.py [--dry-run]
"""

import csv
import json
import os
import re
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path
from collections import defaultdict

WORKSPACE = Path("/Users/victoria/.openclaw/workspace")
LOG_PATH = WORKSPACE / "scripts" / "hubspot_draft_upload.log"
DRY_RUN = "--dry-run" in sys.argv

# County → city mapping (South Florida)
COUNTY_CITY = {
    "palm-beach":  ("West Palm Beach", "FL"),
    "broward":     ("Fort Lauderdale", "FL"),
    "miami-dade":  ("Miami", "FL"),
    "st-lucie":    ("Port St. Lucie", "FL"),
    "martin":      ("Stuart", "FL"),
    "palm beach":  ("West Palm Beach", "FL"),
    "broward county": ("Fort Lauderdale", "FL"),
}

# Category → HubSpot industry
# Contact industry: free text
CONTACT_INDUSTRY = {
    "roofer":            "Construction",
    "plumber":           "Construction",
    "hvac":              "Construction",
    "general-contractor":"Construction",
    "water-mitigation":  "Construction",
    "mold-remediation":  "Construction",
    "property-manager":  "Real Estate",
    "hoa-manager":       "Real Estate",
    "real-estate":       "Real Estate",
    "attorney":          "Legal Services",
    "public-adjuster":   "Insurance",
}

# Company industry: HubSpot enum values
COMPANY_INDUSTRY = {
    "roofer":            "CONSTRUCTION",
    "plumber":           "CONSTRUCTION",
    "hvac":              "CONSTRUCTION",
    "general-contractor":"CONSTRUCTION",
    "water-mitigation":  "CONSTRUCTION",
    "mold-remediation":  "CONSTRUCTION",
    "property-manager":  "REAL_ESTATE",
    "hoa-manager":       "REAL_ESTATE",
    "real-estate":       "REAL_ESTATE",
    "attorney":          "LEGAL_SERVICES",
    "public-adjuster":   "INSURANCE",
}

CATEGORY_INDUSTRY = CONTACT_INDUSTRY  # used for contacts

_TOKEN = None


def log(msg):
    from datetime import datetime
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_PATH, "a") as f:
        f.write(line + "\n")


def load_token():
    global _TOKEN
    setup = WORKSPACE / "scripts" / "setup-hubspot-lists.py"
    m = re.search(r'TOKEN\s*=\s*"([^"]+)"', setup.read_text())
    _TOKEN = m.group(1) if m else os.environ.get("HUBSPOT_API_KEY", "")
    if not _TOKEN:
        sys.exit("ERROR: No HubSpot token found.")


def hs(method, path, body=None, retries=3):
    url = f"https://api.hubapi.com{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {_TOKEN}")
    req.add_header("Content-Type", "application/json")
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            raw = b""
            try: raw = e.read()
            except: pass
            if e.code == 429:
                time.sleep(2 ** attempt)
                continue
            try: return e.code, json.loads(raw)
            except: return e.code, {}
    return 0, {}


def get_all_contacts():
    """Fetch all HubSpot contacts with relevant properties."""
    props = "firstname,lastname,email,phone,company,city,state,website,industry,jobtitle"
    contacts = []
    after = None
    while True:
        url = f"/crm/v3/objects/contacts?limit=100&properties={props}"
        if after:
            url += f"&after={after}"
        status, data = hs("GET", url)
        if status != 200:
            log(f"Error fetching contacts: {status}")
            break
        contacts.extend(data.get("results", []))
        paging = data.get("paging", {}).get("next", {})
        after = paging.get("after") if paging else None
        if not after:
            break
        time.sleep(0.1)
    return contacts


def load_orgs_csv():
    """Load organizations.csv into a dict keyed by contact_name and company name."""
    by_contact = {}
    by_company = {}
    path = WORKSPACE / "crm" / "organizations.csv"
    with open(path) as f:
        for row in csv.DictReader(f):
            name = (row.get("contact_name") or "").strip()
            company = (row.get("name") or "").strip()
            if name:
                by_contact[name.lower()] = row
            if company:
                by_company[company.lower()] = row
    return by_contact, by_company


def load_draft_phones():
    """Extract phone numbers from draft files, keyed by company name fragments."""
    phone_map = defaultdict(set)
    SKIP = {"DAILY-STATUS", "OUTREACH-SUMMARY", "status-summary",
            "DAILY-SUMMARY", "00-BATCH-SUMMARY", "DELIVERY-COMPLETE"}
    for draft_dir in (WORKSPACE / "crm" / "drafts").iterdir():
        if not draft_dir.is_dir():
            continue
        for f in draft_dir.glob("*.md"):
            if any(s in f.name for s in SKIP):
                continue
            text = f.read_text()
            phones = re.findall(r'\b(\d{3}[-.\s]\d{3}[-.\s]\d{4})\b', text)
            # Try to get company from bold Phone: line or filename
            phone_line = re.search(r'\*\*Phone:\*\*\s*(.+)', text)
            if phone_line and phones:
                # Associate with organization name from file
                org_m = re.search(r'\*\*Organization:\*\*\s*(.+)', text)
                if org_m:
                    key = org_m.group(1).strip().lower()
                    phone_map[key].add(phones[0])
            # Also from **Phone:** in structured drafts
            if phones:
                # Use filename as fallback key
                stem = f.stem.replace("-", " ").lower()
                for phone in phones:
                    phone_map[stem].add(phone)
    return phone_map


def build_enrichment(contact, by_contact, by_company, draft_phones):
    """Return dict of properties to update (only non-empty fields that are currently blank)."""
    props = contact.get("properties", {})
    contact_id = contact["id"]

    def blank(field):
        return not (props.get(field) or "").strip()

    updates = {}

    # Match by contact name first, then company name
    full_name = f"{(props.get('firstname') or '').strip()} {(props.get('lastname') or '').strip()}".strip().lower()
    company_name = (props.get("company") or "").strip().lower()

    row = by_contact.get(full_name) or by_company.get(company_name)

    if row:
        county = (row.get("county") or "").strip().lower()
        category = (row.get("category") or "").strip().lower()

        if blank("phone") and row.get("contact_phone"):
            updates["phone"] = row["contact_phone"].strip()
        if blank("email") and row.get("contact_email"):
            updates["email"] = row["contact_email"].strip()
        if blank("jobtitle") and row.get("contact_title"):
            updates["jobtitle"] = row["contact_title"].strip()
        if blank("website") and row.get("website"):
            website = row["website"].strip()
            if not website.startswith("http"):
                website = "https://" + website
            updates["website"] = website
        if blank("city") or blank("state"):
            city, state = COUNTY_CITY.get(county, ("", ""))
            if city and blank("city"):
                updates["city"] = city
            if state and blank("state"):
                updates["state"] = state
        if blank("industry") and category:
            industry = CATEGORY_INDUSTRY.get(category, "")
            if industry:
                updates["industry"] = industry
        if blank("company") and row.get("name"):
            updates["company"] = row["name"].strip()

    else:
        # Try to get phone from draft files
        if blank("phone"):
            for key, phones in draft_phones.items():
                if company_name and company_name in key:
                    updates["phone"] = next(iter(phones))
                    break

        # Try to infer city/state from company name county hints
        if blank("city"):
            for county_key, (city, state) in COUNTY_CITY.items():
                if county_key.replace("-", " ") in company_name:
                    updates["city"] = city
                    updates["state"] = state
                    break

    return updates


def patch_contact(contact_id, updates):
    if not updates:
        return False
    status, data = hs("PATCH", f"/crm/v3/objects/contacts/{contact_id}",
                      {"properties": updates})
    return status in (200, 201)


def get_all_companies():
    """Fetch all HubSpot companies with relevant properties."""
    props = "name,phone,city,state,website,industry,description"
    companies = []
    after = None
    while True:
        url = f"/crm/v3/objects/companies?limit=100&properties={props}"
        if after:
            url += f"&after={after}"
        status, data = hs("GET", url)
        if status != 200:
            break
        companies.extend(data.get("results", []))
        paging = data.get("paging", {}).get("next", {})
        after = paging.get("after") if paging else None
        if not after:
            break
        time.sleep(0.1)
    return companies


def build_company_enrichment(company, by_company):
    props = company.get("properties", {})
    name = (props.get("name") or "").strip().lower()

    def blank(field):
        return not (props.get(field) or "").strip()

    updates = {}
    row = by_company.get(name)
    if not row:
        return updates

    county = (row.get("county") or "").strip().lower()
    category = (row.get("category") or "").strip().lower()

    if blank("phone") and row.get("contact_phone"):
        updates["phone"] = row["contact_phone"].strip()
    if blank("website") and row.get("website"):
        website = row["website"].strip()
        if not website.startswith("http"):
            website = "https://" + website
        updates["website"] = website
    if blank("city") or blank("state"):
        city, state = COUNTY_CITY.get(county, ("", ""))
        if city and blank("city"):
            updates["city"] = city
        if state and blank("state"):
            updates["state"] = state
    if blank("industry") and category:
        industry = COMPANY_INDUSTRY.get(category, "")
        if industry:
            updates["industry"] = industry

    return updates


def patch_company(company_id, updates):
    if not updates:
        return False
    status, _ = hs("PATCH", f"/crm/v3/objects/companies/{company_id}",
                   {"properties": updates})
    return status in (200, 201)


def main():
    load_token()
    mode = "DRY RUN" if DRY_RUN else "LIVE"
    log(f"=== HubSpot enrichment start ({mode}) ===")

    by_contact, by_company = load_orgs_csv()
    draft_phones = load_draft_phones()

    # ── Contacts ──────────────────────────────────────────────────────────────
    log("Fetching all HubSpot contacts...")
    contacts = get_all_contacts()
    log(f"Found {len(contacts)} contacts")

    contact_updated = contact_skipped = 0
    for c in contacts:
        updates = build_enrichment(c, by_contact, by_company, draft_phones)
        if not updates:
            contact_skipped += 1
            continue
        name = f"{c['properties'].get('firstname','')} {c['properties'].get('lastname','')}".strip() \
               or c['properties'].get('company', c['id'])
        if DRY_RUN:
            log(f"  [DRY] {name}: {list(updates.keys())}")
            contact_updated += 1
        else:
            if patch_contact(c["id"], updates):
                log(f"  ✓ {name}: {list(updates.keys())}")
                contact_updated += 1
            else:
                log(f"  ✗ {name}: patch failed")
        time.sleep(0.15)

    log(f"Contacts — updated: {contact_updated} | skipped (already full): {contact_skipped}")

    # ── Companies ─────────────────────────────────────────────────────────────
    log("Fetching all HubSpot companies...")
    companies = get_all_companies()
    log(f"Found {len(companies)} companies")

    co_updated = co_skipped = 0
    for co in companies:
        updates = build_company_enrichment(co, by_company)
        if not updates:
            co_skipped += 1
            continue
        name = co["properties"].get("name", co["id"])
        if DRY_RUN:
            log(f"  [DRY] {name}: {list(updates.keys())}")
            co_updated += 1
        else:
            if patch_company(co["id"], updates):
                log(f"  ✓ {name}: {list(updates.keys())}")
                co_updated += 1
            else:
                log(f"  ✗ {name}: patch failed")
        time.sleep(0.15)

    log(f"Companies — updated: {co_updated} | skipped (already full): {co_skipped}")
    log("=== Enrichment complete ===")


if __name__ == "__main__":
    main()
