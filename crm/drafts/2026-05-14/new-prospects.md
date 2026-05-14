# New Prospects — May 14, 2026

**Status:** No new prospects identified today.

**Reason:** Today's trends file (2026-05-14.md) has not been generated yet. Trends are typically published at 4am EDT on weekdays, and this outreach run executed at 1:31 PM EDT.

**Next action:** Once 2026-05-14 trends are published (or manually reviewed by Duncan), any new organization recommendations will be listed here for manual review and addition to organizations.csv.

---

## What to Look For

When reviewing new prospects, prioritize:
- **Service providers in target counties:** Palm Beach, Martin, Miami-Dade, St. Lucie, Broward
- **Categories:** Roofers, plumbers, A/C, water mitigation, mold remediation, general contractors, P&C attorneys, HOA/condo managers, property managers
- **High-capacity operators:** Look for expansion signals, seasonal hiring, new certifications, or market positioning changes
- **Early-mover advantage:** Orgs not yet receiving heavy PA outreach in the market

---

## How to Add New Prospects

1. Add row to `organizations.csv` with:
   - org_id (format: `{county}-{company-slug}`)
   - Basic org info (name, category, county, website if available)
   - Contact info (name, title, email/phone if available)
   - status: `initial`
   - created_date: today's date (2026-05-14)
   - last_touch_date: empty initially
   - next_followup_date: 2026-05-14 or 2026-05-15 (to trigger first touch on next run)
   - notes: brief context about why this org is being added

2. Don't add to interactions.csv yet — let the cron job create the interaction record when the first draft is prepared.
