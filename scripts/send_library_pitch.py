#!/usr/bin/env python3
"""One-off: free storm-prep talk pitch to Wellington Branch Library."""
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

TO = "JBerkheimer@pbclibrary.org"
CC = "NHamed@pbclibrary.org"
SUBJECT = "Free community talk offer — Hurricane Season Claim Prep for Homeowners"
BODY = """\
Hi Jessica,

I'm Duncan Littlejohn, a licensed public adjuster based in Wellington (Robin Hood Adjusting). With storm season starting June 1, I'd like to offer the Wellington Branch a free 20-30 minute community program for residents:

"What Every Florida Homeowner Should Know Before Filing a Storm Claim"

What's in it for your patrons:
- Plain-English walkthrough of insurance claim basics most homeowners don't learn until after a storm
- Tips on documenting damage, deadlines, and common claim pitfalls (no sales pitch)
- Q&A specifically tailored to Wellington / Palm Beach County homeowners

What's in it for me:
- Community visibility for our practice
- A chance to be useful to Wellington families before they need us

Logistics: I'm flexible on date and time — weekday mornings, evenings, or weekends all work. I can bring printed handouts. No fees, no obligations, no product to sell. Just a community resource.

If this would be a fit, I'm happy to coordinate with you or with Nafisah (cc'd here as system adult-activities coordinator).

Thanks for considering it.

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
    recipients = [TO, CC, HUBSPOT_BCC]
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_USER, pw)
        server.sendmail(GMAIL_USER, recipients, msg.as_string())
    ts = datetime.now().isoformat(timespec="seconds")
    LOG_PATH.open("a").write(f"{ts}  one-off  SENT  {TO},{CC}  {SUBJECT}\n")
    print(f"SENT to {TO} (CC {CC}, BCC HubSpot) @ {ts}")

if __name__ == "__main__":
    main()
