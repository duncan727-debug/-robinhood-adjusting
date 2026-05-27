---
name: weekly-self-review
description: "Sunday evening audit of operations, metrics, skills, AI advances, and industry signals. Produces a delivery-ready improvement report for Duncan's Monday-morning sign-off."
user-invocable: true
---

# Weekly self-review

Fires Sunday ~18:00 EDT. Goal: catch drift, ship upgrades before Monday.

Mode is **propose-first** until Duncan flips to autonomous. Produce a single deliverable: `workspace/weekly-self-review/YYYY-WW.md` + a HubSpot task on Duncan ("Weekly review ready"). Do NOT edit skills, crons, or memory in this mode — only propose.

## Inputs to scan

Run all of these in parallel where possible.

### 1. Operations metrics (last 7 days)
- `scripts/health-check.log` — uptime %, failed checks, recovery time
- `scripts/catchup.log` — runs, missed jobs, errors
- `crm/api_usage.log` — HubSpot call volume / errors
- `crm/email_enrichment.log` — bounce %, enrichment success
- `scripts/outreach_send.log` + `crm/interactions.csv` — sent vs reply rate, by audience + by day
- `scripts/contact_form_queue.log` — fallback submit rate
- `scripts/imap_bridge.log` + `imap_bridge_alert.log` — 5-min push latency, alert noise
- `scripts/drip.log`, `prospect_palm_beach.log`, `networking_discovery.log`, `partner_lifecycle.log`, `newsletter-send.log`
- HubSpot task overflow: count of open tasks assigned to Duncan; flag if >15

### 2. Content quality (the most-likely-to-degrade surface)
- Every brief in `site/briefs/` from last 7 days: audiences present? acronyms present? routine weather snuck in? dedup gap (topic covered ≤4 days prior)?
- Trends in `trends/` — Saturday-only check, HTML mirror present?
- Newsletter sends — open rate, click rate (pull from HubSpot if accessible)

### 3. Cron health
- `cron status` + `cron runs <jobId>` for each enabled job. Failures, skips, timeout hits, runtime trend (slowing down?).
- Compare runtime vs `payload.timeoutSeconds` — flag jobs running >70% of budget.

### 4. Skill performance
- Which of the 5 (now: `daily-brief`, `ops-review`, `crm-outreach-draft`, `schedule-sync`, `weekly-self-review`) actually got invoked this week?
- Mid-flight corrections from Duncan logged in `crm/responses/` or memory `feedback_*` files written this week — each one is a candidate skill amendment.
- Dead skills (>14 days no invocation) — propose retire or fix.

### 5. Technical efficiency
- Token usage by day (from session transcripts or gateway logs if accessible — `/tmp/openclaw/openclaw-*.log`)
- Time-to-completion for each daily cron job — trend up = problem
- Cost: dollar estimate using Opus 4.7 rates × tokens
- Cache hit rate where measurable

### 6. Outside-the-box scans (this is where surprise compounds)
- **Industry**: Run web search for last-7-day news in PA / FL property insurance / FL OIR / hurricane forecast / Citizens depopulation. Surface anything Duncan should know before Monday. Sources: floir.com, AM Best, Insurance Journal, Tampa Bay Times insurance beat, NOAA.
- **Local market**: Wellington / Palm Beach County permits, storm-debris reports, HOA disputes — signal for outreach openings.
- **AI advances**: Search Anthropic, OpenAI, OSS LLM releases in last 7 days. New Claude models, new SDK features (prompt caching, batch, files API, citations), new agentic frameworks. For each: 1-line "could we use this?" verdict.
- **Tooling**: New OpenClaw releases, MCP servers, automation primitives. Check `~/.openclaw/update-check.json`.
- **Competitive**: Other PAs in PBC publishing newsletters? Doing video? Running ads? Public adjuster Facebook groups for chatter.

## Output template

Write to `workspace/weekly-self-review/2026-WXX.md`:

```markdown
# Weekly self-review — 2026-WXX (Sun YYYY-MM-DD)

## TL;DR
3 bullets max. What changed. What's broken. Top 1 upgrade to ship Monday.

## Pipeline metrics
[table: outreach sent / replies / reply % / by audience]
[table: bounces / contact-form-fallback / fallback submit %]
[HubSpot task queue depth, change from last week]

## Cron health
[table: job / runs / fails / avg runtime / % of timeout / verdict]

## Content quality flags
[bulleted issues found in briefs/trends]

## Skill performance
[for each skill: invocations, mid-flight corrections, status]

## Technical efficiency
[tokens by day, $ est, cache hit %, slowest tasks]

## Industry signals
[bullets — only what affects Duncan's week]

## AI / tooling advances
[bullets — only what we could actually adopt]

## Proposed upgrades (for Duncan sign-off Monday)
[numbered list — each item is a concrete diff to a skill, cron, script, or memory entry. Include estimated effort and risk.]

## Proposed new skills
[if any — name, description, why now]
```

## HubSpot task to create

After writing the file, run this exact command (substitute Wxx, N, and the file path):

```bash
python3 scripts/hubspot_task.py \
  --subject "Weekly review ready — Wxx — N upgrades pending" \
  --body "TL;DR: <one-line summary>\n\nReport: file:///Users/victoria/.openclaw/workspace/weekly-self-review/2026-Wxx.html\nMarkdown: workspace/weekly-self-review/2026-Wxx.md\n\nP0 items: <count>\nP1 items: <count>\nP2 items: <count>" \
  --due 2026-MM-DD \
  --priority HIGH \
  --type TODO
```

- Always priority HIGH (Monday-morning sign-off depends on this)
- Due date = next Monday's date
- HTML link is the primary deliverable per Duncan's "always HTML" rule

## Promotion to autonomous mode

Track in `workspace/weekly-self-review/_streak.json`:
- After Duncan signs off on 3 consecutive weekly reports with ≥80% of proposals accepted, automatically prompt him to flip to autonomous mode.

## Do not
- Edit skills, crons, memory, or workspace files this skill is reviewing. Propose only.
- Send the newsletter, run outreach, or push to git from this skill — out of scope.
- Skip the outside-the-box scans even if the operational metrics look clean. The biggest wins come from there.
- Use cheap models for the AI-advances synthesis. Opus 4.7 only (per Duncan's standing rule).

## See also
- `references/metrics-catalog.md` — exact paths + parse hints for every log file
- `references/ai-scan-sources.md` — current source list for AI/tooling advances
- `scripts/collect_metrics.py` — deterministic metric extraction (run first, then write the prose)
