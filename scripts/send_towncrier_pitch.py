#!/usr/bin/env python3
"""One-off: media pitch to Town-Crier newspaper as storm-season PA expert source."""
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

TO = "news@gotowncrier.com"
SUBJECT = "Local expert source for storm-season homeowner coverage"
BODY = """\
Hi Town-Crier team,

I'm Duncan Littlejohn, a licensed public adjuster in Wellington (Robin Hood Adjusting). With hurricane season starting June 1, I wanted to offer myself as a local expert source for any homeowner-focused storm coverage you have planned.

Topics I can comment on or write a guest column about:
- What Wellington homeowners should do BEFORE a storm to make a claim go smoothly
- Common claim mistakes that cost homeowners thousands
- The new Florida claim deadlines (FL Statute 627.70132 — 1-year for new claims, 18 months for supplemental, since 2023 reforms)
- What to do if your insurer denies or underpays a claim
- Public adjuster vs. insurance adjuster vs. attorney — when each makes sense

For context, your reporter Frank Koester did strong coverage of the October Rustic Ranches tornado — I'd be glad to be a follow-up source for similar pieces, or to support storm-season reader-service columns.

I also publish a free daily storm-prep newsletter for Florida homeowners (robinhoodadjusting.com) — happy to share article ideas as the season unfolds.

Best way to reach me: 561-772-7528 or this email. No agenda — just a Wellington-local PA who'd like to be useful to your readers.

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
