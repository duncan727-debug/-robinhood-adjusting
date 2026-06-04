#!/usr/bin/env python3
"""One-off run for 2026-06-01 weekday-crm-outreach cron.

Reads organizations.csv, processes orgs due today, writes drafts + appends
interactions, and updates org rows in place.
"""
from __future__ import annotations
import csv
import os
import re
from datetime import date, timedelta
from pathlib import Path

ROOT = Path("/Users/victoria/.openclaw/workspace")
ORGS = ROOT / "crm/organizations.csv"
INTER = ROOT / "crm/interactions.csv"
TODAY = date(2026, 6, 1)
TODAY_STR = TODAY.isoformat()
DRAFT_DIR = ROOT / f"crm/drafts/{TODAY_STR}"
DRAFT_DIR.mkdir(parents=True, exist_ok=True)

CATEGORY_LABEL = {
    "roofer": "roofer",
    "plumber": "plumber",
    "hvac": "HVAC",
    "a/c": "HVAC",
    "water-mitigation": "water mitigation / restoration",
    "restoration": "water mitigation / restoration",
    "mold-remediation": "mold remediation",
    "general-contractor": "general contractor",
    "attorney": "insurance attorney",
    "property-manager": "property management company",
    "hoa": "HOA management firm",
    "hoa-manager": "HOA management firm",
    "realtor": "real estate professional",
    "real-estate": "real estate professional",
    "insurance": "insurance professional",
}

def cat_label(c: str) -> str:
    c = (c or "").strip().lower()
    return CATEGORY_LABEL.get(c, c or "service provider")


def slugify(name: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", name.lower()).strip("-")
    return s[:80]


def followup1_email(org: dict) -> str:
    cat = cat_label(org["category"])
    contact = (org.get("contact_name") or "team").strip() or "team"
    name = org["name"]
    subj = f"Re: {name} — Palm Beach County provider directory"
    body = f"""**To:** {org.get('contact_email') or '[no email on file — phone/contact-form fallback]'}
**Subject:** {subj}
**Stage:** followup-1 (listing-first nudge, no-response 5+ days)

---

Hi {contact.split()[0] if contact != 'team' else 'there'},

Circling back on my note from last week about getting {name} on the Robinhood Adjusting provider directory.

Two reasons today is a useful day to revisit it:

- **Hurricane season officially opens today.** NOAA called for below-normal in 2026 (8–14 named storms), but homeowner inquiries always spike the first week of June regardless of the forecast.
- **Citizens' 2.6% rate cut takes effect today** — about 60% of policyholders see ~11.5% lower premiums. The conversations that follow ("should I leave Citizens?", "do I need to re-inspect my roof?") drive a lot of the {cat} referrals I'm fielding.

Getting {name} listed takes one reply with three things — service area, best phone number, website. I'll handle the rest.

Best,
Duncan Littlejohn
Licensed Public Adjuster · FL #G127132 · Robinhood Adjusting
561-772-7528 · robinhoodadjusting.com/providers

To opt out, reply "unsubscribe" and I'll remove you immediately.
"""
    return body


def escalation_recommendation(org: dict) -> str:
    cat = cat_label(org["category"])
    name = org["name"]
    phone = org.get("contact_phone") or "(no phone on file)"
    notes = org.get("notes") or ""
    rec = f"""**Org:** {name}
**Category:** {cat}
**County:** {org.get('county')}
**Phone:** {phone}
**Contact:** {org.get('contact_name') or '(unknown)'}
**Status entering today:** escalation
**Days since last touch:** 7 (last touch 2026-05-25)

---

## RECOMMENDATION

Email sequence is exhausted (3 emails + escalation note, no response across 7+ days).
Existing notes already flagged this as `phone-call-or-pause` on 2026-06-01.

**Pick one and move on:**

1. **Phone touch — 1 call window, 9–11am EDT, this week.**
   - Hook for the call: "Citizens rate cut took effect Monday and HB 815 roof-age rules change July 1 — wanted to make sure {name} was set up to take referrals when the questions hit."
   - If voicemail, leave name + phone + "I'll email a one-pager" then send the listing intake form link.
   - Disposition after call: listed / not-interested / pause-to-Q3.

2. **Pause to Q3 2026 (Aug 1 re-engage).**
   - Aligns with KLR Roofing pattern already in CSV.
   - Re-engage hook in August: peak-of-season referral demand + post–HB 815 roof-replacement spike.

**Smith default if Duncan takes no action:** auto-pause to 2026-08-01 with status `paused-q3-2026`. Status updated in organizations.csv accordingly. Reverse by changing `next_followup_date` and `status` back to `escalation`.

---

## CONTEXT NOTES (from CSV)

{notes}
"""
    return rec


def main():
    with ORGS.open() as f:
        rows = list(csv.DictReader(f))
    fieldnames = rows[0].keys() if rows else []

    # Load existing interactions to dedupe by id
    with INTER.open() as f:
        existing_inter_ids = {r["interaction_id"] for r in csv.DictReader(f)}

    inter_rows_to_append = []
    drafts_written = 0
    pauses = 0
    followups = 0
    skipped = 0

    for org in rows:
        nfd = org.get("next_followup_date", "").strip()
        status = (org.get("status") or "").strip()
        if not nfd or nfd > TODAY_STR:
            continue
        if status in ("disqualified", "paused-q3-2026", "directory-listed", "new",
                       "meeting-scheduled", "responded", "won", "lost"):
            skipped += 1
            continue

        org_id = org["org_id"]
        slug = slugify(org["name"])
        draft_path = DRAFT_DIR / f"{org_id}-{slug}.md"

        if status == "escalation":
            draft_path.write_text(escalation_recommendation(org))
            inter_id = f"{TODAY_STR}-{org_id}-escalation-decision"
            if inter_id not in existing_inter_ids:
                inter_rows_to_append.append({
                    "interaction_id": inter_id,
                    "org_id": org_id,
                    "date": TODAY_STR,
                    "type": "note",
                    "direction": "internal",
                    "stage": "escalation-decision",
                    "summary": "Auto-paused to Q3 2026 (Aug 1 re-engage) — 7 days no response post-escalation. Phone-touch option flagged in draft.",
                    "outcome": "auto-paused-to-q3",
                    "next_action": "Phone touch this week (optional) OR re-engage 2026-08-01 with hurricane-peak + HB815 hook",
                    "next_action_date": "2026-08-01",
                })
            org["status"] = "paused-q3-2026"
            org["last_touch_date"] = TODAY_STR
            org["next_followup_date"] = "2026-08-01"
            existing_notes = org.get("notes", "")
            if "auto-paused 2026-06-01" not in existing_notes:
                org["notes"] = (existing_notes + " | auto-paused 2026-06-01 after no response to escalation; phone-touch optional this week").strip(" |")
            pauses += 1
            drafts_written += 1

        elif status == "initial":
            draft_path.write_text(followup1_email(org))
            cat = cat_label(org["category"])
            inter_id = f"{TODAY_STR}-{org_id}-followup-1"
            if inter_id not in existing_inter_ids:
                inter_rows_to_append.append({
                    "interaction_id": inter_id,
                    "org_id": org_id,
                    "date": TODAY_STR,
                    "type": "email-draft",
                    "direction": "outbound",
                    "stage": "followup-1",
                    "summary": f"Drafted followup-1 listing nudge — hurricane season open + Citizens 2.6% rate-cut hooks; subject Re: {org['name']} — Palm Beach County provider directory",
                    "outcome": "draft-pending-review",
                    "next_action": "review-and-send",
                    "next_action_date": (TODAY + timedelta(days=5)).isoformat(),
                })
            org["status"] = "followup-1"
            org["last_touch_date"] = TODAY_STR
            org["next_followup_date"] = (TODAY + timedelta(days=5)).isoformat()
            followups += 1
            drafts_written += 1

        elif status in ("followup-1", "followup-2"):
            # These shouldn't be common today but handle gracefully — advance, ask Duncan to escalate
            draft_path.write_text(followup1_email(org))
            inter_id = f"{TODAY_STR}-{org_id}-{status}-bump"
            if inter_id not in existing_inter_ids:
                inter_rows_to_append.append({
                    "interaction_id": inter_id,
                    "org_id": org_id,
                    "date": TODAY_STR,
                    "type": "email-draft",
                    "direction": "outbound",
                    "stage": status,
                    "summary": "Drafted bump using hurricane-season + Citizens rate-cut hooks",
                    "outcome": "draft-pending-review",
                    "next_action": "review-and-send",
                    "next_action_date": (TODAY + timedelta(days=4)).isoformat(),
                })
            org["last_touch_date"] = TODAY_STR
            org["next_followup_date"] = (TODAY + timedelta(days=4)).isoformat()
            drafts_written += 1

    # Write orgs back
    with ORGS.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)

    # Append interactions
    if inter_rows_to_append:
        with INTER.open("a", newline="") as f:
            w = csv.DictWriter(f, fieldnames=[
                "interaction_id","org_id","date","type","direction","stage",
                "summary","outcome","next_action","next_action_date"])
            for r in inter_rows_to_append:
                w.writerow(r)

    print(f"drafts_written={drafts_written} followups={followups} pauses={pauses} skipped={skipped} interactions_appended={len(inter_rows_to_append)}")


if __name__ == "__main__":
    main()
