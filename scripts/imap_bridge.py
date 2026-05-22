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
REPLY_QUEUE_DIR = WORKSPACE / "crm" / "reply_queue"

BOUNCE_SENDERS = (
    "mailer-daemon@",
    "postmaster@",
    "mail-daemon@",
    "noreply@bounce",
)

SELF_SKIP = {"duncanlittlejohn727@gmail.com"}

CALENDLY_SENDERS = (
    "no-reply@calendly.com",
    "notifications@calendly.com",
)

CALENDLY_PIPELINE = "default"
CALENDLY_STAGE_BOOKED = "3671479994"  # Virtual Review Booked (used for all Calendly bookings until split stages exist)
CALENDLY_INVITEE_EMAIL_RE = re.compile(
    r"(?:Invitee\s*Email|Invitee:|<a[^>]*href=\"mailto:)([\w.\-+@]+@[\w.\-]+\.[a-z]{2,})",
    re.I,
)
CALENDLY_INVITEE_NAME_RE = re.compile(r"Invitee:\s*([^\n<]+)", re.I)
# Map Calendly event slug → (deal-name prefix, medium label)
CALENDLY_EVENT_MAP = {
    "virtual-review": ("Virtual Review", "Google Meet (video)"),
    "30min":          ("Phone Consult",  "Phone call (15 min)"),
}
# Only match URLs under Duncan's Calendly handle so we don't pick up reschedule/cancel link slugs
CALENDLY_EVENT_URL_RE = re.compile(
    r"https?://calendly\.com/duncanlittlejohn727/([\w\-]+)(?:[/?][^\s\"<>]*)?",
    re.I,
)

FAILED_RECIPIENT_RE = re.compile(
    r"(?:Final-Recipient|X-Failed-Recipients|original_address|to=<)[^\n]*?([\w.\-+]+@[\w.\-]+\.[a-z]{2,})",
    re.I,
)
# Gmail soft-bounce notifications use prose, not DSN headers: "delivering your message to <email>"
FAILED_RECIPIENT_PROSE_RE = re.compile(
    r"delivering your message to\s+([\w.\-+]+@[\w.\-]+\.[a-z]{2,})",
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
        state = json.loads(STATE_PATH.read_text())
        state.setdefault("processed_calendly", [])
        return state
    return {"last_uid": 0, "processed_bounces": [], "processed_replies": [], "processed_calendly": []}


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
    m2 = FAILED_RECIPIENT_PROSE_RE.search(body_text)
    if m2:
        return m2.group(1).strip().lower()
    return None


def is_soft_bounce(msg):
    """Detect transient delivery failures (Gmail "(Delay)" notifications).

    Hard bounces have subject "(Failure)" or body containing 5xx SMTP codes.
    Soft bounces have "(Delay)" subject or body text like "Gmail will retry".
    """
    subj = (msg.get("Subject") or "").lower()
    if "(delay)" in subj or "incomplete" in subj:
        return True
    body_text = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                try:
                    payload = part.get_payload(decode=True)
                    if payload:
                        body_text = payload.decode("utf-8", errors="replace")
                        break
                except Exception:
                    pass
    else:
        try:
            body_text = (msg.get_payload(decode=True) or b"").decode("utf-8", errors="replace")
        except Exception:
            body_text = ""
    body_l = body_text.lower()
    if "gmail will retry" in body_l or "temporary problem" in body_l or "delivery incomplete" in body_l:
        return True
    return False


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
        if any(t in line.lower() for t in (
            "smtp error", "550", "554", "5.1.", "5.2.", "5.7.",
            "domain not", "no such user", "mailbox unavailable", "user unknown",
            "did not accept", "timed out", "temporary problem", "could not be delivered",
        )):
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


def mark_soft_bounce(contact_id, recipient, reason):
    """Attach a note about a transient delivery hiccup. Does NOT change lead status —
    Gmail is still retrying, and the contact may yet receive the message."""
    note_body = (
        f"<p><strong>Soft bounce detected via Gmail bridge</strong></p>"
        f"<p><em>Recipient:</em> {recipient}</p>"
        f"<p><em>Reason:</em> {reason}</p>"
        f"<p>Gmail is retrying delivery. Contact NOT marked unqualified — watch for a follow-up hard bounce if delivery ultimately fails.</p>"
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
    status, _ = hs_request("POST", "/crm/v3/objects/notes", note_payload)
    if status not in (200, 201):
        log(f"  ✗ SOFT BOUNCE note failed for {recipient} ({status})")
        return False
    log(f"  ⚠ SOFT BOUNCE → {recipient} (contact {contact_id})  reason: {reason[:80]}")
    return True


def log_reply_note(contact_id, sender, subject, snippet):
    """Create a Note engagement on the contact and bump status to CONNECTED.

    Returns the contact's directory_listing_status BEFORE this call (so the
    caller can detect "this is a qualifying-questions answer reply" and route
    it to parse_listing_answers.py).
    """
    # Read current status first so we don't downgrade listed → pending_add.
    _, cur = hs_request("GET",
        f"/crm/v3/objects/contacts/{contact_id}?properties=directory_listing_status")
    prior_status = (cur.get("properties") or {}).get("directory_listing_status")

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
        return None
    # Advance lead status. Only set directory_listing_status=pending_add on the
    # FIRST YES reply (when it's currently null/empty). Preserve listed/pending_add
    # so a subsequent answers-reply doesn't reset the workflow.
    contact_props = {"hs_lead_status": "CONNECTED"}
    if not prior_status:
        contact_props["directory_listing_status"] = "pending_add"
    hs_request("PATCH", f"/crm/v3/objects/contacts/{contact_id}",
               {"properties": contact_props})
    # Move associated deal(s) to 'Responded' stage so the pipeline reflects the reply.
    _, deal_data = hs_request("GET", f"/crm/v3/objects/contacts/{contact_id}/associations/deals")
    for assoc in (deal_data.get("results") or []):
        did = assoc.get("id") or assoc.get("toObjectId")
        if did:
            hs_request("PATCH", f"/crm/v3/objects/deals/{did}",
                       {"properties": {"dealstage": "presentationscheduled"}})
    log(f"  ✓ REPLY   → {sender} (contact {contact_id})  subject: {subject[:60]}")
    return prior_status or ""


def parse_calendly_booking(msg):
    """Extract (invitee_email, invitee_name, event_label, event_slug, medium) from a Calendly host notification.

    Returns None if the message doesn't look like a Calendly *booking confirmation*
    (we explicitly skip cancellations and reschedules — those need different handling).
    """
    subject = (msg.get("Subject") or "").strip()
    subj_l = subject.lower()
    if "new event" not in subj_l:
        return None
    # Skip cancellations/reschedules — only react to fresh bookings
    if any(x in subj_l for x in ("canceled", "cancelled", "rescheduled")):
        return None

    body_text = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() in ("text/plain", "text/html"):
                try:
                    payload = part.get_payload(decode=True)
                    if payload:
                        body_text += "\n" + payload.decode("utf-8", errors="replace")
                except Exception:
                    pass
    else:
        try:
            body_text = (msg.get_payload(decode=True) or b"").decode("utf-8", errors="replace")
        except Exception:
            return None

    em = CALENDLY_INVITEE_EMAIL_RE.search(body_text)
    if not em:
        return None
    invitee_email = em.group(1).strip().lower()
    if invitee_email == GMAIL_USER.lower():
        return None  # That's Duncan, not the invitee

    nm = CALENDLY_INVITEE_NAME_RE.search(body_text)
    invitee_name = nm.group(1).strip() if nm else invitee_email.split("@")[0]

    # Event label is usually after "New Event:" in the subject
    event_label = subject.replace("New Event:", "").strip().split(" - ")[0].strip() or "Calendly Booking"

    # Identify which event was booked via slug in the body URL
    slug_match = CALENDLY_EVENT_URL_RE.search(body_text)
    event_slug = slug_match.group(1).lower() if slug_match else ""
    medium = CALENDLY_EVENT_MAP.get(event_slug, ("", "Unknown medium"))[1]

    return invitee_email, invitee_name, event_label, event_slug, medium


def upsert_contact_for_calendly(email_addr, name):
    """Find contact by email; create with NEW status if missing. Returns contact_id."""
    search_payload = {
        "filterGroups": [{"filters": [{"propertyName": "email", "operator": "EQ", "value": email_addr}]}],
        "properties": ["email"],
        "limit": 1,
    }
    status, data = hs_request("POST", "/crm/v3/objects/contacts/search", search_payload)
    if status == 200 and data.get("results"):
        return data["results"][0]["id"]

    first = name.split()[0] if name else ""
    last = " ".join(name.split()[1:]) if len(name.split()) > 1 else ""
    create_payload = {"properties": {
        "email": email_addr,
        "firstname": first,
        "lastname": last,
        "lifecyclestage": "lead",
        "hs_lead_status": "NEW",
    }}
    status, data = hs_request("POST", "/crm/v3/objects/contacts", create_payload)
    if status in (200, 201):
        return data.get("id")
    log(f"  ✗ CALENDLY contact upsert failed for {email_addr} ({status})")
    return None


def create_calendly_deal(contact_id, invitee_email, invitee_name, event_label, event_slug, medium):
    """Create a deal in Partner Outreach → Virtual Review Booked, associated with the contact.

    Deal name reflects the actual event (e.g. "Virtual Review — Joe" vs "Phone Consult — Joe").
    A note is attached recording the medium so phone bookings aren't confused with video.
    Idempotent on (contact_id, today): if a deal already exists for this contact
    in this stage today, skip.
    """
    today = datetime.now().strftime("%Y-%m-%d")
    dedupe_payload = {
        "filterGroups": [{"filters": [
            {"propertyName": "dealstage", "operator": "EQ", "value": CALENDLY_STAGE_BOOKED},
            {"propertyName": "associations.contact", "operator": "EQ", "value": contact_id},
        ]}],
        "properties": ["dealname", "createdate"],
        "limit": 5,
    }
    status, data = hs_request("POST", "/crm/v3/objects/deals/search", dedupe_payload)
    if status == 200:
        for d in data.get("results", []):
            created = (d.get("properties", {}).get("createdate") or "")[:10]
            if created == today:
                log(f"  · CALENDLY skip — deal {d['id']} already booked today for contact {contact_id}")
                return d["id"]

    prefix = CALENDLY_EVENT_MAP.get(event_slug, (event_label or "Calendly Booking", ""))[0]
    deal_payload = {
        "properties": {
            "dealname": f"{prefix} — {invitee_name}",
            "pipeline": CALENDLY_PIPELINE,
            "dealstage": CALENDLY_STAGE_BOOKED,
            "amount": "0",
        },
        "associations": [{
            "to": {"id": contact_id},
            "types": [{"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": 3}],
        }],
    }
    status, data = hs_request("POST", "/crm/v3/objects/deals", deal_payload)
    if status not in (200, 201):
        log(f"  ✗ CALENDLY deal create failed for {invitee_email} ({status}): {json.dumps(data)[:200]}")
        return None

    deal_id = data["id"]
    # Attach a note recording the medium + slug so the deal carries context
    note_body = (
        f"<p><strong>Calendly booking detected</strong></p>"
        f"<p><em>Invitee:</em> {invitee_name} &lt;{invitee_email}&gt;</p>"
        f"<p><em>Event:</em> {event_label or '(unknown)'}</p>"
        f"<p><em>Slug:</em> /{event_slug or '(unknown)'}</p>"
        f"<p><em>Medium:</em> {medium}</p>"
    )
    note_payload = {
        "properties": {"hs_note_body": note_body, "hs_timestamp": int(time.time() * 1000)},
        "associations": [{
            "to": {"id": deal_id},
            "types": [{"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": 214}],
        }],
    }
    hs_request("POST", "/crm/v3/objects/notes", note_payload)
    log(f"  ✓ CALENDLY → {invitee_email} → deal {deal_id} ({prefix}, {medium})")
    return deal_id


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


def extract_full_text(msg):
    """Return the plain-text body of a reply with quoted history removed.
    Falls back to stripped HTML if no text/plain part exists."""
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
        if not text:
            for part in msg.walk():
                if part.get_content_type() == "text/html":
                    try:
                        payload = part.get_payload(decode=True)
                        if payload:
                            html = payload.decode("utf-8", errors="replace")
                            text = re.sub(r"<[^>]+>", " ", html)
                            break
                    except Exception:
                        pass
    else:
        try:
            text = (msg.get_payload(decode=True) or b"").decode("utf-8", errors="replace")
        except Exception:
            pass
    # Drop quoted/forwarded blocks: stop at first ">", "On ... wrote:", "From:" header echo
    lines_out = []
    for line in text.splitlines():
        s = line.strip()
        if s.startswith(">"):
            continue
        if re.match(r"On .+ wrote:\s*$", s):
            break
        if re.match(r"From:\s.+<.+@", s):
            break
        if s.startswith("-----Original Message-----"):
            break
        lines_out.append(line)
    return "\n".join(lines_out).strip()


def queue_reply_for_autoresponse(contact_id, sender, subject, full_text, message_id, in_reply_to):
    """Append a reply to today's queue so the auto-reply orchestrator can process it."""
    REPLY_QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    queue_path = REPLY_QUEUE_DIR / f"{datetime.now().strftime('%Y-%m-%d')}.jsonl"
    record = {
        "queued_at": datetime.now(timezone.utc).isoformat(),
        "contact_id": contact_id,
        "sender": sender,
        "subject": subject,
        "message_id": message_id or "",
        "in_reply_to": in_reply_to or "",
        "body": full_text[:8000],
        "status": "pending",
    }
    with queue_path.open("a") as f:
        f.write(json.dumps(record) + "\n")


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
    soft_bounces = 0
    replies = 0
    calendly_deals = 0
    max_uid = state["last_uid"]

    for uid_b in uids:
        uid = int(uid_b)
        if uid <= state["last_uid"]:
            continue
        if uid > max_uid:
            max_uid = uid

        # BODY.PEEK[] preserves the \Seen flag — RFC822 would mark every scanned email as read
        typ, msg_data = M.uid("fetch", uid_b, "(BODY.PEEK[])")
        if typ != "OK" or not msg_data or not msg_data[0]:
            continue
        raw = msg_data[0][1]
        msg = email.message_from_bytes(raw)

        from_addr = parseaddr(msg.get("From", ""))[1].lower()
        subject = (msg.get("Subject") or "").strip()

        # Calendly booking path — runs before bounce/reply since sender domain is distinct
        if any(from_addr.endswith(s) or from_addr == s for s in CALENDLY_SENDERS):
            if uid not in state["processed_calendly"]:
                parsed = parse_calendly_booking(msg)
                if parsed:
                    invitee_email, invitee_name, event_label, event_slug, medium = parsed
                    cid = upsert_contact_for_calendly(invitee_email, invitee_name)
                    if cid and create_calendly_deal(cid, invitee_email, invitee_name, event_label, event_slug, medium):
                        calendly_deals += 1
                state["processed_calendly"].append(uid)
            continue

        # Bounce path
        if any(from_addr.startswith(prefix) for prefix in BOUNCE_SENDERS) or "delivery" in subject.lower() and "fail" in subject.lower():
            failed = extract_failed_recipient(msg)
            if failed and failed in contacts_by_email:
                cid = contacts_by_email[failed]
                if uid not in state["processed_bounces"]:
                    reason = extract_bounce_reason(msg)
                    if is_soft_bounce(msg):
                        if mark_soft_bounce(cid, failed, reason):
                            soft_bounces += 1
                            state["processed_bounces"].append(uid)
                    else:
                        if mark_bounced(cid, failed, reason):
                            bounces += 1
                            state["processed_bounces"].append(uid)
            continue

        # Reply path — sender's email matches a known contact
        if from_addr in contacts_by_email and from_addr not in SELF_SKIP:
            cid = contacts_by_email[from_addr]
            if uid not in state["processed_replies"]:
                snippet = extract_snippet(msg)
                prior_status = log_reply_note(cid, from_addr, subject, snippet)
                if prior_status is not None:
                    replies += 1
                    state["processed_replies"].append(uid)
                    full_text = extract_full_text(msg)
                    # If this contact was awaiting their qualifying-questions
                    # answers (pending_add), route the reply to the parser so it
                    # updates HubSpot properties + sends the welcome email.
                    if prior_status == "pending_add":
                        try:
                            tmp = REPLY_QUEUE_DIR / f"answers_{cid}_{uid}.txt"
                            REPLY_QUEUE_DIR.mkdir(parents=True, exist_ok=True)
                            tmp.write_text(full_text or snippet or "")
                            import subprocess
                            subprocess.Popen([
                                sys.executable,
                                str(WORKSPACE / "scripts" / "parse_listing_answers.py"),
                                str(cid),
                                str(tmp),
                            ])
                            log(f"  ↪ ANSWERS routed to parse_listing_answers.py (contact {cid})")
                        except Exception as e:
                            log(f"  ✗ ANSWERS routing failed for contact {cid}: {e}")
                    queue_reply_for_autoresponse(
                        cid,
                        from_addr,
                        subject,
                        full_text,
                        msg.get("Message-ID", ""),
                        msg.get("In-Reply-To", ""),
                    )

    state["last_uid"] = max_uid
    save_state(state)
    M.logout()

    log(f"=== Done. Hard bounces: {bounces}  Soft bounces: {soft_bounces}  Replies: {replies}  Calendly deals: {calendly_deals}  Max UID: {max_uid} ===")
    log("")


if __name__ == "__main__":
    main()
