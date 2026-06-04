# 2026-06-02 outreach status

**This 6am prompt-driven workflow is now superseded by the automated outreach pipeline.**

Active automation handling today's CRM touches:
- `outreach_send.py` — cold first-touch + follow-up sends (logged: scripts/outreach_send.log)
- `drip.py` — sequence advancement (logged: scripts/drip.log)
- `contact_form_queue.py` — bounce-fallback to website forms (10:45am)
- `imap_bridge.py` — reply/bounce ingestion → HubSpot (every 5 min)
- `stage_gmail_drafts.py` — EMAIL-type HubSpot tasks → Gmail Drafts (per Duncan's review-from-Gmail preference)

## Manual-judgment items flagged today

Scanned `organizations.csv` for orgs whose `next_followup_date <= 2026-06-02` AND not paused/disqualified/directory-listed:

| org_id | status | next_followup | note |
|---|---|---|---|
| miamidade-miami-best-roofing | new | 2026-05-30 | Overdue 3 days. Tier-1 HVHZ prospect, no owner name surfaced. Listing-first first-contact + phone fallback (786-808-6212) by now per row notes. Confirm whether automation queued it; if not, hand-touch. |

Other "due-today" rows (`integrity-plumbing`, `snyder-ac`) parsed as overdue on naive awk but their real `next_followup_date` is 2026-06-06 (commas inside quoted notes broke field parsing). Not actually due.

## Recommendation

Retire this 6am cron prompt and let the automation pipeline run unmanaged. Keep this slot for a daily exception-review only: anything `status=new` and `next_followup_date < today` that the automation hasn't touched.
