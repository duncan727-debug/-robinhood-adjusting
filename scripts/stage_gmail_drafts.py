#!/usr/bin/env python3
"""Stage batch follow-up emails as Gmail Drafts + create HubSpot pointer tasks.

Pattern: hybrid Gmail-Drafts + HubSpot-task-pointer for review-before-send
batches (Chamber, BNI, mixers, event follow-ups, etc.).

Input: JSON file (or stdin) — list of objects:
  {
    "name":       "Mary Lou Bedford",
    "to":         "marylou@cpbchamber.com",
    "contact_id": "488484481744",          # HubSpot contact ID; optional
    "subject":    "Following up from ...",
    "body":       "Hi Mary Lou,\n\n...",   # plain-text, no signature (added by caller)
    "skip_email": false                    # set true for bounced addresses; creates CALL task
  }

Usage:
  python3 scripts/stage_gmail_drafts.py path/to/batch.json
  cat batch.json | python3 scripts/stage_gmail_drafts.py -

Behavior per row:
  - skip_email=false: append plain-text MIME (BCC HubSpot) to [Gmail]/Drafts;
    create/update HubSpot EMAIL task pointing to the Gmail draft.
  - skip_email=true: no Gmail draft; create HubSpot CALL task with phone-only guidance.

If contact_id is omitted, the script searches HubSpot by `to` email.
"""
import imaplib, email, time, os, json, sys, urllib.request
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid
from pathlib import Path

WORKSPACE = Path("/Users/victoria/.openclaw/workspace")
SECRETS = WORKSPACE / "config" / ".secrets"

for line in SECRETS.read_text().splitlines():
    if line.startswith("export "): line = line[len("export "):]
    if "=" in line:
        k,v = line.split("=",1); os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

GMAIL_USER = "duncanlittlejohn727@gmail.com"
GMAIL_PWD  = os.environ["GMAIL_APP_PASSWORD"]
HUBSPOT_BCC = "246055074@bcc.hubspot.com"
HUBSPOT_TOKEN = os.environ["HUBSPOT_API_KEY"]


def hs_post(path, body, method="POST"):
    req = urllib.request.Request(f"https://api.hubapi.com{path}",
        data=json.dumps(body).encode(), method=method,
        headers={"Authorization": f"Bearer {HUBSPOT_TOKEN}", "Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req))


def lookup_contact(email_addr):
    r = hs_post("/crm/v3/objects/contacts/search",
        {"filterGroups":[{"filters":[{"propertyName":"email","operator":"EQ","value":email_addr}]}],
         "properties":["firstname","phone"], "limit":1})
    return r["results"][0] if r["results"] else None


def create_task(contact_id, subject, body, task_type="EMAIL", due_offset_days=1):
    due_ms = int((time.time() + 86400 * due_offset_days) * 1000)
    payload = {
        "properties": {
            "hs_task_subject": subject,
            "hs_task_body": body,
            "hs_task_status": "NOT_STARTED",
            "hs_task_priority": "MEDIUM",
            "hs_task_type": task_type,
            "hs_timestamp": due_ms,
        },
        "associations": [{
            "to": {"id": contact_id},
            "types": [{"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": 204}]
        }]
    }
    return hs_post("/crm/v3/objects/tasks", payload)["id"]


def stage_gmail_draft(imap, to_email, subject, body):
    msg = MIMEText(body, "plain", "utf-8")
    msg["From"] = f"Duncan Littlejohn <{GMAIL_USER}>"
    msg["To"] = to_email
    msg["Bcc"] = HUBSPOT_BCC
    msg["Subject"] = subject
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid(domain="gmail.com")
    typ, _ = imap.append('"[Gmail]/Drafts"', r'(\Draft)',
                          imaplib.Time2Internaldate(time.time()), msg.as_bytes())
    return typ == "OK"


def main(path):
    rows = json.load(sys.stdin if path == "-" else open(path))
    imap = imaplib.IMAP4_SSL("imap.gmail.com", 993)
    imap.login(GMAIL_USER, GMAIL_PWD)
    try:
        for row in rows:
            name = row["name"]
            to_email = row["to"]
            cid = row.get("contact_id") or (lookup_contact(to_email) or {}).get("id")
            if not cid:
                print(f"  SKIP {name}: contact not found in HubSpot ({to_email})")
                continue

            if row.get("skip_email"):
                # phone-only path (e.g., bounced address)
                phone = (lookup_contact(to_email) or {}).get("properties", {}).get("phone", "")
                tid = create_task(cid,
                    f"Call {name} — email bounced",
                    f"Email to {to_email} bounces. Call instead.\n\nPhone: {phone or 'NOT ON FILE'}\n\n--- Draft talking points ---\n{row['body']}",
                    task_type="CALL")
                print(f"  {name}: CALL task {tid} (skip_email)")
                continue

            ok = stage_gmail_draft(imap, to_email, row["subject"], row["body"])
            if not ok:
                print(f"  {name}: IMAP APPEND failed"); continue
            tid = create_task(cid,
                f"Send follow-up: {name}",
                f"Draft staged in Gmail Drafts for {name} ({to_email}). Open Gmail → Drafts → review → send. BCC to HubSpot is pre-filled; sent message will auto-log to this contact.")
            print(f"  {name}: Gmail draft + task {tid}")
    finally:
        imap.logout()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: stage_gmail_drafts.py <batch.json|->", file=sys.stderr); sys.exit(2)
    main(sys.argv[1])
