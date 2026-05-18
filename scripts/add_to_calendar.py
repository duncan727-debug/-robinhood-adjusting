#!/usr/bin/env python3
"""
Generate an .ics file from a list of events and email it to Duncan's personal Gmail
(where his Google Calendar lives). Google auto-detects the attachment and offers
"Add to calendar" with one click.

Usage:
  python3 add_to_calendar.py            # uses CURRENT_EVENTS below
  python3 add_to_calendar.py --dry-run  # writes .ics to crm/calendar/ but does not email

All times are specified in America/New_York. Events are marked TENTATIVE until
the underlying counterparty confirms.
"""

import argparse
import re
import smtplib
import sys
import uuid
from datetime import datetime, timezone, timedelta
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email import encoders
from pathlib import Path

WORKSPACE = Path("/Users/victoria/.openclaw/workspace")
CONFIG_FILE = WORKSPACE / "config" / ".services-config.txt"
ICS_DIR = WORKSPACE / "crm" / "calendar"
LOG_PATH = WORKSPACE / "scripts" / "outreach_send.log"

GMAIL_USER = "duncanlittlejohn727@gmail.com"
FROM_NAME = "Duncan Littlejohn (assistant)"
DUNCAN_PERSONAL = "duncanlittlejohnjr@gmail.com"  # personal Gmail = where his Google Calendar lives

# ── events ──────────────────────────────────────────────────────────────────
# Each event: (date YYYY-MM-DD, start HH:MM, end HH:MM, summary, location, description, status)
# Times in local America/New_York. Status: TENTATIVE or CONFIRMED.

CURRENT_EVENTS = [
    {
        "date": "2026-05-19",
        "start": "17:30",
        "end": "19:30",
        "summary": "Chamber Connections (Central PBC Chamber) — TENTATIVE",
        "location": "Central Palm Beach County Chamber area, Wellington FL (venue TBD)",
        "description": (
            "Central PBC Chamber monthly mixer. Time and venue TBD pending reply from Info@CPBChamber.com (sent 2026-05-16). "
            "Registration: https://cpbchamber.chambermaster.com/events/register/6001697 · "
            "Phone: 561-790-6200"
        ),
        "status": "TENTATIVE",
    },
    {
        "date": "2026-05-20",
        "start": "07:45",
        "end": "09:00",
        "summary": "Wellington/WPB Breakfast Networking @ Nana's — TENTATIVE",
        "location": "Nana's Diner, 1230 Military Trail, West Palm Beach FL 33409",
        "description": (
            "1st & 3rd Wed monthly. FREE, no dues, category-exclusive (one PA per group). "
            "Call Arlene at 561-670-6828 to confirm PA seat is open. No email available for Arlene."
        ),
        "status": "TENTATIVE",
    },
    {
        "date": "2026-05-21",
        "start": "08:00",
        "end": "09:30",
        "summary": "SFL Business Connections — Wellington Thu networking — TENTATIVE",
        "location": "Wellington, FL (venue TBD)",
        "description": (
            "Free Thursday morning Wellington networking group. Owner: Alan Feuerman. "
            "Email sent 2026-05-16 to sflbusinessconnectionsreply@gmail.com asking PA seat status + venue. "
            "Phone: 561-674-4300"
        ),
        "status": "TENTATIVE",
    },
    {
        "date": "2026-05-21",
        "start": "07:45",
        "end": "09:00",
        "summary": "PRE Palm Beach Gardens (visitor) — TENTATIVE — CONFLICTS WITH SFL",
        "location": "Berry Fresh Café, 11658 US Hwy 1, Palm Beach Gardens FL 33408",
        "description": (
            "Professional Referral Exchange — PBG chapter. Thursdays 7:45-9am. "
            "Email sent 2026-05-16 to Craig Valarik (Area Director) at craig@prenetworking.net. "
            "President: Kelly Mueller. PA seat status unknown — asked directly. "
            "CONFLICT: SFL Business Connections is also Thursday AM in Wellington — pick one."
        ),
        "status": "TENTATIVE",
    },
    {
        "date": "2026-06-02",
        "start": "18:30",
        "end": "20:30",
        "summary": "West Palm Beach REI (first Tuesday) — TENTATIVE",
        "location": "West Palm Beach, FL (venue TBD)",
        "description": "Monthly real estate investor meetup. First Tuesday. Meetup.com/west-palm-beach-real-estate-investors",
        "status": "TENTATIVE",
    },
    {
        "date": "2026-06-03",
        "start": "09:00",
        "end": "11:00",
        "summary": "Small Business Boot Camp (Central PBC Chamber) — TENTATIVE",
        "location": "Central PBC Chamber, 12794 W Forest Hill Blvd Suite 19, Wellington FL 33414",
        "description": "Central PBC Chamber workshop series. Reg: https://cpbchamber.chambermaster.com/events/register/6001703 · Phone: 561-790-6200",
        "status": "TENTATIVE",
    },
    {
        "date": "2027-05-01",
        "start": "11:00",
        "end": "14:00",
        "summary": "Wellington Hurricane & Severe Weather Expo 2027 — VENDOR SLOT — TENTATIVE",
        "location": "Mall at Wellington Green, 10300 Forest Hill Blvd, Wellington FL 33414",
        "description": (
            "Vendor inquiry sent 2026-05-16 to Michelle Garvey, mgarvey@wellingtonfl.gov, 561-791-4082. "
            "Free event, ~3000 PBC homeowners attend. High-leverage warm-lead venue. "
            "Confirm vendor slot once Garvey replies."
        ),
        "status": "TENTATIVE",
    },
]

# ── ics builder ─────────────────────────────────────────────────────────────

VTIMEZONE = """\
BEGIN:VTIMEZONE
TZID:America/New_York
BEGIN:STANDARD
DTSTART:20071104T020000
RRULE:FREQ=YEARLY;BYDAY=1SU;BYMONTH=11
TZNAME:EST
TZOFFSETFROM:-0400
TZOFFSETTO:-0500
END:STANDARD
BEGIN:DAYLIGHT
DTSTART:20070311T020000
RRULE:FREQ=YEARLY;BYDAY=2SU;BYMONTH=3
TZNAME:EDT
TZOFFSETFROM:-0500
TZOFFSETTO:-0400
END:DAYLIGHT
END:VTIMEZONE"""

def fold(line):
    """RFC 5545 line folding at 75 octets."""
    out = []
    while len(line.encode("utf-8")) > 75:
        # find a safe split point
        cut = 74
        while cut > 0 and len(line[:cut].encode("utf-8")) > 74:
            cut -= 1
        out.append(line[:cut])
        line = " " + line[cut:]
    out.append(line)
    return "\r\n".join(out)

def escape_text(t):
    return t.replace("\\", "\\\\").replace(",", "\\,").replace(";", "\\;").replace("\n", "\\n")

def build_ics(events):
    now_utc = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Robin Hood Adjusting//Calendar//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        VTIMEZONE,
    ]
    for ev in events:
        date_compact = ev["date"].replace("-", "")
        start = ev["start"].replace(":", "") + "00"
        end = ev["end"].replace(":", "") + "00"
        uid = f"{uuid.uuid4()}@robinhoodadjusting.com"
        block = [
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{now_utc}",
            f"DTSTART;TZID=America/New_York:{date_compact}T{start}",
            f"DTEND;TZID=America/New_York:{date_compact}T{end}",
            f"SUMMARY:{escape_text(ev['summary'])}",
            f"LOCATION:{escape_text(ev['location'])}",
            f"DESCRIPTION:{escape_text(ev['description'])}",
            f"STATUS:{ev['status']}",
            "TRANSP:OPAQUE",
            "END:VEVENT",
        ]
        lines.extend(fold(l) for l in block)
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"

# ── email send ──────────────────────────────────────────────────────────────

def load_gmail_pw():
    text = CONFIG_FILE.read_text()
    m = re.search(r"Gmail App Password.*?:\s*([a-z]{4} [a-z]{4} [a-z]{4} [a-z]{4})", text)
    if not m:
        sys.exit("ERROR: Gmail App Password not found in config.")
    return m.group(1)

def send_with_attachment(ics_text, ics_filename, event_count):
    pw = load_gmail_pw()
    msg = MIMEMultipart()
    msg["Subject"] = f"Calendar invites ({event_count} tentative events) — networking + outreach"
    msg["From"] = f"{FROM_NAME} <{GMAIL_USER}>"
    msg["To"] = DUNCAN_PERSONAL

    body = (
        "Calendar batch from your assistant.\n\n"
        "Attached is an .ics file with all currently-open networking and outreach calendar slots.\n"
        "Every event is marked TENTATIVE until counterparties confirm.\n\n"
        "Google Gmail should detect the .ics and show 'Add to calendar' inline. "
        "If not, open the attachment and confirm import.\n\n"
        "I'll send updated batches as new events are scheduled.\n"
    )
    msg.attach(MIMEText(body, "plain"))

    part = MIMEBase("text", "calendar", method="PUBLISH", name=ics_filename)
    part.set_payload(ics_text)
    encoders.encode_base64(part)
    part.add_header("Content-Disposition", f'attachment; filename="{ics_filename}"')
    msg.attach(part)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_USER, pw)
        server.sendmail(GMAIL_USER, [DUNCAN_PERSONAL], msg.as_string())

# ── main ────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    ICS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    filename = f"calendar-batch-{ts}.ics"
    ics_path = ICS_DIR / filename
    ics_text = build_ics(CURRENT_EVENTS)
    ics_path.write_text(ics_text)
    print(f"Wrote {ics_path}  ({len(CURRENT_EVENTS)} events)")

    if args.dry_run:
        print("DRY RUN — not emailing.")
        return

    send_with_attachment(ics_text, filename, len(CURRENT_EVENTS))
    log_ts = datetime.now().isoformat(timespec="seconds")
    LOG_PATH.open("a").write(
        f"{log_ts}  one-off  SENT  {DUNCAN_PERSONAL}  Calendar batch ({len(CURRENT_EVENTS)} events)\n"
    )
    print(f"SENT to {DUNCAN_PERSONAL} with {filename} attached @ {log_ts}")

if __name__ == "__main__":
    main()
