#!/usr/bin/env python3
"""
Sunday weekly trends send.

Pulls the latest weekly trends HTML (Saturday-generated) and sends as a
single broadcast to all three subscriber lists. Unlike the daily brief,
trends are inherently cross-audience — same body to everyone.

Run on Sunday morning via the `weekly-trends-send` cron.
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


def build_week_label(trends_path: Path) -> str:
    """Best-effort: extract the Mon–Sat date range from the markdown sibling.

    Falls back to a single date from the filename if the markdown isn't present
    or doesn't have a parseable header.
    """
    md_sibling = trends_path.with_suffix(".md")
    if md_sibling.exists():
        text = md_sibling.read_text()
        m = re.search(r"\*\*Week of ([^*]+)\*\*", text)
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
    today = datetime.now()
    date_str = today.strftime("%Y-%m-%d")
    marker = MARKER_DIR / f".weekly-trends-sent-{date_str}"

    log(f"=== Weekly trends send start: {date_str} ===")

    if marker.exists():
        log(f"Already sent for {date_str} — skipping (delete {marker.name} to force)")
        return 0

    trends_path = find_latest_trends_html(today)
    if not trends_path:
        log("ERROR: no trends HTML found in the last 14 days — aborting")
        return 1

    log(f"Using trends file: {trends_path.name}")

    # Extract the body content from the standalone trends HTML
    raw = trends_path.read_text()
    m = re.search(r"<body[^>]*>(.*?)</body>", raw, re.DOTALL | re.IGNORECASE)
    body = m.group(1).strip() if m else raw

    # The standalone trends pages carry their own <style> block. The branded
    # email wrapper expects bare body content, so strip the trends-page
    # container chrome and let the wrapper's styles take over.
    body = re.sub(r"<style[^>]*>.*?</style>", "", body, flags=re.DOTALL | re.IGNORECASE)
    body = re.sub(r'</?(div|main|header)[^>]*>', "", body, flags=re.IGNORECASE)

    week_label = build_week_label(trends_path)
    subject = f"South Florida Weekly Trends — Week of {week_label}"
    html = sdb.build_email_html(body, date_str, subject)

    password, hs_token = sdb.load_credentials()

    # Pull all three lists, dedupe across them — a subscriber on multiple
    # segment lists should still receive only ONE trends email.
    all_emails = []
    for list_id in LIST_IDS:
        emails = sdb.get_list_emails(list_id, hs_token)
        log(f"  list {list_id}: {len(emails)} subscribers")
        all_emails.extend(emails)
    deduped = dedupe(all_emails)
    log(f"  deduped total: {len(deduped)} unique subscribers")

    if not deduped:
        log("No subscribers — exiting without sending")
        marker.touch()
        return 0

    sent, failed = sdb.send_segment(deduped, subject, html, password)
    log(f"  Sent: {sent} | Failed: {len(failed)}")
    for email, err in failed:
        log(f"    FAILED {email}: {err}")

    log(f"=== Done — sent: {sent} | failed: {len(failed)} ===")
    marker.touch()
    return 0


if __name__ == "__main__":
    sys.exit(main())
