#!/usr/bin/env python3
"""One-off: vendor inquiry to Michelle Garvey (Wellington Hurricane Expo)."""
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

TO = "mgarvey@wellingtonfl.gov"
SUBJECT = "Vendor inquiry — 2027 Hurricane Expo + question on 2026 exhibitors"
BODY = """\
Hi Michelle,

I'm Duncan Littlejohn with Robin Hood Adjusting, a Wellington-based licensed public adjusting firm. We help homeowners navigate storm and property claims, and we publish a free daily Florida storm-prep newsletter for homeowners and service pros.

Two quick asks:

1. 2027 Expo (May 1, 2027) — could you share the vendor/sponsorship deck and reserve a slot for us? We want to be in front of Wellington homeowners ahead of next storm season.

2. 2026 Expo exhibitor list — would you be able to share or point me to a list of this year's exhibitors? We're building referral partnerships with local restoration and contracting businesses, and your exhibitors are exactly the network we'd love to connect with.

Happy to swing by the Village offices or jump on a quick call. Thanks for putting on such a great event for the community.

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
