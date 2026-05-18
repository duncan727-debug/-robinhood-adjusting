#!/usr/bin/env python3
"""One-off: guest pitch to 'Inside West Palm Beach' city podcast (Diane Papadakos / Mayor's Communications Office)."""
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

TO = "dpapadakos@wpb.org"
CC = "communications@wpb.org"
SUBJECT = "MEDIA REQUEST — Storm-season guest pitch for 'Inside West Palm Beach'"
BODY = """\
Hi Diane,

I'm Duncan Littlejohn, a licensed public adjuster based in Wellington (Robin Hood Adjusting). I'm writing to pitch a guest segment for "Inside West Palm Beach" tied to hurricane season.

I noticed you've previously featured Robert Norberg from Arden Insurance on hurricane prep, which suggests this is exactly the kind of public-service content the podcast supports. I'd like to offer a complementary perspective from the claims side — what happens AFTER a storm, where homeowners commonly get stuck, and what city residents can do now (before June 1) to avoid those pitfalls.

Proposed segment angles:
1. "What happens after the storm: 5 things WPB homeowners should know before they need to file a claim"
2. "The 2023 Florida claim-deadline reform — what city residents are still getting wrong"
3. "Public adjuster vs. insurance adjuster vs. attorney — when each one helps you and when they don't"

About me: Wellington-based, licensed FL PA, residential focus across Palm Beach County. I also publish a free daily storm-prep newsletter for Florida homeowners. No commercial pitch in the segment — this is public-service content.

Format works for me: short pre-season segment, full episode, or quoted expert in a roundup. Whatever fits the show.

Best contact: 561-772-7528 or this email.

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
    msg["Cc"] = CC
    msg["Bcc"] = HUBSPOT_BCC
    msg.attach(MIMEText(BODY, "plain"))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_USER, pw)
        server.sendmail(GMAIL_USER, [TO, CC, HUBSPOT_BCC], msg.as_string())
    ts = datetime.now().isoformat(timespec="seconds")
    LOG_PATH.open("a").write(f"{ts}  one-off  SENT  {TO},{CC}  {SUBJECT}\n")
    print(f"SENT to {TO} (CC {CC}, BCC HubSpot) @ {ts}")

if __name__ == "__main__":
    main()
