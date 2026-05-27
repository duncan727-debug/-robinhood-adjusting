#!/usr/bin/env python3
"""
Create a Storm Shield deal in HubSpot with the visual + data conventions
that keep SS pipeline items distinct from PA claims work.

Conventions applied automatically:
  - dealname prefixed with 🛡 (shield glyph) — visible on every board card
  - deal_line = "storm_shield" — for filter-based saved views
  - pipeline  = "default" (HubSpot account caps at 1 pipeline)
  - dealstage = appointmentscheduled ("New PM Lead" in SS terms)

Usage (one-off):
  python3 scripts/create_storm_shield_deal.py \
    --name "Castle Group" \
    --company-id 324192xxxxxx \
    --contact-id 490xxxxxxxxx

Usage (batch — when importing the PBC PM CSV later):
  imported elsewhere; reuse create_deal()
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent
SECRETS = (WORKSPACE / "config" / ".secrets").read_text()
TOKEN = re.search(r'HUBSPOT_API_KEY="([^"]+)"', SECRETS).group(1)
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

SHIELD = "\U0001F6E1"   # 🛡  — visual prefix
DEAL_LINE = "storm_shield"
PIPELINE = "default"
STAGE_NEW = "appointmentscheduled"


def hub_request(path: str, body: dict | None = None, method: str = "POST") -> dict:
    req = urllib.request.Request(
        f"https://api.hubapi.com{path}",
        data=json.dumps(body).encode() if body else None,
        headers=HEADERS,
        method=method,
    )
    return json.loads(urllib.request.urlopen(req).read())


def create_deal(firm_name: str, company_id: int | None, contact_id: int | None) -> str:
    props = {
        "dealname": f"{SHIELD} Storm Shield — {firm_name}",
        "dealstage": STAGE_NEW,
        "pipeline": PIPELINE,
        "deal_line": DEAL_LINE,
    }
    deal = hub_request("/crm/v3/objects/deals", {"properties": props})
    deal_id = deal["id"]

    # Associate to company / contact if given
    if company_id:
        urllib.request.urlopen(urllib.request.Request(
            f"https://api.hubapi.com/crm/v3/objects/deals/{deal_id}"
            f"/associations/companies/{company_id}/deal_to_company",
            headers=HEADERS, method="PUT", data=b""))
    if contact_id:
        urllib.request.urlopen(urllib.request.Request(
            f"https://api.hubapi.com/crm/v3/objects/deals/{deal_id}"
            f"/associations/contacts/{contact_id}/deal_to_contact",
            headers=HEADERS, method="PUT", data=b""))
    return deal_id


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True, help="Firm / community name")
    ap.add_argument("--company-id", type=int)
    ap.add_argument("--contact-id", type=int)
    args = ap.parse_args(argv[1:])
    did = create_deal(args.name, args.company_id, args.contact_id)
    print(f"\U0001F6E1  Created Storm Shield deal {did} for {args.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
