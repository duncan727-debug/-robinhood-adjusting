#!/usr/bin/env python3
"""One-off: visitor inquiry to Alan Feuerman, South Florida Business Connections."""
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

TO = "sflbusinessconnectionsreply@gmail.com"
SUBJECT = "Visitor inquiry — Wellington Thursday networking (Public Adjuster)"
BODY = """\
Hi Alan,

I'm Duncan Littlejohn — licensed public adjuster based in Wellington, running a firm called Robin Hood Adjusting. I saw your South Florida Business Connections Thursday morning Wellington group listed and would love to come visit.

Two quick questions:

1. Is the Public Adjuster category currently open in your group?
2. What's the exact venue and best way to register as a visitor this Thursday (May 21)?

Quick background — I work residential property claims (hurricane, storm, water, roof) across Palm Beach County. Strong referral fit with roofers, restoration, real estate, attorneys, and home services pros.

Also — separately — if you happen to know Arlene at the Wednesday breakfast group at Nana's Diner, I'd love an email intro. Couldn't find an email for her anywhere.

Happy to reply by email or jump on a quick call: 561-772-7528.

Thanks,
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
    print(f"SENT to {TO} (BCC {HUBSPOT_BCC}) @ {ts}")

if __name__ == "__main__":
    main()
