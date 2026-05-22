#!/usr/bin/env python3
"""
Partner lifecycle automation — runs daily, sends:
  • 30-day check-in: 30 days after `partner_onboarded_at`
  • Quarterly pulse: every 90 days after the previous pulse (or after the 30-day check-in)

State tracked on the HubSpot contact itself:
  - partner_onboarded_at         (date — set by parse_listing_answers.py)
  - partner_last_pulse_at        (date — set by this script)
  - partner_30day_sent_at        (date — set by this script)
  - partner_referral_count       (number — incremented by the referral-handoff workflow)
  - partner_referral_count_quarter (number — reset each quarterly pulse)

Cron: 9:00 AM EDT daily (after the 8am send batch finishes).
"""

import json
import os
import re
import smtplib
import sys
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone, date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

WORKSPACE = Path("/Users/victoria/.openclaw/workspace")
CONFIG_FILE = WORKSPACE / "config" / ".services-config.txt"
TEMPLATES_DIR = WORKSPACE / "crm" / "templates"

# Map partner_type → (30-day-template, quarterly-template).
# Default segment is `provider` (directory-listed contractor) when partner_type is blank.
TEMPLATE_MAP = {
    "provider":   ("30-day-checkin-provider.md", "quarterly-pulse-provider.md"),
    "field_met":  ("30-day-checkin-field.md",    "quarterly-pulse-field.md"),
    "chamber":    ("30-day-checkin-chamber.md",  "quarterly-pulse-chamber.md"),
}
DEFAULT_SEGMENT = "provider"
PROVIDER_HTML = WORKSPACE / "site" / "providers" / "index.html"
LOG_PATH = WORKSPACE / "scripts" / "partner_lifecycle.log"

GMAIL_USER = "duncanlittlejohn727@gmail.com"
FROM_NAME = "Duncan Littlejohn"
HUBSPOT_BCC = "246055074@bcc.hubspot.com"

TODAY = date.today()


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


def parse_date(s):
    if not s:
        return None
    try:
        return datetime.strptime(s[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def render(template_text, substitutions):
    body = template_text.split("---")[2].strip()
    subj_m = re.search(r"\*\*Subject:\*\*\s*(.+)", body)
    subject = subj_m.group(1).strip()
    body = re.sub(r"\*\*Subject:\*\*.*\n", "", body, count=1).strip()
    for k, v in substitutions.items():
        body = body.replace(k, str(v))
        subject = subject.replace(k, str(v))
    return subject, body


def send_email(to_addr, subject, body, gmail_pw):
    msg = MIMEMultipart()
    msg["From"] = f"{FROM_NAME} <{GMAIL_USER}>"
    msg["To"] = to_addr
    msg["Subject"] = subject
    msg["Bcc"] = HUBSPOT_BCC
    msg.attach(MIMEText(body, "plain"))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_USER, gmail_pw)
        server.sendmail(GMAIL_USER, [to_addr, HUBSPOT_BCC], msg.as_string())


def count_verified_providers():
    try:
        html = PROVIDER_HTML.read_text()
        return html.count("badge-verified")
    except Exception:
        return 0


def search_partners(hs_token):
    """Return all contacts with a partner_onboarded_at date set.

    Anyone with that date is in the lifecycle program — provider, field-met,
    chamber, etc. partner_type drives template selection.
    """
    out = []
    after = None
    while True:
        body = {
            "filterGroups": [{"filters": [
                {"propertyName": "partner_onboarded_at", "operator": "HAS_PROPERTY"}
            ]}],
            "properties": ["firstname", "lastname", "email", "company",
                           "partner_type", "partner_onboarded_at",
                           "partner_last_pulse_at", "partner_30day_sent_at",
                           "partner_referral_count", "partner_referral_count_quarter",
                           "chamber_event_name", "met_context"],
            "limit": 100,
        }
        if after:
            body["after"] = after
        status, data = hs("POST", "/crm/v3/objects/contacts/search", body, token=hs_token)
        if status >= 400:
            log(f"ERROR search: {data}")
            break
        out.extend(data.get("results", []))
        paging = (data.get("paging") or {}).get("next")
        if not paging:
            break
        after = paging.get("after")
    return out


def main():
    gmail_pw, hs_token = load_credentials()
    partners = search_partners(hs_token)
    log(f"START daily lifecycle run — {len(partners)} listed partners")

    network_size = count_verified_providers()

    sent_30 = 0
    sent_qp = 0

    for p in partners:
        props = p.get("properties", {})
        cid = p["id"]
        onboarded = parse_date(props.get("partner_onboarded_at"))
        last_pulse = parse_date(props.get("partner_last_pulse_at"))
        sent_30day = parse_date(props.get("partner_30day_sent_at"))
        email_addr = props.get("email")
        if not onboarded or not email_addr:
            continue

        days_since_onboard = (TODAY - onboarded).days
        firstname = props.get("firstname") or "there"
        company = props.get("company") or "your company"
        ref_count = props.get("partner_referral_count") or "0"
        ref_count_quarter = props.get("partner_referral_count_quarter") or "0"

        # Determine segment + template files
        segment = (props.get("partner_type") or DEFAULT_SEGMENT).lower()
        if segment not in TEMPLATE_MAP:
            segment = DEFAULT_SEGMENT
        tpl_30_name, tpl_qp_name = TEMPLATE_MAP[segment]
        tpl_30_path = TEMPLATES_DIR / tpl_30_name
        tpl_qp_path = TEMPLATES_DIR / tpl_qp_name

        # Common substitutions across segments (missing keys → leave placeholder
        # untouched so we can see it in logs and fix)
        common_subs = {
            "{FIRSTNAME}": firstname,
            "{COMPANY}": company,
            "{REFERRAL_COUNT}": ref_count,
            "{REFERRAL_COUNT_QUARTER}": ref_count_quarter,
            "{MET_CONTEXT}": props.get("met_context") or "out in the field",
            "{EVENT_NAME}": props.get("chamber_event_name") or "the networking event",
            "{EVENT_DATE_FRIENDLY}": "recently",
        }

        # 30-day check-in
        if not sent_30day and 30 <= days_since_onboard < 60:
            subject, body = render(tpl_30_path.read_text(), common_subs)
            try:
                send_email(email_addr, subject, body, gmail_pw)
                hs("PATCH", f"/crm/v3/objects/contacts/{cid}",
                   {"properties": {"partner_30day_sent_at": TODAY.strftime("%Y-%m-%d")}},
                   token=hs_token)
                log(f"30-DAY ({segment}) sent to {email_addr} ({company})")
                sent_30 += 1
            except Exception as e:
                log(f"ERROR 30-day to {email_addr}: {e}")
            continue

        # Quarterly pulse — 90 days after last_pulse, or 90 days after 30-day check-in
        anchor = last_pulse or sent_30day
        if anchor and (TODAY - anchor).days >= 90:
            highlights = (
                f"- Hurricane season is in full swing — claim activity tracking above last year's pace.\n"
                f"- Provider network grew to {network_size} verified partners across South Florida.\n"
                f"- If you've adjusted your service area or specialty, reply and I'll update your listing."
            )
            qp_subs = {
                **common_subs,
                "{NETWORK_SIZE}": str(network_size),
                "{NEW_PARTNERS_THIS_QUARTER}": "several",
                "{NETWORK_HIGHLIGHTS}": highlights,
            }
            subject, body = render(tpl_qp_path.read_text(), qp_subs)
            try:
                send_email(email_addr, subject, body, gmail_pw)
                hs("PATCH", f"/crm/v3/objects/contacts/{cid}",
                   {"properties": {
                       "partner_last_pulse_at": TODAY.strftime("%Y-%m-%d"),
                       "partner_referral_count_quarter": "0",
                   }},
                   token=hs_token)
                log(f"PULSE ({segment}) sent to {email_addr} ({company})")
                sent_qp += 1
            except Exception as e:
                log(f"ERROR pulse to {email_addr}: {e}")

    log(f"DONE — 30-day: {sent_30}, quarterly pulse: {sent_qp}")


if __name__ == "__main__":
    main()
