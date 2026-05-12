#!/usr/bin/env python3
"""
Daily newsletter send: routes segment-specific briefs to the correct HubSpot lists.

Brief files expected at: content/briefs/YYYY-MM-DD-{segment}.html
  Segments: homeowner, service-provider, real-estate

Falls back to a single content/briefs/YYYY-MM-DD.html if segment files don't exist
(backward compat with older briefs).
"""

import html as html_lib
import json
import os
import re
import smtplib
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

WORKSPACE = Path("/Users/victoria/.openclaw/workspace")
BRIEFS_DIR = WORKSPACE / "content" / "briefs"
MD_BRIEFS_DIR = WORKSPACE / "briefs"
CONFIG_FILE = WORKSPACE / "config" / ".services-config.txt"
LOG_PATH    = WORKSPACE / "scripts" / "newsletter-send.log"
MARKER_DIR  = WORKSPACE / "scripts"

GMAIL_USER = "duncanlittlejohn727@gmail.com"
FROM_NAME = "Robinhood Adjusting"

SEGMENTS = [
    {"list_id": "18", "key": "homeowner",       "label": "South Florida Property Intelligence"},
    {"list_id": "19", "key": "service-provider", "label": "South Florida Trade Professional Brief"},
    {"list_id": "20", "key": "real-estate",      "label": "South Florida Real Estate & Insurance Brief"},
]


def load_credentials():
    content = CONFIG_FILE.read_text()
    m = re.search(r"Gmail App Password.*?:\s*([a-z]{4} [a-z]{4} [a-z]{4} [a-z]{4})", content)
    gmail_pw = m.group(1) if m else None
    if not gmail_pw:
        sys.exit("ERROR: Gmail App Password not found in config.")
    hs_token = os.environ.get("HUBSPOT_API_KEY", "")
    if not hs_token:
        secrets_path = WORKSPACE / "config" / ".secrets"
        if secrets_path.exists():
            m2 = re.search(r'HUBSPOT_API_KEY="([^"]+)"', secrets_path.read_text())
            hs_token = m2.group(1) if m2 else ""
    if not hs_token:
        sys.exit("ERROR: HUBSPOT_API_KEY not set and fallback not found.")
    return gmail_pw, hs_token


def hubspot_get(path, token, retries=3):
    url = f"https://api.hubapi.com{path}"
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {token}")
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(2 ** attempt)
                continue
            log(f"HubSpot error {e.code} on {path}")
            return {}
    return {}


def get_list_emails(list_id, token):
    """Fetch all contact emails from a single HubSpot list."""
    emails = []
    after = None
    while True:
        url = f"/crm/v3/lists/{list_id}/memberships?limit=100"
        if after:
            url += f"&after={after}"
        data = hubspot_get(url, token)
        for member in data.get("results", []):
            contact_id = member.get("recordId")
            if contact_id:
                contact = hubspot_get(f"/crm/v3/objects/contacts/{contact_id}?properties=email", token)
                email = contact.get("properties", {}).get("email", "")
                if email:
                    emails.append(email.lower())
                time.sleep(0.05)
        paging = data.get("paging", {}).get("next", {})
        after = paging.get("after") if paging else None
        if not after:
            break
    return emails


def md_to_html_body(md_text):
    """Convert markdown brief to a styled HTML body for email."""
    lines = md_text.splitlines()
    out = ['<div style="font-family:Georgia,\'Times New Roman\',serif;color:#333;line-height:1.7;max-width:640px;">']
    in_table = False
    in_list = False
    table_rows = []

    def flush_table():
        nonlocal table_rows
        if not table_rows:
            return ""
        h = ['<table style="width:100%;border-collapse:collapse;font-size:13px;margin:0 0 24px;">']
        for i, row in enumerate(table_rows):
            cells = [c.strip() for c in row.strip("|").split("|")]
            if i == 0:
                h.append('<thead><tr style="background:#0f2d4a;color:#fff;">')
                for c in cells:
                    h.append(f'<th style="padding:8px 12px;text-align:left;font-family:Arial,sans-serif;">{c}</th>')
                h.append("</tr></thead><tbody>")
            elif i == 1:
                continue  # separator row
            else:
                bg = ' style="background:#fafafa;"' if i % 2 == 0 else ""
                h.append(f"<tr{bg}>")
                for c in cells:
                    h.append(f'<td style="padding:8px 12px;border-bottom:1px solid #e0e0e0;">{c}</td>')
                h.append("</tr>")
        h.append("</tbody></table>")
        table_rows = []
        return "\n".join(h)

    i = 0
    while i < len(lines):
        line = lines[i]

        # Table detection
        if "|" in line and line.strip().startswith("|"):
            if in_list:
                out.append("</ul>")
                in_list = False
            table_rows.append(line)
            i += 1
            continue
        elif table_rows:
            out.append(flush_table())
            in_table = False

        stripped = line.strip()

        if not stripped:
            if in_list:
                out.append("</ul>")
                in_list = False
            out.append("")
            i += 1
            continue

        # Headings
        if stripped.startswith("### "):
            if in_list:
                out.append("</ul>"); in_list = False
            text = _inline(stripped[4:])
            out.append(f'<h3 style="font-size:16px;color:#0f2d4a;margin:16px 0 8px;">{text}</h3>')
        elif stripped.startswith("## "):
            if in_list:
                out.append("</ul>"); in_list = False
            text = _inline(stripped[3:])
            out.append(f'<h2 style="font-size:19px;color:#0f2d4a;margin:24px 0 12px;padding-bottom:6px;border-bottom:3px solid #c41e3a;">{text}</h2>')
        elif stripped.startswith("# "):
            if in_list:
                out.append("</ul>"); in_list = False
            text = _inline(stripped[2:])
            out.append(f'<h1 style="font-size:22px;color:#0f2d4a;margin:0 0 16px;">{text}</h1>')
        elif stripped.startswith("---"):
            if in_list:
                out.append("</ul>"); in_list = False
            out.append('<hr style="border:none;border-top:1px solid #e0e0e0;margin:20px 0;">')
        elif stripped.startswith("- ") or stripped.startswith("* "):
            if not in_list:
                out.append('<ul style="margin:0 0 12px;padding-left:20px;">')
                in_list = True
            text = _inline(stripped[2:])
            out.append(f'<li style="margin-bottom:6px;">{text}</li>')
        elif re.match(r"^\*\*Why it matters", stripped):
            if in_list:
                out.append("</ul>"); in_list = False
            text = _inline(stripped)
            out.append(f'<div style="background:#f8f4ee;border-left:4px solid #c9922a;padding:12px 16px;margin:12px 0 20px;font-size:14px;">{text}</div>')
        else:
            if in_list:
                out.append("</ul>"); in_list = False
            text = _inline(stripped)
            out.append(f'<p style="margin:0 0 12px;">{text}</p>')
        i += 1

    if in_list:
        out.append("</ul>")
    if table_rows:
        out.append(flush_table())

    out.append("</div>")
    return "\n".join(out)


def _inline(text):
    """Convert inline markdown (bold, italic, links) to HTML."""
    # Bold+italic ***text***
    text = re.sub(r'\*\*\*(.+?)\*\*\*', r'<strong><em>\1</em></strong>', text)
    # Bold **text**
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    # Italic *text*
    text = re.sub(r'\*([^*]+?)\*', r'<em>\1</em>', text)
    # Links [text](url)
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2" style="color:#c41e3a;">\1</a>', text)
    # Inline code `code`
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
    return text


def ensure_html_brief(date_str):
    """Convert markdown brief to HTML if HTML doesn't exist yet."""
    html_path = BRIEFS_DIR / f"{date_str}.html"
    if html_path.exists():
        return
    md_path = MD_BRIEFS_DIR / f"{date_str}.md"
    if not md_path.exists():
        return
    md_text = md_path.read_text()
    body_html = md_to_html_body(md_text)
    date_fmt = datetime.strptime(date_str, "%Y-%m-%d").strftime("%B %-d, %Y")
    full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>South Florida Property Intelligence — {date_fmt}</title>
</head>
<body>
{body_html}
</body>
</html>"""
    BRIEFS_DIR.mkdir(parents=True, exist_ok=True)
    html_path.write_text(full_html)


def get_brief_html(date_str, segment_key=None):
    """Load segment-specific brief, falling back to generic brief."""
    if segment_key:
        path = BRIEFS_DIR / f"{date_str}-{segment_key}.html"
        if path.exists():
            html = path.read_text()
            m = re.search(r"<body[^>]*>(.*?)</body>", html, re.DOTALL | re.IGNORECASE)
            return m.group(1).strip() if m else html

    # Fallback: single brief for all segments
    path = BRIEFS_DIR / f"{date_str}.html"
    if not path.exists():
        return None
    html = path.read_text()
    m = re.search(r"<body[^>]*>(.*?)</body>", html, re.DOTALL | re.IGNORECASE)
    return m.group(1).strip() if m else html


def build_email_html(body_content, date_str, subject):
    date_fmt = datetime.strptime(date_str, "%Y-%m-%d").strftime("%B %-d, %Y")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{subject}</title>
</head>
<body style="margin:0;padding:0;background:#f5f5f5;font-family:Georgia,'Times New Roman',serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f5f5f5;padding:20px 0;">
  <tr><td align="center">
    <table width="680" cellpadding="0" cellspacing="0" style="background:#ffffff;max-width:680px;width:100%;">
      <tr><td style="background:#0f2d4a;padding:28px 20px;text-align:center;border-bottom:5px solid #c9922a;">
        <img src="https://robinhoodadjusting.com/logo-dark.svg" alt="Robinhood Adjusting" width="280" height="60" style="display:inline-block;max-width:100%;height:auto;">
        <div style="color:rgba(255,255,255,0.5);font-family:Arial,sans-serif;font-size:12px;letter-spacing:1px;margin-top:12px;">{date_fmt}</div>
      </td></tr>
      <tr><td style="padding:30px 24px;">
        {body_content}
      </td></tr>
      <tr><td style="background:#1a1a1a;padding:20px;text-align:center;border-top:4px solid #c41e3a;">
        <p style="color:#999;font-size:12px;margin:0;">
          Robinhood Adjusting · Wellington, FL ·
          <a href="https://robinhoodadjusting.com" style="color:#c41e3a;">robinhoodadjusting.com</a>
        </p>
        <p style="color:#666;font-size:11px;margin:8px 0 0;">
          You're receiving this because you subscribed at robinhoodadjusting.com.
          To unsubscribe, reply with "unsubscribe" in the subject line.
        </p>
      </td></tr>
    </table>
  </td></tr>
</table>
</body>
</html>"""


def send_segment(emails, subject, html, password):
    sent = 0
    failed = []
    with smtplib.SMTP("smtp.gmail.com", 587) as smtp:
        smtp.starttls()
        smtp.login(GMAIL_USER, password)
        for to_email in emails:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{FROM_NAME} <{GMAIL_USER}>"
            msg["To"] = to_email
            msg.attach(MIMEText(html, "html"))
            try:
                smtp.sendmail(GMAIL_USER, to_email, msg.as_string())
                sent += 1
            except Exception as e:
                failed.append((to_email, str(e)))
            time.sleep(0.3)
    return sent, failed


def log(message):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"[{ts}] {message}")
    with open(LOG_PATH, "a") as f:
        f.write(f"[{ts}] {message}\n")


def main():
    date_str = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime("%Y-%m-%d")
    marker = MARKER_DIR / f".newsletter-sent-{date_str}"

    log(f"=== Daily brief send start: {date_str} ===")

    if marker.exists():
        log(f"Already sent for {date_str} — skipping (delete {marker.name} to force resend)")
        return

    ensure_html_brief(date_str)
    password, hs_token = load_credentials()
    date_fmt = datetime.strptime(date_str, "%Y-%m-%d").strftime("%B %-d, %Y")

    total_sent = 0
    total_failed = 0

    for segment in SEGMENTS:
        list_id = segment["list_id"]
        key = segment["key"]
        label = segment["label"]

        brief_body = get_brief_html(date_str, key)
        if not brief_body:
            log(f"  [{key}] No brief found for {date_str} — skipping segment")
            continue

        using_generic = not (BRIEFS_DIR / f"{date_str}-{key}.html").exists()
        if using_generic:
            log(f"  [{key}] Using fallback generic brief")

        emails = get_list_emails(list_id, hs_token)
        log(f"  [{key}] {len(emails)} subscribers in list {list_id}")

        if not emails:
            log(f"  [{key}] No subscribers — skipping")
            continue

        subject = f"{label} — {date_fmt}"
        html = build_email_html(brief_body, date_str, subject)

        sent, failed = send_segment(emails, subject, html, password)
        log(f"  [{key}] Sent: {sent} | Failed: {len(failed)}")
        for email, err in failed:
            log(f"    FAILED {email}: {err}")

        total_sent += sent
        total_failed += len(failed)

    log(f"=== Done — total sent: {total_sent} | total failed: {total_failed} ===")
    marker.touch()


if __name__ == "__main__":
    main()
