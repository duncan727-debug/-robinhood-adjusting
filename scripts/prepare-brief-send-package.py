#!/usr/bin/env python3
"""Prepare a review package for a published daily brief email send.

This tool is read-only against HubSpot and never sends email. It creates a
browser-friendly review package so Duncan can approve recipients, subjects, and
links before a separate send step.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from workspace_config import get_secret, load_dotenv_secrets


ROOT = Path(__file__).resolve().parents[1]
SITE_URL = "https://robinhoodadjusting.com"

SEGMENTS = [
    {"list_id": "18", "key": "homeowner", "label": "South Florida Property Intelligence"},
    {"list_id": "19", "key": "service-provider", "label": "South Florida Trade Professional Brief"},
    {"list_id": "20", "key": "real-estate", "label": "South Florida Real Estate & Insurance Brief"},
]

SUBSCRIBER_STAGES = {"subscriber", "lead", "marketingqualifiedlead", "customer", "evangelist"}
SEND_ALLOWLIST = {"duncanlittlejohn727@gmail.com", "duncanlittlejohnjr@gmail.com"}


@dataclass
class SegmentPackage:
    key: str
    label: str
    list_id: str
    subject: str
    recipients: list[str]
    skipped: list[str]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare a no-send daily brief email package.")
    parser.add_argument("date", help="Brief date in YYYY-MM-DD format.")
    parser.add_argument("--write", action="store_true", help="Write package files under publication/briefs/YYYY-MM-DD/.")
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Skip HubSpot lookup and generate the shell package only.",
    )
    return parser.parse_args()


def validate_date(date_text: str) -> str:
    try:
        return datetime.strptime(date_text, "%Y-%m-%d").strftime("%Y-%m-%d")
    except ValueError as exc:
        raise SystemExit(f"Date must be YYYY-MM-DD, got {date_text!r}") from exc


def display_date(date_text: str) -> str:
    return datetime.strptime(date_text, "%Y-%m-%d").strftime("%B %-d, %Y")


def load_token() -> str:
    load_dotenv_secrets()
    return get_secret("HUBSPOT_API_KEY")


def hubspot_get(path: str, token: str, retries: int = 3) -> dict:
    url = f"https://api.hubapi.com{path}"
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {token}")
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                return json.loads(response.read())
        except urllib.error.HTTPError as exc:
            if exc.code == 429 and attempt < retries - 1:
                time.sleep(2 ** attempt)
                continue
            body = exc.read().decode(errors="replace")
            raise SystemExit(f"HubSpot read failed {exc.code} on {path}: {body[:300]}") from exc
    return {}


def get_list_recipients(list_id: str, token: str) -> tuple[list[str], list[str]]:
    recipients: list[str] = []
    skipped: list[str] = []
    after = None
    while True:
        path = f"/crm/v3/lists/{list_id}/memberships?limit=100"
        if after:
            path += f"&after={after}"
        data = hubspot_get(path, token)
        for member in data.get("results", []):
            contact_id = member.get("recordId")
            if not contact_id:
                continue
            contact = hubspot_get(
                f"/crm/v3/objects/contacts/{contact_id}?properties=email,lifecyclestage",
                token,
            )
            props = contact.get("properties", {})
            email_addr = (props.get("email") or "").strip().lower()
            stage = (props.get("lifecyclestage") or "").strip().lower()
            if not email_addr:
                continue
            if email_addr in SEND_ALLOWLIST or stage in SUBSCRIBER_STAGES:
                recipients.append(email_addr)
            else:
                skipped.append(f"{email_addr} (stage={stage or 'unset'})")
            time.sleep(0.05)
        paging = data.get("paging", {}).get("next", {})
        after = paging.get("after") if paging else None
        if not after:
            break
    return sorted(set(recipients)), sorted(set(skipped))


def load_brief_title(date_text: str) -> str:
    page_path = ROOT / "site" / "briefs" / f"{date_text}.html"
    if not page_path.exists():
        raise SystemExit(f"Published site brief not found: {page_path}")
    page = page_path.read_text(encoding="utf-8")
    h3 = re.search(r"<h3[^>]*>(.*?)</h3>", page, re.S | re.I)
    if h3:
        return re.sub(r"<[^>]+>", "", h3.group(1)).strip()
    title = re.search(r"<title[^>]*>(.*?)</title>", page, re.S | re.I)
    if title:
        return re.sub(r"<[^>]+>", "", title.group(1)).strip()
    return f"South Florida Property Intelligence - {display_date(date_text)}"


def build_packages(date_text: str, offline: bool) -> list[SegmentPackage]:
    date_fmt = display_date(date_text)
    token = "" if offline else load_token()
    packages: list[SegmentPackage] = []
    for segment in SEGMENTS:
        recipients: list[str] = []
        skipped: list[str] = []
        if not offline:
            recipients, skipped = get_list_recipients(segment["list_id"], token)
        packages.append(
            SegmentPackage(
                key=segment["key"],
                label=segment["label"],
                list_id=segment["list_id"],
                subject=f"{segment['label']} - {date_fmt}",
                recipients=recipients,
                skipped=skipped,
            )
        )
    return packages


def render_html(date_text: str, brief_title: str, packages: list[SegmentPackage], offline: bool) -> str:
    generated = datetime.now().strftime("%Y-%m-%d %H:%M")
    rows = []
    for package in packages:
        recipients = "Offline" if offline else str(len(package.recipients))
        skipped = "Offline" if offline else str(len(package.skipped))
        sample = ", ".join(package.recipients[:5]) if package.recipients else "None loaded"
        rows.append(
            f"""
            <section class="card">
              <div class="kicker">HubSpot list {html.escape(package.list_id)}</div>
              <h2>{html.escape(package.label)}</h2>
              <dl>
                <div><dt>Subject</dt><dd>{html.escape(package.subject)}</dd></div>
                <div><dt>Approved link</dt><dd><a href="{SITE_URL}/briefs/{date_text}">{SITE_URL}/briefs/{date_text}</a></dd></div>
                <div><dt>Recipients</dt><dd>{recipients}</dd></div>
                <div><dt>Skipped by guardrail</dt><dd>{skipped}</dd></div>
                <div><dt>Sample</dt><dd>{html.escape(sample)}</dd></div>
              </dl>
            </section>
            """
        )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Brief Send Package - {html.escape(display_date(date_text))}</title>
  <style>
    :root {{ --navy:#0f2d4a; --red:#c41e3a; --gold:#c9922a; --ink:#26313d; --muted:#667085; --line:#dde3ea; --bg:#f6f7f9; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; background:var(--bg); color:var(--ink); font-family:Arial,sans-serif; line-height:1.55; }}
    header {{ background:var(--navy); color:white; padding:28px 24px; border-bottom:5px solid var(--gold); }}
    main {{ max-width:980px; margin:0 auto; padding:28px 20px 56px; }}
    .inner {{ max-width:980px; margin:0 auto; }}
    .kicker {{ color:var(--red); text-transform:uppercase; letter-spacing:1.7px; font-size:12px; font-weight:700; }}
    h1 {{ margin:8px 0 10px; font-family:Georgia,'Times New Roman',serif; font-size:34px; line-height:1.15; }}
    h2 {{ margin:4px 0 14px; color:var(--navy); font-family:Georgia,'Times New Roman',serif; font-size:22px; }}
    p {{ margin:0; color:rgba(255,255,255,.75); max-width:760px; }}
    .status {{ background:#fff8ea; border:1px solid #ead7aa; border-radius:8px; padding:16px 18px; margin-bottom:18px; }}
    .status strong {{ color:var(--navy); }}
    .grid {{ display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:16px; }}
    .card {{ background:white; border:1px solid var(--line); border-radius:8px; padding:18px; }}
    dl {{ margin:0; display:grid; gap:10px; }}
    dt {{ color:var(--muted); font-size:12px; text-transform:uppercase; letter-spacing:.8px; font-weight:700; }}
    dd {{ margin:2px 0 0; overflow-wrap:anywhere; }}
    a {{ color:var(--red); }}
    .footer {{ margin-top:20px; color:var(--muted); font-size:13px; }}
    @media (max-width:820px) {{ .grid {{ grid-template-columns:1fr; }} h1 {{ font-size:28px; }} }}
  </style>
</head>
<body>
  <header>
    <div class="inner">
      <div class="kicker">Review before send</div>
      <h1>{html.escape(display_date(date_text))} Daily Brief Send Package</h1>
      <p>{html.escape(brief_title)}</p>
    </div>
  </header>
  <main>
    <div class="status">
      <strong>No email has been sent.</strong> This package is a preflight view only. Approval to send must be separate and explicit.
    </div>
    <div class="grid">
      {''.join(rows)}
    </div>
    <div class="footer">Generated {html.escape(generated)} local time. Published brief: <a href="{SITE_URL}/briefs/{date_text}">{SITE_URL}/briefs/{date_text}</a></div>
  </main>
</body>
</html>
"""


def package_json(date_text: str, brief_title: str, packages: list[SegmentPackage], offline: bool) -> str:
    payload = {
        "date": date_text,
        "brief_title": brief_title,
        "published_url": f"{SITE_URL}/briefs/{date_text}",
        "offline": offline,
        "segments": [
            {
                "key": package.key,
                "label": package.label,
                "list_id": package.list_id,
                "subject": package.subject,
                "recipient_count": len(package.recipients),
                "skipped_count": len(package.skipped),
                "recipients": package.recipients,
                "skipped": package.skipped,
            }
            for package in packages
        ],
    }
    return json.dumps(payload, indent=2)


def main() -> int:
    args = parse_args()
    date_text = validate_date(args.date)
    brief_title = load_brief_title(date_text)
    packages = build_packages(date_text, args.offline)
    out_dir = ROOT / "publication" / "briefs" / date_text
    html_out = render_html(date_text, brief_title, packages, args.offline)
    json_out = package_json(date_text, brief_title, packages, args.offline)

    print(f"Brief: {SITE_URL}/briefs/{date_text}")
    print(f"Title: {brief_title}")
    for package in packages:
        recipient_text = "offline" if args.offline else str(len(package.recipients))
        skipped_text = "offline" if args.offline else str(len(package.skipped))
        print(f"- {package.key}: {recipient_text} recipients, {skipped_text} skipped")

    if not args.write:
        print("\nDry run only. Re-run with --write to create review files.")
        return 0

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "send-package.html").write_text(html_out, encoding="utf-8")
    (out_dir / "send-package.json").write_text(json_out, encoding="utf-8")
    print(f"\nWrote {out_dir / 'send-package.html'}")
    print(f"Wrote {out_dir / 'send-package.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
