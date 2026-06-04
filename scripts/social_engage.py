#!/usr/bin/env python3
"""
Social engagement queue + executor for Robinhood Adjusting.

Reads:  crm/wellington_service_pros_social.csv
        crm/social_engagement_queue.csv  (drafted comments + scheduled actions)
Logs:   crm/social_engagement_log.csv     (every action taken)
Drives: Duncan's second Chrome window via JXA + cliclick

Modes:
    python3 social_engage.py queue          # populate tomorrow's batch from CSV
    python3 social_engage.py drafts         # generate comment drafts for queued items
    python3 social_engage.py run            # execute the next queued slot
    python3 social_engage.py status         # show queue + log summary

Honest constraint: Page-to-Page liking + commenting requires being signed in as
the Robinhood Adjusting Page on facebook.com. This script writes the queue and
opens the target URLs in Duncan's second Chrome window; cliclick automation of
the actual Like/Comment is added incrementally.
"""
import csv
import json
import sys
import subprocess
import random
import os
from datetime import datetime, timedelta
from pathlib import Path

WORKSPACE = Path("/Users/victoria/.openclaw/workspace")
TARGETS_CSV = WORKSPACE / "crm" / "wellington_service_pros_social.csv"
QUEUE_CSV = WORKSPACE / "crm" / "social_engagement_queue.csv"
LOG_CSV = WORKSPACE / "crm" / "social_engagement_log.csv"
SECRETS = WORKSPACE / "config" / ".secrets"

QUEUE_FIELDS = [
    "queued_date", "scheduled_for", "company_name", "category", "fb_page_url",
    "ig_handle", "action", "comment_draft", "status", "executed_at", "notes",
]
LOG_FIELDS = [
    "ts", "company_name", "action", "platform", "url_or_handle", "result",
]


def load_targets():
    with open(TARGETS_CSV) as f:
        return list(csv.DictReader(f))


def load_queue():
    if not QUEUE_CSV.exists():
        return []
    with open(QUEUE_CSV) as f:
        return list(csv.DictReader(f))


def save_queue(rows):
    with open(QUEUE_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=QUEUE_FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in QUEUE_FIELDS})


def append_log(entry):
    new = not LOG_CSV.exists()
    with open(LOG_CSV, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=LOG_FIELDS)
        if new:
            w.writeheader()
        w.writerow(entry)


def already_engaged(company):
    if not LOG_CSV.exists():
        return False
    with open(LOG_CSV) as f:
        for row in csv.DictReader(f):
            if row["company_name"] == company:
                return True
    return False


def cmd_queue():
    """Build next batch: 6 actions/day (3 follows + 3 comment-likes), Mon-Fri."""
    targets = load_targets()
    queue = load_queue()
    queued_companies = {q["company_name"] for q in queue if q["status"] in ("pending", "drafted")}

    # Pick the next 6 untouched companies, mix categories
    candidates = [t for t in targets
                  if t["company_name"] not in queued_companies
                  and not already_engaged(t["company_name"])
                  and (t.get("fb_page_url") or t.get("ig_handle"))]

    if not candidates:
        print("No untouched targets remain. Queue empty by design.")
        return

    # Shuffle for variety, take up to 6
    random.shuffle(candidates)
    today_str = datetime.now().strftime("%Y-%m-%d")
    # Next weekday slots: tomorrow 10:30am if it's a weekday
    next_day = datetime.now() + timedelta(days=1)
    while next_day.weekday() > 4:  # 0=Mon, 4=Fri
        next_day += timedelta(days=1)
    slot_morning = next_day.replace(hour=10, minute=30, second=0, microsecond=0)
    slot_afternoon = next_day.replace(hour=16, minute=30, second=0, microsecond=0)

    new_rows = []
    for idx, t in enumerate(candidates[:6]):
        slot = slot_morning if idx < 3 else slot_afternoon
        action = "follow_and_comment" if idx % 2 == 0 else "follow_only"
        new_rows.append({
            "queued_date": today_str,
            "scheduled_for": slot.strftime("%Y-%m-%d %H:%M"),
            "company_name": t["company_name"],
            "category": t["category"],
            "fb_page_url": t.get("fb_page_url", ""),
            "ig_handle": t.get("ig_handle", ""),
            "action": action,
            "comment_draft": "",
            "status": "pending" if action == "follow_only" else "needs_draft",
            "executed_at": "",
            "notes": t.get("why_relevant_one_line", ""),
        })

    queue.extend(new_rows)
    save_queue(queue)
    print(f"Queued {len(new_rows)} new actions for {next_day.strftime('%a %Y-%m-%d')}")
    for r in new_rows:
        print(f"  {r['scheduled_for']}  {r['action']:20s}  {r['company_name']} ({r['category']})")


def cmd_drafts():
    """Draft comments for any queued items where status='needs_draft'."""
    queue = load_queue()
    drafted = 0
    for r in queue:
        if r.get("status") != "needs_draft":
            continue
        # Per-category seed lines — Duncan's voice, tips-not-pitch
        cat = r.get("category", "")
        templates = {
            "plumber": [
                "Good thread. Quick one for homeowners watching: water-damage claims hinge on whether the leak was 'sudden and accidental' vs slow seepage. Photo timestamps make or break it. Glad y'all are out there.",
                "Solid work. One thing most folks don't realize until they're in a claim: a sudden burst is usually covered, slow long-term seepage usually isn't. Documenting the moment you found it is huge.",
            ],
            "hvac": [
                "Nice. AC-line condensate leaks are one of the most under-paid claims out there — carriers love to argue 'wear and tear.' Photos of the original install date plate help a lot.",
                "Good post. Worth knowing on the homeowner side: if an AC failure causes ceiling/drywall damage, the resulting damage is usually covered even if the unit itself isn't.",
            ],
            "roofer": [
                "Good work. Reminder for homeowners: if your roof is 15+ as of July 1, HB 815 gives you the right to a pro inspection before a forced replacement. Don't sign off on a non-renewal without that.",
                "Solid. The wind-mit form changed April 1 — if your last 1802 was pre-2023, a fresh inspection often pays for itself in year one.",
            ],
            "general-contractor": [
                "Quality work. Reminder for anyone in a rebuild: 'matching' coverage in Florida means the carrier owes a reasonable match for damaged materials — don't accept a half-job.",
                "Nice build. Building-code-upgrade coverage (Ord & Law) is one of the most-overlooked endorsements when reconstruction starts.",
            ],
            "real-estate": [
                "Great listing. Quick PSA for buyers: pull the wind-mit and 4-point before closing — it's the cheapest way to know if the policy will price reasonably. Happy to read one if anyone needs it.",
                "Nice. Wellington has been getting some 11%+ premium decreases this cycle — worth a re-shop at renewal even if the original quote felt locked in.",
            ],
            "restoration": [
                "Good work — y'all are usually first on scene for the worst weeks of a homeowner's year. Appreciate the field.",
                "Nice. The cleanest claims I see are the ones where mitigation gets documented as it happens. Y'all make our job easier.",
            ],
            "pool": [
                "Good post. Pool-cage damage is the most under-claimed wind loss in PBC — homeowners assume it's not covered, but it usually is if the policy includes 'other structures.'",
                "Solid. Heads-up for homeowners: pool screen + cage replacement after a storm runs $8-15K — make sure your 'other structures' limit isn't sitting at 2% of dwelling.",
            ],
            "tree-landscape": [
                "Good work. Quick one for homeowners: trees that fall and don't hit anything generally aren't covered for removal — but if it hits the house or blocks the driveway, removal usually is. Document before cleanup.",
                "Solid. After a storm, photograph any fallen tree before removal — even if it didn't hit the house, the disposal cost can sometimes attach to a covered loss.",
            ],
        }
        choices = templates.get(cat, ["Good work — glad to see you out there in Wellington."])
        r["comment_draft"] = random.choice(choices)
        r["status"] = "drafted"
        drafted += 1
    save_queue(queue)
    print(f"Drafted {drafted} comments. Review at: {QUEUE_CSV}")


def cmd_status():
    queue = load_queue()
    now = datetime.now()
    pending = [r for r in queue if r["status"] in ("pending", "drafted")]
    done = [r for r in queue if r["status"] == "executed"]
    failed = [r for r in queue if r["status"] == "failed"]
    print(f"Queue: {len(pending)} pending  |  {len(done)} executed  |  {len(failed)} failed")
    print("Next 5 upcoming:")
    for r in sorted(pending, key=lambda x: x["scheduled_for"])[:5]:
        print(f"  {r['scheduled_for']}  {r['action']:20s}  {r['company_name']}")
    print(f"\nLog: {LOG_CSV}")


def cmd_run():
    """Execute the next due action(s) — for cron use.

    Right now this is the safe path: it opens the target page in Duncan's
    second Chrome window and logs that we 'staged' the action. The actual
    Like/Comment cliclick driver is added once we've reliably mapped the
    Page-identity switcher coords.
    """
    queue = load_queue()
    now = datetime.now()
    due = [r for r in queue
           if r["status"] in ("pending", "drafted")
           and r["scheduled_for"]
           and datetime.strptime(r["scheduled_for"], "%Y-%m-%d %H:%M") <= now]
    if not due:
        print("No due actions.")
        return
    # Take up to 2 per run to keep human pacing
    batch = due[:2]
    for r in batch:
        url = r["fb_page_url"] or (f"https://www.instagram.com/{r['ig_handle']}/" if r["ig_handle"] else "")
        if not url:
            r["status"] = "failed"
            r["notes"] = (r.get("notes", "") + " | no URL").strip()
            continue
        # Open in second Chrome window (do NOT activate)
        jxa = (
            'var Chrome = Application("Google Chrome");'
            'var ws = Chrome.windows;'
            'var targetW = ws.length > 1 ? 1 : 0;'
            'var tab = Chrome.Tab({url: "' + url + '"});'
            'ws[targetW].tabs.push(tab);'
            '"opened";'
        )
        try:
            subprocess.run(["osascript", "-l", "JavaScript", "-e", jxa], check=True, timeout=10)
            r["status"] = "staged"
            r["executed_at"] = now.strftime("%Y-%m-%d %H:%M:%S")
            append_log({
                "ts": r["executed_at"], "company_name": r["company_name"],
                "action": "staged_" + r["action"], "platform": "fb" if r["fb_page_url"] else "ig",
                "url_or_handle": url, "result": "tab_opened",
            })
            print(f"Staged: {r['company_name']} — {url}")
        except Exception as e:
            r["status"] = "failed"
            r["notes"] = (r.get("notes", "") + f" | err: {e}").strip()
            append_log({
                "ts": now.strftime("%Y-%m-%d %H:%M:%S"), "company_name": r["company_name"],
                "action": r["action"], "platform": "fb" if r["fb_page_url"] else "ig",
                "url_or_handle": url, "result": f"failed: {e}",
            })
    save_queue(queue)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    {"queue": cmd_queue, "drafts": cmd_drafts, "run": cmd_run, "status": cmd_status}[cmd]()
