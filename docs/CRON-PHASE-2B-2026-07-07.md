# Robinhood Cron Phase 2B

Date installed: 2026-07-07  
Scheduler: OpenClaw cron  
Timezone: America/New_York  
Mode: Review-first daily publishing prep

## Purpose

Phase 2B drafts the daily property intelligence package each morning, but keeps publishing manual. It should give Duncan a browser-friendly review page and clear questions before anything goes live.

## Live Job

| Time | Days | Job | ID | Delivery | Risk |
|---:|---|---|---|---|---|
| 4:15 AM | Mon-Sat | Robinhood Phase 2B - Daily Brief Draft Package | `efe45a19-aebd-48c4-9523-67f9f9aacdcb` | Announce | Local draft only |

## Required Output

For the current America/New_York date, the job should create:

- `publication/briefs/YYYY-MM-DD/README.md`
- `publication/briefs/YYYY-MM-DD/review.html`

The HTML review page matters because Duncan does not want Markdown opened for review.

## Editorial Rules

- Do not make "no major weather" the main story unless there is truly no better business signal.
- Use weather as loss-environment context.
- Prefer a strong market, policy, claims, transaction, regulatory, or service-provider lead.
- Cross-check claims and include source links.
- Include segment notes for homeowners, real estate professionals, and service providers.

## Guardrails

- Do not modify `site/`.
- Do not commit.
- Do not push.
- Do not deploy.
- Do not send emails.
- Do not post externally.
- Do not create, update, or delete HubSpot records.

Publishing remains a separate human-approved follow-up.
