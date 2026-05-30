#!/usr/bin/env python3
"""
Enrichment gate — runs after prospect_palm_beach.py, before outreach batches.

Reads crm/.prospect_pending.json, tries to find a real email for each company,
then routes to one of these outcomes:

  Real email scraped + verified  → HubSpot (company + contact, hs_lead_status=NEW)
  No web email → FB/IG fallback  → if found + verified, same upload path
  No email anywhere, but co valid → HubSpot phone-only (lead_status=PHONE_ONLY, no email)
  Verification rejected           → crm/review_queue/rejected_YYYY-MM-DD.csv
  No website / failed             → crm/.prospect_recycle.json (retry up to 3 days)

Rationale (2026-05-29 update):
  * Best-guess `info@domain` generation REMOVED. Per Duncan, franchise sites
    (Allstate, Brightway, etc.) route info@ to corporate, not the local
    operator, so the guess pattern is a bounce engine. We now either find a
    real email or admit we don't have one.
  * verify_prospect.classify() runs as a gate before any HubSpot upload (MX
    record + Sunbiz check + email source validation). Anything that fails
    verification is parked in review queue, not uploaded.
  * FB + IG profile scraping is the new fallback when the company website
    yields no email — covers franchise agents whose corporate site hides
    them but whose own social profiles show their direct address.

State files (all gitignored):
  crm/.prospect_pending.json   — discovered today, awaiting enrichment
  crm/.prospect_recycle.json   — failed enrichment, queued for retry
  crm/.prospect_uploaded.json  — all-time list of names uploaded (dedup guard)
  crm/review_queue/            — weekly CSV files of best-guesses for manual review

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

sys.path.insert(0, str(Path(__file__).parent))
from verify_prospect import classify as verify_classify  # noqa: E402
from find_social_email import find_email_via_social      # noqa: E402

WORKSPACE       = Path("/Users/victoria/.openclaw/workspace")
PENDING_FILE    = WORKSPACE / "crm" / ".prospect_pending.json"
RECYCLE_FILE    = WORKSPACE / "crm" / ".prospect_recycle.json"
UPLOADED_FILE   = WORKSPACE / "crm" / ".prospect_uploaded.json"
LOG_PATH        = WORKSPACE / "crm" / "email_enrichment.log"
REVIEW_DIR      = WORKSPACE / "crm" / "review_queue"

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

def create_deal(prospect, company_id, contact_id):
    """Spawn a deal at 'New Prospect' stage so the pipeline reflects every outbound contact.
    send_outreach.py advances to 'Outreach Sent' on send; imap_bridge.py advances to
    'Responded' on reply; manual moves take it to 'Listed in Directory' onward."""
    props = {
        "dealname":  f"{prospect['name']} — Outreach",
        "dealstage": "appointmentscheduled",   # New Prospect
        "pipeline":  "default",
        "deal_line": "public_adjusting",       # Storm Shield deals are created separately
    }
    status, data = hs("POST", "/crm/v3/objects/deals", {"properties": props})
    deal_id = data.get("id") if status in (200, 201) else None
    if not deal_id:
        return None
    if company_id:
        hs("PUT", f"/crm/v4/objects/deals/{deal_id}/associations/default/companies/{company_id}", None)
    if contact_id:
        hs("PUT", f"/crm/v4/objects/deals/{deal_id}/associations/default/contacts/{contact_id}", None)
    return deal_id

# ── email scraping ────────────────────────────────────────────────────────────

def fetch_page(url, timeout=8):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout, context=ssl_ctx) as r:
            return r.read().decode("utf-8", errors="ignore")
    except Exception:
        return ""

def scrape_email(raw_url):
    """Returns (email, status) where status is 'scraped' or None.
    No more 'best-guess' info@domain fallback — that was a bounce engine."""
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
    return None, None


def find_real_email(prospect):
    """Full discovery cascade: website scrape → FB/IG social fallback.
    Returns (email, source) where source ∈ {"scraped", "facebook", "instagram"} or (None, None)."""
    email, status = scrape_email(prospect.get("website", ""))
    if status == "scraped":
        return email, "scraped"
    # Web scrape failed — try social profiles
    email, source = find_email_via_social(prospect.get("name", ""), prospect.get("website"))
    if email:
        return email, source
    return None, None


def verify_email_is_real(name, email, source):
    """Run MX + Sunbiz + source gate before uploading. Returns True if safe to upload."""
    row = {"name": name, "company": name, "email": email, "source": source}
    result = verify_classify(row)
    return result.get("verdict") == "verified", result.get("reasons", [])

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

    ready_count = social_count = rejected_count = recycle_count = skip_count = phone_only_count = 0
    rejected_rows = []  # verification failures for Duncan to review
    phone_only_rows = []  # no email found at all but company is real — call list

    def _upload(prospect, email, source):
        nonlocal ready_count, social_count, rejected_count
        ok, reasons = verify_email_is_real(prospect["name"], email, source)
        if not ok:
            rejected_count += 1
            log(f"  REJECT (verify failed: {','.join(reasons)}): {prospect['name']} | {email}")
            rejected_rows.append({
                "name": prospect["name"], "sector": prospect.get("sector",""),
                "city": prospect.get("city",""), "phone": prospect.get("phone",""),
                "website": prospect.get("website",""), "email_attempted": email,
                "source": source, "reject_reasons": ";".join(reasons),
            })
            uploaded.add(prospect["name"])
            return False
        company_id = create_company(prospect)
        if not company_id:
            log(f"  ERROR: Could not create company for {prospect['name']}")
            return False
        contact_id = create_contact(prospect, company_id, email, "NEW")
        deal_id    = create_deal(prospect, company_id, contact_id)
        uploaded.add(prospect["name"])
        ready_count += 1
        if source != "scraped":
            social_count += 1
        log(f"  ✓ NEW → HubSpot ({source}): {prospect['name']} | {email} | deal={deal_id}")
        time.sleep(0.2)
        return True

    # Process today's pending queue
    remaining_pending = []
    for prospect in pending:
        name = prospect["name"]
        if name in uploaded or company_exists(name):
            log(f"  SKIP (already in HubSpot): {name}")
            uploaded.add(name)
            skip_count += 1
            continue

        email, source = find_real_email(prospect)

        if email:
            _upload(prospect, email, source)
            continue

        # No email anywhere — recycle for retry; after MAX attempts, park in phone-only list
        prospect["attempts"] = prospect.get("attempts", 0) + 1
        if prospect["attempts"] >= MAX_RECYCLE_ATTEMPTS:
            log(f"  PHONE-ONLY (no email found after {MAX_RECYCLE_ATTEMPTS} attempts): {name}")
            phone_only_rows.append({
                "name": name, "sector": prospect.get("sector",""),
                "city": prospect.get("city",""), "phone": prospect.get("phone",""),
                "website": prospect.get("website",""), "rating": prospect.get("rating",""),
            })
            uploaded.add(name)
            phone_only_count += 1
        else:
            log(f"  RECYCLE (attempt {prospect['attempts']}): {name} — no email found")
            recycle.append(prospect)
            recycle_count += 1

    # Process recycle queue (retry previous failures)
    still_recycling = []
    for prospect in recycle:
        name = prospect["name"]
        if name in uploaded:
            continue

        email, source = find_real_email(prospect)
        if email:
            _upload(prospect, email, source)
            continue

        prospect["attempts"] = prospect.get("attempts", 0) + 1
        if prospect["attempts"] >= MAX_RECYCLE_ATTEMPTS:
            log(f"  PHONE-ONLY (recycled, still no email): {name}")
            phone_only_rows.append({
                "name": name, "sector": prospect.get("sector",""),
                "city": prospect.get("city",""), "phone": prospect.get("phone",""),
                "website": prospect.get("website",""), "rating": prospect.get("rating",""),
            })
            uploaded.add(name)
            phone_only_count += 1
        else:
            still_recycling.append(prospect)

    # Persist updated state
    save_json(PENDING_FILE, remaining_pending)
    save_json(RECYCLE_FILE, still_recycling)
    save_json(UPLOADED_FILE, sorted(uploaded))

    today = datetime.now().strftime("%Y-%m-%d")
    if rejected_rows or phone_only_rows:
        import csv as _csv
        REVIEW_DIR.mkdir(parents=True, exist_ok=True)
        if rejected_rows:
            p = REVIEW_DIR / f"rejected_{today}.csv"
            with p.open("w", newline="") as f:
                w = _csv.DictWriter(f, fieldnames=["name","sector","city","phone","website","email_attempted","source","reject_reasons"])
                w.writeheader()
                w.writerows(rejected_rows)
            log(f"  Rejected (failed verify): wrote {len(rejected_rows)} → {p}")
        if phone_only_rows:
            p = REVIEW_DIR / f"phone_only_{today}.csv"
            with p.open("w", newline="") as f:
                w = _csv.DictWriter(f, fieldnames=["name","sector","city","phone","website","rating"])
                w.writeheader()
                w.writerows(phone_only_rows)
            log(f"  Phone-only call list: wrote {len(phone_only_rows)} → {p}")

    log(f"=== Done ===")
    log(f"  Uploaded to HubSpot (NEW, verified): {ready_count}  (of which {social_count} via FB/IG fallback)")
    log(f"  Rejected by verify gate: {rejected_count}")
    log(f"  Phone-only (no email found): {phone_only_count}")
    log(f"  Recycled (retry tomorrow): {recycle_count}")
    log(f"  Skipped (duplicates): {skip_count}")

    # Append summary to today's ops-review
    ops_file = WORKSPACE / "ops-review" / f"{today}.md"
    if ops_file.exists():
        with open(ops_file, "a") as f:
            f.write(
                f"\n## Email Enrichment Gate — {today}\n"
                f"- Uploaded to HubSpot (verified real email): {ready_count}\n"
                f"- Found via FB/IG social fallback: {social_count}\n"
                f"- Rejected by verify gate (MX/Sunbiz/source): {rejected_count}\n"
                f"- Phone-only call list: {phone_only_count}\n"
                f"- Recycled for retry: {recycle_count}\n"
            )


if __name__ == "__main__":
    main()
