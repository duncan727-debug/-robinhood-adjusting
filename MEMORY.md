# Long-Term Memory


## Promoted From Short-Term Memory (2026-06-05)

<!-- openclaw-memory-promotion:memory:memory/2026-05-20-0818.md:20:20 -->
- Key actionable findings: **6 named decision-makers identified:** Richard H. Anderson Jr. (Anderson Construction), David Benchetrit (Davies/DES Plumbing), Robert Ayrsman (Florida Coastal Premier Realty), Mainor Cuadra (Nena's), Lisa Kleinfeld (DRYmedic NPB), Jorge Leal Varela (Kelvin Comfort AC). [score=0.898 recalls=0 avg=0.620 source=memory/2026-05-20-0818.md:20-20]
<!-- openclaw-memory-promotion:memory:memory/2026-05-20-0818.md:22:22 -->
- Key actionable findings: **3 still anonymous:** EES Restoration, Healthy Builds Restoration, PETRA A/C — info@ first-touch, Sunbiz lookups recommended before second-touch. [score=0.898 recalls=0 avg=0.620 source=memory/2026-05-20-0818.md:22-22]
<!-- openclaw-memory-promotion:memory:memory/2026-05-20-0818.md:26:28 -->
- Files: `crm/intelligence/2026-05-20/SUMMARY.md` — scorecard + action items; `crm/intelligence/2026-05-20/NOTHING-DUE-TODAY.md` — explains the pivot; `crm/intelligence/2026-05-20/*-intel.md` — 10 individual intel files [score=0.898 recalls=0 avg=0.620 source=memory/2026-05-20-0818.md:26-28]
<!-- openclaw-memory-promotion:memory:memory/2026-05-20-0818.md:8:8 -->
- What happened: Cron fired with literal scope of 0 orgs (no `next_followup_date <= 2026-05-20` in organizations.csv). Earliest is Wave-1 at 5/21. Rather than no-op, pre-built deep intel on all 10 Wave-1 PBC orgs so it's ready whether Duncan approves the pre-NOAA pull-forward (per 5/20 outreach SUMMARY recommendation) or Wave-1 fires on schedule tomorrow. [score=0.816 recalls=0 avg=0.620 source=memory/2026-05-20-0818.md:8-8]
<!-- openclaw-memory-promotion:memory:memory/2026-05-20-0818.md:14:14 -->
- Key actionable findings: **Nena's Roofing — CRM fix needed.** Phone is `(561) 670-4919` (currently blank) and email should be `nenasroofing@hotmail.com` (their own published address), not guessed `info@`. Site LIVE, A-rated BBB, license valid through 8/2026. Stale-source "Nana's lesson" risk is killed — keep in Wave-1. [score=0.816 recalls=0 avg=0.620 source=memory/2026-05-20-0818.md:14-14]
<!-- openclaw-memory-promotion:memory:memory/2026-05-20-0818.md:16:16 -->
- Key actionable findings: **Palm Beach HVAC Repair Co. — recommend SKIP.** Lead-gen funnel: multi-brand domain with out-of-state phone numbers per city, no DBPR license, no Sunbiz. Should be swapped for a verified CAC-licensed PBC operator from the candidate pool. [score=0.816 recalls=0 avg=0.620 source=memory/2026-05-20-0818.md:16-16]
<!-- openclaw-memory-promotion:memory:memory/2026-05-20-0818.md:18:18 -->
- Key actionable findings: **DRYmedic NPB — channel swap.** `info@drymedic.com` routes to Authority Brands corporate, not local franchisee. Lisa Kleinfeld (President, named via BBB) needs phone or LinkedIn, not email. [score=0.816 recalls=0 avg=0.620 source=memory/2026-05-20-0818.md:18-18]

## Promoted From Short-Term Memory (2026-06-15)

<!-- openclaw-memory-promotion:memory:memory/2026-06-12.md:3:6 -->
- Daily brief run (10:08 AM, late cron): Produced + sent 2026-06-12 brief (master + 3 segments). Verify pass: 0 contradictions. Site rebuilt + pushed (commit 50db183).; **MAJOR CORRECTION:** SB 266 (PA contracts) AND HB 815 (roof-age reform) both DIED in committee 3/13/2026 per flsenate.gov. The July 1 effective dates carried in June 1–4 briefs are dead. Today's brief leads with the correction; calendar struck through. Any planning premised on July-1 PA contract changes (18-pt font, vulnerable-adult rescission) is moot until 2027 session.; **GAP FLAG:** No briefs were produced June 5–11 (last was 2026-06-04).... [score=0.857 recalls=0 avg=0.620 source=memory/2026-06-12.md:3-6]
<!-- openclaw-memory-promotion:memory:memory/2026-06-12.md:16:19 -->
- CRM outreach run (10:20am cron, first since outage restore): Found 28 overdue orgs; cross-check showed the 24 followup-1 drafts from 6/01 were NEVER sent (no send-log trace, 0 replies in IMAP bridge) — refreshed them at same stage instead of escalating; New hooks from today's brief: PB Gardens $90K bond-fraud arrest (verification checklist) + first NHC disturbance; realty orgs got vendor-vetting variant; Staged all 24 in Gmail Drafts via IMAP (stage_gmail_drafts.py skipped them — generic info@ addresses have no HubSpot contacts; likely why 6/01 batch stranded too); HubSpot tasks: 1 batch EMAIL pointer + 4 CALL tasks (iTHINK HOT —... [score=0.857 recalls=0 avg=0.620 source=memory/2026-06-12.md:16-19]
<!-- openclaw-memory-promotion:memory:memory/2026-06-12.md:20:21 -->
- CRM outreach run (10:20am cron, first since outage restore): State: +28 interactions.csv rows; organizations.csv dates advanced (backup .bak.2026-06-12-1025); Gap identified: drafts marked draft-pending-review have no stale-draft tripwire — recommend adding >3-day pending check to ops-review [score=0.857 recalls=0 avg=0.620 source=memory/2026-06-12.md:20-21]

## Promoted From Short-Term Memory (2026-06-16)

<!-- openclaw-memory-promotion:memory:memory/2026-06-12.md:7:7 -->
- Daily brief run (10:08 AM, late cron): Subscriber counts at send: homeowner 1, service-provider 1, real-estate 0. [score=0.861 recalls=0 avg=0.620 source=memory/2026-06-12.md:7-7]
<!-- openclaw-memory-promotion:memory:memory/2026-06-12.md:10:13 -->
- daily-trends catch-up fire (10:17 AM) — intentionally skipped: The weekly trends cron (Saturday 9am ET) fired today (Friday) as a catch-up replay after the 6/12 cron restoration — it was making up the missed 6/06 run.; Skipped generation: schedule is correctly Saturday-only; tomorrow 6/13 9am run covers the same data (briefs were down 6/05–6/11, so only 6/12 briefs exist in the window either way).; No trends file exists for 6/06 — that week's report is permanently missing due to the outage; Sunday 6/07 trends email did not send.; Tomorrow's run should note the limited brief window (outage gap) in the report. [score=0.861 recalls=0 avg=0.620 source=memory/2026-06-12.md:10-13]
<!-- openclaw-memory-promotion:memory:memory/2026-06-12.md:24:26 -->
- Ops review (11:35 AM, end-of-day cron fired late-morning post-restore): Wrote ops-review/2026-06-12.md — recovery-day verdict (🟡): outage triage clean, but iTHINK now 11 days stale, 6/01 batch root cause = stage_gmail_drafts.py silently skips generic info@ orgs; Top asks for Duncan: call Ileana TODAY; decide send-now vs Monday for the 24 refreshed drafts (Friday 3pm window); batch 3 phone fallbacks next week; Improvement proposed: output-existence canary in catchup.sh (watch outputs, not job counts) + stale-draft >3d tripwire in ops-review [score=0.861 recalls=0 avg=0.620 source=memory/2026-06-12.md:24-26]

## Promoted From Short-Term Memory (2026-06-17)

<!-- openclaw-memory-promotion:memory:memory/2026-06-13.md:5:5 -->
- 08:07 EDT — dashboard cron fired, health=0%: First morning after the 6/04–6/12 cron migration outage was restored. Dashboard reports 0% with most morning jobs flagged "Not found": [score=0.844 recalls=0 avg=0.620 source=memory/2026-06-13.md:5-5]
<!-- openclaw-memory-promotion:memory:memory/2026-06-13.md:6:9 -->
- 08:07 EDT — dashboard cron fired, health=0%: daily-research-brief (5am): cron fired ~2h ago, status=error → no briefs/2026-06-13*.md; daily-content (5:30am): still actively `running` at 8:07am — long-running; prospect-deep-intelligence (5am): error → no prospect data; response-handler (7am): error [score=0.844 recalls=0 avg=0.620 source=memory/2026-06-13.md:6-9]
<!-- openclaw-memory-promotion:memory:memory/2026-06-13.md:20:20 -->
- 08:07 EDT — dashboard cron fired, health=0%: Letting the 10:30am `daily-health-check` cron triage with the playbook; if it can't recover, it'll surface to Duncan. [score=0.844 recalls=0 avg=0.620 source=memory/2026-06-13.md:20-20]

## Promoted From Short-Term Memory (2026-06-18)

<!-- openclaw-memory-promotion:memory:memory/2026-06-13.md:16:16 -->
- 08:07 EDT — dashboard cron fired, health=0%: Pattern resembles 2026-05-23 + 2026-05-30 Saturday widespread cron misses but with a twist — the cron *fires*, the agent errors out before writing files. Could be model overload (Fable 5 free-window pressure per memory note) or first-day-after-restoration plumbing. [score=0.893 recalls=0 avg=0.620 source=memory/2026-06-13.md:16-16]
<!-- openclaw-memory-promotion:memory:memory/2026-06-13.md:18:18 -->
- 08:07 EDT — dashboard cron fired, health=0%: Saturday brief is site-only per Duncan's rules (no newsletter send), so subscriber impact = zero. [score=0.893 recalls=0 avg=0.620 source=memory/2026-06-13.md:18-18]
<!-- openclaw-memory-promotion:memory:memory/2026-06-13.md:22:22 -->
- 08:07 EDT — dashboard cron fired, health=0%: No user message — this was the 8:05am dashboard cron firing. Staying quiet on channel. [score=0.893 recalls=0 avg=0.620 source=memory/2026-06-13.md:22-22]
<!-- openclaw-memory-promotion:memory:memory/2026-06-13.md:10:13 -->
- 08:07 EDT — dashboard cron fired, health=0%: weekday-crm-outreach (6am, last fire 7:52am): error → no crm/drafts/2026-06-13/; weekday-ops-review (8am): currently `running` at 8:07am; daily-trends (9am Sat): not yet due — will fire 9:00am; daily-hubspot-consolidation: scheduled 8:30am [score=0.861 recalls=0 avg=0.620 source=memory/2026-06-13.md:10-13]
<!-- openclaw-memory-promotion:memory:memory/2026-06-13.md:14:14 -->
- 08:07 EDT — dashboard cron fired, health=0%: update-dashboard (this job): ran fine [score=0.861 recalls=0 avg=0.620 source=memory/2026-06-13.md:14-14]
