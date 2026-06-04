# Prospect Intelligence — 2026-06-01

**Run:** prospect-deep-intelligence cron, 05:00 EDT
**Files written:** 36 org intel briefs in this folder.

## Headline for the 5am outreach run

### ⛔ Escalation tier (10 orgs) — DO NOT auto-send today
All 10 escalation-stage orgs already received the "Last note from me" close-out email on **2026-05-25**. They have 7+ prior touches and zero confirmed replies. Today's `next_followup_date = 2026-06-01` should resolve to one of:
- **Close out in CRM** (recommended default — mark `status = closed-no-response`)
- **Duncan-only personal phone call** if any are strategically worth one final human touch
- **Wait for inbound** (passive — leave open another week)

Sending another templated email here would breach the cold-outreach voice rule and look spammy.

**Sub-flag:** 5 of the 10 escalation websites **did not resolve** on today's probe — strong signal these were seed/test data, not real prospects:
- `stormshieldfl.com` (Storm Shield Roofing)
- `coastalproperty.com` (Coastal Property Management Group)
- `atlanticwaterfl.com` (Atlantic Water & Mold Solutions)
- `safehavenprop.com` (SafeHaven Property Consulting)
- `hoaadvocatesfl.com` (HOA Advocates Management)

Recommend Duncan reviews these for full removal from the active pipeline.

The other 5 escalation sites **do resolve** (allphaseusa.com, quantumroofing.com, prestigerealty.com, elitecontractorsfl.com, floridainsurancepartners.com) but the on-file contact names look templated — no decision-maker has been independently verified. Treat with caution.

### ✅ Initial tier (26 orgs) — fresh cold touches
All 26 are PBC small-business directory listings with generic `info@` mailboxes and **no named decision-maker**. These are legit first-touch targets but the personalization ceiling is low until Duncan (or a manual pass) attaches a real name/title.

**Recommended approach for today's 5am batch:**
- Send the compare-notes cold-touch template (per `feedback_cold_outreach_voice`)
- Lead with vertical-specific PBC market angle (heat-dome HVAC, NOAA outlook for roofers, Citizens depopulation for PMs/RE, HB 837 for restoration)
- Do **not** invent specific projects, news, or owner names — none are independently verified

## Per-vertical breakdown (initial tier)

| Vertical | Count | Hook to lead with |
|---|---|---|
| Roofing | 4 | NOAA 2026 season outlook + FBC 7th edition scope |
| Restoration / water / mold | 3 | HB 837 / § 627.7152 mit-only squeeze |
| Plumbing | 4 | Cast-iron sudden-discharge denial patterns |
| HVAC / A/C | 4 | Lightning/surge condenser underpayment trend |
| General contractor / construction | 5 | Supplements + Ord-&-Law under-claim |
| Real estate / realty | 3 | OIR-21 + binder-stage non-renewal stalls |
| Roof repairs (sub-roofer) | 3 | Repair-vs-replace push at end of life |

## Research gaps Duncan owns

Across all 36 files, these did NOT auto-pull (no fabrication, so flagged for manual):
- BBB / FL OIR complaint histories
- Recent permit activity (PBC ePZB / Broward eTRAKiT)
- Decision-maker names for all 26 initial-tier orgs
- Working URLs for the 5 unresolved escalation sites

## Cross-references

- Outreach voice: `feedback_cold_outreach_voice` (compare-notes, no pitch, asks on touch 2)
- Cold tier seed data warning: applies to escalation tier here
- Truth-source rule: this intel is CSV + interaction-history + category-based inference only — verify before citing specifics
