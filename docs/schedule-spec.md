# Daily Operations Schedule (v1 — drafted 2026-04-21)

Timezone: **America/New_York (EDT)**. Goal: new public adjuster targeting 100 clients in 100 days in South Florida.

Counties in scope: Palm Beach, Martin, Miami-Dade, St. Lucie, Broward.

All triggers fire as fresh agents (no memory of live chat). Each prompt must be self-contained.

## Daily triggers

### 4:00 AM — Industry Research Brief
- **Model:** Sonnet
- **Runs:** Every day, 7 days/week (storms don't take weekends off)
- **Reads:** web (news sources, local papers, government, insurance industry)
- **Writes:** `workspace/briefs/YYYY-MM-DD.md`
- **Format:** text-only, newspaper-style structure, sources cited, charts/tables as markdown where useful
- **Goal:** surface the most important industry news for PA work — insurance, real estate, residential/commercial service industries (plumbing, A/C, general contracting, roofing)

### 8:00 AM — Trend + Service-Provider Matching
- **Model:** Opus (strategic synthesis)
- **Runs:** Every day, 7 days/week
- **Reads:** last 7 days of `workspace/briefs/*.md`
- **Writes:** `workspace/trends/YYYY-MM-DD.md`
- **Goal:** identify recurring themes, problems, concerns. For each, flag which type of service provider could benefit (readers are service providers, not end clients — they want leads).

### 9:00 AM — Content Creation
- **Model:** Sonnet
- **Runs:** Every day, 7 days/week
- **Reads:** today's `workspace/trends/YYYY-MM-DD.md` + today's brief
- **Writes:** `workspace/content/YYYY-MM-DD/` folder with:
  - `facebook.md` — Facebook post draft
  - `instagram.md` — Instagram post draft (caption + suggested image description)
  - `blog.md` — blog post draft
- **Goal:** each format has its own voice/length/structure. Drafts only — posting is manual until accounts are set up and we wire integrations.

### 12:00 PM — CRM Outreach + Followup
- **Model:** Sonnet (drafts), Opus (strategic decisions: escalate/pause/reassess)
- **Runs:** Monday–Friday (no cold outreach on weekends)
- **Reads:** `workspace/crm/organizations.csv`, `workspace/crm/interactions.csv`, today's trends
- **Writes:**
  - Drafts in `workspace/crm/drafts/YYYY-MM-DD/` (one file per target)
  - Updates `workspace/crm/interactions.csv` with planned touches
  - Updates `next_followup_date` on orgs
- **Sending:** NEVER. All outreach is drafts-for-review. Duncan approves and sends manually.
- **Cadence:** every 3–5 days per target, with escalating message tone. Goal is to schedule in-person / Zoom / call meeting.
- **Compliance:** every template passes anti-spam (CAN-SPAM, state UDAP) and platform TOS check before being drafted.

### 5:00 PM — End-of-Day Operations Review
- **Model:** Opus
- **Runs:** Monday–Thursday, 5:00 PM (Friday handled by weekly rollup)
- **Reads:** everything produced today + previous review files
- **Writes:** `workspace/ops-review/YYYY-MM-DD.md`
- **Goal:** status report, what worked, what didn't, questions for Duncan, suggestions to improve the next day's ops. Small improvements compound.

## Weekly trigger

### Friday 5:00 PM — Weekly Rollup
- **Model:** Opus
- **Runs:** Fridays
- **Reads:** this week's ops-reviews, briefs, content, CRM state
- **Writes:** `workspace/weekly/YYYY-WW.md`
- **Goal:** patterns the daily review misses, week-level suggestions, prioritization for next week.

## Folder layout

```
workspace/
  briefs/          4am output
  trends/          8am output
  content/         9am output (one folder per day)
  crm/
    organizations.csv
    interactions.csv
    templates.md
    drafts/        12pm outreach drafts (one folder per day)
  ops-review/      5pm daily review
  weekly/          Friday 5pm rollup
```

## Explicit agreements

- **Drafts-for-review everywhere.** Nothing sends on its own — not email, not social posts, not CRM messages. All require Duncan's explicit approval until that changes.
- **Consent-first.** Triggers fire scheduled tasks; if a task wants to take a new category of action not in this spec, it asks first.
- **Model routing.** Each trigger specifies its model. Haiku not yet assigned anywhere; can slot in for Compliance Scan or light classification if we identify a cheap-enough task.

## Open for later

- Social media account setup (Facebook, Instagram, blog platform) — Duncan hasn't set up accounts yet. Defer.
- Sending integrations (email, LinkedIn, platform posting APIs) — defer until drafts are consistently good enough to automate.
- Airtable migration of CRM — once V0 local files validate the schema.
- Haiku-tier tasks — open slot for cheap pre-processing or compliance checks if they emerge.
