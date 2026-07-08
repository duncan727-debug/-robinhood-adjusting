#!/usr/bin/env python3
"""
Sunday weekly trends send.

Pulls the latest weekly trends HTML (Saturday-generated) and sends as a
single broadcast to all three subscriber lists. Unlike the daily brief,
trends are inherently cross-audience — same body to everyone.

Safety default: this script does not send unless --send-approved is passed and
publication/trends/YYYY-MM-DD/send-package.json exists for the trends issue.
"""
from __future__ import annotations

import re
import smtplib
import sys
import time
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from workspace_config import REPO_ROOT

# Reuse the daily-brief helpers (HubSpot list fetch, branded HTML wrapper, etc.)
sys.path.insert(0, str(Path(__file__).resolve().parent))
import importlib.util
from publication_guard import assert_publication_safe
spec = importlib.util.spec_from_file_location(
    "sdb",
    str(Path(__file__).resolve().parent / "send-daily-brief.py"),
)
sdb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sdb)

WORKSPACE = REPO_ROOT
TRENDS_DIR = WORKSPACE / "content" / "trends"
LOG_PATH = WORKSPACE / "scripts" / "newsletter-send.log"
MARKER_DIR = WORKSPACE / "scripts"

# Reuse the same list IDs the daily brief sends to. Trends go to all three.
LIST_IDS = ["18", "19", "20"]


def parse_cli(argv: list[str]) -> tuple[str | None, bool, str | None]:
    date_str = None
    send_approved = False
    test_to = None
    idx = 0
    while idx < len(argv):
        arg = argv[idx]
        if arg == "--send-approved":
            send_approved = True
        elif arg == "--test-to":
            idx += 1
            if idx >= len(argv):
                raise SystemExit("ERROR: --test-to requires an email address")
            test_to = argv[idx].strip().lower()
            if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", test_to):
                raise SystemExit(f"ERROR: invalid --test-to email address: {test_to}")
        elif arg.startswith("-"):
            raise SystemExit(f"ERROR: Unknown option {arg}")
        elif date_str is None:
            if not re.match(r"^\d{4}-\d{2}-\d{2}$", arg):
                raise SystemExit(f"ERROR: trends date must be YYYY-MM-DD, got {arg}")
            date_str = arg
        else:
            raise SystemExit(f"ERROR: Unexpected extra argument {arg}")
        idx += 1
    if test_to and not send_approved:
        raise SystemExit("ERROR: --test-to requires --send-approved")
    return date_str, send_approved, test_to


def log(message: str) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"[{ts}] {message}")
    with open(LOG_PATH, "a") as f:
        f.write(f"[{ts}] {message}\n")


def find_latest_trends_html(today: datetime) -> Path | None:
    """Find the most recent trends HTML on or before `today` (looks back 14 days)."""
    for back in range(14):
        d = today - timedelta(days=back)
        candidate = TRENDS_DIR / f"{d.strftime('%Y-%m-%d')}.html"
        if candidate.exists():
            return candidate
    return None


def find_trends_html(date_str: str | None, today: datetime) -> Path | None:
    if date_str:
        candidate = TRENDS_DIR / f"{date_str}.html"
        return candidate if candidate.exists() else None
    return find_latest_trends_html(today)


def require_send_package(trends_date: str) -> Path:
    package_path = WORKSPACE / "publication" / "trends" / trends_date / "send-package.json"
    if not package_path.exists():
        raise SystemExit(
            "ERROR: weekly trends send package missing. Run "
            f"`python3 scripts/prepare-weekly-trends-send-package.py {trends_date} --write` "
            "and get explicit approval before sending."
        )
    return package_path


def build_week_label(trends_path: Path) -> str:
    """Best-effort: extract the Mon-Sat date range from source files.

    Falls back to a single date from the filename if the markdown isn't present
    or doesn't have a parseable header.
    """
    md_sibling = trends_path.with_suffix(".md")
    if md_sibling.exists():
        text = md_sibling.read_text()
        m = re.search(r"\*\*Week of ([^*]+)\*\*", text)
        if m:
            return m.group(1).strip()
        m = re.search(r"^\*\*([^*]+)\*\*\s*\|", text, flags=re.MULTILINE)
        if m:
            return m.group(1).strip()
    html_text = trends_path.read_text(errors="replace")
    m = re.search(r'<div class="date-info">Week of ([^|<]+)', html_text)
    if m:
        return m.group(1).strip()
    return trends_path.stem


def dedupe(emails: list[str]) -> list[str]:
    seen, out = set(), []
    for e in emails:
        key = e.strip().lower()
        if key and key not in seen:
            seen.add(key)
            out.append(key)
    return out


def main() -> int:
    requested_date, send_approved, test_to = parse_cli(sys.argv[1:])
    today = datetime.now()
    mode = "NO-SEND PREFLIGHT"
    if send_approved and test_to:
        mode = f"TEST-SEND to {test_to}"
    elif send_approved:
        mode = "SEND-APPROVED"

    log(f"=== Weekly trends send start ({mode}) ===")

    trends_path = find_trends_html(requested_date, today)
    if not trends_path:
        log("ERROR: no trends HTML found in the last 14 days — aborting")
        return 1

    trends_date = trends_path.stem
    marker = MARKER_DIR / f".weekly-trends-sent-{trends_date}"
    if marker.exists() and not test_to:
        log(f"Already sent for {trends_date} — skipping (delete {marker.name} to force)")
        return 0

    log(f"Using trends file: {trends_path.name}")
    if send_approved:
        package_path = require_send_package(trends_date)
        log(f"Approval package found: {package_path.relative_to(WORKSPACE)}")
        if test_to:
            log("TEST-SEND mode: real subscriber lists will not receive email.")
    else:
        log("NO-SEND mode: pass --send-approved after Duncan approves the weekly package.")

    # Extract the body content from the standalone trends HTML
    raw = trends_path.read_text()
    assert_publication_safe(raw, trends_path)
    m = re.search(r"<body[^>]*>(.*?)</body>", raw, re.DOTALL | re.IGNORECASE)
    body = m.group(1).strip() if m else raw

    # The standalone trends pages carry their own <style> block. The branded
    # email wrapper expects bare body content, so strip the trends-page
    # container chrome and let the wrapper's styles take over.
    body = re.sub(r"<style[^>]*>.*?</style>", "", body, flags=re.DOTALL | re.IGNORECASE)
    body = re.sub(r'</?(div|main|header)[^>]*>', "", body, flags=re.IGNORECASE)

    week_label = build_week_label(trends_path)
    subject = f"South Florida Weekly Trends — Week of {week_label}"
    html = sdb.build_email_html(body, trends_date, subject)

    password, hs_token = sdb.load_credentials(require_gmail=send_approved)

    # Pull all three lists, dedupe across them — a subscriber on multiple
    # segment lists should still receive only ONE trends email.
    all_emails = []
    for list_id in LIST_IDS:
        emails = sdb.get_list_emails(list_id, hs_token)
        log(f"  list {list_id}: {len(emails)} subscribers")
        all_emails.extend(emails)
    deduped = dedupe(all_emails)
    log(f"  deduped total: {len(deduped)} unique subscribers")

    if test_to:
        deduped = [test_to]
        log(f"  TEST-SEND recipient override: {test_to}")
    elif not deduped:
        log("No subscribers — exiting without sending")
        if send_approved:
            marker.touch()
        return 0

    if not send_approved:
        log(f"=== Done — no emails sent | planned recipients: {len(deduped)} ===")
        return 0

    sent, failed = sdb.send_segment(deduped, subject, html, password)
    log(f"  Sent: {sent} | Failed: {len(failed)}")
    for email, err in failed:
        log(f"    FAILED {email}: {err}")

    if test_to:
        log(f"=== Done — test emails sent: {sent} | failed: {len(failed)} ===")
        log("TEST-SEND mode: weekly sent marker not created.")
    else:
        log(f"=== Done — sent: {sent} | failed: {len(failed)} ===")
        marker.touch()
    return 0


if __name__ == "__main__":
    sys.exit(main())
