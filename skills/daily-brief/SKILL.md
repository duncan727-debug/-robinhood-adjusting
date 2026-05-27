---
name: daily-brief
description: "Produce Duncan's 3-audience South Florida daily brief: research, dedupe against last 4 days, write audience-segmented commentary, mirror to HTML, queue newsletter send."
user-invocable: true
---

# Daily brief

Fires 04:00 EDT Mon–Sat. Saturday brief is site-only (no email). Sunday = weekly trends, not this skill.

## Audiences (always 3, always in this order)

1. **Homeowner** — "what it means for your house, your insurance, your money"
2. **Provider** — roofers / plumbers / HVAC / restoration: "what it means for your jobs, your risk, your demand"
3. **Real estate pro** — agents/brokers: "what it means for inventory, deals, disclosures"

Omit an audience section only if there is genuinely nothing relevant. Empty sections are worse than absent ones.

## Workflow

1. **Dedupe first**. Read briefs from past 4 days (`site/briefs/`). Build a topic-set. Any new finding that overlaps a recent topic by >60% is dropped or angled differently (new data, new audience cut).
2. **Research scope**: PBC, Martin, Miami-Dade, St. Lucie, Broward. Topics: PA news, FL insurance regs, carrier moves, named-storm + flood + weather events with property impact, real estate trends, residential service industries, regulatory changes, industry events. Local newspapers + TV + county announcements are mandatory sources.
3. **Skip routine weather**. Only weather events with material property impact (named storm, hail, flooding above advisory). Daily "70-80°F sunny" goes nowhere.
4. **Write the brief**. Markdown source at `content/YYYY-MM-DD/blog.md`, audience-segmented HTML at `site/briefs/YYYY-MM-DD.html`. Storm countdown banner if hurricane season active.
5. **Mirror HTML** — every brief gets an HTML version. No exceptions.
6. **Update PA-WEBSITE.html** — latest 3 briefs surface on the site.
7. **Queue newsletter** — Mon–Fri only. Sat is site-only. Add HubSpot send + BCC dropbox `246055074@bcc.hubspot.com`. Footer must include FB+IG links.

## Voice
- Plain English. Zero acronyms unless on allowlist (HOA, FL, OIR, NOAA, NWS, PA, HVAC, A/C, FEMA).
- "What it means" sections are concrete: dollar figures, percentages, named carriers, dated deadlines.
- No "stay tuned" / "watch this space" filler.
- No Duncan-in-first-person unless quoting him.

## Do not
- Mention Duncan, CRM targets, outreach hooks, or content-marketing plans in the published brief. The brief is reader-facing only.
- Send Saturday brief by email (site-only per Duncan's standing rule).
- Use personal email `duncanlittlejohnjr@gmail.com` anywhere — always `duncanlittlejohn727@gmail.com`.
- Skip the dedup step. Repeated topics within 4 days = unsubscribe risk.

## Outputs
- `content/YYYY-MM-DD/blog.md`
- `site/briefs/YYYY-MM-DD.html`
- Updated `PA-WEBSITE.html` index
- `crm/.daily-brief-sent-YYYY-MM-DD` flag (so catchup doesn't re-fire)
- HubSpot send queued (M–F only)
