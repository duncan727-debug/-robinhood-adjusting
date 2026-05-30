#!/usr/bin/env python3
"""One-shot: stage 2nd-touch follow-up drafts in Gmail + update existing HubSpot
tasks to point at the Gmail draft. Does NOT create new tasks (existing ones)."""
import json, imaplib, os, urllib.request, time, sys
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid
from pathlib import Path

WORKSPACE = Path("/Users/victoria/.openclaw/workspace")
for line in (WORKSPACE/"config/.secrets").read_text().splitlines():
    if line.startswith("export "): line = line[7:]
    if "=" in line:
        k,v = line.split("=",1); os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

GMAIL_USER  = "duncanlittlejohn727@gmail.com"
GMAIL_PWD   = os.environ["GMAIL_APP_PASSWORD"]
HUBSPOT_BCC = "246055074@bcc.hubspot.com"
HUBSPOT_TOKEN = os.environ["HUBSPOT_API_KEY"]

SIGNATURE = """
Duncan Littlejohn
Robinhood Adjusting
duncanlittlejohn727@gmail.com
https://robinhoodadjusting.com
"""

def hs_patch(tid, props):
    req = urllib.request.Request(f"https://api.hubapi.com/crm/v3/objects/tasks/{tid}",
        data=json.dumps({"properties":props}).encode(), method="PATCH",
        headers={"Authorization":f"Bearer {HUBSPOT_TOKEN}","Content-Type":"application/json"})
    urllib.request.urlopen(req)

def main():
    rows = json.load(open(sys.argv[1]))
    M = imaplib.IMAP4_SSL("imap.gmail.com")
    M.login(GMAIL_USER, GMAIL_PWD)
    M.select('"[Gmail]/Drafts"')

    for r in rows:
        body_text = r["body"].rstrip() + "\n" + SIGNATURE
        msg = MIMEText(body_text, "plain", "utf-8")
        msg["From"]    = f"Duncan Littlejohn <{GMAIL_USER}>"
        msg["To"]      = r["to"]
        msg["Bcc"]     = HUBSPOT_BCC
        msg["Subject"] = r["subject"]
        msg["Date"]    = formatdate(localtime=True)
        msg["Message-ID"] = make_msgid(domain="gmail.com")
        raw = msg.as_bytes()
        typ, _ = M.append('"[Gmail]/Drafts"', "", imaplib.Time2Internaldate(time.time()), raw)
        ok = typ == "OK"
        # update task
        hs_patch(r["task_id"], {
            "hs_task_body": f"Gmail draft staged 2026-05-28 — Subject: \"{r['subject']}\" — review & send from Gmail Drafts."
        })
        print(f"  {'✓' if ok else '✗'} {r['name'][:30]:30s} | task {r['task_id']} | {r['subject'][:50]}")
    M.logout()

if __name__ == "__main__":
    main()
