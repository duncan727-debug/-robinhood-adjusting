#!/usr/bin/env python3
"""
Daily newsletter send: fetches subscriber list from HubSpot, sends today's
brief to each subscriber via Gmail SMTP.
"""

import json
import os
import re
import smtplib
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

WORKSPACE = Path("/Users/victoria/.openclaw/workspace")
BRIEFS_DIR = WORKSPACE / "content" / "briefs"
CONFIG_FILE = WORKSPACE / "config" / ".services-config.txt"
LOG_PATH = WORKSPACE / "scripts" / "newsletter-send.log"

GMAIL_USER = "duncanlittlejohn727@gmail.com"
FROM_NAME = "Robinhood Adjusting"

LIST_IDS = ["18", "19", "20"]


def load_credentials():
    content = CONFIG_FILE.read_text()
    # Gmail App Password
    m = re.search(r"Gmail App Password.*?:\s*([a-z]{4} [a-z]{4} [a-z]{4} [a-z]{4})", content)
    gmail_pw = m.group(1) if m else None
    if not gmail_pw:
        sys.exit("ERROR: Gmail App Password not found in config.")
    # HubSpot token — env var takes precedence
    hs_token = os.environ.get("HUBSPOT_API_KEY", "")
    if not hs_token:
        m2 = re.search(r'TOKEN\s*=\s*"([^"]+)"',
                       (WORKSPACE / "scripts" / "setup-hubspot-lists.py").read_text())
        hs_token = m2.group(1) if m2 else ""
    if not hs_token:
        sys.exit("ERROR: HUBSPOT_API_KEY not set and fallback not found.")
    return gmail_pw, hs_token


def hubspot_get(path, token):
    url = f"https://api.hubapi.com{path}"
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        log(f"HubSpot error {e.code} on {path}")
        return {}


def get_subscribers(token):
    """Fetch all contact emails from the 3 subscriber lists, deduplicated."""
    emails = set()
    for list_id in LIST_IDS:
        after = None
        while True:
            url = f"/crm/v3/lists/{list_id}/memberships?limit=100"
            if after:
                url += f"&after={after}"
            data = hubspot_get(url, token)
            for member in data.get("results", []):
                contact_id = member.get("recordId")
                if contact_id:
                    contact = hubspot_get(f"/crm/v3/objects/contacts/{contact_id}?properties=email", token)
                    email = contact.get("properties", {}).get("email", "")
                    if email:
                        emails.add(email.lower())
            paging = data.get("paging", {}).get("next", {})
            after = paging.get("after") if paging else None
            if not after:
                break
    return list(emails)


def get_brief_html(date_str):
    path = BRIEFS_DIR / f"{date_str}.html"
    if not path.exists():
        return None
    html = path.read_text()
    body_match = re.search(r"<body[^>]*>(.*?)</body>", html, re.DOTALL | re.IGNORECASE)
    return body_match.group(1).strip() if body_match else html


def build_email_html(body_content, date_str, subject):
    date_fmt = datetime.strptime(date_str, "%Y-%m-%d").strftime("%B %-d, %Y")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{subject}</title>
</head>
<body style="margin:0;padding:0;background:#f5f5f5;font-family:Georgia,'Times New Roman',serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f5f5f5;padding:20px 0;">
  <tr><td align="center">
    <table width="680" cellpadding="0" cellspacing="0" style="background:#ffffff;max-width:680px;width:100%;">
      <tr><td style="background:#0f2d4a;padding:28px 20px;text-align:center;border-bottom:5px solid #c9922a;">
        <img src="https://robinhoodadjusting.com/logo-dark.svg" alt="Robinhood Adjusting" width="280" height="60" style="display:inline-block;max-width:100%;height:auto;">
        <div style="color:rgba(255,255,255,0.5);font-family:Arial,sans-serif;font-size:12px;letter-spacing:1px;margin-top:12px;">{date_fmt}</div>
      </td></tr>
      <tr><td style="padding:30px 24px;">
        {body_content}
      </td></tr>
      <tr><td style="background:#1a1a1a;padding:20px;text-align:center;border-top:4px solid #c41e3a;">
        <p style="color:#999;font-size:12px;margin:0;">
          Robinhood Adjusting · Wellington, FL ·
          <a href="https://robinhoodadjusting.com" style="color:#c41e3a;">robinhoodadjusting.com</a>
        </p>
        <p style="color:#666;font-size:11px;margin:8px 0 0;">
          You're receiving this because you subscribed at robinhoodadjusting.com.
          To unsubscribe, reply with "unsubscribe" in the subject line.
        </p>
      </td></tr>
    </table>
  </td></tr>
</table>
</body>
</html>"""


def send_via_smtp(to_emails, subject, html, password):
    sent = 0
    failed = []
    with smtplib.SMTP("smtp.gmail.com", 587) as smtp:
        smtp.starttls()
        smtp.login(GMAIL_USER, password)
        for to_email in to_emails:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{FROM_NAME} <{GMAIL_USER}>"
            msg["To"] = to_email
            msg.attach(MIMEText(html, "html"))
            try:
                smtp.sendmail(GMAIL_USER, to_email, msg.as_string())
                sent += 1
            except Exception as e:
                failed.append((to_email, str(e)))
            time.sleep(0.3)  # stay well under Gmail's rate limit
    return sent, failed


def log(message):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"[{ts}] {message}")
    with open(LOG_PATH, "a") as f:
        f.write(f"[{ts}] {message}\n")


def main():
    date_str = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime("%Y-%m-%d")
    log(f"=== Daily brief send start: {date_str} ===")

    password, hs_token = load_credentials()

    brief_body = get_brief_html(date_str)
    if not brief_body:
        log(f"ERROR: No brief found for {date_str}")
        sys.exit(1)
    log(f"Loaded brief for {date_str}")

    subscribers = get_subscribers(hs_token)
    log(f"Fetched {len(subscribers)} subscribers from HubSpot lists")

    if not subscribers:
        log("No subscribers yet — skipping send. Will retry tomorrow.")
        sys.exit(0)

    date_fmt = datetime.strptime(date_str, "%Y-%m-%d").strftime("%B %-d, %Y")
    subject = f"South Florida Property Intelligence — {date_fmt}"
    html = build_email_html(brief_body, date_str, subject)

    log(f"Sending to {len(subscribers)} subscribers via Gmail SMTP...")
    sent, failed = send_via_smtp(subscribers, subject, html, password)

    log(f"Sent: {sent} | Failed: {len(failed)}")
    for email, err in failed:
        log(f"  FAILED {email}: {err}")
    log("=== Done ===")


if __name__ == "__main__":
    main()
