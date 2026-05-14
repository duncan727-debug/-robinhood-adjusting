#!/usr/bin/env python3
"""
Audit HubSpot deal pipeline:
- Lists every deal with stage + associated contact/company
- Cross-checks against local crm/interactions.csv and crm/organizations.csv
- Flags mismatches (e.g. multiple follow-ups sent but deal still in 'New Prospect')
"""
import csv
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
    if token:
        return token
    secrets = WORKSPACE / "config" / ".secrets"
    m = re.search(r'HUBSPOT_API_KEY="([^"]+)"', secrets.read_text())
    if m:
        return m.group(1)
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

def get_pipeline():
    status, data = hs("GET", "/crm/v3/pipelines/deals")
    if status != 200 or not data.get("results"):
        sys.exit(f"ERROR fetching pipeline: {data}")
    return data["results"][0]

def get_all_deals():
    deals, after = [], None
    while True:
        body = {
            "properties": ["dealname", "dealstage", "pipeline", "hs_lead_status", "closedate", "createdate"],
            "limit": 100,
        }
        if after:
            body["after"] = after
        _, data = hs("POST", "/crm/v3/objects/deals/search", body)
        deals.extend(data.get("results", []))
        after = data.get("paging", {}).get("next", {}).get("after")
        if not after:
            break
        time.sleep(0.1)
    return deals

def get_deal_associations(deal_id):
    contacts, companies = [], []
    _, c = hs("GET", f"/crm/v3/objects/deals/{deal_id}/associations/contacts")
    contacts = [r["id"] for r in c.get("results", [])]
    _, co = hs("GET", f"/crm/v3/objects/deals/{deal_id}/associations/companies")
    companies = [r["id"] for r in co.get("results", [])]
    return contacts, companies

def get_company_name(company_id):
    _, d = hs("GET", f"/crm/v3/objects/companies/{company_id}?properties=name")
    return (d.get("properties", {}).get("name") or "")

def get_contact_props(contact_id):
    _, d = hs("GET", f"/crm/v3/objects/contacts/{contact_id}?properties=firstname,lastname,email,company,hs_lead_status")
    return d.get("properties", {})

def load_local_outreach():
    """Count outreach touchpoints per org from interactions.csv"""
    by_org = defaultdict(list)
    p = WORKSPACE / "crm" / "interactions.csv"
    with p.open() as f:
        reader = csv.DictReader(f)
        for row in reader:
            by_org[row["org_id"]].append(row)
    return by_org

def load_org_names():
    p = WORKSPACE / "crm" / "organizations.csv"
    by_name = {}
    with p.open() as f:
        reader = csv.DictReader(f)
        for row in reader:
            by_name[row["name"].lower().strip()] = row
    return by_name

def main():
    pipeline = get_pipeline()
    stage_labels = {s["id"]: s["label"] for s in pipeline["stages"]}

    print(f"\n{'='*70}")
    print(f"  HubSpot Deal Pipeline Audit — {time.strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*70}\n")
    print(f"Pipeline: [{pipeline['id']}] {pipeline['label']}\n")

    deals = get_all_deals()
    print(f"Total deals: {len(deals)}\n")

    # Bucket by stage
    by_stage = defaultdict(list)
    for d in deals:
        s = d["properties"].get("dealstage", "?")
        by_stage[s].append(d)

    for stage_id, stage_label in [
        ("appointmentscheduled", "New Prospect"),
        ("qualifiedtobuy", "Outreach Sent"),
        ("presentationscheduled", "Responded"),
        ("decisionmakerboughtin", "Listed in Directory"),
        ("contractsent", "Meeting Scheduled"),
        ("closedwon", "Active Partner"),
        ("closedlost", "Declined"),
    ]:
        count = len(by_stage.get(stage_id, []))
        print(f"  [{stage_label:22s}] {count}")
    print()

    local_outreach = load_local_outreach()
    local_orgs = load_org_names()

    # Cross-check
    print(f"{'='*70}")
    print(f"  Detailed audit — comparing HubSpot stage vs local touchpoints")
    print(f"{'='*70}\n")

    mismatches = []
    audit_rows = []

    for d in deals:
        deal_id = d["id"]
        props = d["properties"]
        deal_name = props.get("dealname", "")
        stage_id = props.get("dealstage", "")
        stage_label = stage_labels.get(stage_id, stage_id)

        contact_ids, company_ids = get_deal_associations(deal_id)
        time.sleep(0.05)

        company_name = ""
        if company_ids:
            company_name = get_company_name(company_ids[0])
            time.sleep(0.05)

        # Try to match to local org
        local_org_id = None
        local_org = local_orgs.get(company_name.lower().strip())
        if local_org:
            local_org_id = local_org["org_id"]

        local_touches = local_outreach.get(local_org_id, []) if local_org_id else []
        sent_touches = [t for t in local_touches if t.get("outcome") not in ("draft_prepared", "queued_for_review")]
        n_local = len(local_touches)
        n_followups = sum(1 for t in local_touches if t.get("stage", "").startswith("followup"))
        n_escalations = sum(1 for t in local_touches if t.get("stage") == "escalation")

        # Determine expected stage
        expected = "appointmentscheduled"  # default
        if n_escalations > 0:
            expected = "qualifiedtobuy"  # Outreach Sent (multi-touch but no response)
        elif n_followups >= 1:
            expected = "qualifiedtobuy"
        elif n_local >= 1:
            expected = "qualifiedtobuy"

        mismatch = (expected != stage_id) and stage_id not in ("closedwon", "closedlost", "presentationscheduled", "decisionmakerboughtin", "contractsent")

        row = {
            "deal_id": deal_id,
            "deal_name": deal_name,
            "company": company_name,
            "current_stage": stage_label,
            "current_stage_id": stage_id,
            "local_org_id": local_org_id or "(unmatched)",
            "n_touches": n_local,
            "n_followups": n_followups,
            "n_escalations": n_escalations,
            "expected_stage_id": expected,
            "mismatch": mismatch,
        }
        audit_rows.append(row)
        if mismatch:
            mismatches.append(row)

        flag = " ⚠️" if mismatch else ""
        print(f"  [{stage_label:22s}] {company_name or deal_name}{flag}")
        print(f"    deal_id={deal_id}  local={local_org_id}  touches={n_local} (followups={n_followups}, escalations={n_escalations})")

    print(f"\n{'='*70}")
    print(f"  Summary")
    print(f"{'='*70}\n")
    print(f"  Total deals     : {len(deals)}")
    print(f"  Stage mismatches: {len(mismatches)}")
    print(f"  Unmatched orgs  : {sum(1 for r in audit_rows if r['local_org_id'] == '(unmatched)')}")
    print()

    if mismatches:
        print(f"  Mismatched deals (current → expected):")
        for r in mismatches:
            expected_label = stage_labels.get(r["expected_stage_id"], r["expected_stage_id"])
            print(f"    • {r['company']}: {r['current_stage']} → {expected_label}")
            print(f"      (touches={r['n_touches']}, followups={r['n_followups']}, escalations={r['n_escalations']})")
        print()

    # Write audit report
    report_path = WORKSPACE / "crm" / f"deal_audit_{time.strftime('%Y-%m-%d')}.json"
    with report_path.open("w") as f:
        json.dump({
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "pipeline_id": pipeline["id"],
            "deals": audit_rows,
            "mismatches": mismatches,
        }, f, indent=2)
    print(f"  Audit report saved: {report_path}\n")

if __name__ == "__main__":
    main()
