#!/usr/bin/env python3
"""
Build the daily contact-form-fallback queue.

Identifies HubSpot companies that:
  - have a website on file
  - have at least one associated contact with hs_lead_status = UNQUALIFIED
    (hard bounce or filtered)
  - have a deal still in early pipeline stages (not yet advanced past Listed
    in Directory, not Wrong Fit, not already Contact Form Submitted)

Writes the queue to crm/contact_form_queue/<YYYY-MM-DD>.csv with one row
per company. The actual form-submission work happens in the openclaw cron
agent run (which uses the browser tool to navigate, fill, submit, and update
HubSpot).

Cap: 15 candidates/day to keep submission load realistic.
"""
from __future__ import annotations

import csv
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent
SECRETS = (WORKSPACE / "config" / ".secrets").read_text()
TOKEN = re.search(r'HUBSPOT_API_KEY="([^"]+)"', SECRETS).group(1)
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

QUEUE_DIR = WORKSPACE / "crm" / "contact_form_queue"
LOG_PATH = WORKSPACE / "scripts" / "contact_form_queue.log"
BLACKLIST_PATH = WORKSPACE / "crm" / "contact_form_blacklist.csv"
DAILY_CAP = 15

EARLY_STAGE_IDS = {
    "appointmentscheduled",      # New Prospect
    "qualifiedtobuy",            # Outreach Sent
    "presentationscheduled",     # Responded
    "3670098632",                # No Response — Circle Back
}
SKIP_STAGE_IDS = {
    "3676569326",   # Wrong Fit
    "3676570348",   # Contact Form Submitted (already attempted)
    "closedwon",    # Active Partner
    "closedlost",   # Declined
}


def log(msg: str) -> None:
    LOG_PATH.parent.mkdir(exist_ok=True)
    with LOG_PATH.open("a") as f:
        f.write(f"[{datetime.now().isoformat(timespec='seconds')}] {msg}\n")
    print(msg)


def hub_post(path: str, body: dict) -> dict:
    req = urllib.request.Request(
        f"https://api.hubapi.com{path}",
        data=json.dumps(body).encode(),
        headers=HEADERS,
        method="POST",
    )
    return json.loads(urllib.request.urlopen(req).read())


def hub_get(path: str) -> dict:
    req = urllib.request.Request(f"https://api.hubapi.com{path}", headers=HEADERS)
    return json.loads(urllib.request.urlopen(req).read())


def fetch_unqualified_contact_company_ids() -> set[int]:
    """Return all company IDs that have at least one UNQUALIFIED contact."""
    company_ids: set[int] = set()
    after = None
    while True:
        body = {
            "filterGroups": [{"filters": [{
                "propertyName": "hs_lead_status",
                "operator": "EQ",
                "value": "UNQUALIFIED",
            }]}],
            "properties": ["hs_lead_status"],
            "limit": 100,
        }
        if after:
            body["after"] = after
        res = hub_post("/crm/v3/objects/contacts/search", body)
        for c in res.get("results", []):
            try:
                assoc = hub_get(
                    f"/crm/v4/objects/contacts/{c['id']}/associations/companies"
                )
                for a in assoc.get("results", []):
                    company_ids.add(int(a["toObjectId"]))
            except urllib.error.HTTPError:
                pass
            time.sleep(0.05)
        nxt = res.get("paging", {}).get("next", {}).get("after")
        if not nxt:
            break
        after = nxt
    return company_ids


def fetch_company(company_id: int) -> dict | None:
    try:
        return hub_get(
            f"/crm/v3/objects/companies/{company_id}"
            "?properties=name,website,domain,phone,city,industry"
        )
    except urllib.error.HTTPError:
        return None


def fetch_company_deals(company_id: int) -> list[dict]:
    try:
        assoc = hub_get(
            f"/crm/v4/objects/companies/{company_id}/associations/deals"
        )
        deal_ids = [a["toObjectId"] for a in assoc.get("results", [])]
    except urllib.error.HTTPError:
        return []
    deals = []
    for did in deal_ids:
        try:
            deals.append(
                hub_get(
                    f"/crm/v3/objects/deals/{did}?properties=dealname,dealstage,pipeline"
                )
            )
        except urllib.error.HTTPError:
            pass
    return deals


def normalize_website(url: str) -> str | None:
    if not url:
        return None
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url.rstrip("/")


def guess_trade(name: str, industry: str | None) -> str:
    """Pick the right trade keyword for the message template."""
    text = f"{name or ''} {industry or ''}".lower()
    rules = [
        (r"plumb", "plumber"),
        (r"roof", "roofer"),
        (r"hvac|air condition|heating|cooling", "HVAC tech"),
        (r"mold", "mold remediation team"),
        (r"water|restoration|mitigation", "restoration crew"),
        (r"property manage|community manage|hoa", "property manager"),
        (r"realt|real estate|broker", "real estate partner"),
        (r"general contractor|construction|remodel|build", "general contractor"),
        (r"attorney|law firm|legal", "insurance attorney"),
        (r"adjuster", "claims professional"),
    ]
    for pat, label in rules:
        if re.search(pat, text):
            return label
    return "trusted local pro"


def load_blacklist() -> set[int]:
    """Companies we've already tried via form and confirmed unreachable."""
    blacklist: set[int] = set()
    if not BLACKLIST_PATH.exists():
        return blacklist
    with BLACKLIST_PATH.open() as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                blacklist.add(int(row["company_id"]))
            except (KeyError, ValueError):
                continue
    return blacklist


def main() -> int:
    today = datetime.now().strftime("%Y-%m-%d")
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    out_path = QUEUE_DIR / f"{today}.csv"

    log(f"=== Build contact-form queue for {today} ===")
    blacklist = load_blacklist()
    log(f"  Loaded {len(blacklist)} companies on do-not-retry blacklist")
    log("Fetching UNQUALIFIED contacts and their companies…")
    company_ids = fetch_unqualified_contact_company_ids()
    company_ids -= blacklist
    log(f"  Found {len(company_ids)} eligible companies after blacklist filter")

    rows = []
    for cid in company_ids:
        co = fetch_company(cid)
        if not co:
            continue
        props = co["properties"]
        website = normalize_website(props.get("website") or props.get("domain"))
        if not website:
            continue
        deals = fetch_company_deals(cid)
        if not deals:
            continue
        # Skip if any deal is in a blocking stage
        if any(d["properties"].get("dealstage") in SKIP_STAGE_IDS for d in deals):
            continue
        # Require at least one deal in an early stage
        early = [d for d in deals if d["properties"].get("dealstage") in EARLY_STAGE_IDS]
        if not early:
            continue
        rows.append({
            "company_id": cid,
            "name": props.get("name") or "",
            "website": website,
            "phone": props.get("phone") or "",
            "city": props.get("city") or "",
            "industry": props.get("industry") or "",
            "trade": guess_trade(props.get("name") or "", props.get("industry")),
            "deal_id": early[0]["id"],
            "deal_stage": early[0]["properties"].get("dealstage"),
        })
        time.sleep(0.05)

    rows = rows[:DAILY_CAP]
    with out_path.open("w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "company_id", "name", "website", "phone", "city",
                "industry", "trade", "deal_id", "deal_stage",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    log(f"  Wrote {len(rows)} candidates to {out_path}")
    log("=== Done ===\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
