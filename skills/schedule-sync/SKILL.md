---
name: schedule-sync
description: "Whenever a cron is added, edited, removed, or run-manually, mirror the change to OPERATIONS-SCHEDULE.html and the schedule memory entries. Locks the always-in-sync rule."
user-invocable: true
---

# Schedule sync

Trigger conditions:
- I just called `cron add`, `cron update`, `cron remove`, or `cron enabled toggle`
- Duncan asked about the schedule
- Weekly self-review identified schedule drift

## Workflow

1. Read `~/.openclaw/cron/jobs.json` — source of truth.
2. Read `docs/OPERATIONS-SCHEDULE.html` (or `PA-WEBSITE.html` schedule section — confirm path).
3. Diff. Reconcile so HTML matches jobs.json exactly:
   - Job name
   - Schedule (cron expr in human form: "4:00 AM EDT Mon–Sat")
   - Description
   - Enabled state (grey out disabled jobs)
   - Last run + next run timestamps
4. Commit with message `ops: sync schedule (NN jobs)`.
5. If a job was added/removed, also update memory (`memory/feedback_operations_schedule.md` and `MEMORY.md` index if needed).

## Format expectations

OPERATIONS-SCHEDULE.html groups jobs by category:
- Content & briefs (daily-research-brief, daily-trends, daily-content, daily-newsletter-send)
- CRM & outreach (weekday-crm-outreach, response-handler, daily-contact-form-fallback, daily-hubspot-consolidation)
- Intel & prospecting (prospect-deep-intelligence, daily-networking-event-discovery, partnership-network-builder)
- Ops & health (weekday-ops-review, daily-health-check, daily-git-sync, update-dashboard, friday-weekly-rollup, monthly-velocity-review)
- Memory & system (Memory Dreaming Promotion, weekly-trends-send)

## Do not
- Edit jobs.json directly when the change is purely cosmetic — that's the cron tool's job. Use this skill only for HTML/memory mirroring.
- Leave the HTML stale even for an hour. Duncan asks "what's running?" and if HTML lies, trust drops.
- Skip the git commit. The HTML update must be in git so Netlify deploys it.
- Convert times to UTC. Always local-wall-clock (America/New_York).

## Outputs
- Updated `docs/OPERATIONS-SCHEDULE.html`
- Git commit
- Optional memory update if structure changed
