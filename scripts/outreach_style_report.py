#!/usr/bin/env python3
"""Report reply rate by outreach style.

Joins scripts/outreach_style_log.csv with HubSpot contact lead status to
classify each row as replied / bounced / no-response, then prints reply rate
per style. A 'reply' = hs_lead_status in {CONNECTED, OPEN, OPEN_DEAL} OR an
associated deal at presentationscheduled (Responded) or beyond.

Usage: python3 scripts/outreach_style_report.py
"""
import csv, json, os, urllib.request
from pathlib import Path
from collections import defaultdict

for line in Path("config/.secrets").read_text().splitlines():
    if line.startswith("export "): line = line[7:]
    if "=" in line:
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
TOK = os.environ["HUBSPOT_API_KEY"]

POSITIVE_STAGES = {
    "presentationscheduled", "decisionmakerboughtin", "contractsent", "closedwon",
    "3671479994", "3671664335", "3671479995", "3671664336", "3671664337",
}


def api(path):
    req = urllib.request.Request(f"https://api.hubapi.com{path}",
        headers={"Authorization": f"Bearer {TOK}"})
    return json.load(urllib.request.urlopen(req))


def contact_replied(cid):
    if not cid:
        return False
    try:
        c = api(f"/crm/v3/objects/contacts/{cid}?properties=hs_lead_status")
        if c["properties"].get("hs_lead_status") == "CONNECTED":
            return True
        d = api(f"/crm/v4/objects/contacts/{cid}/associations/deals")
        for a in d.get("results", []):
            did = a["toObjectId"]
            de = api(f"/crm/v3/objects/deals/{did}?properties=dealstage")
            if de["properties"].get("dealstage") in POSITIVE_STAGES:
                return True
    except Exception:
        pass
    return False


def main():
    rows = list(csv.DictReader(open("scripts/outreach_style_log.csv")))
    by_style = defaultdict(lambda: {"sent": 0, "bounced": 0, "delivered": 0, "replied": 0})
    for r in rows:
        s = r["style"]
        by_style[s]["sent"] += 1
        if r.get("bounced"):
            by_style[s]["bounced"] += 1
            continue
        by_style[s]["delivered"] += 1
        if contact_replied(r["contact_id"]):
            by_style[s]["replied"] += 1

    print(f"{'Style':18s} {'Sent':>5s} {'Bounced':>8s} {'Deliv':>6s} {'Replied':>8s} {'Reply %':>9s}")
    print("-" * 60)
    for style, m in sorted(by_style.items(), key=lambda x: -x[1]["delivered"]):
        rate = f"{(100*m['replied']/m['delivered']):.0f}%" if m["delivered"] else "n/a"
        print(f"{style:18s} {m['sent']:>5d} {m['bounced']:>8d} {m['delivered']:>6d} {m['replied']:>8d} {rate:>9s}")


if __name__ == "__main__":
    main()
