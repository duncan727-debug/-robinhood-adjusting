#!/usr/bin/env python3
"""One-off: visitor inquiry to Professional Referral Exchange — Palm Beach Gardens chapter."""
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

TO = "craig@prenetworking.net"
SUBJECT = "Visitor inquiry — Palm Beach Gardens chapter (Public Adjuster)"
BODY = """\
Hi Craig,

I'm Duncan Littlejohn, a licensed public adjuster based in Wellington — Robin Hood Adjusting. I'm looking for a structured referral group in the Palm Beach Gardens / Wellington area and the PRE Palm Beach Gardens chapter looks like a strong fit (Thursday mornings at Berry Fresh Café).

Two quick questions before I come visit:

1. Is the Public Adjuster seat currently open in your chapter?
2. What's the process to attend as a visitor — can I just show up this Thursday, or do you prefer I register in advance?

For context, my book of business is built on residential property claims (hurricane/storm/water/roof) across Palm Beach County. I bring strong referral fit for roofers, restoration cos, real estate agents, attorneys, mortgage brokers, and home services pros.

Happy to chat by phone if easier — 561-772-7528.

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
