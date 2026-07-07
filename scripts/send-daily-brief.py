#!/usr/bin/env python3
"""
Daily newsletter send: routes segment-specific briefs to the correct HubSpot lists.

Safety default: this script does not send unless --send-approved is passed and
publication/briefs/YYYY-MM-DD/send-package.json exists.

Brief files expected at: content/briefs/YYYY-MM-DD-{segment}.html
  Segments: homeowner, service-provider, real-estate

Falls back to a single content/briefs/YYYY-MM-DD.html if segment files don't exist
(backward compat with older briefs).

Usage:
  python3 scripts/send-daily-brief.py 2026-07-07
  python3 scripts/send-daily-brief.py 2026-07-07 --send-approved
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
from workspace_config import REPO_ROOT, WORKSPACE_CONFIG_DIR, get_secret, load_dotenv_secrets

WORKSPACE = REPO_ROOT
BRIEFS_DIR = WORKSPACE / "content" / "briefs"
MD_BRIEFS_DIR = WORKSPACE / "briefs"
SITE_BRIEFS_DIR = WORKSPACE / "site" / "briefs"
CONFIG_FILE = WORKSPACE_CONFIG_DIR / ".services-config.txt"
LOG_PATH    = WORKSPACE / "scripts" / "newsletter-send.log"
MARKER_DIR  = WORKSPACE / "scripts"
PACKAGE_DIR = WORKSPACE / "publication" / "briefs"

GMAIL_USER = "duncanlittlejohn727@gmail.com"
FROM_NAME = "Robinhood Adjusting"
HUBSPOT_BCC = "246055074@bcc.hubspot.com"  # portal 246055074 — auto-logs sends + creates contacts

SEGMENTS = [
    {"list_id": "18", "key": "homeowner",       "label": "South Florida Property Intelligence"},
    {"list_id": "19", "key": "service-provider", "label": "South Florida Trade Professional Brief"},
    {"list_id": "20", "key": "real-estate",      "label": "South Florida Real Estate & Insurance Brief"},
]


def load_credentials(require_gmail=True):
    load_dotenv_secrets()
    gmail_pw = os.environ.get("GMAIL_APP_PASSWORD", "").replace(" ", "")
    content = CONFIG_FILE.read_text() if CONFIG_FILE.exists() else ""
    if require_gmail and not gmail_pw:
        m = re.search(r"Gmail App Password.*?:\s*([a-z]{4} [a-z]{4} [a-z]{4} [a-z]{4})", content)
        gmail_pw = m.group(1).replace(" ", "") if m else None
    if require_gmail and not gmail_pw:
        sys.exit("ERROR: Gmail App Password not found in config.")
    hs_token = os.environ.get("HUBSPOT_API_KEY", "")
    if not hs_token:
        hs_token = get_secret("HUBSPOT_API_KEY", "")
    if not hs_token:
        sys.exit("ERROR: HUBSPOT_API_KEY not set and fallback not found.")
    return gmail_pw, hs_token


def parse_cli(argv):
    date_str = None
    send_approved = False
    for arg in argv:
        if arg == "--send-approved":
            send_approved = True
        elif arg.startswith("-"):
            sys.exit(f"ERROR: Unknown option {arg}")
        elif date_str is None:
            date_str = arg
        else:
            sys.exit(f"ERROR: Unexpected extra argument {arg}")
    return date_str or datetime.now().strftime("%Y-%m-%d"), send_approved


def require_send_package(date_str):
    package_path = PACKAGE_DIR / date_str / "send-package.json"
    if not package_path.exists():
        sys.exit(
            "ERROR: send approval package missing. Run "
            f"`python3 scripts/prepare-brief-send-package.py {date_str} --write` "
            "and get explicit approval before sending."
        )
    try:
        package = json.loads(package_path.read_text())
    except Exception as exc:
        sys.exit(f"ERROR: invalid send package JSON at {package_path}: {exc}")
    if package.get("date") != date_str:
        sys.exit(f"ERROR: send package date mismatch in {package_path}")
    return package_path


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


SUBSCRIBER_STAGES = {"subscriber", "lead", "marketingqualifiedlead", "customer", "evangelist"}
# Allowlist: addresses Duncan wants to receive the brief regardless of lifecyclestage
# (his own personal inbox — clarified 2026-06-01). NOT for prospect-stage contacts.
SEND_ALLOWLIST = {"duncanlittlejohn727@gmail.com", "duncanlittlejohnjr@gmail.com"}


def get_list_emails(list_id, token):
    """Fetch opt-in subscriber emails from a HubSpot list.

    Guardrail: skip any contact whose lifecyclestage is not in SUBSCRIBER_STAGES
    (e.g. 'opportunity' = sales prospect). Prospects landing on a newsletter list
    by accident must not receive cold marketing. Allowlist covers Duncan's own
    inboxes.
    """
    emails = []
    skipped = []
    after = None
    while True:
        url = f"/crm/v3/lists/{list_id}/memberships?limit=100"
        if after:
            url += f"&after={after}"
        data = hubspot_get(url, token)
        for member in data.get("results", []):
            contact_id = member.get("recordId")
            if not contact_id:
                continue
            contact = hubspot_get(
                f"/crm/v3/objects/contacts/{contact_id}?properties=email,lifecyclestage",
                token,
            )
            props = contact.get("properties", {})
            email = (props.get("email") or "").lower()
            stage = (props.get("lifecyclestage") or "").lower()
            if not email:
                continue
            if email in SEND_ALLOWLIST or stage in SUBSCRIBER_STAGES:
                emails.append(email)
            else:
                skipped.append(f"{email} (stage={stage or 'unset'})")
            time.sleep(0.05)
        paging = data.get("paging", {}).get("next", {})
        after = paging.get("after") if paging else None
        if not after:
            break
    if skipped:
        log(f"  [list {list_id}] guardrail skipped {len(skipped)} non-subscriber contact(s): {', '.join(skipped[:5])}{' ...' if len(skipped) > 5 else ''}")
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


SEGMENT_TITLES = {
    None: "South Florida Property Intelligence",
    "homeowner": "South Florida Property Intelligence — Homeowner Brief",
    "service-provider": "South Florida Trade Professional Brief",
    "real-estate": "South Florida Real Estate & Insurance Brief",
}


def _render_one(date_str, segment_key=None):
    """Render briefs/{date}[-{seg}].md -> content/briefs/{date}[-{seg}].html.

    Idempotent: skips when the HTML already exists. Returns True if rendered or
    already present, False if no source markdown exists.
    """
    suffix = f"-{segment_key}" if segment_key else ""
    html_path = BRIEFS_DIR / f"{date_str}{suffix}.html"
    md_path = MD_BRIEFS_DIR / f"{date_str}{suffix}.md"
    if html_path.exists():
        return True
    if not md_path.exists():
        return False
    body_html = md_to_html_body(md_path.read_text())
    date_fmt = datetime.strptime(date_str, "%Y-%m-%d").strftime("%B %-d, %Y")
    title = f"{SEGMENT_TITLES[segment_key]} — {date_fmt}"
    full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
</head>
<body>
{body_html}
</body>
</html>"""
    BRIEFS_DIR.mkdir(parents=True, exist_ok=True)
    html_path.write_text(full_html)
    return True


def ensure_html_brief(date_str):
    """Render the master brief and any per-segment markdowns to HTML."""
    _render_one(date_str)
    for key in ("homeowner", "service-provider", "real-estate"):
        _render_one(date_str, key)


def ensure_segmented_briefs(date_str):
    """Run build_segmented_briefs.py if any segment HTML is missing.

    Self-healing: keeps the newsletter from silently falling back to generic
    copy when the generator step was skipped earlier in the chain.
    """
    needed = [BRIEFS_DIR / f"{date_str}-{s['key']}.html"
              for s in SEGMENTS]
    if all(p.exists() for p in needed):
        return
    src = BRIEFS_DIR / f"{date_str}.html"
    if not src.exists():
        return  # no source to split — send loop will skip the day
    script = Path(__file__).resolve().parent / "build_segmented_briefs.py"
    if not script.exists():
        log(f"  [segmented] {script.name} missing — cannot auto-split")
        return
    import subprocess
    log(f"  [segmented] splitting {src.name} into 3 segment variants")
    rc = subprocess.run(
        [sys.executable, str(script), date_str],
        capture_output=True, text=True,
    )
    if rc.returncode != 0:
        log(f"  [segmented] split failed rc={rc.returncode}: {rc.stderr.strip()}")
    else:
        for line in rc.stdout.strip().splitlines():
            log(f"  [segmented] {line.strip()}")


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
    if path.exists():
        html = path.read_text()
        m = re.search(r"<body[^>]*>(.*?)</body>", html, re.DOTALL | re.IGNORECASE)
        return m.group(1).strip() if m else html

    # Current review-first workflow publishes approved briefs under site/briefs.
    # Use the core article body when legacy content/briefs files have not been
    # generated for the date.
    site_path = SITE_BRIEFS_DIR / f"{date_str}.html"
    if site_path.exists():
        site_html = site_path.read_text()
        core = re.search(
            r'(<div style="font-family:Georgia,[^"]*max-width:640px;">.*?</div>)\s*</td></tr>',
            site_html,
            re.DOTALL | re.IGNORECASE,
        )
        if core:
            return core.group(1).strip()
        body = re.search(r"<body[^>]*>(.*?)</body>", site_html, re.DOTALL | re.IGNORECASE)
        return body.group(1).strip() if body else site_html
    return None


def build_brief_page_html(body_content, date_str, subject, *, include_unsubscribe=False):
    """Branded brief wrapper used for both website pages and email broadcasts.

    Set include_unsubscribe=True for email; the unsubscribe line is omitted for
    public web pages, where it doesn't apply.
    """
    date_fmt = datetime.strptime(date_str, "%Y-%m-%d").strftime("%B %-d, %Y")
    unsubscribe_html = (
        '<p style="color:#666;font-size:11px;margin:8px 0 0;">'
        "You're receiving this because you subscribed at robinhoodadjusting.com. "
        'To unsubscribe, reply with "unsubscribe" in the subject line.'
        "</p>"
    ) if include_unsubscribe else ""
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
      <tr><td style="background:#fff8ea;padding:20px;text-align:center;border-top:1px solid #eee;border-bottom:1px solid #eee;">
        <p style="color:#0f2d4a;font-size:13px;font-weight:bold;margin:0 0 6px;">🎥 Got damage or a denial letter? Show us on video.</p>
        <p style="color:#555;font-size:12px;margin:0 0 10px;line-height:1.55;">A free 15-min video call with a licensed Florida public adjuster — straight read on whether your loss is likely a covered insurable event. No contracts on the call.</p>
        <a href="https://robinhoodadjusting.com/free-review.html" style="display:inline-block;background:#c9922a;color:#0f2d4a;padding:10px 22px;text-decoration:none;border-radius:4px;font-family:Arial,sans-serif;font-size:13px;font-weight:bold;">Book a Free Virtual Review →</a>
      </td></tr>
      <tr><td style="background:#1a1a1a;padding:20px;text-align:center;border-top:4px solid #c41e3a;">
        <p style="color:#999;font-size:12px;margin:0;">
          Robinhood Adjusting · Wellington, FL ·
          <a href="https://robinhoodadjusting.com" style="color:#c41e3a;">robinhoodadjusting.com</a>
        </p>
        <p style="color:#bbb;font-size:12px;margin:10px 0 0;">
          Follow us:
          <a href="https://www.facebook.com/RobinhoodAdjusting/" style="color:#c9922a;text-decoration:none;font-weight:bold;">Facebook</a>
          &nbsp;·&nbsp;
          <a href="https://www.instagram.com/robinhoodadjusting/" style="color:#c9922a;text-decoration:none;font-weight:bold;">Instagram</a>
        </p>
        {unsubscribe_html}
      </td></tr>
    </table>
  </td></tr>
</table>
</body>
</html>"""


def build_email_html(body_content, date_str, subject):
    return build_brief_page_html(body_content, date_str, subject, include_unsubscribe=True)


def wrap_brief_for_web(input_html, date_str, default_subject=None):
    """Wrap a bare-body brief HTML file with the branded website template.

    Returns input unchanged when:
      - already wrapped (logo-dark.svg sentinel present), or
      - legacy self-styled page (has its own <style> block that the body relies on).
    """
    if "logo-dark.svg" in input_html:
        return input_html
    if re.search(r"<style[\s>]", input_html, re.IGNORECASE):
        return input_html
    tm = re.search(r"<title[^>]*>(.*?)</title>", input_html, re.DOTALL | re.IGNORECASE)
    subject = tm.group(1).strip() if tm else (default_subject or f"Robinhood Adjusting Brief — {date_str}")
    bm = re.search(r"<body[^>]*>(.*?)</body>", input_html, re.DOTALL | re.IGNORECASE)
    body = bm.group(1).strip() if bm else input_html
    return build_brief_page_html(body, date_str, subject, include_unsubscribe=False)


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
            msg["Bcc"] = HUBSPOT_BCC
            msg.attach(MIMEText(html, "html"))
            try:
                smtp.sendmail(GMAIL_USER, [to_email, HUBSPOT_BCC], msg.as_string())
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
    date_str, send_approved = parse_cli(sys.argv[1:])
    marker = MARKER_DIR / f".newsletter-sent-{date_str}"
    mode = "SEND-APPROVED" if send_approved else "NO-SEND PREFLIGHT"

    log(f"=== Daily brief send start: {date_str} ({mode}) ===")

    if marker.exists():
        log(f"Already sent for {date_str} — skipping (delete {marker.name} to force resend)")
        return

    package_path = None
    if send_approved:
        package_path = require_send_package(date_str)
        log(f"Approval package found: {package_path.relative_to(WORKSPACE)}")
    else:
        log("NO-SEND mode: pass --send-approved after Duncan approves the send package.")

    ensure_html_brief(date_str)
    ensure_segmented_briefs(date_str)
    password, hs_token = load_credentials(require_gmail=send_approved)
    date_fmt = datetime.strptime(date_str, "%Y-%m-%d").strftime("%B %-d, %Y")

    total_sent = 0
    total_failed = 0
    total_planned = 0
    fallback_segments = []

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
            fallback_segments.append(key)

        emails = get_list_emails(list_id, hs_token)
        log(f"  [{key}] {len(emails)} subscribers in list {list_id}")

        if not emails:
            log(f"  [{key}] No subscribers — skipping")
            continue

        subject = f"{label} — {date_fmt}"
        html = build_email_html(brief_body, date_str, subject)

        if not send_approved:
            total_planned += len(emails)
            log(f"  [{key}] NO-SEND would send subject `{subject}` to {len(emails)} recipient(s)")
            continue

        sent, failed = send_segment(emails, subject, html, password)
        log(f"  [{key}] Sent: {sent} | Failed: {len(failed)}")
        for email, err in failed:
            log(f"    FAILED {email}: {err}")

        total_sent += sent
        total_failed += len(failed)

    if send_approved:
        log(f"=== Done — total sent: {total_sent} | total failed: {total_failed} ===")
    else:
        log(f"=== Done — no emails sent | planned recipients: {total_planned} ===")

    if send_approved and fallback_segments:
        alert_fallback(date_str, fallback_segments)
    elif fallback_segments:
        log(f"  [no-send] fallback alert suppressed for: {', '.join(fallback_segments)}")

    if send_approved:
        marker.touch()


def alert_fallback(date_str, segments):
    """Loud-fail when one or more segments fell back to the generic brief.
    Writes a marker to health-check.log AND creates a HubSpot task for Duncan."""
    msg = f"newsletter fallback for {date_str}: {', '.join(segments)} (segmented variant missing)"
    log(f"  ⚠️  ALERT: {msg}")

    try:
        health_log = WORKSPACE / "scripts" / "health-check.log"
        ts = datetime.now().strftime("%Y-%m-%d %H:%M EDT")
        with health_log.open("a") as f:
            f.write(f"[{ts}] ⚠️ {msg}\n")
    except Exception as e:
        log(f"  alert: failed to write health-check.log: {e}")

    try:
        import subprocess
        body = (
            f"Newsletter for {date_str} fell back to the generic brief for: "
            f"{', '.join(segments)}.\n\n"
            "These subscribers received the homeowner-flavored copy instead of their "
            "audience-targeted variant. Fix the brief generator so segmented HTML files "
            "are produced at content/briefs/YYYY-MM-DD-{segment}.html, then verify the "
            "next send doesn't trip this alert.\n\n"
            "Auto-created by scripts/send-daily-brief.py."
        )
        subprocess.run(
            [
                "python3", str(WORKSPACE / "scripts" / "hubspot_task.py"),
                "--subject", f"Newsletter silent-fallback {date_str}",
                "--body", body,
                "--priority", "HIGH",
            ],
            check=False, timeout=30,
        )
    except Exception as e:
        log(f"  alert: failed to create HubSpot task: {e}")


if __name__ == "__main__":
    main()
