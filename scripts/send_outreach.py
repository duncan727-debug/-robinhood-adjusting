#!/usr/bin/env python3
"""
Outreach email sender — Listing-First template, 25/day in 4 batches.

Usage:
  OUTREACH_BATCH=1 python3 send_outreach.py   # 8:00am  — 6 emails
  OUTREACH_BATCH=2 python3 send_outreach.py   # 10:30am — 6 emails
  OUTREACH_BATCH=3 python3 send_outreach.py   # 12:30pm — 7 emails
  OUTREACH_BATCH=4 python3 send_outreach.py   # 3:00pm  — 6 emails

State is tracked in crm/.outreach_state.json so batches stay in sync
and no contact is ever sent to twice.
"""

import csv
import json
import os
import re
import smtplib
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

WORKSPACE   = Path("/Users/victoria/.openclaw/workspace")
CONFIG_FILE = WORKSPACE / "config" / ".services-config.txt"
STATE_FILE  = WORKSPACE / "crm" / ".outreach_state.json"
LOG_PATH    = WORKSPACE / "scripts" / "outreach_send.log"
MASTER_CSV  = WORKSPACE / "crm" / "hubspot_master_import.csv"

GMAIL_USER  = "duncanlittlejohn727@gmail.com"
FROM_NAME   = "Duncan Littlejohn"
HUBSPOT_BCC = "246055074@bcc.hubspot.com"  # portal 246055074 — auto-logs outbound + threads replies
SITE_URL    = "https://robinhoodadjusting.com"

BATCH_SLICES = {
    1: (0,  6),
    2: (6,  12),
    3: (12, 19),
    4: (19, 25),
}

CATEGORY_LABELS = {
    "roofer":            "roofing",
    "plumber":           "plumbing",
    "hvac":              "HVAC",
    "property-manager":  "property management",
    "hoa-manager":       "HOA management",
    "attorney":          "insurance law",
    "general-contractor":"general contracting",
    "water-mitigation":  "water mitigation",
    "mold":              "mold remediation",
    "CONSTRUCTION":      "contracting",
    "REAL_ESTATE":       "property management",
}

# ── credentials ─────────────────────────────────────────────────────────────

def load_credentials():
    text = CONFIG_FILE.read_text()
    m = re.search(r"Gmail App Password.*?:\s*([a-z]{4} [a-z]{4} [a-z]{4} [a-z]{4})", text)
    gmail_pw = m.group(1) if m else None
    if not gmail_pw:
        sys.exit("ERROR: Gmail App Password not found in config.")

    hs_token = os.environ.get("HUBSPOT_API_KEY", "")
    if not hs_token:
        m2 = re.search(r'TOKEN\s*=\s*"([^"]+)"',
                       (WORKSPACE / "scripts" / "setup-hubspot-lists.py").read_text())
        hs_token = m2.group(1) if m2 else ""
    if not hs_token:
        sys.exit("ERROR: HUBSPOT_API_KEY not found.")
    return gmail_pw, hs_token

# ── HubSpot helpers ──────────────────────────────────────────────────────────

def hs(method, path, body=None, token=""):
    url = f"https://api.hubapi.com{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req) as r:
                raw = r.read()
                return r.status, json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(2 ** attempt)
                continue
            return e.code, {}
    return 0, {}

def get_eligible_contacts(token):
    """Return contacts with email whose hs_lead_status is NEW or OPEN."""
    contacts = []
    after = None
    while True:
        body = {
            "filterGroups": [
                {"filters": [
                    {"propertyName": "email", "operator": "HAS_PROPERTY"},
                    {"propertyName": "hs_lead_status", "operator": "EQ", "value": "NEW"},
                ]},
                {"filters": [
                    {"propertyName": "email", "operator": "HAS_PROPERTY"},
                    {"propertyName": "hs_lead_status", "operator": "EQ", "value": "OPEN"},
                ]},
            ],
            "properties": ["firstname", "lastname", "email", "phone", "company", "hs_lead_status"],
            "limit": 100,
        }
        if after:
            body["after"] = after
        _, data = hs("POST", "/crm/v3/objects/contacts/search", body, token)
        contacts.extend(data.get("results", []))
        after = data.get("paging", {}).get("next", {}).get("after")
        if not after:
            break
        time.sleep(0.1)
    return contacts

def get_company_for_contact(contact_id, token):
    _, data = hs("GET", f"/crm/v3/objects/contacts/{contact_id}/associations/companies", token=token)
    ids = [r["id"] for r in data.get("results", [])]
    if not ids:
        return None, None, None
    _, co = hs("GET", f"/crm/v3/objects/companies/{ids[0]}?properties=name,industry", token=token)
    props = co.get("properties", {})
    return ids[0], props.get("name", ""), props.get("industry", "")

def log_email_to_hubspot(contact_id, company_id, to_email, subject, body_text, token):
    ts = str(int(datetime.now(tz=timezone.utc).timestamp() * 1000))
    payload = {
        "properties": {
            "hs_email_direction":        "EMAIL",
            "hs_email_status":           "SENT",
            "hs_email_subject":          subject,
            "hs_email_text":             body_text,
            "hs_timestamp":              ts,
            "hs_email_sender_email":     GMAIL_USER,
            "hs_email_sender_firstname": "Duncan",
            "hs_email_to_email":         to_email,
        },
        "associations": [],
    }
    if contact_id:
        payload["associations"].append({
            "to": {"id": contact_id},
            "types": [{"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": 198}],
        })
    if company_id:
        payload["associations"].append({
            "to": {"id": company_id},
            "types": [{"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": 186}],
        })
    hs("POST", "/crm/v3/objects/emails", payload, token)

def update_contact_status(contact_id, status, token):
    hs("PATCH", f"/crm/v3/objects/contacts/{contact_id}",
       {"properties": {"hs_lead_status": status}}, token)

def move_deal_stage(contact_id, stage_id, token):
    """Find the deal associated with this contact and move it to stage_id."""
    _, data = hs("GET", f"/crm/v3/objects/contacts/{contact_id}/associations/deals", token=token)
    deal_ids = [r["id"] for r in data.get("results", [])]
    for deal_id in deal_ids:
        hs("PATCH", f"/crm/v3/objects/deals/{deal_id}",
           {"properties": {"dealstage": stage_id}}, token)

# ── local category lookup ────────────────────────────────────────────────────

def load_category_map():
    mapping = {}
    if MASTER_CSV.exists():
        with open(MASTER_CSV) as f:
            for row in csv.DictReader(f):
                name = row.get("company_name", "").strip().lower()
                cat  = row.get("category", "").strip()
                if name and cat:
                    mapping[name] = cat
    return mapping

# ── state management ─────────────────────────────────────────────────────────

def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"date": "", "queue": [], "batches_sent": [], "all_sent": [], "confirmations_sent": []}

def save_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=2))

# ── email template ───────────────────────────────────────────────────────────

SUBJECT_TEMPLATE = (
    "Homeowners are asking me for {category} referrals in Palm Beach County — can I list you?"
)

BODY_TEMPLATE = """\
Hi {first_name},

I'm Duncan Littlejohn, a licensed public adjuster based in Wellington. I run a daily newsletter \
for South Florida homeowners, contractors, and real estate professionals — currently covering \
Palm Beach, Broward, and Miami-Dade counties.

Through that newsletter I regularly hear from homeowners specifically looking for trusted {category} \
companies in Palm Beach County, and right now I don't have enough vetted providers to send their way. \
A lot of these folks are coming out of a claim situation, so they're ready to move.

I'd like to add {company_name} to our free provider directory at {site_url}/providers so I can \
start referring that business to you. No fee, no pitch — just a free listing visible to our \
homeowner subscriber base.

All I need to get you listed:
- Your service area (cities/zip codes)
- Best contact number
- Website, if you have one

As a bonus, I'll add you to our trade professional brief — a free daily update on insurance \
market trends, PBC property activity, and roofing/restoration news that most contractors in \
the area find worth having.

→ YES, add my listing: {yes_link}
→ No thanks: {no_link}

Or just reply with those three details and I'll get you added. Hurricane season starts June 1 — \
this is the window when homeowners start making calls.

Best,
Duncan Littlejohn
Licensed Public Adjuster · Robinhood Adjusting · Wellington, FL
561-772-7528 · {site_url}/providers

To opt out, reply "unsubscribe" and I'll remove you immediately.\
"""

CONFIRMATION_SUBJECT = "You're listed — {company_name} is now on the Robinhood Adjusting provider directory"

CONFIRMATION_BODY = """\
Hi {first_name},

Great news — {company_name} is now listed on our provider directory at:
{site_url}/providers

Homeowners searching for trusted {category} professionals in Palm Beach County will be able \
to find you there. Your listing shows your business name, phone, city, and service area.

A few things to know:
- Listings are free, always
- You'll receive a "Verified Provider" badge once we confirm your details
- I'll reach out personally when I have a referral that matches your service area

I've also added you to our daily Trade Professional Brief — you can unsubscribe anytime \
by replying "unsubscribe."

Thanks for being part of the network. Hurricane season starts June 1, so the timing is good.

Best,
Duncan Littlejohn
Licensed Public Adjuster · Robinhood Adjusting · Wellington, FL
561-772-7528 · {site_url}\
"""

# ── sending ──────────────────────────────────────────────────────────────────

def send_email(gmail_pw, to_addr, subject, body):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = f"{FROM_NAME} <{GMAIL_USER}>"
    msg["To"]      = to_addr
    msg["Bcc"]     = HUBSPOT_BCC
    msg.attach(MIMEText(body, "plain"))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_USER, gmail_pw)
        server.sendmail(GMAIL_USER, [to_addr, HUBSPOT_BCC], msg.as_string())

def log(msg):
    ts   = datetime.now().strftime("%Y-%m-%d %H:%M")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_PATH, "a") as f:
        f.write(line + "\n")

# ── confirmation pass ────────────────────────────────────────────────────────

def run_confirmation_pass(gmail_pw, token, state, cat_map):
    """Send confirmation emails to contacts HubSpot marked CONNECTED but not yet emailed."""
    _, data = hs("POST", "/crm/v3/objects/contacts/search", {
        "filterGroups": [{"filters": [
            {"propertyName": "hs_lead_status", "operator": "EQ", "value": "CONNECTED"},
        ]}],
        "properties": ["firstname", "email", "company"],
        "limit": 50,
    }, token)

    sent = 0
    for c in data.get("results", []):
        cid   = c["id"]
        props = c["properties"]
        email = props.get("email", "").strip()
        if not email or cid in state["confirmations_sent"]:
            continue

        first        = props.get("firstname") or "there"
        company_name = props.get("company") or ""
        cat_key      = cat_map.get(company_name.lower(), "CONSTRUCTION")
        category     = CATEGORY_LABELS.get(cat_key, "contracting")

        company_id, _, _ = get_company_for_contact(cid, token)

        subject = CONFIRMATION_SUBJECT.format(company_name=company_name)
        body    = CONFIRMATION_BODY.format(
            first_name=first, company_name=company_name,
            category=category, site_url=SITE_URL,
        )

        try:
            send_email(gmail_pw, email, subject, body)
            log_email_to_hubspot(cid, company_id, email, subject, body, token)
            state["confirmations_sent"].append(cid)
            log(f"  ✓ Confirmation sent: {first} @ {company_name} <{email}>")
            sent += 1
            time.sleep(1)
        except Exception as e:
            log(f"  ✗ Confirmation failed for {email}: {e}")

    return sent

# ── main ─────────────────────────────────────────────────────────────────────

def main():
    batch = int(os.environ.get("OUTREACH_BATCH", "0"))
    if batch not in BATCH_SLICES:
        sys.exit("ERROR: Set OUTREACH_BATCH=1, 2, 3, or 4")

    gmail_pw, token = load_credentials()
    state           = load_state()
    today           = datetime.now().strftime("%Y-%m-%d")
    cat_map         = load_category_map()

    log(f"=== Outreach batch {batch} start ({today}) ===")

    # Rebuild queue at the start of each day (batch 1 or stale date)
    if state["date"] != today or not state["queue"]:
        log("Building today's send queue...")
        contacts  = get_eligible_contacts(token)
        already   = set(state["all_sent"])
        fresh     = [c for c in contacts if c["id"] not in already]
        queue_ids = [c["id"] for c in fresh[:25]]
        state.update({"date": today, "queue": queue_ids, "batches_sent": []})
        save_state(state)
        log(f"Queue built: {len(queue_ids)} contacts for today")

    if batch in state["batches_sent"]:
        log(f"Batch {batch} already sent today — skipping.")
        conf = run_confirmation_pass(gmail_pw, token, state, cat_map)
        save_state(state)
        log(f"Confirmation pass: {conf} sent")
        return

    start, end   = BATCH_SLICES[batch]
    batch_ids    = state["queue"][start:end]

    if not batch_ids:
        log("No contacts left in queue for this batch.")
        save_state(state)
        return

    log(f"Sending {len(batch_ids)} emails (batch {batch}, slots {start}–{end-1})...")
    sent = errors = 0

    for cid in batch_ids:
        # Fetch fresh contact data
        _, cdata = hs("GET", f"/crm/v3/objects/contacts/{cid}?properties=firstname,email,company", token=token)
        props    = cdata.get("properties", {})
        email    = props.get("email", "").strip()
        first    = props.get("firstname") or "there"
        co_name  = props.get("company") or ""

        if not email:
            log(f"  — Skipping {cid}: no email")
            continue

        company_id, hs_co_name, industry = get_company_for_contact(cid, token)
        company_name = hs_co_name or co_name
        cat_key      = cat_map.get(company_name.lower(), industry or "CONSTRUCTION")
        category     = CATEGORY_LABELS.get(cat_key, "contracting")

        yes_link = (
            f"{SITE_URL}/.netlify/functions/listing-response"
            f"?company_id={company_id or ''}&contact_id={cid}&action=yes"
        )
        no_link  = (
            f"{SITE_URL}/.netlify/functions/listing-response"
            f"?company_id={company_id or ''}&contact_id={cid}&action=no"
        )

        subject = SUBJECT_TEMPLATE.format(category=category)
        body    = BODY_TEMPLATE.format(
            first_name=first, category=category, company_name=company_name,
            site_url=SITE_URL, yes_link=yes_link, no_link=no_link,
        )

        try:
            send_email(gmail_pw, email, subject, body)
            log_email_to_hubspot(cid, company_id, email, subject, body, token)
            update_contact_status(cid, "IN_PROGRESS", token)
            move_deal_stage(cid, "qualifiedtobuy", token)  # → Outreach Sent
            state["all_sent"].append(cid)
            log(f"  ✓ Sent: {first} @ {company_name} <{email}>")
            sent += 1
        except Exception as e:
            log(f"  ✗ Failed {email}: {e}")
            errors += 1

        time.sleep(2)  # ~2s between sends — looks human, well inside Gmail limits

    state["batches_sent"].append(batch)
    save_state(state)
    log(f"Batch {batch} done — sent: {sent}, errors: {errors}")

    # Always run confirmation pass at end of every batch
    conf = run_confirmation_pass(gmail_pw, token, state, cat_map)
    save_state(state)
    if conf:
        log(f"Confirmation pass: {conf} sent")

    log(f"=== Batch {batch} complete ===")


if __name__ == "__main__":
    main()
