#!/usr/bin/env python3
"""Prepare a no-send review package for weekly trends distribution."""

from __future__ import annotations

import html
import importlib.util
import json
import sys
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SITE_URL = "https://robinhoodadjusting.com"

spec = importlib.util.spec_from_file_location(
    "swt",
    str(Path(__file__).resolve().parent / "send-weekly-trends.py"),
)
swt = importlib.util.module_from_spec(spec)
spec.loader.exec_module(swt)


def parse_cli(argv: list[str]) -> tuple[str | None, bool]:
    date_str = None
    write = False
    for arg in argv:
        if arg == "--write":
            write = True
        elif arg.startswith("-"):
            raise SystemExit(f"ERROR: Unknown option {arg}")
        elif date_str is None:
            date_str = arg
        else:
            raise SystemExit(f"ERROR: Unexpected extra argument {arg}")
    return date_str, write


def render_html(trends_date: str, week_label: str, subject: str, recipients: list[str], list_counts: dict[str, int]) -> str:
    generated = datetime.now().strftime("%Y-%m-%d %H:%M")
    sample = ", ".join(recipients[:8]) if recipients else "None loaded"
    rows = "".join(
        f"<tr><td>HubSpot list {html.escape(list_id)}</td><td>{count}</td></tr>"
        for list_id, count in list_counts.items()
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Weekly Trends Send Package - {html.escape(trends_date)}</title>
  <style>
    :root {{ --navy:#0f2d4a; --red:#c41e3a; --gold:#c9922a; --ink:#26313d; --muted:#667085; --line:#dde3ea; --bg:#f6f7f9; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; background:var(--bg); color:var(--ink); font-family:Arial,sans-serif; line-height:1.55; }}
    header {{ background:var(--navy); color:white; padding:28px 24px; border-bottom:5px solid var(--gold); }}
    main, .inner {{ max-width:920px; margin:0 auto; }}
    main {{ padding:28px 20px 56px; }}
    .kicker {{ color:var(--red); text-transform:uppercase; letter-spacing:1.7px; font-size:12px; font-weight:700; }}
    h1 {{ margin:8px 0 10px; font-family:Georgia,'Times New Roman',serif; font-size:34px; line-height:1.15; }}
    h2 {{ margin:0 0 14px; color:var(--navy); font-family:Georgia,'Times New Roman',serif; }}
    p {{ margin:0; color:rgba(255,255,255,.75); max-width:760px; }}
    .card {{ background:white; border:1px solid var(--line); border-radius:8px; padding:20px; margin-bottom:16px; }}
    .status {{ background:#fff8ea; border-color:#ead7aa; }}
    dl {{ margin:0; display:grid; gap:12px; }}
    dt {{ color:var(--muted); font-size:12px; text-transform:uppercase; letter-spacing:.8px; font-weight:700; }}
    dd {{ margin:2px 0 0; overflow-wrap:anywhere; }}
    table {{ width:100%; border-collapse:collapse; }}
    td {{ border-top:1px solid var(--line); padding:10px 0; }}
    a {{ color:var(--red); }}
  </style>
</head>
<body>
  <header>
    <div class="inner">
      <div class="kicker">Weekly review before send</div>
      <h1>{html.escape(week_label)}</h1>
      <p>{html.escape(subject)}</p>
    </div>
  </header>
  <main>
    <section class="card status">
      <strong>No email has been sent.</strong> This package is a preflight view only. Approval to send must be separate and explicit.
    </section>
    <section class="card">
      <h2>Send Plan</h2>
      <dl>
        <div><dt>Published link</dt><dd><a href="{SITE_URL}/trends/{trends_date}">{SITE_URL}/trends/{trends_date}</a></dd></div>
        <div><dt>Subject</dt><dd>{html.escape(subject)}</dd></div>
        <div><dt>Unique recipients</dt><dd>{len(recipients)}</dd></div>
        <div><dt>Sample</dt><dd>{html.escape(sample)}</dd></div>
      </dl>
    </section>
    <section class="card">
      <h2>HubSpot Lists</h2>
      <table>{rows}</table>
    </section>
    <div style="color:var(--muted);font-size:13px;">Generated {html.escape(generated)} local time.</div>
  </main>
</body>
</html>
"""


def main() -> int:
    requested_date, write = parse_cli(sys.argv[1:])
    trends_path = swt.find_trends_html(requested_date, datetime.now())
    if not trends_path:
        raise SystemExit("ERROR: no weekly trends HTML found")
    trends_date = trends_path.stem
    week_label = swt.build_week_label(trends_path)
    subject = f"South Florida Weekly Trends - Week of {week_label}"

    _, hs_token = swt.sdb.load_credentials(require_gmail=False)
    all_emails: list[str] = []
    list_counts: dict[str, int] = {}
    for list_id in swt.LIST_IDS:
        emails = swt.sdb.get_list_emails(list_id, hs_token)
        list_counts[list_id] = len(emails)
        all_emails.extend(emails)
    recipients = swt.dedupe(all_emails)

    out_dir = ROOT / "publication" / "trends" / trends_date
    payload = {
        "date": trends_date,
        "week_label": week_label,
        "subject": subject,
        "published_url": f"{SITE_URL}/trends/{trends_date}",
        "recipient_count": len(recipients),
        "list_counts": list_counts,
        "recipients": recipients,
    }

    print(f"Trends: {payload['published_url']}")
    print(f"Subject: {subject}")
    print(f"Recipients: {len(recipients)}")
    for list_id, count in list_counts.items():
        print(f"- list {list_id}: {count}")

    if not write:
        print("\nDry run only. Re-run with --write to create review files.")
        return 0

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "send-package.html").write_text(
        render_html(trends_date, week_label, subject, recipients, list_counts),
        encoding="utf-8",
    )
    (out_dir / "send-package.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nWrote {out_dir / 'send-package.html'}")
    print(f"Wrote {out_dir / 'send-package.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
