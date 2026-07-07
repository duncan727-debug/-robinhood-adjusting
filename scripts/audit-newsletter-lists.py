#!/usr/bin/env python3
"""Read-only audit of HubSpot newsletter lists.

This helps keep subscriber sends consent-safe. It never writes to HubSpot; it
only classifies list members as send-eligible or skipped by the sender guardrail.
"""

from __future__ import annotations

import argparse
import html
import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path

from workspace_config import get_secret, load_dotenv_secrets


ROOT = Path(__file__).resolve().parents[1]
OUT_ROOT = ROOT / "ops" / "newsletter-list-audits"

LISTS = [
    {"list_id": "18", "key": "homeowner", "label": "Homeowner"},
    {"list_id": "19", "key": "service-provider", "label": "Service Provider"},
    {"list_id": "20", "key": "real-estate", "label": "Real Estate"},
]

SUBSCRIBER_STAGES = {"subscriber", "lead", "marketingqualifiedlead", "customer", "evangelist"}
SEND_ALLOWLIST = {"duncanlittlejohn727@gmail.com", "duncanlittlejohnjr@gmail.com"}


@dataclass
class ContactAudit:
    list_id: str
    list_key: str
    contact_id: str
    email: str
    name: str
    lifecyclestage: str
    eligible: bool
    reason: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit HubSpot newsletter list membership.")
    parser.add_argument("--write", action="store_true", help="Write HTML and JSON audit files under ops/newsletter-list-audits/.")
    return parser.parse_args()


def load_token() -> str:
    load_dotenv_secrets()
    return get_secret("HUBSPOT_API_KEY")


def hubspot_get(path: str, token: str, retries: int = 3) -> dict:
    req = urllib.request.Request(f"https://api.hubapi.com{path}")
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
            raise SystemExit(f"HubSpot read failed {exc.code} on {path}: {body[:300]}")
    return {}


def classify(email_addr: str, stage: str) -> tuple[bool, str]:
    if not email_addr:
        return False, "missing email"
    if email_addr in SEND_ALLOWLIST:
        return True, "allowlist"
    if stage in SUBSCRIBER_STAGES:
        return True, f"stage={stage}"
    return False, f"stage={stage or 'unset'}"


def audit_list(list_id: str, list_key: str, token: str) -> list[ContactAudit]:
    audits: list[ContactAudit] = []
    after = None
    while True:
        path = f"/crm/v3/lists/{list_id}/memberships?limit=100"
        if after:
            path += f"&after={after}"
        data = hubspot_get(path, token)
        for member in data.get("results", []):
            contact_id = str(member.get("recordId") or "")
            if not contact_id:
                continue
            contact = hubspot_get(
                f"/crm/v3/objects/contacts/{contact_id}?properties=email,firstname,lastname,lifecyclestage",
                token,
            )
            props = contact.get("properties", {})
            email_addr = (props.get("email") or "").strip().lower()
            stage = (props.get("lifecyclestage") or "").strip().lower()
            name = " ".join(
                part for part in [(props.get("firstname") or "").strip(), (props.get("lastname") or "").strip()]
                if part
            )
            eligible, reason = classify(email_addr, stage)
            audits.append(
                ContactAudit(
                    list_id=list_id,
                    list_key=list_key,
                    contact_id=contact_id,
                    email=email_addr,
                    name=name,
                    lifecyclestage=stage,
                    eligible=eligible,
                    reason=reason,
                )
            )
            time.sleep(0.05)
        paging = data.get("paging", {}).get("next", {})
        after = paging.get("after") if paging else None
        if not after:
            break
    return audits


def render_html(generated: str, audits: list[ContactAudit]) -> str:
    sections = []
    for list_info in LISTS:
        rows = [item for item in audits if item.list_id == list_info["list_id"]]
        eligible = [item for item in rows if item.eligible]
        skipped = [item for item in rows if not item.eligible]
        row_html = "\n".join(
            f"<tr class=\"{'ok' if item.eligible else 'skip'}\"><td>{html.escape(item.email or '(missing)')}</td>"
            f"<td>{html.escape(item.name or '')}</td><td>{html.escape(item.lifecyclestage or 'unset')}</td>"
            f"<td>{'Eligible' if item.eligible else 'Skip'}</td><td>{html.escape(item.reason)}</td></tr>"
            for item in rows
        )
        sections.append(
            f"""
            <section class="card">
              <h2>{html.escape(list_info['label'])}</h2>
              <p>{len(eligible)} eligible / {len(skipped)} skipped / {len(rows)} total</p>
              <table>
                <thead><tr><th>Email</th><th>Name</th><th>Stage</th><th>Decision</th><th>Reason</th></tr></thead>
                <tbody>{row_html}</tbody>
              </table>
            </section>
            """
        )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Newsletter List Audit - {html.escape(generated)}</title>
  <style>
    :root {{ --navy:#0f2d4a; --red:#c41e3a; --gold:#c9922a; --line:#dde3ea; --bg:#f6f7f9; --ink:#26313d; --muted:#667085; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; background:var(--bg); color:var(--ink); font-family:Arial,sans-serif; line-height:1.55; }}
    header {{ background:var(--navy); color:white; padding:28px 24px; border-bottom:5px solid var(--gold); }}
    main, .inner {{ max-width:1100px; margin:0 auto; }}
    main {{ padding:28px 20px 56px; }}
    .kicker {{ color:var(--gold); text-transform:uppercase; letter-spacing:1.7px; font-size:12px; font-weight:700; }}
    h1 {{ margin:8px 0 10px; font-family:Georgia,'Times New Roman',serif; font-size:34px; }}
    h2 {{ margin:0 0 6px; color:var(--navy); font-family:Georgia,'Times New Roman',serif; }}
    p {{ margin:0 0 14px; color:var(--muted); }}
    .card {{ background:white; border:1px solid var(--line); border-radius:8px; padding:20px; margin-bottom:18px; overflow:auto; }}
    table {{ width:100%; border-collapse:collapse; min-width:760px; }}
    th, td {{ border-top:1px solid var(--line); padding:9px 8px; text-align:left; font-size:13px; }}
    th {{ color:var(--muted); text-transform:uppercase; letter-spacing:.7px; font-size:11px; }}
    tr.ok td:nth-child(4) {{ color:#177245; font-weight:700; }}
    tr.skip td:nth-child(4) {{ color:var(--red); font-weight:700; }}
  </style>
</head>
<body>
  <header>
    <div class="inner">
      <div class="kicker">Read-only HubSpot audit</div>
      <h1>Newsletter List Hygiene</h1>
      <p>Generated {html.escape(generated)}. No HubSpot records were changed.</p>
    </div>
  </header>
  <main>{''.join(sections)}</main>
</body>
</html>
"""


def main() -> int:
    args = parse_args()
    token = load_token()
    audits: list[ContactAudit] = []
    for list_info in LISTS:
        audits.extend(audit_list(list_info["list_id"], list_info["key"], token))

    for list_info in LISTS:
        rows = [item for item in audits if item.list_id == list_info["list_id"]]
        eligible = sum(1 for item in rows if item.eligible)
        skipped = len(rows) - eligible
        print(f"{list_info['key']}: {eligible} eligible / {skipped} skipped / {len(rows)} total")

    if not args.write:
        print("\nDry run only. Re-run with --write to create audit files.")
        return 0

    generated = datetime.now().strftime("%Y-%m-%d-%H%M")
    out_dir = OUT_ROOT / generated
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "audit.html").write_text(render_html(generated, audits), encoding="utf-8")
    (out_dir / "audit.json").write_text(
        json.dumps([asdict(item) for item in audits], indent=2),
        encoding="utf-8",
    )
    print(f"\nWrote {out_dir / 'audit.html'}")
    print(f"Wrote {out_dir / 'audit.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
