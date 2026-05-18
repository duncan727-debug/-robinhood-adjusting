#!/usr/bin/env python3
"""One-off: HOA partnership pitch to FirstService Residential FL (John Matteo, Regional Director)."""
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

# Try both pattern guesses; fsresidential.com pattern is typically firstname.lastname@fsresidential.com
TO = "john.matteo@fsresidential.com"
CC = "info@fsresidential.com"
SUBJECT = "Free storm-season talk for your PBC HOA boards (no fees, no pitch)"
BODY = """\
Hi John,

I'm Duncan Littlejohn, a licensed public adjuster based in Wellington (Robin Hood Adjusting). With hurricane season starting June 1 and FirstService managing a large portion of Palm Beach County's HOA and condo communities, I'd like to offer a free, no-strings resource for your boards.

What I'm offering — for any FirstService-managed HOA / condo in PBC, free:
- A 20-minute pre-season board meeting talk: "Storm Claim Prep for Community Associations" — covers wind/water claim basics, common board pitfalls, FL claim deadline reform (Statute 627.70132, 1-yr new / 18-mo supplemental), and how to coordinate community-wide claims after a storm
- A free 1-page resident storm-prep handout boards can distribute
- Same-day claim-question triage for board members during storm season
- For any post-storm claim that becomes PA work, standard market commission — no soft-dollar arrangements, no kickbacks

Why I'm offering: boards are unpaid volunteers and hate hurricane season. A free, neutral PA voice at a pre-season meeting demystifies the post-storm process before it's urgent — and I get to be useful to a community well before anyone needs to file.

If you'd like to put me in front of one or two of your boards as a pilot, I'm happy to coordinate with the appropriate community manager. Easiest if you reply with names of communities that might want this, or forward this offer to them.

Reach me: 561-772-7528.

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
