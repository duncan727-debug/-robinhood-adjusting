---
name: daily-brief
description: "Produce Duncan's 3-audience South Florida daily brief: research once, write three audience-distinct briefs (homeowner / service-provider / real-estate), mirror to HTML, queue newsletter send."
user-invocable: true
---

# Daily brief

Fires 04:00 EDT Mon–Sat. Saturday brief is site-only (no email). Sunday = weekly trends, not this skill.

## Goal

When a homeowner, a trade professional, and a real-estate agent open their respective newsletters, they should each think: *"this was written for me."* Same underlying research, three distinct briefs in three voices. Shallow callouts at the end of a shared body are not enough — the prose, the lead story, the framing, and the practical actions must differ per audience.

## Audiences (always 3, always in this order)

1. **Homeowner** — Wellington / Boca / Coral Springs / Pinecrest etc. SFH or condo owner, $400-900K range, cares about premiums, hurricane prep, contractor scams, renewal letters.
2. **Service provider** — owner-operator roofer / plumber / HVAC / restoration / GC. Reads it on a phone between jobs. Cares about pipeline, jobs, credentials, cross-sell.
3. **Real-estate professional** — licensed agent or broker managing 8-20 active listings. Cares about: closing the deal, disclosures, contract contingencies, buyer questions.

## Workflow

1. **Dedupe first.** Read briefs from past 4 days (`site/briefs/`). Build a topic-set. Any new finding overlapping a recent topic >60% gets dropped or re-angled.
2. **Research scope.** PBC, Martin, Miami-Dade, St. Lucie, Broward. Topics: PA news, FL insurance regs, carrier moves, named-storm + flood + weather events with property impact, real estate trends, residential service industries, regulatory changes, industry events. Local newspapers + TV + county announcements are mandatory sources.
3. **Skip routine weather.** Only weather events with material property impact.
4. **Build the shared research note** (`briefs/YYYY-MM-DD.md`). This is the master — every fact, every source, all audience-tagged callouts. Used for the site display and as fallback for any segment that fails to render.
5. **Write 3 distinct briefs.** From the shared research, produce three independently-readable briefs in three voices (see Voice profiles below). Each picks its own lead story, its own emphasis, its own ordering, its own actions. ~700-1000 words each.
6. **Mirror to HTML.** Each markdown gets rendered to inline-styled HTML via the existing `md_to_html_body` path in `scripts/send-daily-brief.py`. Outputs at `content/briefs/YYYY-MM-DD[-{segment}].html`.
7. **Update PA-WEBSITE.html** — latest 3 master briefs surface on the site (segments are email-only).
8. **Queue newsletter** — Mon-Fri only. Sat is site-only. HubSpot send + BCC `246055074@bcc.hubspot.com`. Footer FB+IG links.

## Voice profiles

### Homeowner
- Reader: smart non-specialist. Knows what a deductible is, doesn't know what HVHZ means without a quick gloss.
- Tone: plainspoken, decisive, slightly protective — like a smart friend in the industry. Not sales-y, not jargon-heavy.
- Lead with the dollar/decision impact. Then the why. Then 1-3 concrete actions a homeowner can take this week.
- Headlines are action-oriented: "Your roof age just stopped being a renewal-killer" beats "HB 815 takes effect July 1."
- Length: 700-900 words. Reads in 4 min.

### Service provider
- Reader: owner-operator, wears 5 hats, reads on phone between jobs.
- Tone: peer-to-peer, pragmatic, trade-press cadence. Numbers and timelines matter.
- Frame as pipeline impact: "this changes which leads you chase," "this credential is now worth more," "this work category just opened up."
- Be explicit about cross-sell + credential angles. Name the specific approval, license, or training where relevant.
- Length: 800-1000 words. Reads in 5 min.

### Real-estate professional
- Reader: licensed agent or broker, comfortable with insurance vocabulary if a term is defined once.
- Tone: professional, transaction-focused, slightly more polished prose.
- Frame stories as "what this changes at the closing table," "what buyers will ask you this week," "what to put in the disclosure conversation."
- Practical hooks: showings, disclosures, contract contingencies, financing conditions.
- Length: 750-900 words. Reads in 4-5 min.

## General voice rules (all 3 briefs)
- Plain English. Zero acronyms unless on allowlist (HOA, FL, OIR, NOAA, NWS, PA, HVAC, A/C, FEMA) — and even those should be expanded on first use per brief.
- Every claim is concrete: dollar figures, percentages, named carriers, dated deadlines.
- No "stay tuned" / "watch this space" filler.
- No Duncan-in-first-person unless quoting him.
- No mention of Duncan, the CRM, outreach, or content-marketing plans. Reader-facing only.
- No watchlist items or internal operational notes in any reader-facing brief, site page, newsletter, or send package. Keep watchlists in private planning files only.

## Fact-checking (mandatory before publish)
Every factual claim must be verified against a primary or major-publisher source before it appears in the brief. No plausible-sounding fakes. No estimates rendered as facts. If a number can't be verified, either omit it or label it explicitly (e.g., "industry-estimated", "as reported by [source]"). When citing legislation, link the bill page (flsenate.gov / flhouse.gov). When citing carrier filings, link FLOIR or the carrier's release. When citing weather, link NOAA / NWS / NHC. Per `feedback_no_fabrication` — verified or labeled estimate, nothing in between.

### Independent verifier pass (mandatory before send)
After all 4 brief files are written and BEFORE the send/publish step:
1. Run `python3 scripts/extract_brief_claims.py briefs/YYYY-MM-DD*.md` — produces `*-verify.md` checklists.
2. For each claim, run an independent web search and judge: `[x]` verified, `[!]` contradicted, `[?]` unfindable. Record the source URL inline.
3. If ANY `[!]` flag fires, halt publish, fix the brief, and re-run the extractor + verifier loop.
4. Watch for **claim-conflation** specifically: numbers attributed to the wrong entity (e.g., a Governor's-office aggregate ascribed to a single carrier). When two facts share a paragraph, verify each independently. **Reference incident (2026-06-01):** the 26,000 PBC homes / 11.9% figure was bound to Heritage; it actually belongs to a broader DeSantis market-relief aggregate spanning multiple carriers.

## Naming rules in real-estate stories
- **Firms / brokerages OK.** When referencing a recent sale or transaction, the listing firm or brokerage name can appear (e.g., "listed by Compass," "Sotheby's International Realty closed…").
- **Family / last names NOT OK.** Do not include the buyer or seller's surname, even if it is in the public record. First names alone are also not allowed unless the person is a public figure quoted on the record. The real-estate brief is for the professional reader, not a society page.
- This applies to private-party transactions only. Public-figure / corporate seller-buyer transactions (a publicly-traded REIT, a municipal entity, a named development company) are fine to name in full.

## Do not
- Ship a homeowner brief that opens with the same lead as the service-provider brief.
- Skip the dedup step. Repeated topics within 4 days = unsubscribe risk.
- Send Saturday brief by email.
- Use personal email `duncanlittlejohnjr@gmail.com` anywhere — always `duncanlittlejohn727@gmail.com`.

## Outputs
- `briefs/YYYY-MM-DD.md` — master research note (site)
- `briefs/YYYY-MM-DD-homeowner.md`
- `briefs/YYYY-MM-DD-service-provider.md`
- `briefs/YYYY-MM-DD-real-estate.md`
- `content/briefs/YYYY-MM-DD.html` + 3 segment HTMLs (rendered by `ensure_html_brief`)
- Updated `PA-WEBSITE.html` index (master only)
- `crm/.daily-brief-sent-YYYY-MM-DD` flag
- HubSpot send queued (M-F only)

## Fallbacks
- If a segment .md is missing at send time, `scripts/build_segmented_briefs.py` does a structural split of the master HTML (strips other-audience callouts). This is the *light* fallback — quality drops, but no audience gets a blank send. Loud-fail alert logs which segments fell back.
