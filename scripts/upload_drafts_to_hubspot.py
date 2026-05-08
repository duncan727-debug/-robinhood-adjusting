#!/usr/bin/env python3
"""
Upload backlogged outreach email drafts to HubSpot.
For each draft file:
  1. Find or create the contact + company in HubSpot
  2. Log the email body as a Note engagement
  3. Create a Task for Duncan to review and send manually

Usage:
  python3 upload_drafts_to_hubspot.py [--dry-run]
"""

import json
import os
import re
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE = Path("/Users/victoria/.openclaw/workspace")
DRAFTS_ROOT = WORKSPACE / "crm" / "drafts"
LOG_PATH = WORKSPACE / "scripts" / "hubspot_draft_upload.log"
UPLOADED_PATH = WORKSPACE / "crm" / ".uploaded_drafts.json"

DRAFT_DATES = [
    "2026-04-23",
    "2026-04-24",
    "2026-04-27",
    "2026-04-28",
    "2026-04-29",
    "2026-04-30",
    "2026-05-01",
    "2026-05-02",
    "2026-05-04",
    "2026-05-05",
    "2026-05-06",
]

DRY_RUN = "--dry-run" in sys.argv


def load_uploaded() -> set:
    if UPLOADED_PATH.exists():
        return set(json.loads(UPLOADED_PATH.read_text()))
    return set()


def mark_uploaded(source_file: str, uploaded: set):
    uploaded.add(source_file)
    if not DRY_RUN:
        UPLOADED_PATH.write_text(json.dumps(sorted(uploaded), indent=2))

_TOKEN = None


def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_PATH, "a") as f:
        f.write(line + "\n")


def load_token():
    global _TOKEN
    setup = WORKSPACE / "scripts" / "setup-hubspot-lists.py"
    m = re.search(r'TOKEN\s*=\s*"([^"]+)"', setup.read_text())
    if not m:
        token = os.environ.get("HUBSPOT_API_KEY", "")
        if not token:
            sys.exit("ERROR: No HubSpot token found.")
        _TOKEN = token
    else:
        _TOKEN = m.group(1)


def hs(method, path, body=None, retries=3):
    url = f"https://api.hubapi.com{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {_TOKEN}")
    req.add_header("Content-Type", "application/json")
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            raw = b""
            try:
                raw = e.read()
            except Exception:
                pass
            if e.code == 429:
                time.sleep(2 ** attempt)
                continue
            try:
                return e.code, json.loads(raw)
            except Exception:
                return e.code, {"raw": raw.decode(errors="replace")}
    return 0, {}


SKIP_FILES = {
    "DAILY-STATUS", "OUTREACH-SUMMARY", "status-summary",
    "DAILY-SUMMARY", "00-BATCH-SUMMARY", "DELIVERY-COMPLETE",
}

def parse_draft(path: Path):
    text = path.read_text()

    # Skip non-draft files
    if any(s in path.name for s in SKIP_FILES):
        return None

    def bold(label):
        m = re.search(rf"\*\*{label}:\*\*\s*(.+)", text)
        return m.group(1).strip() if m else ""

    # ── Format A: structured (May 4-5) ──────────────────────────────────────
    # Has **Org ID:**, **Contact:**, **Subject:** bold headers
    org_id = bold("Org ID")
    if org_id:
        contact_raw = bold("Contact")
        contact_name = contact_raw.split(",")[0].strip() if contact_raw else ""
        phone = bold("Phone")
        subject = bold("Subject")
        body_match = re.search(
            r"\*\*Subject:\*\*.*?\n\n(.*?)(?=\n---\n|\n## NOTES FOR DUNCAN)",
            text, re.DOTALL,
        )
        body_md = body_match.group(1).strip() if body_match else ""
        h1 = re.search(r"^# (.+)", text, re.MULTILINE)
        raw_title = h1.group(1).split("—")[0].strip() if h1 else org_id
        company_name = re.sub(r"^Follow-Up Outreach:\s*", "", raw_title).strip()

        if subject and body_md:
            return {"org_id": org_id, "company_name": company_name,
                    "contact_name": contact_name, "phone": phone,
                    "subject": subject, "body": body_md, "source_file": str(path)}
        return None

    # ── Format B: semi-structured (Apr 24) ──────────────────────────────────
    # Has **Organization:**, **Phone:**, ## Email Draft, **Subject:**
    organization = bold("Organization")
    if organization:
        phone = bold("Phone")
        contact_raw = bold("Recipient")
        contact_name = "" if "No contact" in contact_raw else contact_raw.split(",")[0].strip()
        subject_m = re.search(r"\*\*Subject:\*\*\s*(.+)", text)
        subject = subject_m.group(1).strip() if subject_m else ""
        body_match = re.search(
            r"\*\*Subject:\*\*.*?\n---\n\n(.*?)(?=\n---|\Z)",
            text, re.DOTALL,
        )
        body_md = body_match.group(1).strip() if body_match else ""
        org_id = path.stem.split("-")[0] + "-" + path.stem.split("-")[1] if "-" in path.stem else path.stem

        if subject and body_md:
            return {"org_id": org_id, "company_name": organization,
                    "contact_name": contact_name, "phone": phone,
                    "subject": subject, "body": body_md, "source_file": str(path)}
        return None

    # ── Format C: minimal (Apr 27) ───────────────────────────────────────────
    # Starts with "Subject: ..." line, body follows, ends with "---"
    subject_m = re.search(r"^Subject:\s*(.+)", text, re.MULTILINE)
    if subject_m:
        subject = subject_m.group(1).strip()
        # Company from subject: "... at CompanyName" or "... for CompanyName ..."
        co_m = re.search(r" at (.+?)(?:\s*—|$)", subject) or \
               re.search(r"^(?:Insurance Claim Support|Collaboration Opportunity|Partnership Opportunity) for (.+?)(?:\s+and\b|\s*—|$)", subject)
        company_name = co_m.group(1).strip() if co_m else path.stem
        # Body: after subject line until first ---
        body_match = re.search(r"^Subject:.+\n\n(.*?)(?=\n---)", text, re.DOTALL | re.MULTILINE)
        body_md = body_match.group(1).strip() if body_match else ""
        # Org ID from filename stem
        org_id = re.sub(r"-[^-]+-[^-]+$", "", path.stem)  # strip doubled suffix
        # Phone from body
        phone_m = re.search(r"\b(\d{3}[-.\s]\d{3}[-.\s]\d{4})\b", text)
        phone = phone_m.group(1) if phone_m else ""

        if subject and body_md:
            return {"org_id": org_id, "company_name": company_name,
                    "contact_name": "", "phone": phone,
                    "subject": subject, "body": body_md, "source_file": str(path)}

    return None


def search_contact(contact_name: str, phone: str):
    """Return HubSpot contact ID if found by name."""
    if not contact_name:
        return None
    first, *rest = contact_name.split()
    last = rest[-1] if rest else ""
    status, data = hs("POST", "/crm/v3/objects/contacts/search", {
        "filterGroups": [{
            "filters": [
                {"propertyName": "firstname", "operator": "EQ", "value": first},
                {"propertyName": "lastname", "operator": "EQ", "value": last},
            ]
        }]
    })
    if status == 200 and data.get("results"):
        return str(data["results"][0]["id"])

    # fallback: phone search
    if phone:
        status, data = hs("POST", "/crm/v3/objects/contacts/search", {
            "filterGroups": [{
                "filters": [{"propertyName": "phone", "operator": "EQ", "value": phone}]
            }]
        })
        if status == 200 and data.get("results"):
            return str(data["results"][0]["id"])

    return None


def create_contact(draft: dict):
    if not draft["contact_name"]:
        return None
    first, *rest = draft["contact_name"].split()
    last = rest[-1] if rest else ""
    props = {
        "firstname": first,
        "lastname": last,
        "company": draft["company_name"],
    }
    if draft["phone"]:
        props["phone"] = draft["phone"]

    status, data = hs("POST", "/crm/v3/objects/contacts", {"properties": props})
    if status in (200, 201):
        return str(data["id"])
    log(f"  ✗ Failed to create contact {draft['contact_name']}: {data}")
    return None


def search_company(name: str):
    status, data = hs("POST", "/crm/v3/objects/companies/search", {
        "filterGroups": [{
            "filters": [{"propertyName": "name", "operator": "EQ", "value": name}]
        }]
    })
    if status == 200 and data.get("results"):
        return str(data["results"][0]["id"])
    return None


def create_company(name: str):
    status, data = hs("POST", "/crm/v3/objects/companies", {
        "properties": {"name": name}
    })
    if status in (200, 201):
        return str(data["id"])
    log(f"  ✗ Failed to create company {name}: {data}")
    return None


def associate(contact_id: str, company_id: str):
    hs("PUT",
       f"/crm/v3/objects/contacts/{contact_id}/associations/companies/{company_id}/contact_to_company")


def create_note(contact_id: str, company_id: str, draft: dict) -> bool:
    note_body = (
        f"DRAFT EMAIL — READY TO SEND\n\n"
        f"Subject: {draft['subject']}\n\n"
        f"---\n\n"
        f"{draft['body']}\n\n"
        f"---\n"
        f"Source: {Path(draft['source_file']).name}"
    )
    body = {
        "properties": {
            "hs_note_body": note_body,
            "hs_timestamp": str(int(datetime.now(tz=timezone.utc).timestamp() * 1000)),
        },
        "associations": []
    }
    if contact_id:
        body["associations"].append({
            "to": {"id": contact_id},
            "types": [{"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": 202}]
        })
    if company_id:
        body["associations"].append({
            "to": {"id": company_id},
            "types": [{"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": 190}]
        })

    status, data = hs("POST", "/crm/v3/objects/notes", body)
    return status in (200, 201)


def create_task(contact_id: str, company_id: str, draft: dict) -> bool:
    due_ts = int((datetime.now(tz=timezone.utc).timestamp() + 86400) * 1000)  # due tomorrow
    body = {
        "properties": {
            "hs_task_subject": f"Review & Send: {draft['subject']}",
            "hs_task_body": (
                f"Email draft ready for {draft['contact_name']} at {draft['company_name']}.\n\n"
                f"Review the associated note, copy the email, and send manually from Gmail.\n\n"
                f"Phone: {draft['phone']}"
            ),
            "hs_task_status": "NOT_STARTED",
            "hs_task_type": "EMAIL",
            "hs_timestamp": str(due_ts),
        },
        "associations": []
    }
    if contact_id:
        body["associations"].append({
            "to": {"id": contact_id},
            "types": [{"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": 204}]
        })
    if company_id:
        body["associations"].append({
            "to": {"id": company_id},
            "types": [{"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": 192}]
        })

    status, data = hs("POST", "/crm/v3/objects/tasks", body)
    return status in (200, 201)


def process_draft(draft: dict, uploaded: set):
    name = draft["contact_name"]
    company = draft["company_name"]
    source = draft["source_file"]

    if source in uploaded:
        log(f"  Skipping (already uploaded): {Path(source).name}")
        return True

    log(f"  Processing: {name} @ {company}")

    if DRY_RUN:
        log(f"    [DRY RUN] Would upload: {draft['subject']}")
        return True

    # Find or create contact
    contact_id = search_contact(name, draft["phone"])
    if contact_id:
        log(f"    Found contact: {contact_id}")
    else:
        contact_id = create_contact(draft)
        if contact_id:
            log(f"    Created contact: {contact_id}")

    # Find or create company
    company_id = search_company(company)
    if company_id:
        log(f"    Found company: {company_id}")
    else:
        company_id = create_company(company)
        if company_id:
            log(f"    Created company: {company_id}")

    # Associate contact ↔ company
    if contact_id and company_id:
        associate(contact_id, company_id)

    # Create note with draft content
    if create_note(contact_id, company_id, draft):
        log(f"    ✓ Note created")
    else:
        log(f"    ✗ Note failed")

    # Create task for Duncan
    if create_task(contact_id, company_id, draft):
        log(f"    ✓ Task created: Review & Send")
    else:
        log(f"    ✗ Task failed")

    mark_uploaded(source, uploaded)
    time.sleep(0.3)
    return True


def main():
    load_token()
    mode = "DRY RUN" if DRY_RUN else "LIVE"
    log(f"=== Draft upload start ({mode}) ===")

    uploaded = load_uploaded()
    log(f"Already uploaded: {len(uploaded)} drafts")

    drafts = []
    for date_str in DRAFT_DATES:
        draft_dir = DRAFTS_ROOT / date_str
        if not draft_dir.exists():
            log(f"  No drafts dir for {date_str}, skipping")
            continue
        for f in sorted(draft_dir.glob("*.md")):
            d = parse_draft(f)
            if d:
                drafts.append(d)

    log(f"Found {len(drafts)} drafts total")

    success = 0
    for draft in drafts:
        if process_draft(draft, uploaded):
            success += 1

    log(f"=== Done — {success}/{len(drafts)} processed ===")


if __name__ == "__main__":
    main()
