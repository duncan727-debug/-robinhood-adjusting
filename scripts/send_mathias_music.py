#!/usr/bin/env python3
"""One-off: send Mathias the music-store résumé + Wellington music store shortlist."""
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
SUBJECT = "Music résumé — v2 (one page, no fluff)"

BODY = """\
Mathias,

Your dad asked me to tighten it to one page and drop the "Why a Music
Store" section. Attached is v2 — one page, music + instruments up
front, no preamble.

The store shortlist hasn't changed — still in your inbox from earlier.

— Smith
"""

ATTACHMENTS = [
    Path("/Users/victoria/Desktop/Mathias-Resume-MusicStore.pdf"),
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
