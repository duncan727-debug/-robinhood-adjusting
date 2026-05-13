#!/usr/bin/env python3
"""
Enrichment gate — runs after prospect_palm_beach.py, before outreach batches.

Reads crm/.prospect_pending.json, tries to find a real email for each company,
then routes to one of three outcomes:

  Real email scraped  → HubSpot (company + contact, hs_lead_status=NEW)
  Best-guess only     → HubSpot (company + contact, hs_lead_status=OPEN)
  No website / failed → crm/.prospect_recycle.json (retry up to 3 days, then manual flag)

State files (all gitignored):
  crm/.prospect_pending.json   — discovered today, awaiting enrichment
  crm/.prospect_recycle.json   — failed enrichment, queued for retry
  crm/.prospect_uploaded.json  — all-time list of names uploaded (dedup guard)

Cron: runs at 10:00am Mon–Sat, 43 min after prospecting (9:17am).
Outreach batch 2 at 10:30am picks up newly uploaded contacts.
"""

import json
import os
import re
import ssl
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE       = Path("/Users/victoria/.openclaw/workspace")
PENDING_FILE    = WORKSPACE / "crm" / ".prospect_pending.json"
RECYCLE_FILE    = WORKSPACE / "crm" / ".prospect_recycle.json"
UPLOADED_FILE   = WORKSPACE / "crm" / ".prospect_uploaded.json"
LOG_PATH        = WORKSPACE / "crm" / "email_enrichment.log"

MAX_RECYCLE_ATTEMPTS = 3

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
SKIP_EMAIL = re.compile(
    r"noreply|no-reply|donotreply|example\.com|sentry\.|wix\.|squarespace|"
    r"wordpress|godaddy|hubspot|google|facebook|instagram|privacy@|legal@|"
    r"press@|media@|@w3\.org|@schema", re.I
)
PREFER_EMAIL = re.compile(r"^(info|contact|hello|office|admin|service|estimates?|quotes?)@", re.I)
PAGES = ["", "/contact", "/contact-us", "/about", "/about-us", "/get-in-touch"]

SECTOR_TO_HS_INDUSTRY = {
    "Roofing Contractor":        "CONSTRUCTION",
    "Restoration / Remediation": "CONSTRUCTION",
    "HVAC":                      "CONSTRUCTION",
    "Plumbing Contractor":       "CONSTRUCTION",
    "Property Management":       "REAL_ESTATE",
    "Real Estate":               "REAL_ESTATE",
    "General Contractor":        "CONSTRUCTION",
}

ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

# ── credentials ──────────────────────────────────────────────────────────────

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

# ── HubSpot ───────────────────────────────────────────────────────────────────

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
            if e.code == 429:
                time.sleep(2 ** attempt)
                continue
            return e.code, {}
    return 0, {}

def company_exists(name):
    status, data = hs("POST", "/crm/v3/objects/companies/search", {
        "filterGroups": [{"filters": [
            {"propertyName": "name", "operator": "EQ", "value": name}
        ]}],
        "properties": ["name"], "limit": 1,
    })
    return status == 200 and bool(data.get("results"))

def create_company(prospect):
    name   = prospect["name"]
    sector = prospect["sector"]
    domain = ""
    if prospect.get("website"):
        domain = re.sub(r"^https?://", "", prospect["website"]).rstrip("/").split("/")[0]
        domain = re.sub(r"^www\.", "", domain, flags=re.IGNORECASE)
        if "google" in domain:
            domain = ""
    props = {
        "name":        name,
        "city":        prospect.get("city", "Palm Beach County"),
        "state":       "Florida",
        "country":     "United States",
        "industry":    SECTOR_TO_HS_INDUSTRY.get(sector, "CONSTRUCTION"),
        "description": sector,
    }
    if prospect.get("phone"):
        props["phone"] = prospect["phone"]
    if domain:
        props["domain"] = domain
    status, data = hs("POST", "/crm/v3/objects/companies", {"properties": props})
    return data.get("id") if status in (200, 201) else None

def create_contact(prospect, company_id, email, lead_status):
    props = {
        "firstname":           "Owner",
        "lastname":            prospect["name"],
        "newsletter_category": "service-provider",
        "hs_lead_status":      lead_status,
    }
    if email:
        props["email"] = email
    if prospect.get("phone"):
        props["phone"] = prospect["phone"]
    if prospect.get("city"):
        props["city"]  = prospect["city"]
        props["state"] = "Florida"
    status, data = hs("POST", "/crm/v3/objects/contacts", {"properties": props})
    contact_id = data.get("id") if status in (200, 201) else None
    if contact_id and company_id:
        hs("PUT",
           f"/crm/v3/objects/contacts/{contact_id}/associations/companies/{company_id}/contact_to_company",
           None)
    return contact_id

def get_owner_id():
    status, data = hs("GET", "/crm/v3/owners?limit=10")
    if status == 200 and data.get("results"):
        for o in data["results"]:
            if "duncan" in o.get("email", "").lower():
                return o["id"]
        return data["results"][0]["id"]
    return None

def create_task(contact_id, prospect, email, lead_status, owner_id):
    due_ts = int(datetime.now(timezone.utc).timestamp() * 1000) + 86400000
    status_note = "Confirmed email scraped from website." if lead_status == "NEW" \
                  else "Best-guess email (info@domain) — verify before sending."
    details = [
        f"Sector: {prospect['sector']}",
        f"City: {prospect.get('city','Palm Beach County')}, FL",
        f"Phone: {prospect.get('phone') or 'not listed'}",
        f"Website: {prospect.get('website') or 'not listed'}",
        f"Email: {email or 'not found'}",
        f"Google Rating: {prospect.get('rating') or 'n/a'}",
        f"Email status: {status_note}",
        "",
        "Action: Review email, personalize outreach template, send.",
    ]
    props = {
        "hs_task_subject": f"Outreach ready: {prospect['name']} [{prospect.get('city','')}]",
        "hs_task_body":    "\n".join(details),
        "hs_task_status":  "NOT_STARTED",
        "hs_task_type":    "TODO",
        "hs_timestamp":    due_ts,
    }
    if owner_id:
        props["hubspot_owner_id"] = owner_id
    status, data = hs("POST", "/crm/v3/objects/tasks", {"properties": props})
    task_id = data.get("id") if status in (200, 201) else None
    if task_id and contact_id:
        hs("PUT",
           f"/crm/v3/objects/tasks/{task_id}/associations/contacts/{contact_id}/task_to_contact",
           None)

# ── email scraping ────────────────────────────────────────────────────────────

def fetch_page(url, timeout=8):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout, context=ssl_ctx) as r:
            return r.read().decode("utf-8", errors="ignore")
    except Exception:
        return ""

def scrape_email(raw_url):
    """Returns (email, status) where status is 'scraped', 'best-guess', or None."""
    if not raw_url:
        return None, None
    domain = re.sub(r"^https?://", "", raw_url).split("/")[0].strip()
    domain = re.sub(r"^www\.", "", domain, flags=re.IGNORECASE)
    if not domain or "." not in domain or "google" in domain:
        return None, None
    base = f"https://{domain}"
    for page in PAGES:
        html = fetch_page(base + page)
        emails = [
            m.group(0).lower() for m in EMAIL_RE.finditer(html)
            if not SKIP_EMAIL.search(m.group(0))
        ]
        domain_emails = [e for e in emails if domain in e]
        preferred     = [e for e in domain_emails if PREFER_EMAIL.match(e)]
        if preferred:
            return preferred[0], "scraped"
        if domain_emails:
            return sorted(domain_emails)[0], "scraped"
        time.sleep(0.3)
    # No real email found — return best-guess
    return f"info@{domain}", "best-guess"

# ── state helpers ─────────────────────────────────────────────────────────────

def load_json(path):
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            pass
    return []

def save_json(path, data):
    path.write_text(json.dumps(data, indent=2))

# ── logging ───────────────────────────────────────────────────────────────────

def log(msg):
    ts   = datetime.now().strftime("%Y-%m-%d %H:%M")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_PATH, "a") as f:
        f.write(line + "\n")

# ── main ──────────────────────────────────────────────────────────────────────

def main():
    log("=== enrich_before_upload start ===")

    pending  = load_json(PENDING_FILE)
    recycle  = load_json(RECYCLE_FILE)
    uploaded = set(load_json(UPLOADED_FILE))
    owner_id = get_owner_id()

    ready_count = recycle_count = skip_count = manual_flag = 0

    # Process today's pending queue
    remaining_pending = []
    for prospect in pending:
        name = prospect["name"]
        if name in uploaded or company_exists(name):
            log(f"  SKIP (already in HubSpot): {name}")
            uploaded.add(name)
            skip_count += 1
            continue

        email, email_status = scrape_email(prospect.get("website", ""))

        if email_status == "scraped":
            lead_status = "NEW"
        elif email_status == "best-guess":
            lead_status = "OPEN"
        else:
            # No website or scrape failed — send to recycle
            prospect["attempts"] = prospect.get("attempts", 0) + 1
            if prospect["attempts"] >= MAX_RECYCLE_ATTEMPTS:
                log(f"  FLAG (manual lookup needed): {name} — {MAX_RECYCLE_ATTEMPTS} attempts exhausted")
                manual_flag += 1
                # Still add to HubSpot but mark for review
                lead_status = "OPEN"
                email = None
            else:
                log(f"  RECYCLE (attempt {prospect['attempts']}): {name} — no email found")
                recycle.append(prospect)
                recycle_count += 1
                continue

        company_id = create_company(prospect)
        if not company_id:
            log(f"  ERROR: Could not create company for {name}")
            remaining_pending.append(prospect)
            continue

        contact_id = create_contact(prospect, company_id, email, lead_status)
        create_task(contact_id, prospect, email, lead_status, owner_id)
        uploaded.add(name)
        ready_count += 1
        flag = "⚑ MANUAL" if manual_flag and email is None else ""
        log(f"  ✓ {lead_status:4s} → HubSpot: {name} | {email or 'no email'} {flag}")
        time.sleep(0.2)

    # Process recycle queue (retry previous failures)
    still_recycling = []
    for prospect in recycle:
        name = prospect["name"]
        if name in uploaded:
            continue

        email, email_status = scrape_email(prospect.get("website", ""))

        if email_status in ("scraped", "best-guess"):
            lead_status = "NEW" if email_status == "scraped" else "OPEN"
            company_id  = create_company(prospect)
            if company_id:
                contact_id = create_contact(prospect, company_id, email, lead_status)
                create_task(contact_id, prospect, email, lead_status, owner_id)
                uploaded.add(name)
                ready_count += 1
                log(f"  ✓ RECYCLED → HubSpot: {name} | {email}")
                time.sleep(0.2)
            else:
                still_recycling.append(prospect)
        else:
            prospect["attempts"] = prospect.get("attempts", 0) + 1
            if prospect["attempts"] >= MAX_RECYCLE_ATTEMPTS:
                log(f"  FLAG (manual lookup needed): {name}")
                manual_flag += 1
                # Upload anyway with no email so Duncan can see it
                company_id = create_company(prospect)
                if company_id:
                    create_contact(prospect, company_id, None, "OPEN")
                    create_task(contact_id=None, prospect=prospect, email=None,
                                lead_status="OPEN", owner_id=owner_id)
                    uploaded.add(name)
            else:
                still_recycling.append(prospect)

    # Persist updated state
    save_json(PENDING_FILE, remaining_pending)
    save_json(RECYCLE_FILE, still_recycling)
    save_json(UPLOADED_FILE, sorted(uploaded))

    log(f"=== Done ===")
    log(f"  Uploaded to HubSpot : {ready_count}")
    log(f"  Recycled (retry tmrw): {recycle_count}")
    log(f"  Skipped (duplicates) : {skip_count}")
    log(f"  Flagged manual lookup: {manual_flag}")

    # Append summary to today's ops-review
    today    = datetime.now().strftime("%Y-%m-%d")
    ops_file = WORKSPACE / "ops-review" / f"{today}.md"
    with open(ops_file, "a") as f:
        f.write(
            f"\n## Email Enrichment Gate — {today}\n"
            f"- Uploaded to HubSpot: {ready_count} (ready to email)\n"
            f"- Recycled for retry: {recycle_count}\n"
            f"- Manual lookup needed: {manual_flag}\n"
        )


if __name__ == "__main__":
    main()
