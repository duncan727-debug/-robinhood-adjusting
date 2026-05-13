#!/usr/bin/env python3
"""
HubSpot CRM Upload — upserts companies + contacts from master import CSV.
Reads HUBSPOT_API_KEY from environment; falls back to local setup script token.
Run daily after consolidate_crm_daily.py produces hubspot_master_import.csv.
"""

import csv
import json
import os
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime

WORKSPACE = Path("/Users/victoria/.openclaw/workspace")
CSV_PATH = WORKSPACE / "crm" / "hubspot_master_import.csv"
LOG_PATH = WORKSPACE / "crm" / "hubspot_upload.log"

def get_token():
    token = os.environ.get("HUBSPOT_API_KEY", "").strip()
    if token:
        return token
    # Fallback: read from config/.secrets (the actual stored secret)
    secrets = WORKSPACE / "config" / ".secrets"
    if secrets.exists():
        for line in secrets.read_text().splitlines():
            if "HUBSPOT_API_KEY=" in line and not line.strip().startswith("#"):
                val = line.split("HUBSPOT_API_KEY=", 1)[1].strip().strip('"').strip("'")
                if val.startswith("pat-"):
                    return val
    sys.exit("ERROR: HUBSPOT_API_KEY not set in env and not found in config/.secrets.")

TOKEN = get_token()

def hs_request(method, path, payload=None, retries=3):
    url = f"https://api.hubapi.com{path}"
    data = json.dumps(payload).encode() if payload else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {TOKEN}")
    req.add_header("Content-Type", "application/json")
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req) as resp:
                return resp.status, json.loads(resp.read())
        except urllib.error.HTTPError as e:
            body = {}
            try:
                body = json.loads(e.read())
            except Exception:
                pass
            if e.code == 429:
                time.sleep(2 ** attempt)
                continue
            return e.code, body
    return 0, {"error": "max retries exceeded"}

def split_name(full):
    parts = full.strip().split(None, 1)
    return (parts[0], parts[1]) if len(parts) == 2 else (full.strip(), "")

def upsert_company(name, website, county, category):
    props = {"name": name}
    if website:
        props["domain"] = website.lstrip("https://").lstrip("http://").rstrip("/")
    if county:
        props["city"] = county  # Using city field for county
    if category:
        props["industry"] = category

    # Search for existing company by name
    status, data = hs_request("POST", "/crm/v3/objects/companies/search", {
        "filterGroups": [{"filters": [{"propertyName": "name", "operator": "EQ", "value": name}]}],
        "properties": ["name", "hs_object_id"],
        "limit": 1
    })
    if status == 200 and data.get("results"):
        company_id = data["results"][0]["id"]
        hs_request("PATCH", f"/crm/v3/objects/companies/{company_id}", {"properties": props})
        return company_id, "updated"

    status, data = hs_request("POST", "/crm/v3/objects/companies", {"properties": props})
    if status in (200, 201):
        return data["id"], "created"
    return None, f"error:{status}"

def upsert_contact(first, last, email, phone, company_id):
    props = {"firstname": first, "lastname": last}
    if phone:
        props["phone"] = phone

    if email:
        # Upsert by email
        status, data = hs_request("PATCH",
            f"/crm/v3/objects/contacts/{email}?idProperty=email",
            {"properties": props})
        if status in (200, 204):
            contact_id = data.get("id")
        else:
            status, data = hs_request("POST", "/crm/v3/objects/contacts",
                {"properties": {**props, "email": email}})
            contact_id = data.get("id") if status in (200, 201) else None
    else:
        # Search by phone or name
        search_filter = {"propertyName": "phone", "operator": "EQ", "value": phone} if phone else \
                        {"propertyName": "firstname", "operator": "EQ", "value": first}
        status, data = hs_request("POST", "/crm/v3/objects/contacts/search", {
            "filterGroups": [{"filters": [search_filter]}],
            "properties": ["firstname", "lastname", "hs_object_id"],
            "limit": 1
        })
        if status == 200 and data.get("results"):
            contact_id = data["results"][0]["id"]
            hs_request("PATCH", f"/crm/v3/objects/contacts/{contact_id}", {"properties": props})
        else:
            status, data = hs_request("POST", "/crm/v3/objects/contacts", {"properties": props})
            contact_id = data.get("id") if status in (200, 201) else None

    # Associate contact with company
    if contact_id and company_id:
        hs_request("PUT",
            f"/crm/v3/objects/contacts/{contact_id}/associations/companies/{company_id}/contact_to_company",
            None)

    return contact_id

def main():
    log_lines = [f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] HubSpot upload started"]
    created = updated = errors = skipped = 0

    with open(CSV_PATH, newline="") as f:
        rows = list(csv.DictReader(f))

    log_lines.append(f"  Records to process: {len(rows)}")
    print(f"Processing {len(rows)} records...")

    for i, row in enumerate(rows):
        company_name = row.get("company_name", "").strip()
        contact_name = row.get("contact_name", "").strip()
        email = row.get("contact_email", "").strip()
        phone = row.get("phone", "").strip()
        county = row.get("county", "").strip()
        category = row.get("category", "").strip()
        website = row.get("website", "").strip()

        if not company_name:
            skipped += 1
            continue

        company_id, company_action = upsert_company(company_name, website, county, category)

        contact_id = None
        if contact_name and company_id:
            first, last = split_name(contact_name)
            contact_id = upsert_contact(first, last, email, phone, company_id)

        if company_action == "created":
            created += 1
        elif company_action == "updated":
            updated += 1
        else:
            errors += 1

        if (i + 1) % 10 == 0:
            print(f"  {i+1}/{len(rows)} processed...")
        time.sleep(0.1)  # Rate limit safety

    summary = (f"  Done: {created} created, {updated} updated, "
               f"{errors} errors, {skipped} skipped")
    print(summary)
    log_lines.append(summary)
    log_lines.append(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Upload complete\n")

    with open(LOG_PATH, "a") as f:
        f.write("\n".join(log_lines) + "\n")

    return errors == 0

if __name__ == "__main__":
    sys.exit(0 if main() else 1)
