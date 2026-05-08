#!/usr/bin/env python3
"""
Enrich HubSpot contact emails from company website fields.
1. Find contacts missing email whose company has a website
2. Scrape homepage + /contact + /about for real email addresses
3. If found: write to HubSpot, mark hs_lead_status=NEW
4. If not found: write info@domain as best-guess, mark hs_lead_status=OPEN (needs review)
5. Log everything — Duncan reviews OPEN ones tomorrow
"""

import json
import re
import ssl
import time
import urllib.request
import urllib.error
from pathlib import Path

WORKSPACE = Path("/Users/victoria/.openclaw/workspace")
LOG_PATH = WORKSPACE / "crm" / "email_enrichment.log"

TOKEN_RE = re.compile(r'TOKEN\s*=\s*"([^"]+)"')
token = TOKEN_RE.search((WORKSPACE / "scripts" / "setup-hubspot-lists.py").read_text()).group(1)

EMAIL_RE = re.compile(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}')
SKIP_EMAIL_PATTERNS = re.compile(
    r'noreply|no-reply|donotreply|example\.com|sentry\.|wix\.|squarespace|'
    r'wordpress|godaddy|hubspot|google|facebook|instagram|privacy@|legal@|'
    r'press@|media@|@w3\.org|@schema', re.I
)
PREFER_PATTERNS = re.compile(r'^(info|contact|hello|office|admin|service|estimates?|quotes?)@', re.I)

PAGES_TO_TRY = ["", "/contact", "/contact-us", "/about", "/about-us", "/get-in-touch"]

ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE


def hs(method, path, body=None):
    url = f"https://api.hubapi.com{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(2 ** attempt)
                continue
            return e.code, {}
    return 0, {}


def fetch_page(url, timeout=8):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout, context=ssl_ctx) as r:
            return r.read().decode("utf-8", errors="ignore")
    except Exception:
        return ""


def extract_emails(html, domain):
    found = set()
    for m in EMAIL_RE.finditer(html):
        e = m.group(0).lower()
        if SKIP_EMAIL_PATTERNS.search(e):
            continue
        found.add(e)
    # Prefer emails matching the company domain
    domain_emails = [e for e in found if domain in e]
    preferred = [e for e in domain_emails if PREFER_PATTERNS.match(e)]
    if preferred:
        return preferred[0], "scraped"
    if domain_emails:
        return sorted(domain_emails)[0], "scraped"
    # Any non-domain email as last resort
    preferred_any = [e for e in found if PREFER_PATTERNS.match(e)]
    if preferred_any:
        return preferred_any[0], "scraped"
    return None, None


def scrape_website(raw_url):
    if not raw_url:
        return None, None
    domain = raw_url.lower().replace("https://", "").replace("http://", "").split("/")[0].strip()
    if not domain or "." not in domain:
        return None, None
    base = f"https://{domain}"
    for page in PAGES_TO_TRY:
        html = fetch_page(base + page)
        email, source = extract_emails(html, domain)
        if email:
            return email, domain
        time.sleep(0.3)
    return None, domain


def log(msg):
    print(msg)
    with open(LOG_PATH, "a") as f:
        f.write(msg + "\n")


def main():
    log("=== email enrichment from websites start ===")

    # Get contacts missing email, not unqualified
    contacts = []
    after = None
    while True:
        payload = {
            "filterGroups": [{"filters": [
                {"propertyName": "email", "operator": "NOT_HAS_PROPERTY"},
                {"propertyName": "hs_lead_status", "operator": "NEQ", "value": "UNQUALIFIED"},
            ]}],
            "properties": ["firstname", "lastname", "phone", "hs_lead_status"],
            "limit": 100,
        }
        if after:
            payload["after"] = after
        _, data = hs("POST", "/crm/v3/objects/contacts/search", payload)
        contacts.extend(data.get("results", []))
        after = data.get("paging", {}).get("next", {}).get("after")
        if not after:
            break
        time.sleep(0.1)

    log(f"Contacts missing email: {len(contacts)}")

    found_count = 0
    guess_count = 0
    no_website_count = 0

    for contact in contacts:
        cid = contact["id"]
        cname = f"{contact['properties'].get('firstname','') or ''} {contact['properties'].get('lastname','') or ''}".strip()

        # Get associated company for website
        _, assoc_data = hs("GET", f"/crm/v3/objects/contacts/{cid}/associations/companies")
        company_ids = [r["id"] for r in assoc_data.get("results", [])]
        if not company_ids:
            continue

        # Get company website
        _, co_data = hs("GET", f"/crm/v3/objects/companies/{company_ids[0]}?properties=name,domain,website")
        co_props = co_data.get("properties", {})
        co_name = co_props.get("name", "?")
        website = co_props.get("website") or co_props.get("domain") or ""

        if not website:
            no_website_count += 1
            log(f"  —  {co_name:45s} | no website on file")
            continue

        # Try to scrape a real email
        email, domain = scrape_website(website)

        if email:
            # Real email found — write it, mark NEW
            hs("PATCH", f"/crm/v3/objects/contacts/{cid}", {
                "properties": {"email": email, "hs_lead_status": "NEW"}
            })
            log(f"  ✓  {co_name:45s} | {email}  (scraped)")
            found_count += 1
        elif domain:
            # Best-guess fallback
            guess_email = f"info@{domain}"
            hs("PATCH", f"/crm/v3/objects/contacts/{cid}", {
                "properties": {"email": guess_email, "hs_lead_status": "OPEN"}
            })
            log(f"  ~  {co_name:45s} | {guess_email}  (best-guess — needs review)")
            guess_count += 1
        else:
            no_website_count += 1
            log(f"  —  {co_name:45s} | couldn't parse website: {website}")

        time.sleep(0.2)

    log(f"\n=== Done ===")
    log(f"  Scraped real email : {found_count}")
    log(f"  Best-guess (review): {guess_count}  — these have hs_lead_status=OPEN in HubSpot")
    log(f"  No website / error : {no_website_count}")


if __name__ == "__main__":
    main()
