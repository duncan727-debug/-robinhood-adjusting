#!/usr/bin/env python3
"""
Recompute hs_lead_status for a contact based on actual engagement history.

Use case (Fix #1, KLR autopsy 2026-05-22): when an inbound reply lands at an
alias that wasn't yet on the HubSpot contact, the IMAP bridge can't auto-match.
We later add the alias by hand — but the contact still shows UNQUALIFIED, and
downstream cron jobs (contact-form fallback) act on stale status.

This script reads the contact's Note engagements and:
  - if a "Reply received" note exists in the last 90 days, flips
    hs_lead_status off UNQUALIFIED to CONNECTED
  - advances the most recent early-stage deal to presentationscheduled
    (Responded) so the pipeline matches reality

Usage:
  python3 scripts/recompute_lead_status.py <contact_id> [<contact_id> ...]
"""
from __future__ import annotations

import json
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

EARLY_STAGE_IDS = {
    "appointmentscheduled",
    "qualifiedtobuy",
    "3670098632",  # No Response — Circle Back
    "closedlost",  # Declined (we'll reopen if a reply arrived)
}
RESPONDED_STAGE = "presentationscheduled"


def hub_get(path: str) -> dict:
    req = urllib.request.Request(f"https://api.hubapi.com{path}", headers=HEADERS)
    return json.loads(urllib.request.urlopen(req).read())


def hub_patch(path: str, body: dict) -> int:
    req = urllib.request.Request(
        f"https://api.hubapi.com{path}",
        data=json.dumps(body).encode(),
        headers=HEADERS,
        method="PATCH",
    )
    try:
        urllib.request.urlopen(req).read()
        return 200
    except urllib.error.HTTPError as e:
        return e.code


def find_recent_reply(contact_id: int, days: int = 90) -> bool:
    cutoff_ms = int((time.time() - days * 86400) * 1000)
    try:
        assoc = hub_get(f"/crm/v4/objects/contacts/{contact_id}/associations/notes")
    except urllib.error.HTTPError:
        return False
    for a in assoc.get("results", []):
        try:
            note = hub_get(
                f"/crm/v3/objects/notes/{a['toObjectId']}"
                "?properties=hs_note_body,hs_timestamp"
            )
        except urllib.error.HTTPError:
            continue
        props = note.get("properties") or {}
        ts_raw = props.get("hs_timestamp") or "0"
        try:
            ts_ms = int(datetime.fromisoformat(
                ts_raw.replace("Z", "+00:00")
            ).timestamp() * 1000) if not ts_raw.isdigit() else int(ts_raw)
        except (ValueError, AttributeError):
            ts_ms = 0
        if ts_ms < cutoff_ms:
            continue
        if "reply received" in (props.get("hs_note_body") or "").lower():
            return True
    return False


def advance_company_deal(contact_id: int) -> str | None:
    try:
        companies = hub_get(
            f"/crm/v4/objects/contacts/{contact_id}/associations/companies"
        ).get("results", [])
    except urllib.error.HTTPError:
        return None
    for c in companies:
        co_id = c["toObjectId"]
        try:
            deals = hub_get(
                f"/crm/v4/objects/companies/{co_id}/associations/deals"
            ).get("results", [])
        except urllib.error.HTTPError:
            continue
        for d in deals:
            did = d["toObjectId"]
            try:
                deal = hub_get(
                    f"/crm/v3/objects/deals/{did}?properties=dealname,dealstage"
                )
            except urllib.error.HTTPError:
                continue
            stage = deal["properties"].get("dealstage")
            if stage in EARLY_STAGE_IDS and stage != RESPONDED_STAGE:
                code = hub_patch(
                    f"/crm/v3/objects/deals/{did}",
                    {"properties": {"dealstage": RESPONDED_STAGE}},
                )
                if code == 200:
                    return deal["properties"].get("dealname")
    return None


def recompute(contact_id: int) -> None:
    contact = hub_get(
        f"/crm/v3/objects/contacts/{contact_id}"
        "?properties=email,firstname,lastname,hs_lead_status"
    )
    props = contact["properties"]
    cur_status = props.get("hs_lead_status")
    label = props.get("email") or f"{props.get('firstname','')} {props.get('lastname','')}".strip() or contact_id
    if not find_recent_reply(contact_id):
        print(f"  ·  {label} (cid {contact_id}) — no recent inbound reply, leaving status={cur_status}")
        return
    if cur_status == "CONNECTED":
        print(f"  ·  {label} (cid {contact_id}) — already CONNECTED, checking deal stage…")
    else:
        code = hub_patch(
            f"/crm/v3/objects/contacts/{contact_id}",
            {"properties": {"hs_lead_status": "CONNECTED"}},
        )
        if code == 200:
            print(f"  ✓  {label} (cid {contact_id}) — lead_status {cur_status} → CONNECTED")
        else:
            print(f"  ✗  {label} (cid {contact_id}) — lead_status patch failed ({code})")
            return
    advanced = advance_company_deal(contact_id)
    if advanced:
        print(f"      deal '{advanced}' → Responded")


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: recompute_lead_status.py <contact_id> [<contact_id> ...]", file=sys.stderr)
        return 2
    for arg in argv[1:]:
        try:
            recompute(int(arg))
        except (ValueError, urllib.error.HTTPError) as e:
            print(f"  ✗ {arg}: {e}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
