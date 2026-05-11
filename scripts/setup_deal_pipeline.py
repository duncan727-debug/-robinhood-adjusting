#!/usr/bin/env python3
"""
One-time setup: updates the default HubSpot deal pipeline with "Partner Outreach"
stages and backfills all existing contacts into the correct stage based on
their current hs_lead_status.

Run once:  python3 setup_deal_pipeline.py
Safe to re-run — skips contacts that already have an open deal.
"""

import json
import os
import re
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE = Path("/Users/victoria/.openclaw/workspace")

def get_token():
    token = os.environ.get("HUBSPOT_API_KEY", "").strip()
    if token:
        return token
    setup = WORKSPACE / "scripts" / "setup-hubspot-lists.py"
    m = re.search(r'TOKEN\s*=\s*"([^"]+)"', setup.read_text())
    if m:
        return m.group(1)
    sys.exit("ERROR: HUBSPOT_API_KEY not found.")

TOKEN = get_token()

def hs(method, path, body=None):
    url  = f"https://api.hubapi.com{path}"
    data = json.dumps(body).encode() if body else None
    req  = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {TOKEN}")
    req.add_header("Content-Type", "application/json")
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                raw = r.read()
                return r.status, json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            raw = b""
            try: raw = e.read()
            except: pass
            if e.code == 429:
                time.sleep(2 ** attempt)
                continue
            try: return e.code, json.loads(raw)
            except: return e.code, {"raw": raw.decode(errors="replace")}
    return 0, {}

# Pipeline stages — mapped to existing HubSpot stage IDs in the default pipeline
STAGES = {
    "New Prospect":         {"id": "appointmentscheduled", "label": "New Prospect"},
    "Outreach Sent":        {"id": "qualifiedtobuy", "label": "Outreach Sent"},
    "Responded":            {"id": "presentationscheduled", "label": "Responded"},
    "Listed in Directory":  {"id": "decisionmakerboughtin", "label": "Listed in Directory"},
    "Meeting Scheduled":    {"id": "contractsent", "label": "Meeting Scheduled"},
    "Active Partner":       {"id": "closedwon", "label": "Active Partner"},
    "Declined":             {"id": "closedlost", "label": "Declined"},
}

# Maps hs_lead_status → pipeline stage ID
STATUS_TO_STAGE_ID = {
    "NEW":          "appointmentscheduled",      # New Prospect
    "OPEN":         "appointmentscheduled",      # New Prospect
    "IN_PROGRESS":  "qualifiedtobuy",            # Outreach Sent
    "CONNECTED":    "decisionmakerboughtin",     # Listed in Directory
    "UNQUALIFIED":  "closedlost",                # Declined
}

# ── step 1: get pipeline + stages ────────────────────────────────────────────

def get_pipeline():
    print("Fetching default pipeline...")
    status, data = hs("GET", "/crm/v3/pipelines/deals")
    if status != 200 or not data.get("results"):
        print(f"  ERROR: {data}")
        sys.exit(1)
    pipeline = data["results"][0]  # First (and usually only) pipeline in free tier
    print(f"  Found: [{pipeline['id']}] {pipeline['label']}\n")
    return pipeline

# ── step 2: fetch all contacts ────────────────────────────────────────────────

def get_all_contacts():
    contacts = []
    after    = None
    while True:
        body = {
            "filterGroups": [],
            "properties": ["firstname", "lastname", "email", "company", "hs_lead_status"],
            "limit": 100,
        }
        if after:
            body["after"] = after
        _, data = hs("POST", "/crm/v3/objects/contacts/search", body)
        contacts.extend(data.get("results", []))
        after = data.get("paging", {}).get("next", {}).get("after")
        if not after:
            break
        time.sleep(0.1)
    return contacts

def get_company_for_contact(contact_id):
    _, data = hs("GET", f"/crm/v3/objects/contacts/{contact_id}/associations/companies")
    ids = [r["id"] for r in data.get("results", [])]
    return ids[0] if ids else None

def contact_has_deal(contact_id):
    _, data = hs("GET", f"/crm/v3/objects/contacts/{contact_id}/associations/deals")
    return bool(data.get("results"))

# ── step 3: create deal per contact ──────────────────────────────────────────

def create_deal(contact_id, company_id, contact_props, pipeline_id, stage_id):
    company    = contact_props.get("company") or "Unknown"
    deal_name  = f"{company} — Outreach"

    props = {
        "dealname":   deal_name,
        "pipeline":   pipeline_id,
        "dealstage":  stage_id,
        "closedate":  str(int((datetime.now(timezone.utc).timestamp() + 90*86400) * 1000)),
    }

    status, data = hs("POST", "/crm/v3/objects/deals", {"properties": props})
    if status not in (200, 201):
        print(f"    ERROR creating deal: {data}")
        return None

    deal_id = data["id"]

    # Associate deal → contact
    if contact_id:
        hs("PUT",
           f"/crm/v3/objects/deals/{deal_id}/associations/contacts/{contact_id}/deal_to_contact",
           None)

    # Associate deal → company
    if company_id:
        hs("PUT",
           f"/crm/v3/objects/deals/{deal_id}/associations/companies/{company_id}/deal_to_company",
           None)

    return deal_id

# ── main ─────────────────────────────────────────────────────────────────────

def main():
    print(f"\n{'='*60}")
    print(f"  HubSpot Partner Outreach Pipeline Setup")
    print(f"{'='*60}\n")

    pipeline = get_pipeline()
    pipeline_id = pipeline["id"]

    # Build stage ID map
    stage_id_map = {s["label"]: s["id"] for s in pipeline.get("stages", [])}

    print("Fetching all contacts...")
    contacts = get_all_contacts()
    print(f"  Found {len(contacts)} contacts\n")

    created = skipped = errors = 0

    for contact in contacts:
        cid   = contact["id"]
        props = contact["properties"]
        company = props.get("company") or "(no company)"
        lead_status = props.get("hs_lead_status") or "NEW"

        # Skip if already has a deal
        if contact_has_deal(cid):
            print(f"  SKIP (has deal): {company}")
            skipped += 1
            time.sleep(0.05)
            continue

        stage_id = STATUS_TO_STAGE_ID.get(lead_status, "appointmentscheduled")
        stage_label = next((s["label"] for s in STAGES.values() if s["id"] == stage_id), "New Prospect")

        company_id = get_company_for_contact(cid)
        deal_id    = create_deal(cid, company_id, props, pipeline_id, stage_id)

        if deal_id:
            print(f"  ✓ [{stage_label:22s}] {company}")
            created += 1
        else:
            errors += 1

        time.sleep(0.2)

    print(f"\n{'='*60}")
    print(f"  Done")
    print(f"  Deals created : {created}")
    print(f"  Skipped       : {skipped}")
    print(f"  Errors        : {errors}")
    print(f"\n  View pipeline in HubSpot:")
    print(f"  CRM → Deals → switch view to 'Board'")
    print(f"  (or click the board icon at top-right)")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    main()
