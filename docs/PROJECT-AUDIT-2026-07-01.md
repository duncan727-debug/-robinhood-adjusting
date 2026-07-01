# Robinhood Adjusting Project Audit

Date: 2026-07-01  
Scope: website, publication, CRM files, automation scripts, integrations, and operating direction.

## Executive Read

Robinhood is no longer just a static public-adjuster website. It is becoming a small media-and-referral engine: public adjuster credibility on the front end, free South Florida property intelligence as the trust-builder, and partner/referral workflows behind it.

The healthiest parts of the project are the public website, the brief archive, the newly repackaged `Robinhood Property Intelligence` pages, GitHub/Netlify deployment, and local Gmail access. The weakest parts are HubSpot connectivity, stale automation paths, duplicated content locations, and old project experiments that make the repo feel harder to operate than it needs to be.

The immediate direction should be:

1. Keep the current live website stable.
2. Use daily briefs and weekly trends as the audience-building engine.
3. Bring HubSpot back online.
4. Modernize only the scripts that support the current operating model.
5. Archive old experiments so the working system is easier to trust.

## Current Strategic Goal

Use the website and newsletter to get Robinhood in front of:

- Local homeowners and property owners.
- Real estate agents, brokers, investors, and property managers.
- Contractors, mitigation firms, roofers, plumbers, HVAC firms, GCs, and home-service businesses.
- Professionals who regularly see damage, insurance friction, or claim confusion before a public adjuster is called.

The offer is not "hire us now" as the first touch. The front-door offer is free market insight, useful checklists, and a free review when a real claim issue appears.

## What Is Live And Working

### Website

Live site:

- `https://robinhoodadjusting.com/`
- Netlify publish directory: `site/`
- Deploy path: GitHub `main` -> Netlify -> production.

Key public pages:

- `site/index.html` - current homepage.
- `site/PA-WEBSITE.html` - duplicate/legacy homepage copy still maintained.
- `site/briefs/index.html` - daily brief archive.
- `site/trends/index.html` - weekly trends archive.
- `site/providers/index.html` - trusted provider directory.
- `site/free-review.html` - free virtual review offer.
- `site/hurricane-checklist.html`
- `site/insurance-policy-review.html`
- `site/contractor-vetting-guide.html`
- `site/storm-shield.html`
- `site/articles/` - public education articles.

The July 1 brief package is live and wired into:

- Homepage intelligence section.
- Brief archive.
- Sitemap.
- Segment pages:
  - homeowner
  - real estate
  - service provider
  - full research edition

### Facelift Preview

Saved but not live:

- `previews/robinhood-home-facelift.html`

Netlify publishes only `site/`, so this preview is safely outside the live site. It can be used as the base for the next homepage revision after approval.

### GitHub And Netlify

GitHub connection health is verified through:

- `/.netlify/functions/github-health`

Current production health check confirms:

- Repo: `duncan727-debug/-robinhood-adjusting`
- Branch: `main`
- GitHub API access: working
- Repository content checks: working

### Gmail

Local Gmail access is connected for:

- `duncanlittlejohn727@gmail.com`

Verified:

- IMAP login works.
- SMTP login works.
- Draft creation works.
- Sending works.

Local secret storage:

- `/Users/smith/.openclaw/workspace/config/.secrets`

This file is outside the Git repo and should stay that way.

## What Is Partially Working

### Publication System

There are three overlapping content locations:

- `briefs/` - markdown/source brief history.
- `content/briefs/` - older/generated email-ready brief files.
- `site/briefs/` - public website brief pages.

There are also trend locations:

- `trends/`
- `content/trends/`
- `site/trends/`
- `publication/trends/`

This is workable, but confusing. The new convention should be:

- `publication/briefs/YYYY-MM-DD/` for working notes and source trails.
- `publication/trends/` for trend working notes.
- `site/briefs/` for public final HTML.
- `site/trends/` for public final HTML.

Older `briefs/` and `content/briefs/` should be treated as historical/source archive unless a script still depends on them.

### Netlify Functions

Functions in `netlify/functions/` include:

- `subscribe-newsletter.js`
- `subscribe.js`
- `contact-request.js`
- `get-listed.js`
- `listing-response.js`
- `qualify.js`
- `github-health.js`

The GitHub health function is working. The HubSpot-dependent functions depend on Netlify `HUBSPOT_API_KEY`. Production may have it, but local HubSpot is currently not connected.

## What Is Blocked

### HubSpot

Local `HUBSPOT_API_KEY` is missing. Until HubSpot access is restored and a private-app token is added locally, these workflows are blocked or incomplete:

- Newsletter list lookup/send automation.
- HubSpot task creation for staged Gmail drafts.
- Contact/list enrollment testing from local scripts.
- Pipeline/deal updates.
- IMAP bridge reply/bounce logging into HubSpot.
- Provider/listing workflows that depend on HubSpot writes.

Needed token scopes:

- Contacts read/write.
- Companies read/write.
- Deals read/write.
- Tasks read/write.
- Lists read.

### Old Script Paths

There are 81 top-level script files under `scripts/`. A scan found 49 scripts still referencing the old path:

- `/Users/victoria/.openclaw/workspace`

That means many legacy scripts will fail on this machine unless modernized.

Core Gmail/newsletter scripts already patched to use `scripts/workspace_config.py`:

- `scripts/stage_gmail_drafts.py`
- `scripts/send-daily-brief.py`
- `scripts/send-weekly-trends.py`
- `scripts/imap_bridge.py`
- `scripts/drip.py`

Still needing triage before use:

- CRM upload/enrichment scripts.
- social/Meta scripts.
- Google Sheets/Calendar scripts.
- catchup/build shell scripts.
- one-off send scripts.
- old outreach restoration scripts.

Do not run old scripts blindly.

## Repo Areas By Recommendation

### Keep Active

- `site/`
- `netlify/functions/`
- `publication/`
- `previews/`
- `scripts/workspace_config.py`
- `scripts/stage_gmail_drafts.py`
- `scripts/send-daily-brief.py`
- `scripts/send-weekly-trends.py`
- `scripts/imap_bridge.py`
- `scripts/drip.py`
- `crm/directory_companies.json`
- `crm/templates.md`
- `docs/PROJECT-AUDIT-2026-07-01.md`

### Keep As Historical Source

- `briefs/`
- `content/briefs/`
- `content/trends/`
- `trends/`
- `weekly/`
- `ops-review/`
- `memory/`
- `content/YYYY-MM-DD/`

These contain useful history, but they should not be treated as the current operating source of truth without checking age and dependencies.

### Update Before Use

- `scripts/build-website.sh`
- `scripts/catchup.sh`
- `scripts/git-sync-daily.sh`
- `scripts/send_outreach.py`
- `scripts/partner_lifecycle.py`
- `scripts/parse_listing_answers.py`
- `scripts/hubspot_upload.py`
- `scripts/prospect_palm_beach.py`
- `scripts/upload_drafts_to_hubspot.py`
- `scripts/hubspot_task.py`
- `scripts/audit_deal_pipeline.py`
- `scripts/setup_deal_pipeline.py`
- `scripts/cleanup_deal_pipeline.py`
- `scripts/google_calendar_oauth.py`
- `scripts/google_sheets_oauth.py`

### Archive Or Quarantine Candidates

- old one-off email send scripts after confirming no recurring use.
- old social/Meta scripts until Meta credentials are intentionally connected.
- old docs that describe May launch assumptions no longer true.
- duplicate homepage file strategy once the live homepage is consolidated.
- generated logs if they are no longer operationally useful.

## Public Website Assessment

Strengths:

- Clear public-adjuster positioning.
- Strong trust assets: free review, guides, provider directory, articles.
- Daily brief archive is now more credible and easier to understand.
- July 1 package is timely and segmented correctly.
- Sitemap includes latest brief pages.

Weaknesses:

- Homepage is long and a little split between old claims-site structure and newer intelligence/referral strategy.
- `site/index.html` and `site/PA-WEBSITE.html` duplicate much of the same content.
- Publication is still lower on the current live homepage than it should be for audience-building.
- Some visual language feels older than the current strategic direction.

Recommended next public-site move:

- Use the saved facelift preview as the basis for a new homepage.
- Keep the current site live until the facelift is approved.
- When approved, replace both homepage copies or eliminate the duplicate route.

## Publication Assessment

Strengths:

- The segmented brief model is right.
- Homeowner, real estate, and service-provider angles map directly to referral channels.
- The July 1 issue is current, useful, and not overly salesy.
- The source trail approach in `publication/briefs/YYYY-MM-DD/` is the right pattern.

Weaknesses:

- Weekly trends are stale; latest public weekly trend is May 30.
- There is no clean "today's production checklist" script or SOP yet.
- Sending is partly manual because HubSpot is unavailable.

Recommended next publication move:

- Produce the next weekly trend issue.
- Create a repeatable daily brief SOP:
  1. research
  2. draft
  3. verify
  4. publish to `site/briefs`
  5. update archive/homepage/sitemap
  6. send test email
  7. send to segments once HubSpot is connected

## CRM And Referral Engine Assessment

Strengths:

- There is a large amount of CRM source data and prior outreach work.
- Provider directory concept fits the referral strategy.
- Gmail is connected and can send, receive, and stage drafts.

Weaknesses:

- HubSpot is the central missing integration.
- CRM files are numerous and not obviously current without a consolidation pass.
- Prior automation assumed daily cron reliability, which broke previously.
- Some metrics in older docs are no longer useful for a new/no-subscriber relaunch.

Recommended next CRM move:

- Reconnect HubSpot.
- Run a read-only HubSpot audit first.
- Reconcile local CRM files against HubSpot state.
- Restart outreach as a controlled manual-review queue, not full automation.

## Immediate Action Plan

### Today / Next Work Block

1. Keep live site stable.
2. Finish feedback edits to July 1 briefs if needed.
3. Reconnect HubSpot when password/access is restored.
4. Add `HUBSPOT_API_KEY` to local secrets through hidden prompt.
5. Run read-only HubSpot token test.

### This Week

1. Approve or revise homepage facelift.
2. Publish homepage facelift after approval.
3. Produce a fresh weekly trends issue.
4. Create a clean daily brief production SOP.
5. Modernize only the scripts required for:
   - brief publishing
   - Gmail send/drafts
   - HubSpot contact/list/task workflows
   - reply monitoring

### Next 30 Days

1. Build list growth around three audience tracks.
2. Send property intelligence consistently.
3. Use provider directory as relationship currency.
4. Track every real conversation, reply, review request, provider referral, and claim opportunity.
5. Move from "content exists" to "content creates conversations."

## Bottom Line

The project has the right strategic shape now: public adjuster credibility plus property intelligence plus referral partner infrastructure. The biggest risk is operational clutter from old automations and stale paths. The biggest opportunity is to make the live website and newsletter feel like one coherent machine: useful local intelligence first, free review when needed, trusted claim resource when the opportunity appears.
