#!/usr/bin/env python3
"""One-off: PA partnership pitch to KW Wellington Team Leader Daniel Garcia."""
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

TO = "danielgarcia68@kw.com"
SUBJECT = "Free claim-help resource for your KW Wellington agents (no fees, no pitch)"
BODY = """\
Hi Daniel,

I'm Duncan Littlejohn, a licensed public adjuster in Wellington — Robin Hood Adjusting. I'd like to offer your KW Wellington office a free resource your agents may not know they need: a go-to public adjuster for claim-related questions on their listings and buyer deals.

The agent pain point: a roof leak surfaces during inspection, or a seller's hurricane claim gets denied, or a buyer inherits a half-settled water-damage claim at closing. Most agents don't know whom to call, and most send the client straight to their insurance company (which rarely ends well for the deal).

What I'm offering — no fees, no MOU, no obligation:
- Free 10-minute claim consultations for any KW Wellington agent's client
- Same-day response on inspection-period claim questions
- Office hours / Q&A at your next team meeting if you'd like (no sales pitch — just answer agent questions)
- Free homeowner storm-prep guide your agents can attach to listing packets

What's in it for me: when your agent has a client with a real claim that needs a PA, I'd appreciate the referral. That's it — I'd rather earn it deal by deal than ask for a formal arrangement.

If this would be useful, I can swing by the office for a 15-minute coffee with you whenever you have an opening. Happy to meet Diane too if relevant.

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
