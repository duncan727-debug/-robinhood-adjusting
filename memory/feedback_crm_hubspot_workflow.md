---
name: CRM HubSpot Auto-Upload Workflow
description: All new CRM partner research must be automatically uploaded to HubSpot with drafted email, note, and task for Duncan's manual review
type: feedback
---

For every new CRM prospect or partner added during research:
1. Find or create the contact + company in HubSpot
2. Log the drafted outreach email as a Note on the contact/company record
3. Create a Task ("Review & Send: [subject]") so it appears in Duncan's task queue
4. Do NOT send the email — Duncan reviews and sends manually

**Why:** Duncan wants full visibility in HubSpot before anything goes out. Manual send is intentional — he controls all outreach.

**How to apply:** After any CRM outreach draft is generated (weekday-crm-outreach cron or ad-hoc research), call upload_drafts_to_hubspot.py or equivalent to sync to HubSpot immediately. LinkedIn is paused — do not queue LinkedIn sequences until re-enabled.
