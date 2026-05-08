#!/usr/bin/env python3
"""
Palm Beach County Prospect Research & HubSpot Upload
- Source: Google Places API (New) — Text Search
- Targets: roofing, restoration, HVAC, plumbing, RE agents, property mgmt, contractors
- Focuses on small/mid firms in Palm Beach County (owner-direct, no gatekeepers)
- Deduplicates against HubSpot before uploading
- Uploads company + contact, creates review task for Duncan
- Goal: 25 new contacts per daily run
"""

import json
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE = Path("/Users/victoria/.openclaw/workspace")
STATE_FILE = WORKSPACE / "crm" / ".prospect_state.json"
LOG_PATH = WORKSPACE / "crm" / "prospect_palm_beach.log"
DAILY_TARGET = 25

# API key loaded from config file — not hardcoded here
def get_google_key():
    cfg = WORKSPACE / "config" / ".services-config.txt"
    if cfg.exists():
        for line in cfg.read_text().splitlines():
            if "API Key:" in line and "AIza" in line:
                return line.split("API Key:")[-1].strip()
    return os.environ.get("GOOGLE_PLACES_API_KEY", "")

GOOGLE_API_KEY = get_google_key()

# Pricing — Google Places API (New), Basic fields
COST_PER_REQUEST = 0.017   # USD
MONTHLY_FREE_CREDIT = 200  # USD
USAGE_LOG = WORKSPACE / "crm" / "api_usage.log"

# Palm Beach County center + radius covers the full county
PBC_LAT = 26.7153
PBC_LNG = -80.0534
SEARCH_RADIUS_M = 40000  # ~25 miles, covers Palm Beach County

SECTOR_TO_HS_INDUSTRY = {
    "Roofing Contractor":       "CONSTRUCTION",
    "Restoration / Remediation":"CONSTRUCTION",
    "HVAC":                     "CONSTRUCTION",
    "Plumbing Contractor":      "CONSTRUCTION",
    "Property Management":      "REAL_ESTATE",
    "Real Estate":              "REAL_ESTATE",
    "General Contractor":       "CONSTRUCTION",
}

# National chains to skip — owner-direct targeting only
CHAIN_KEYWORDS = [
    "home depot", "lowe's", "lowes", "servicemaster", "servpro", "belfor",
    "roto-rooter", "roto rooter", "one hour", "mr. rooter", "mr rooter",
    "comfort systems", "lennox", "carrier", "trane", "keller williams",
    "re/max", "remax", "coldwell", "century 21", "exp realty",
]

SEARCH_QUERIES = [
    ("roofing contractor Palm Beach County FL",        "Roofing Contractor"),
    ("restoration company Palm Beach County FL",       "Restoration / Remediation"),
    ("HVAC company Palm Beach County FL",              "HVAC"),
    ("plumbing company Palm Beach County FL",          "Plumbing Contractor"),
    ("property management Palm Beach County FL",       "Property Management"),
    ("real estate brokerage Palm Beach County FL",     "Real Estate"),
    ("general contractor Palm Beach County FL",        "General Contractor"),
    ("water damage restoration Palm Beach County FL",  "Restoration / Remediation"),
    ("roofing company Boca Raton FL",                  "Roofing Contractor"),
    ("roofing company Wellington FL",                  "Roofing Contractor"),
    ("roofing company West Palm Beach FL",             "Roofing Contractor"),
    ("HVAC service Boca Raton FL",                     "HVAC"),
    ("property manager West Palm Beach FL",            "Property Management"),
    ("insurance restoration contractor FL",            "Restoration / Remediation"),
]


# ---------------------------------------------------------------------------
# Token
# ---------------------------------------------------------------------------

def get_hs_token():
    token = os.environ.get("HUBSPOT_API_KEY", "").strip()
    if token:
        return token
    setup = WORKSPACE / "scripts" / "setup-hubspot-lists.py"
    if setup.exists():
        for line in setup.read_text().splitlines():
            if line.strip().startswith("TOKEN ="):
                return line.split('"')[1]
    sys.exit("ERROR: HUBSPOT_API_KEY not set and fallback not found.")

HS_TOKEN = get_hs_token()


# ---------------------------------------------------------------------------
# HubSpot helpers
# ---------------------------------------------------------------------------

def hs_request(method, path, payload=None, retries=3):
    url = f"https://api.hubapi.com{path}"
    data = json.dumps(payload).encode() if payload else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {HS_TOKEN}")
    req.add_header("Content-Type", "application/json")
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
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
        except Exception:
            time.sleep(1)
    return 0, {"error": "max retries exceeded"}


def company_exists(name):
    status, data = hs_request("POST", "/crm/v3/objects/companies/search", {
        "filterGroups": [{"filters": [
            {"propertyName": "name", "operator": "EQ", "value": name}
        ]}],
        "properties": ["name"],
        "limit": 1
    })
    return status == 200 and bool(data.get("results"))


def create_company(name, city, phone, website, sector):
    import re
    hs_industry = SECTOR_TO_HS_INDUSTRY.get(sector, "CONSTRUCTION")
    props = {
        "name": name,
        "city": city,
        "state": "Florida",
        "country": "United States",
        "industry": hs_industry,
        "description": sector,  # store specific trade label
    }
    if phone:
        props["phone"] = phone
    if website:
        domain = re.sub(r"^https?://", "", website).rstrip("/").split("/")[0]
        if domain and "google" not in domain:
            props["domain"] = domain
    status, data = hs_request("POST", "/crm/v3/objects/companies", {"properties": props})
    return data.get("id") if status in (200, 201) else None


def create_contact(first, last, phone, company_id, city):
    props = {
        "firstname": first,
        "lastname": last,
        "newsletter_category": "service-provider",
        "hs_lead_status": "NEW",
    }
    if phone:
        props["phone"] = phone
    if city:
        props["city"] = city
        props["state"] = "Florida"
    status, data = hs_request("POST", "/crm/v3/objects/contacts", {"properties": props})
    contact_id = data.get("id") if status in (200, 201) else None
    if contact_id and company_id:
        hs_request("PUT",
            f"/crm/v3/objects/contacts/{contact_id}/associations/companies/{company_id}/contact_to_company",
            None)
    return contact_id


def get_owner_id():
    status, data = hs_request("GET", "/crm/v3/owners?limit=10")
    if status == 200 and data.get("results"):
        for owner in data["results"]:
            if "duncan" in owner.get("email", "").lower():
                return owner["id"]
        return data["results"][0]["id"]
    return None


def create_task(contact_id, company_name, city, sector, phone, website, rating, owner_id):
    due_ts = int(datetime.now(timezone.utc).timestamp() * 1000) + 86400000
    details = [
        f"Sector: {sector}",
        f"City: {city}, Palm Beach County FL",
        f"Phone: {phone or 'not listed'}",
        f"Website: {website or 'not listed'}",
        f"Google Rating: {rating or 'n/a'}",
        "",
        "Action: Confirm owner name, personalize first outreach, enroll in drip sequence.",
    ]
    props = {
        "hs_task_subject": f"New prospect: {company_name} [{city}]",
        "hs_task_body": "\n".join(details),
        "hs_task_status": "NOT_STARTED",
        "hs_task_type": "TODO",
        "hs_timestamp": due_ts,
    }
    if owner_id:
        props["hubspot_owner_id"] = owner_id
    status, data = hs_request("POST", "/crm/v3/objects/tasks", {"properties": props})
    task_id = data.get("id") if status in (200, 201) else None
    if task_id and contact_id:
        hs_request("PUT",
            f"/crm/v3/objects/tasks/{task_id}/associations/contacts/{contact_id}/task_to_contact",
            None)
    return task_id


# ---------------------------------------------------------------------------
# Google Places API
# ---------------------------------------------------------------------------

_api_call_count = 0

def places_text_search(query, page_token=None):
    """Text Search (New) — returns up to 20 results per call."""
    global _api_call_count
    url = "https://places.googleapis.com/v1/places:searchText"
    payload = {"textQuery": query}
    if page_token:
        payload["pageToken"] = page_token

    req = urllib.request.Request(url, data=json.dumps(payload).encode(), method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("X-Goog-Api-Key", GOOGLE_API_KEY)
    req.add_header("X-Goog-FieldMask",
        "places.displayName,places.formattedAddress,places.nationalPhoneNumber,"
        "places.websiteUri,places.rating,places.userRatingCount")

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            _api_call_count += 1
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = {}
        try:
            body = json.loads(e.read())
        except Exception:
            pass
        print(f"    Places API error {e.code}: {body.get('error', {}).get('message', '')}")
        return {}
    except Exception as e:
        print(f"    Places API exception: {e}")
        return {}


def extract_city(address):
    """Pull city from formatted address like '123 Main St, Boca Raton, FL 33431, USA'."""
    if not address:
        return "Palm Beach County"
    parts = [p.strip() for p in address.split(",")]
    if len(parts) >= 3:
        return parts[-3]
    return "Palm Beach County"


def is_chain(name):
    """Skip national chains — we want owner-operated businesses only."""
    lower = name.lower()
    return any(kw in lower for kw in CHAIN_KEYWORDS)


# ---------------------------------------------------------------------------
# State management
# ---------------------------------------------------------------------------

def load_state():
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return {"query_idx": 0, "seen": []}


def save_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=2))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def log(msg, lines):
    print(msg)
    lines.append(msg)


def main():
    log_lines = [f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Palm Beach prospect run started"]
    added = skipped_dup = skipped_large = errors = 0

    state = load_state()
    seen_set = set(state.get("seen", []))
    owner_id = get_owner_id()

    queries_tried = 0
    query_idx = state.get("query_idx", 0)

    while added < DAILY_TARGET and queries_tried < len(SEARCH_QUERIES):
        query, sector = SEARCH_QUERIES[query_idx % len(SEARCH_QUERIES)]
        query_idx += 1
        queries_tried += 1

        log(f"  Searching: {query}", log_lines)
        result = places_text_search(query)
        places = result.get("places", [])
        log(f"    → {len(places)} results", log_lines)

        for place in places:
            if added >= DAILY_TARGET:
                break

            name = (place.get("displayName") or {}).get("text", "").strip()
            if not name:
                continue

            norm = name.upper()
            if norm in seen_set:
                skipped_dup += 1
                continue

            # Skip national chains — target owner-operated firms only
            if is_chain(name):
                skipped_large += 1
                seen_set.add(norm)
                continue

            if company_exists(name):
                seen_set.add(norm)
                skipped_dup += 1
                log(f"    SKIP (exists): {name}", log_lines)
                time.sleep(0.1)
                continue

            address = place.get("formattedAddress", "")
            city = extract_city(address)
            phone = place.get("nationalPhoneNumber", "")
            website = place.get("websiteUri", "")
            rating = place.get("rating", "")

            company_id = create_company(name, city, phone, website, sector)
            if not company_id:
                errors += 1
                seen_set.add(norm)
                continue

            # Create a placeholder contact (owner name TBD — task prompts Duncan to confirm)
            contact_id = create_contact("Owner", name, phone, company_id, city)
            create_task(contact_id, name, city, sector, phone, website, rating, owner_id)

            seen_set.add(norm)
            added += 1
            log(f"    ADDED ({added}/{DAILY_TARGET}): {name} [{city}] — {phone or 'no phone'}", log_lines)
            time.sleep(0.15)

        time.sleep(0.5)

    state["query_idx"] = query_idx % len(SEARCH_QUERIES)
    state["seen"] = list(seen_set)[-3000:]
    save_state(state)

    summary = (
        f"  Done: {added} added, {skipped_dup} duplicate/existing, "
        f"{skipped_large} large firms skipped, {errors} errors"
    )
    log(summary, log_lines)

    # --- API usage accounting ---
    today = datetime.now().strftime("%Y-%m-%d")
    daily_cost = round(_api_call_count * COST_PER_REQUEST, 4)

    # Load month-to-date from usage log
    month_key = datetime.now().strftime("%Y-%m")
    mtd_cost = 0.0
    if USAGE_LOG.exists():
        for line in USAGE_LOG.read_text().splitlines():
            if line.startswith(month_key) and "|" in line:
                try:
                    mtd_cost += float(line.split("|")[2].strip().replace("$",""))
                except Exception:
                    pass

    mtd_cost = round(mtd_cost + daily_cost, 4)
    pct_used = round((mtd_cost / MONTHLY_FREE_CREDIT) * 100, 2)
    pct_remaining = round(100 - pct_used, 2)

    usage_line = (
        f"{today} | calls: {_api_call_count} | ${daily_cost:.4f} today | "
        f"${mtd_cost:.4f} MTD | {pct_used}% used | {pct_remaining}% remaining"
    )
    log(f"  Google Places API: {usage_line}", log_lines)

    with open(USAGE_LOG, "a") as f:
        f.write(usage_line + "\n")

    # Append usage note to today's ops-review
    ops_review = WORKSPACE / "ops-review" / f"{today}.md"
    usage_note = (
        f"\n## Google Places API Usage — {today}\n"
        f"- Calls today: {_api_call_count} (${daily_cost:.4f})\n"
        f"- Month-to-date: ${mtd_cost:.4f} of ${MONTHLY_FREE_CREDIT:.0f} free credit "
        f"({pct_used}% used, {pct_remaining}% remaining)\n"
        f"- Prospecting: {added} new contacts added to HubSpot\n"
    )
    with open(ops_review, "a") as f:
        f.write(usage_note)

    log_lines.append(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Run complete\n")

    with open(LOG_PATH, "a") as f:
        f.write("\n".join(log_lines) + "\n")

    return errors == 0


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
