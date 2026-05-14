#!/usr/bin/env python3
"""
Cleanup HubSpot deal pipeline based on the 2026-05-14 audit:
1. Delete 11 duplicate deals (keep the most advanced stage; on tie keep lower ID)
2. Delete 15 ghost deals (no associated company/contact)
3. Move 40 prospect-uploader deals from 'Outreach Sent' → 'New Prospect'
4. Add new pipeline stage: 'No Response — Circle Back'

Run:  python3 cleanup_deal_pipeline.py
"""
import json
import os
import re
import sys
import time
import urllib.request
import urllib.error
from collections import defaultdict
from pathlib import Path

WORKSPACE = Path("/Users/victoria/.openclaw/workspace")

def get_token():
    token = os.environ.get("HUBSPOT_API_KEY", "").strip()
    if token: return token
    secrets = WORKSPACE / "config" / ".secrets"
    m = re.search(r'HUBSPOT_API_KEY="([^"]+)"', secrets.read_text())
    if m: return m.group(1)
    sys.exit("ERROR: HUBSPOT_API_KEY not found.")

TOKEN = get_token()

def hs(method, path, body=None):
    url = f"https://api.hubapi.com{path}"
    data = json.dumps(body).encode() if body else None
    for attempt in range(5):
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Authorization", f"Bearer {TOKEN}")
        req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
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
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            if attempt < 4:
                time.sleep(2 ** attempt)
                continue
            return 0, {"error": str(e)}
    return 0, {}

# --- inputs --------------------------------------------------------------

STAGE_NEW_PROSPECT = "appointmentscheduled"
STAGE_OUTREACH_SENT = "qualifiedtobuy"

# Duplicates: keep one deal per company, delete the other.
# Rule applied: keep the deal in the most advanced stage; on tie keep lower (older) ID.
DUPLICATES_TO_DELETE = [
    # company, keep_id, delete_id
    ("All Phase Construction USA",           "324409554642", "324411361979"),
    ("Atlantic Water & Mold Solutions",      "324434333404", "324396259005"),
    ("Coastal Property Management Group",    "324332847824", "324341940954"),
    ("Elite General Contracting",            "324378341087", "324407796467"),
    ("Florida Insurance Partners LLC",       "324355725018", "324378341096"),
    ("HOA Advocates Management",             "324409554640", "324409554647"),
    ("KLR Roofing Corp.",                    "324335061738", "324340132574"),
    ("Prestige Realty Management",           "324366002889", "324335061742"),
    ("Quantum Roofing Solutions",            "324396258026", "324409554648"),
    ("SafeHaven Property Consulting",        "324378341091", "324439719632"),
    ("Storm Shield Roofing",                 "324358926018", "324432528119"),
]

GHOST_DEALS_TO_DELETE = [
    "324332847820",  # HubSpot — Outreach
    "324396258019",  # HubSpot — Outreach
    "324352183032",  # None None — Outreach
    "324411361991",  # None None — Outreach (Declined)
    "324434333433",  # None None — Outreach (Declined)
    "324439719639",  # None None — Outreach (Declined)
    "324335061748",  # None None — Outreach (Outreach Sent)
    "324387378892",  # None None — Outreach
    "324413153988",  # None None — Outreach
    "324407796469",  # None None — Outreach
    "324396259009",  # None None — Outreach
    "324358926033",  # None None — Outreach
    "324396259010",  # R. Littlejohn — Outreach
    "324437919471",  # None None — Outreach
    "324413154017",  # rzvsjqxtlr None — Outreach
]

# --- helpers ------------------------------------------------------------

def delete_deal(deal_id):
    status, data = hs("DELETE", f"/crm/v3/objects/deals/{deal_id}")
    return status in (200, 204)

def move_deal_to_stage(deal_id, stage_id):
    status, data = hs("PATCH", f"/crm/v3/objects/deals/{deal_id}",
                      {"properties": {"dealstage": stage_id}})
    return status in (200, 201)

def list_deals_in_stage(stage_id):
    deals, after = [], None
    while True:
        body = {
            "filterGroups": [{"filters": [{"propertyName": "dealstage",
                                            "operator": "EQ", "value": stage_id}]}],
            "properties": ["dealname", "dealstage"],
            "limit": 100,
        }
        if after: body["after"] = after
        _, data = hs("POST", "/crm/v3/objects/deals/search", body)
        deals.extend(data.get("results", []))
        after = data.get("paging", {}).get("next", {}).get("after")
        if not after: break
        time.sleep(0.1)
    return deals

# --- main ---------------------------------------------------------------

def main():
    print(f"\n{'='*70}")
    print(f"  HubSpot Deal Pipeline Cleanup")
    print(f"{'='*70}\n")

    # ── Step 1: delete duplicates ─────────────────────────────────────
    print(f"Step 1: Delete {len(DUPLICATES_TO_DELETE)} duplicate deals")
    print("-" * 70)
    for company, keep_id, del_id in DUPLICATES_TO_DELETE:
        ok = delete_deal(del_id)
        marker = "✓" if ok else "✗"
        print(f"  {marker} {company:40s}  deleted={del_id}  (kept {keep_id})")
        time.sleep(0.15)
    print()

    # ── Step 2: delete ghosts ─────────────────────────────────────────
    print(f"Step 2: Delete {len(GHOST_DEALS_TO_DELETE)} ghost deals")
    print("-" * 70)
    for did in GHOST_DEALS_TO_DELETE:
        ok = delete_deal(did)
        marker = "✓" if ok else "✗"
        print(f"  {marker} ghost  deleted={did}")
        time.sleep(0.15)
    print()

    # ── Step 3: revert prospect-uploader deals back to New Prospect ───
    # Strategy: load audit JSON, find all deals where:
    #   current_stage_id == 'qualifiedtobuy' (Outreach Sent)
    #   AND n_touches == 0
    #   AND deal NOT in any duplicate/ghost list
    audit_path = WORKSPACE / "crm" / "deal_audit_2026-05-14.json"
    with audit_path.open() as f:
        audit = json.load(f)

    deleted_ids = set(d for _, _, d in DUPLICATES_TO_DELETE) | set(GHOST_DEALS_TO_DELETE)
    to_revert = [
        r for r in audit["deals"]
        if r["current_stage_id"] == STAGE_OUTREACH_SENT
        and r["n_touches"] == 0
        and r["deal_id"] not in deleted_ids
        and r["company"]  # must have a real company name
    ]
    print(f"Step 3: Revert {len(to_revert)} prospect deals from 'Outreach Sent' → 'New Prospect'")
    print("-" * 70)
    for r in to_revert:
        ok = move_deal_to_stage(r["deal_id"], STAGE_NEW_PROSPECT)
        marker = "✓" if ok else "✗"
        print(f"  {marker} {r['company'][:50]:50s}  deal_id={r['deal_id']}")
        time.sleep(0.15)
    print()

    # ── Step 4: add new pipeline stage ────────────────────────────────
    print(f"Step 4: Add 'No Response — Circle Back' pipeline stage")
    print("-" * 70)
    _, pdata = hs("GET", "/crm/v3/pipelines/deals")
    pipeline = pdata["results"][0]
    pipeline_id = pipeline["id"]
    existing_labels = {s["label"] for s in pipeline["stages"]}
    if "No Response — Circle Back" in existing_labels:
        print("  ✓ stage already exists, skipping")
    else:
        # Insert before 'Declined' (closedlost)
        new_stage_body = {
            "label": "No Response — Circle Back",
            "metadata": {"probability": "0.1", "isClosed": "false"},
            "displayOrder": 6,  # before Declined which we'll bump to 7
        }
        status, resp = hs("POST",
            f"/crm/v3/pipelines/deals/{pipeline_id}/stages",
            new_stage_body)
        if status in (200, 201):
            print(f"  ✓ created stage: {resp.get('id', '?')}  label={resp.get('label')}")
        else:
            print(f"  ✗ failed to create stage: {status} {resp}")
    print()

    print(f"{'='*70}")
    print(f"  Cleanup complete. Re-run audit to verify.")
    print(f"{'='*70}\n")

if __name__ == "__main__":
    main()
