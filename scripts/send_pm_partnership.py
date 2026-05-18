#!/usr/bin/env python3
"""One-off: storm-season partnership pitch to Florida's Property Management (Glenn Gurvitch)."""
import re
import smtplib
import sys
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

WORKSPACE = Path("/Users/victoria/.openclaw/workspace")
CONFIG_FILE = WORKSPACE / "config" / ".services-config.txt"
LOG_PATH = WORKSPACE / "scripts" / "outreach_send.log"

GMAIL_USER = "duncanlittlejohn727@gmail.com"
FROM_NAME = "Duncan Littlejohn"
HUBSPOT_BCC = "246055074@bcc.hubspot.com"

TO = "NewLandlords@FloridasPropertyManagement.com"
SUBJECT = "Storm-season claim help for your owners — free resource"
BODY = """\
Hi Glenn,

I'm Duncan Littlejohn, a licensed public adjuster based in Wellington (Robin Hood Adjusting). With hurricane season starting June 1 and Florida's Property Management overseeing 1,200+ units across Palm Beach County, I wanted to reach out about a free resource your team and owners could use this storm season.

The painful scenario you've probably already lived through: a storm hits, multiple properties get damage, tenants call you with leaks and water intrusion, owners call you panicked about deductibles and what's covered, and you become the bottleneck between insurance carriers and 100+ scattered owners. PAs help unlock that bottleneck.

What I can offer your team — no fees, no MOU, no obligation:
- A free 30-min pre-season walkthrough for your team: claim process, documentation requirements, common pitfalls, FL claim deadlines (Statute 627.70132)
- Same-day phone triage for any owner with a fresh claim — your team can refer and I'll handle it
- A free 1-page storm-prep checklist your team can send to owners ahead of June 1
- For any claim that turns into PA work, fair-market commission (typically 10%) — no kickbacks, no soft-dollar shenanigans

What's in it for me: when an owner has a claim that's stalling or underpaid, I get the referral. Earn it deal by deal.

If this would be useful, I'm happy to grab coffee or jump on a 15-min call. 561-772-7528.

Duncan Littlejohn
Robin Hood Adjusting · Licensed Public Adjuster · Wellington, FL
561-772-7528 · duncanlittlejohn727@gmail.com
https://robinhoodadjusting.com
"""

def load_gmail_pw():
    text = CONFIG_FILE.read_text()
    m = re.search(r"Gmail App Password.*?:\s*([a-z]{4} [a-z]{4} [a-z]{4} [a-z]{4})", text)
    if not m:
        sys.exit("ERROR: Gmail App Password not found in config.")
    return m.group(1)

def main():
    pw = load_gmail_pw()
    msg = MIMEMultipart("alternative")
    msg["Subject"] = SUBJECT
    msg["From"] = f"{FROM_NAME} <{GMAIL_USER}>"
    msg["To"] = TO
    msg["Bcc"] = HUBSPOT_BCC
    msg.attach(MIMEText(BODY, "plain"))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_USER, pw)
        server.sendmail(GMAIL_USER, [TO, HUBSPOT_BCC], msg.as_string())
    ts = datetime.now().isoformat(timespec="seconds")
    LOG_PATH.open("a").write(f"{ts}  one-off  SENT  {TO}  {SUBJECT}\n")
    print(f"SENT to {TO} (BCC HubSpot) @ {ts}")

if __name__ == "__main__":
    main()
