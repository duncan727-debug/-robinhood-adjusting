#!/usr/bin/env python3
"""One-off: RSVP request to Central PBC Chamber for Chamber Connections May 19, 2026."""
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

TO = "Info@CPBChamber.com"
SUBJECT = "RSVP — Chamber Connections, Tue May 19"
BODY = """\
Hi there,

I'd like to RSVP for Chamber Connections on Tuesday, May 19. Your online registration page (chambermaster events ID 6001697) is loading slowly on my end, so I figured I'd reach out directly to make sure my spot is reserved.

A bit about me: I'm Duncan Littlejohn with Robin Hood Adjusting, a Wellington-based licensed public adjusting firm. I'd love to come meet folks and learn what other Central PBC businesses are working on.

Could you confirm:
- Time and venue for the May 19 event
- Whether non-members can attend (and, if so, the guest rate)
- Anything I should bring (business cards, payment, etc.)

Happy to register/pay online if you can send a working link, or to drop by the office Monday to handle in person.

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
