#!/usr/bin/env python3
"""
Restore: my prior cleanup wrongly reverted 39 prospect-uploader deals back to
'New Prospect'. The outreach automation (send_outreach.py) actually sent real
emails to all 39 — they belong in 'Outreach Sent'. This script moves them back.
"""
import json
import os
import re
import sys
import time
import urllib.request
import urllib.error
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
                time.sleep(2 ** attempt); continue
            try: return e.code, json.loads(raw)
            except: return e.code, {"raw": raw.decode(errors="replace")}
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            if attempt < 4: time.sleep(2 ** attempt); continue
            return 0, {"error": str(e)}
    return 0, {}

# Deal IDs to restore (from cleanup_deal_pipeline.py Step 3 output)
DEAL_IDS = [
    ("324335061751", "EDS Air Conditioning & Plumbing"),
    ("324434334399", "Plumbtastic Plumbing"),
    ("324437919473", "North County Plumbing, Inc."),
    ("324352184031", "Top Notch Property Watch"),
    ("324340133573", "GRS Community Management"),
    ("324436129511", "Palm Beach Estate Management"),
    ("324409554662", "Craft Realty"),
    ("324332847861", "Island Construction & Design"),
    ("324332847863", "House Call Construction"),
    ("324340133577", "TXB Roofing"),
    ("324350226108", "Castle Group"),
    ("324437919475", "All Insurance Restoration"),
    ("324336567004", "Coastal Roofing of South Florida"),
    ("324378342085", "Neal Roofing & Waterproofing"),
    ("324366002915", "Altec Roofing"),
    ("324355726015", "Complete Roofing Solutions Inc."),
    ("324341940968", "Elite Roofing Inc"),
    ("324407797436", "Ace Pro Roofing"),
    ("324409554666", "Evans Roofing of the Palm Beaches"),
    ("324434334408", "Rainbow Roofing LLC"),
    ("324387378904", "Top Roofer West Palm Beach"),
    ("324358926052", "Leon Roofing Contractor"),
    ("324358926054", "A1 Pro Roofing, LLC"),
    ("324340133585", "Roofing Systems Of Florida"),
    ("324341940978", "SuperClean Restoration"),
    ("324396259023", "Thunder Restoration"),
    ("324407797449", "Paul Davis Restoration"),
    ("324355726023", "Titan Restoration Construction"),
    ("324437920458", "Coastal Restoration Specialists"),
    ("324341941946", "Rescue Clean 911"),
    ("324350226126", "Ewing & Ewing Air Conditioning"),
    ("324413153999", "Hopkins Air Conditioning"),
    ("324439719658", "First Degree Air Conditioning"),
    ("324436130498", "Sansone AC"),
    ("324413154000", "Shoreline Air Conditioning"),
    ("324437920462", "Hilling Air Conditioning"),
    ("324382216895", "Swift Air Conditioning"),
    ("324411362017", "A.R. Williams Air Conditioning"),
    ("324366002930", "Gulfstream Cooling"),
]

def main():
    print(f"\nRestoring {len(DEAL_IDS)} deals to 'Outreach Sent' (qualifiedtobuy)\n")
    ok_count = err_count = 0
    for did, company in DEAL_IDS:
        status, _ = hs("PATCH", f"/crm/v3/objects/deals/{did}",
                       {"properties": {"dealstage": "qualifiedtobuy"}})
        if status in (200, 201):
            print(f"  ✓ {company[:50]:50s}  {did}")
            ok_count += 1
        else:
            print(f"  ✗ {company[:50]:50s}  {did}  status={status}")
            err_count += 1
        time.sleep(0.15)
    print(f"\nRestored: {ok_count}  Errors: {err_count}\n")

if __name__ == "__main__":
    main()
