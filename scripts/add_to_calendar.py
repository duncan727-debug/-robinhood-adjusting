#!/usr/bin/env python3
"""
Add pending events directly to Duncan's Google Calendar
(duncanlittlejohn727@gmail.com) via the Calendar API.

Usage:
  python3 add_to_calendar.py                      # uses CURRENT_EVENTS below
  python3 add_to_calendar.py --dry-run            # plans events but does not insert
  python3 add_to_calendar.py --events-json PATH   # load events from JSON (used by cron)
  python3 add_to_calendar.py --max-months-out N   # skip events >N months out (default 12)
  python3 add_to_calendar.py --no-dedup           # ignore dedup state

All times in America/New_York. Events default to TENTATIVE (transparency=transparent
so they don't block work hours).

Dedup: a state file (crm/calendar/.events_state.json) tracks which event
signatures (date+start+summary+location hash) have already been inserted.
"""

import argparse
import hashlib
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

WORKSPACE = Path("/Users/victoria/.openclaw/workspace")
TOKEN_FILE = WORKSPACE / "config" / "google_calendar_token.json"
ICS_DIR = WORKSPACE / "crm" / "calendar"
STATE_FILE = ICS_DIR / ".events_state.json"
LOG_PATH = WORKSPACE / "scripts" / "outreach_send.log"

CALENDAR_ID = "duncanlittlejohn727@gmail.com"
TZ = "America/New_York"

CURRENT_EVENTS = [
    {
        "date": "2026-05-21",
        "start": "07:45",
        "end": "09:00",
        "summary": "PRE Palm Beach Gardens (visitor) — TENTATIVE",
        "location": "Berry Fresh Café, 11658 US Hwy 1, Palm Beach Gardens FL 33408",
        "description": (
            "Professional Referral Exchange — Palm Beach Gardens chapter. Thursdays 7:45-9am.\n"
            "Cost: FREE for first-time visitors (PRE policy). Membership dues if Duncan joins (TBD).\n"
            "Contact: Craig Valarik (Area Director) — craig@prenetworking.net\n"
            "President: Kelly Mueller\n"
            "Website: https://prenetworking.net\n"
            "Status: Email inquiry sent 2026-05-16 asking PA seat status. Drop-ins usually allowed if no reply.\n"
            "CONFLICT: SFL Business Connections is also Thursday AM in Wellington — pick one."
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
            "Free Thursday morning Wellington networking group.\n"
            "Cost: FREE (no dues per group description).\n"
            "Contact: Alan Feuerman — sflbusinessconnectionsreply@gmail.com · 561-674-4300\n"
            "Status: Email inquiry sent 2026-05-16 asking PA seat status + venue.\n"
            "CONFLICT: PRE Palm Beach Gardens is also Thursday AM — pick one."
        ),
        "status": "TENTATIVE",
    },
    {
        "date": "2026-06-02",
        "start": "18:30",
        "end": "20:30",
        "summary": "West Palm Beach REI (first Tuesday) — TENTATIVE",
        "location": "West Palm Beach, FL (venue TBD)",
        "description": (
            "Monthly real estate investor meetup. First Tuesday of every month.\n"
            "Cost: Usually free for first-time visitors; $20-25 for non-members thereafter (typical REI fee).\n"
            "Website: https://www.meetup.com/west-palm-beach-real-estate-investors/\n"
            "Status: Researched 2026-05-16, not yet contacted. Drop-in friendly."
        ),
        "status": "TENTATIVE",
    },
    {
        "date": "2026-06-03",
        "start": "09:00",
        "end": "11:00",
        "summary": "Small Business Boot Camp (Central PBC Chamber) — TENTATIVE",
        "location": "Central PBC Chamber, 12794 W Forest Hill Blvd Suite 19, Wellington FL 33414",
        "description": (
            "Central PBC Chamber workshop series for small business owners.\n"
            "Cost: Usually free or low-cost for Chamber members; non-member fee TBD.\n"
            "Contact: Central PBC Chamber — 561-790-6200 · Info@CPBChamber.com\n"
            "Registration: https://cpbchamber.chambermaster.com/events/register/6001703\n"
            "Website: https://cpbchamber.com\n"
            "Status: Researched 2026-05-16, register once 5/19 Chamber Connections traction confirmed."
        ),
        "status": "TENTATIVE",
    },
    {
        "date": "2027-05-01",
        "start": "11:00",
        "end": "14:00",
        "summary": "Wellington Hurricane & Severe Weather Expo 2027 — VENDOR SLOT — TENTATIVE",
        "location": "Mall at Wellington Green, 10300 Forest Hill Blvd, Wellington FL 33414",
        "description": (
            "Annual hurricane preparedness expo for PBC residents. ~3000 homeowner attendees.\n"
            "Cost: TBD for vendor booth (typical municipal expos $0-500 for local businesses).\n"
            "Contact: Michelle Garvey — mgarvey@wellingtonfl.gov · 561-791-4082\n"
            "Website: https://www.wellingtonfl.gov\n"
            "Status: Vendor inquiry sent 2026-05-16, awaiting reply. High-leverage warm-lead venue."
        ),
        "status": "TENTATIVE",
    },
]


def event_signature(ev):
    raw = f"{ev['date']}|{ev['start']}|{ev['summary'].strip().lower()}|{ev['location'].strip().lower()}"
    return hashlib.sha1(raw.encode()).hexdigest()[:16]


def load_state():
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return {"sent_signatures": {}}


def save_state(state):
    ICS_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2, sort_keys=True))


def filter_events(events, state, max_months_out):
    today = datetime.now().date()
    cutoff = today + timedelta(days=int(max_months_out * 30.4375))
    sent = state.get("sent_signatures", {})
    kept, skipped_dup, skipped_far, skipped_past = [], [], [], []
    for ev in events:
        ev_date = datetime.strptime(ev["date"], "%Y-%m-%d").date()
        if ev_date < today:
            skipped_past.append(ev["summary"])
            continue
        if ev_date > cutoff:
            skipped_far.append(ev["summary"])
            continue
        sig = event_signature(ev)
        if sig in sent:
            skipped_dup.append(ev["summary"])
            continue
        kept.append((ev, sig))
    return kept, {"duplicates": skipped_dup, "too_far": skipped_far, "past": skipped_past}


def get_calendar_service():
    if not TOKEN_FILE.exists():
        sys.exit(f"missing {TOKEN_FILE} — run scripts/google_calendar_oauth.py first")
    info = json.loads(TOKEN_FILE.read_text())
    creds = Credentials.from_authorized_user_info(info, info["scopes"])
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return build("calendar", "v3", credentials=creds, cache_discovery=False)


def to_api_event(ev):
    start_dt = f"{ev['date']}T{ev['start']}:00"
    end_dt = f"{ev['date']}T{ev['end']}:00"
    status_map = {"TENTATIVE": "tentative", "CONFIRMED": "confirmed", "CANCELLED": "cancelled"}
    return {
        "summary": ev["summary"],
        "location": ev["location"],
        "description": ev["description"],
        "start": {"dateTime": start_dt, "timeZone": TZ},
        "end": {"dateTime": end_dt, "timeZone": TZ},
        "status": status_map.get(ev.get("status", "TENTATIVE"), "tentative"),
        "transparency": "transparent",
        "reminders": {"useDefault": True},
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--events-json", help="Load events from JSON file (list of dicts)")
    ap.add_argument("--max-months-out", type=float, default=12.0,
                    help="Skip events further than N months from today (default 12)")
    ap.add_argument("--no-dedup", action="store_true",
                    help="Skip dedup check (re-insert everything in input)")
    args = ap.parse_args()

    events = json.loads(Path(args.events_json).read_text()) if args.events_json else CURRENT_EVENTS
    state = {"sent_signatures": {}} if args.no_dedup else load_state()
    kept, skipped = filter_events(events, state, args.max_months_out)

    print(f"Input: {len(events)} events")
    print(f"Kept: {len(kept)}  |  Skipped — past: {len(skipped['past'])}, "
          f"too-far: {len(skipped['too_far'])}, dup: {len(skipped['duplicates'])}")
    for s in skipped["too_far"]:
        print(f"  too-far (>{args.max_months_out}mo): {s}")
    for s in skipped["duplicates"]:
        print(f"  dup: {s}")
    for s in skipped["past"]:
        print(f"  past: {s}")

    if not kept:
        print("Nothing new to add.")
        return

    if args.dry_run:
        for ev, _sig in kept:
            print(f"DRY: {ev['date']} {ev['start']} — {ev['summary']}")
        return

    svc = get_calendar_service()
    now_iso = datetime.now().isoformat(timespec="seconds")
    inserted = 0
    for ev, sig in kept:
        body = to_api_event(ev)
        try:
            created = svc.events().insert(calendarId=CALENDAR_ID, body=body).execute()
        except HttpError as e:
            print(f"  ERROR inserting {ev['summary']}: {e}")
            continue
        link = created.get("htmlLink", "")
        gid = created.get("id", "")
        print(f"  +  {ev['date']} {ev['start']} — {ev['summary']}  ->  {link}")
        if not args.no_dedup:
            state["sent_signatures"][sig] = {
                "date": ev["date"],
                "summary": ev["summary"],
                "sent_at": now_iso,
                "google_event_id": gid,
            }
        inserted += 1

    if not args.no_dedup and inserted:
        save_state(state)

    LOG_PATH.open("a").write(
        f"{now_iso}  one-off  ADDED  {CALENDAR_ID}  Calendar API insert ({inserted} events)\n"
    )
    print(f"Inserted {inserted} events into {CALENDAR_ID} @ {now_iso}")


if __name__ == "__main__":
    main()
