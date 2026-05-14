#!/usr/bin/env python3
"""
Gmail → HubSpot IMAP bridge.

Scans Duncan's inbox for:
  1. Bounce notifications (mailer-daemon, postmaster) → mark contacts as bounced
  2. Replies from contacts we emailed → log engagement + advance lead status

State file: crm/.imap_bridge_state.json — last processed UID so we don't re-process.

Run via cron hourly (or trigger manually).
"""

import imaplib
import email
import json
import os
import re
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime, timezone, timedelta
from email.utils import parseaddr, parsedate_to_datetime

WORKSPACE = Path("/Users/victoria/.openclaw/workspace")
STATE_PATH = WORKSPACE / "crm" / ".imap_bridge_state.json"
LOG_PATH = WORKSPACE / "scripts" / "imap_bridge.log"
SECRETS_PATH = WORKSPACE / "config" / ".secrets"

BOUNCE_SENDERS = (
    "mailer-daemon@",
    "postmaster@",
    "mail-daemon@",
    "noreply@bounce",
)

SELF_SKIP = {"duncanlittlejohn727@gmail.com"}

FAILED_RECIPIENT_RE = re.compile(
    r"(?:Final-Recipient|X-Failed-Recipients|original_address|to=<)[^\n]*?([\w.\-+]+@[\w.\-]+\.[a-z]{2,})",
    re.I,
)


def log(msg):
    line = f"[{datetime.now().isoformat(timespec='seconds')}] {msg}"
    print(line)
    with LOG_PATH.open("a") as f:
        f.write(line + "\n")


def load_secret(name):
    val = os.environ.get(name, "").strip()
    if val:
        return val
    if SECRETS_PATH.exists():
        for line in SECRETS_PATH.read_text().splitlines():
            if line.strip().startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k = k.replace("export", "").strip()
            v = v.strip().strip('"').strip("'")
            if k == name:
                return v
    sys.exit(f"ERROR: {name} not set in env or config/.secrets")


GMAIL_USER = load_secret("GMAIL_USER")
GMAIL_PASS = load_secret("GMAIL_APP_PASSWORD").replace(" ", "")
HUBSPOT_TOKEN = load_secret("HUBSPOT_API_KEY")


def load_state():
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text())
    return {"last_uid": 0, "processed_bounces": [], "processed_replies": []}


def save_state(state):
    STATE_PATH.write_text(json.dumps(state, indent=2))


def hs_request(method, path, payload=None):
    url = f"https://api.hubapi.com{path}"
    data = json.dumps(payload).encode() if payload else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {HUBSPOT_TOKEN}")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read() or b"{}")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def fetch_hubspot_contacts_by_email():
    """Returns dict: email_lower -> contact_id"""
    by_email = {}
    after = None
    while True:
        path = f"/crm/v3/objects/contacts?limit=100&properties=email,hs_lead_status"
        if after:
            path += f"&after={after}"
        status, data = hs_request("GET", path)
        if status != 200:
            log(f"HubSpot contacts fetch failed: {status}")
            return by_email
        for c in data.get("results", []):
            e = (c["properties"].get("email") or "").lower().strip()
            if e:
                by_email[e] = c["id"]
        nxt = data.get("paging", {}).get("next", {}).get("after")
        if not nxt:
            break
        after = nxt
    return by_email


def extract_failed_recipient(msg):
    """Pull the bounced-to address from a DSN/bounce message."""
    if msg.get("X-Failed-Recipients"):
        return msg["X-Failed-Recipients"].strip().lower()
    body_text = ""
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            if ctype in ("text/plain", "message/delivery-status", "message/rfc822"):
                try:
                    payload = part.get_payload(decode=True)
                    if payload:
                        body_text += payload.decode("utf-8", errors="replace")
                except Exception:
                    pass
    else:
        try:
            body_text = (msg.get_payload(decode=True) or b"").decode("utf-8", errors="replace")
        except Exception:
            body_text = ""
    m = FAILED_RECIPIENT_RE.search(body_text)
    if m:
        return m.group(1).strip().lower()
    return None


def extract_bounce_reason(msg):
    """Grab a short reason from the DSN."""
    body_text = ""
    if msg.is_multipart():
        for part in msg.walk():
            try:
                payload = part.get_payload(decode=True)
                if payload:
                    body_text += payload.decode("utf-8", errors="replace")
            except Exception:
                pass
    else:
        try:
            body_text = (msg.get_payload(decode=True) or b"").decode("utf-8", errors="replace")
        except Exception:
            body_text = ""
    # Pick the first informative line
    for line in body_text.splitlines():
        line = line.strip()
        if not line or line.startswith(">"):
            continue
        if any(t in line.lower() for t in ("smtp error", "550", "554", "5.1.", "5.2.", "5.7.", "domain not", "no such user", "mailbox unavailable", "user unknown")):
            return line[:200]
    return "Unspecified bounce"


def mark_bounced(contact_id, recipient, reason):
    """Mark contact UNQUALIFIED + create a Note engagement with the bounce reason.
    hs_email_hard_bounce_reason is read-only in HubSpot, so we record via Note + status."""
    status, _ = hs_request(
        "PATCH",
        f"/crm/v3/objects/contacts/{contact_id}",
        {"properties": {"hs_lead_status": "UNQUALIFIED"}},
    )
    if status != 200:
        log(f"  ✗ BOUNCE  → {recipient} status patch failed ({status})")
        return False

    note_body = (
        f"<p><strong>Hard bounce detected via Gmail bridge</strong></p>"
        f"<p><em>Recipient:</em> {recipient}</p>"
        f"<p><em>Reason:</em> {reason}</p>"
        f"<p>Contact marked UNQUALIFIED. Do not retry without re-verifying address.</p>"
    )
    note_payload = {
        "properties": {
            "hs_note_body": note_body,
            "hs_timestamp": int(time.time() * 1000),
        },
        "associations": [
            {
                "to": {"id": contact_id},
                "types": [{"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": 202}],
            }
        ],
    }
    hs_request("POST", "/crm/v3/objects/notes", note_payload)
    log(f"  ✓ BOUNCE  → {recipient} (contact {contact_id})  reason: {reason[:80]}")
    return True


def log_reply_note(contact_id, sender, subject, snippet):
    """Create a Note engagement on the contact and bump status to CONNECTED."""
    note_body = f"<p><strong>Reply received via Gmail bridge</strong></p>" \
                f"<p><em>Subject:</em> {subject}</p>" \
                f"<p>{snippet[:500]}</p>"
    note_payload = {
        "properties": {
            "hs_note_body": note_body,
            "hs_timestamp": int(time.time() * 1000),
        },
        "associations": [
            {
                "to": {"id": contact_id},
                "types": [{"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": 202}],
            }
        ],
    }
    status, _ = hs_request("POST", "/crm/v3/objects/notes", note_payload)
    if status not in (200, 201):
        log(f"  ✗ REPLY note creation failed for {sender} ({status})")
        return False
    # Advance lead status
    hs_request("PATCH", f"/crm/v3/objects/contacts/{contact_id}",
               {"properties": {"hs_lead_status": "CONNECTED"}})
    log(f"  ✓ REPLY   → {sender} (contact {contact_id})  subject: {subject[:60]}")
    return True


def extract_snippet(msg):
    text = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                try:
                    payload = part.get_payload(decode=True)
                    if payload:
                        text = payload.decode("utf-8", errors="replace")
                        break
                except Exception:
                    pass
    else:
        try:
            text = (msg.get_payload(decode=True) or b"").decode("utf-8", errors="replace")
        except Exception:
            pass
    # Strip quoted prior-message lines
    keep = [l for l in text.splitlines() if not l.strip().startswith(">") and l.strip()]
    return " ".join(keep)[:800]


def main():
    state = load_state()
    log(f"=== IMAP bridge run (last_uid={state['last_uid']}) ===")

    log("Fetching HubSpot contacts…")
    contacts_by_email = fetch_hubspot_contacts_by_email()
    log(f"  Loaded {len(contacts_by_email)} contacts")

    log("Connecting to Gmail IMAP…")
    M = imaplib.IMAP4_SSL("imap.gmail.com", 993)
    M.login(GMAIL_USER, GMAIL_PASS)
    M.select("INBOX")

    # Search messages newer than last_uid (or all messages if first run)
    if state["last_uid"]:
        typ, data = M.uid("search", None, f"UID {state['last_uid']+1}:*")
    else:
        # First run: scan only last 30 days
        cutoff = (datetime.now() - timedelta(days=30)).strftime("%d-%b-%Y")
        typ, data = M.uid("search", None, f"SINCE {cutoff}")

    uids = data[0].split()
    log(f"  {len(uids)} messages to inspect")

    bounces = 0
    replies = 0
    max_uid = state["last_uid"]

    for uid_b in uids:
        uid = int(uid_b)
        if uid <= state["last_uid"]:
            continue
        if uid > max_uid:
            max_uid = uid

        typ, msg_data = M.uid("fetch", uid_b, "(RFC822)")
        if typ != "OK" or not msg_data or not msg_data[0]:
            continue
        raw = msg_data[0][1]
        msg = email.message_from_bytes(raw)

        from_addr = parseaddr(msg.get("From", ""))[1].lower()
        subject = (msg.get("Subject") or "").strip()

        # Bounce path
        if any(from_addr.startswith(prefix) for prefix in BOUNCE_SENDERS) or "delivery" in subject.lower() and "fail" in subject.lower():
            failed = extract_failed_recipient(msg)
            if failed and failed in contacts_by_email:
                cid = contacts_by_email[failed]
                if uid not in state["processed_bounces"]:
                    reason = extract_bounce_reason(msg)
                    if mark_bounced(cid, failed, reason):
                        bounces += 1
                        state["processed_bounces"].append(uid)
            continue

        # Reply path — sender's email matches a known contact
        if from_addr in contacts_by_email and from_addr not in SELF_SKIP:
            cid = contacts_by_email[from_addr]
            if uid not in state["processed_replies"]:
                snippet = extract_snippet(msg)
                if log_reply_note(cid, from_addr, subject, snippet):
                    replies += 1
                    state["processed_replies"].append(uid)

    state["last_uid"] = max_uid
    save_state(state)
    M.logout()

    log(f"=== Done. Bounces logged: {bounces}  Replies logged: {replies}  Max UID: {max_uid} ===")
    log("")


if __name__ == "__main__":
    main()
