#!/usr/bin/env python3
"""
Parse a partner's reply to the listing qualifying-questions email, populate
HubSpot contact properties, advance the listing workflow, and send the
welcome-confirmation email.

Called by imap_bridge.py when a reply arrives on a contact whose
`directory_listing_status` is `pending_add` (i.e. they've been added to the
directory and are now answering the 6-question follow-up).

Usage (typically invoked from imap_bridge.py):
    python3 parse_listing_answers.py <contact_id> <reply_body_file>

State:
- Updates HubSpot contact properties (service_counties, primary_trade,
  job_size_focus, emergency_availability, referral_channel_pref)
- Flips directory_listing_status: pending_add → listed
- Advances deal to 'decisionmakerboughtin' (Listed in Directory) if still earlier
- Logs to scripts/listing_answers.log
"""

import json
import os
import re
import smtplib
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

WORKSPACE   = Path("/Users/victoria/.openclaw/workspace")
CONFIG_FILE = WORKSPACE / "config" / ".services-config.txt"
TEMPLATE    = WORKSPACE / "crm" / "templates" / "listing-welcome-confirmation.md"
LOG_PATH    = WORKSPACE / "scripts" / "listing_answers.log"

GMAIL_USER  = "duncanlittlejohn727@gmail.com"
FROM_NAME   = "Duncan Littlejohn"
HUBSPOT_BCC = "246055074@bcc.hubspot.com"

COUNTY_MAP = {"a": "Palm Beach", "b": "Martin", "c": "St. Lucie", "d": "Broward", "e": "Miami-Dade"}
TRADE_MAP  = {"a": "general_contractor", "b": "roofing", "c": "hvac", "d": "plumbing", "e": "restoration"}
JOBSIZE_MAP = {
    "a": ("residential", "Residential only"),
    "b": ("commercial", "Commercial only"),
    "c": ("both", "Residential and Commercial"),
    "d": ("insurance_claims", "Insurance-claim repairs"),
}
EMERGENCY_MAP = {"a": (True, "24/7 emergency calls"), "b": (False, "Business hours only")}
CHANNEL_MAP = {
    "a": ("text", "text"),
    "b": ("phone", "phone"),
    "c": ("email", "email"),
    "d": ("any", "any of the three"),
}


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


def hs(method, path, body=None, token=""):
    url = f"https://api.hubapi.com{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        return e.code, {"error": e.read().decode(errors="ignore")}


def log(msg):
    line = f"{datetime.now(timezone.utc).isoformat()} {msg}\n"
    LOG_PATH.parent.mkdir(exist_ok=True)
    with LOG_PATH.open("a") as f:
        f.write(line)


# ── parsing ─────────────────────────────────────────────────────────────────

def find_answer(body, question_num):
    """Find the answer line(s) for a given question number.

    Matches patterns like:
        2) a, c
        2. a,c
        2 - a c
        Q2: a, c
        **2)** a, c
    Returns lowercase string of detected letters (e.g. "ac"), or "" if not found.
    """
    body = body.replace("*", "")  # strip markdown bold
    # Lines that start (after optional whitespace/Q) with the question number
    pattern = rf"(?im)^\s*(?:Q\s*)?{question_num}\s*[\)\.\-:]\s*(.+)$"
    m = re.search(pattern, body)
    if not m:
        return ""
    line = m.group(1).lower()
    # Stop at the next question marker if present on same logical line
    line = re.split(r"\b[2-6]\s*[\)\.\-:]", line)[0]
    letters = re.findall(r"\b([a-e])\b", line)
    return "".join(sorted(set(letters)))


def extract_phone(body):
    m = re.search(r"(\+?1?[\s\-\.]?\(?\d{3}\)?[\s\-\.]?\d{3}[\s\-\.]?\d{4})", body)
    return m.group(1).strip() if m else None


def parse_reply(body):
    """Return dict of parsed answers. Missing keys = couldn't parse."""
    result = {}

    # Q1: name + phone (free text) — best-effort phone extract
    phone = extract_phone(body)
    if phone:
        result["phone"] = phone

    # Q2: counties (multi)
    q2 = find_answer(body, 2)
    if q2:
        counties = [COUNTY_MAP[c] for c in q2 if c in COUNTY_MAP]
        if counties:
            result["service_counties"] = ";".join(counties)
            result["_counties_display"] = ", ".join(counties)

    # Q3: primary trade (single) — only present in multi-trade sends
    q3 = find_answer(body, 3)
    if q3 and q3[0] in TRADE_MAP:
        result["primary_trade"] = TRADE_MAP[q3[0]]

    # Q4 in multi-trade send = job size. In single-trade send, q3 was dropped
    # so job size is at Q3. Detect by checking which slot has a-d (jobsize) vs a-e (trade).
    q4 = find_answer(body, 4)
    q5 = find_answer(body, 5)

    # Heuristic: if Q3 has no valid trade letter, treat single-trade layout
    # (Q3=jobsize, Q4=emergency, Q5=channel).
    single_trade = not result.get("primary_trade")
    if single_trade:
        jobsize_q, emergency_q, channel_q = q3, q4, q5
    else:
        jobsize_q, emergency_q, channel_q = q4, q5, find_answer(body, 6)

    if jobsize_q and jobsize_q[0] in JOBSIZE_MAP:
        value, label = JOBSIZE_MAP[jobsize_q[0]]
        result["job_size_focus"] = value
        result["_jobsize_label"] = label

    if emergency_q and emergency_q[0] in EMERGENCY_MAP:
        value, label = EMERGENCY_MAP[emergency_q[0]]
        result["emergency_availability"] = value
        result["_emergency_label"] = label

    if channel_q and channel_q[0] in CHANNEL_MAP:
        value, label = CHANNEL_MAP[channel_q[0]]
        result["referral_channel_pref"] = value
        result["_channel_label"] = label

    return result


# ── send welcome ────────────────────────────────────────────────────────────

def render_welcome(template_text, contact, parsed):
    firstname = contact.get("firstname") or "there"
    company   = contact.get("company") or "your company"
    body = template_text.split("---")[2].strip()  # strip header + frontmatter, take email body
    subj_m = re.search(r"\*\*Subject:\*\*\s*(.+)", body)
    subject = subj_m.group(1).strip() if subj_m else "You're all set on the directory"
    body = re.sub(r"\*\*Subject:\*\*.*\n", "", body, count=1).strip()

    substitutions = {
        "{FIRSTNAME}": firstname,
        "{COMPANY}": company,
        "{COUNTIES_LIST}": parsed.get("_counties_display", "the counties you selected"),
        "{JOB_SIZE_LABEL}": parsed.get("_jobsize_label", "the job mix you described"),
        "{EMERGENCY_LABEL}": parsed.get("_emergency_label", "the availability you described"),
        "{CHANNEL_LABEL}": parsed.get("_channel_label", "your preferred channel"),
    }
    for k, v in substitutions.items():
        body = body.replace(k, v)
    return subject, body


def send_email(to_addr, subject, body, gmail_pw):
    msg = MIMEMultipart()
    msg["From"]    = f"{FROM_NAME} <{GMAIL_USER}>"
    msg["To"]      = to_addr
    msg["Subject"] = subject
    msg["Bcc"]     = HUBSPOT_BCC
    msg.attach(MIMEText(body, "plain"))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_USER, gmail_pw)
        server.sendmail(GMAIL_USER, [to_addr, HUBSPOT_BCC], msg.as_string())


# ── main ────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 3:
        sys.exit("Usage: parse_listing_answers.py <contact_id> <reply_body_file>")

    contact_id = sys.argv[1]
    body = Path(sys.argv[2]).read_text()

    gmail_pw, hs_token = load_credentials()

    # Fetch contact
    status, contact_data = hs("GET",
        f"/crm/v3/objects/contacts/{contact_id}?properties=firstname,lastname,email,company,phone,directory_listing_status,hs_lead_status",
        token=hs_token)
    if status >= 400:
        log(f"ERROR fetch contact {contact_id}: {contact_data}")
        sys.exit(1)
    props = contact_data.get("properties", {})

    if props.get("directory_listing_status") not in ("pending_add", "listed"):
        log(f"SKIP contact {contact_id} — directory_listing_status={props.get('directory_listing_status')}")
        return

    parsed = parse_reply(body)
    log(f"PARSED contact {contact_id}: { {k:v for k,v in parsed.items() if not k.startswith('_')} }")

    # Update contact properties
    updates = {k: v for k, v in parsed.items() if not k.startswith("_")}
    updates["directory_listing_status"] = "listed"
    updates["partner_onboarded_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    s, r = hs("PATCH", f"/crm/v3/objects/contacts/{contact_id}",
              {"properties": updates}, token=hs_token)
    if s >= 400:
        log(f"ERROR update contact {contact_id}: {r}")

    # Advance deal to Listed in Directory if still earlier in the funnel
    _, deals = hs("GET", f"/crm/v3/objects/contacts/{contact_id}/associations/deals", token=hs_token)
    advance_from = {"appointmentscheduled", "qualifiedtobuy", "presentationscheduled"}
    for assoc in (deals.get("results") or []):
        did = assoc.get("id") or assoc.get("toObjectId")
        if not did:
            continue
        _, deal = hs("GET", f"/crm/v3/objects/deals/{did}?properties=dealstage", token=hs_token)
        cur = (deal.get("properties") or {}).get("dealstage")
        if cur in advance_from:
            hs("PATCH", f"/crm/v3/objects/deals/{did}",
               {"properties": {"dealstage": "decisionmakerboughtin"}}, token=hs_token)
            log(f"DEAL {did}: {cur} → decisionmakerboughtin")

    # Send welcome email
    to_addr = props.get("email")
    if not to_addr:
        log(f"SKIP welcome — no email on contact {contact_id}")
        return
    template_text = TEMPLATE.read_text()
    subject, email_body = render_welcome(template_text, props, parsed)
    try:
        send_email(to_addr, subject, email_body, gmail_pw)
        log(f"WELCOME sent to {to_addr} (contact {contact_id})")
    except Exception as e:
        log(f"ERROR sending welcome to {to_addr}: {e}")


if __name__ == "__main__":
    main()
