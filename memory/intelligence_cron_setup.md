---
name: Prospect Intelligence Cron Job Setup
description: Automated daily prospect research pipeline; deep intel on followup-due orgs feeds morning outreach
type: project
---

## Setup Date
2026-04-24 (live as of 5:28 AM EDT)

## What It Does

Daily cron job fires at 5:28 AM EDT:
1. Reads CRM (organizations.csv, interactions.csv)
2. Identifies orgs with `next_followup_date <= today`
3. Does web research (WebSearch, company sites) on each
4. Generates intelligence files: `/crm/intelligence/YYYY-MM-DD/[org_id]-intel.md`
5. Creates summary for Duncan's 8am review

## Current Stats (First Run)

- **67 organizations** all due for followup on 2026-04-24
- **9 deep intel files** created (with decision makers, contact info, pain points, hooks)
- **58 flagged** for manual research (incomplete contact data)

## Intel File Format

Each file includes:
- Company overview (2-3 sentences)
- Key decision maker(s) + titles + phone/email
- Recent activity/news (6 months)
- Likely pain points (industry + company-specific)
- Personalization angle (1-2 sentence hook Duncan can use verbatim)

## Outreach Priority

1. **High-Contact:** 9 orgs with complete data → email/call immediately
2. **Strategic Partners:** Grant PM, Parker Adjusters, Reliant Adjusters (partnership model)
3. **Manual Research:** 58 orgs needing decision-maker lookup (batch by category)

## Ongoing Maintenance

- Update organizations.csv when new orgs added or contact info found
- Mark status = "contacted" or "next_followup_date" when interaction recorded
- Cron job will skip non-initial status orgs (prevents duplicate research)

## Why This Matters

**For Duncan:** Pre-researched targets = hyper-personalized outreach emails. Generic spray-and-pray fails; specific hooks (e.g., "noticed you're doing 700 projects/year" or "your family business is vulnerable to insurance delays") get responses.

**Frequency:** Daily at 5:28 AM (early enough for 8am review window; batches new prospects as they're added)
