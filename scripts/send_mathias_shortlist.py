#!/usr/bin/env python3
"""One-off: send Wellington club shortlist PDF + HTML to Mathias."""
import re, smtplib, sys, mimetypes
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path

WORKSPACE = Path("/Users/victoria/.openclaw/workspace")
CONFIG_FILE = WORKSPACE / "config" / ".services-config.txt"
LOG_PATH = WORKSPACE / "scripts" / "outreach_send.log"

GMAIL_USER = "duncanlittlejohn727@gmail.com"
FROM_NAME = "Duncan Littlejohn"

TO = "mathiaspokeman123@gmail.com"
SUBJECT = "Country club shortlist + your tailored résumé"

BODY = """\
Hey Mathias,

Your dad asked me to tailor your résumé for a country club setting and
put together a shortlist of Wellington clubs to target this summer.

Attached:
  1. Mathias-Littlejohn-Resume.pdf — your résumé, reworked to lead with
     hospitality/club-fit qualities (trilingual moved up front, swimming
     framed as poolside-environment fluency, added a Roles of Interest
     section listing realistic spots: pool attendant, snack bar, locker /
     bag room, junior tennis or aquatics helper, banquet support).

  2. Mathias-Club-Shortlist.pdf — 7 clubs ranked by likelihood, with
     phone numbers, addresses, and a step-by-step approach. Top 3 to
     start with: Wanderers Club, Wellington National (at Binks Forest),
     and Palm Beach Polo.

A few tips from your dad's playbook:
  - Private clubs hire by walk-in and phone call, not online apps.
    Print the résumé, dress neatly (collared shirt), bring a pen.
  - Tue-Thu mornings 9:30-11:00 a.m. is the right window to drop in.
  - Always get the name of the manager you hand it to, then send a
     short thank-you email the same day.

Phone script is in the shortlist PDF — just read it off the page when
you call.

Good luck. Tell your dad how it goes.

— Smith
(your dad's assistant)
"""

ATTACHMENTS = [
    Path("/Users/victoria/Desktop/Mathias-Littlejohn-Resume.pdf"),
    Path("/Users/victoria/Desktop/Mathias-Club-Shortlist.pdf"),
]

def load_gmail_pw():
    text = CONFIG_FILE.read_text()
    m = re.search(r"Gmail App Password.*?:\s*([a-z]{4} [a-z]{4} [a-z]{4} [a-z]{4})", text)
    if not m:
        sys.exit("ERROR: Gmail App Password not found in config.")
    return m.group(1)

def attach(msg, path):
    ctype, _ = mimetypes.guess_type(str(path))
    maintype, subtype = (ctype or "application/octet-stream").split("/", 1)
    part = MIMEBase(maintype, subtype)
    part.set_payload(path.read_bytes())
    encoders.encode_base64(part)
    part.add_header("Content-Disposition", f'attachment; filename="{path.name}"')
    msg.attach(part)

def main():
    pw = load_gmail_pw()
    msg = MIMEMultipart()
    msg["Subject"] = SUBJECT
    msg["From"] = f"{FROM_NAME} <{GMAIL_USER}>"
    msg["To"] = TO
    msg["Cc"] = GMAIL_USER
    msg.attach(MIMEText(BODY, "plain"))
    for p in ATTACHMENTS:
        attach(msg, p)
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_USER, pw)
        server.sendmail(GMAIL_USER, [TO, GMAIL_USER], msg.as_string())
    ts = datetime.now().isoformat(timespec="seconds")
    LOG_PATH.open("a").write(f"{ts}  one-off  SENT  {TO}  {SUBJECT}\n")
    print(f"SENT to {TO} (cc {GMAIL_USER}) @ {ts}")

if __name__ == "__main__":
    main()
