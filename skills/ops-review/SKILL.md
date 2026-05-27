---
name: ops-review
description: "Generate Duncan's morning operations review: pipeline state, replies needing action, overdue tasks, service health, schedule deltas, decisions due today."
user-invocable: true
---

# Ops review

Fires ~07:30 EDT daily. Output: `ops-review/YYYY-MM-DD.md`. Duncan reads it by 08:00.

Goal: he should be able to act on the entire day's priorities in one read. No fluff. No "system is healthy" prose if there's nothing to do — say so in one line.

## Sections (in this order)

### 1. Decisions due today
What does Duncan have to choose / approve / send / sign? Each item links to the artifact. If the list is empty, write "None — proceed."

### 2. Replies waiting on Duncan
From IMAP bridge + HubSpot + responses queue. For each: sender, intent, urgency, suggested next step. If I drafted a response already, link to draft.

### 3. Pipeline movement (last 24h)
- Outreach sent (count, by audience)
- Replies received (count, link to thread)
- New listings added to directory
- Provider directory signups
- HubSpot pipeline stage changes

### 4. Overdue / stuck
- HubSpot tasks past due
- Drafts >48h old without send
- Contact-form fallback queue depth
- Listings stuck in pending >7 days

### 5. Service health
One-line status: Gmail / GitHub / Netlify / HubSpot / Namecheap / gateway. Green dot if all OK. Red + details if any down.

### 6. Cron deltas
Any cron that failed, was skipped, or runs late since yesterday's review.

### 7. Calendar today
Meetings, networking events, RSVPs due. From Google Calendar API.

### 8. Today's content
What's scheduled to publish: brief, social posts, newsletter. With links.

## Workflow
1. Pull metrics in parallel (`scripts/collect_ops.py` if it exists; else inline).
2. Draft prose. Keep total under 400 words unless something major broke.
3. Write to `ops-review/YYYY-MM-DD.md`.
4. Surface anything urgent as a HubSpot task on Duncan (don't bury in chat per `feedback_hubspot_tasks_for_duncan_actions`).

## Do not
- Repeat the same overdue item every day without escalating. After 3 days flag for Duncan as "decision required."
- Write the section header if the section has zero items — replace with a single line.
- Wait for Duncan to ask. This skill is push, not pull.
- Drop schedule changes — if a cron was added/edited/removed in last 24h, OPERATIONS-SCHEDULE.html must show it (use `schedule-sync` skill).
