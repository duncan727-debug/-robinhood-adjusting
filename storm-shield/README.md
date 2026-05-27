# Storm Shield

Pre-loss home documentation product line. Operates as an affiliate of Robinhood Adjusting.

## Tiers
- **Lite** — free PDF checklist
- **Guided** — $149/yr, homeowner-built file, AI gap check, cloud storage
- **Concierge** — $499/yr, on-site documentation visit by trained specialist

## Folder layout
- `marketing/` — landing pages, decks, social assets
- `prospects/` — HOA / property manager target lists for outreach
- `product/` — signup flow code, app prototypes (V2+)
- `legal/` — affiliate-disclosure drafts, FL Ch. 626.854 compliance review

## Deployed assets
- Live landing page: `/site/storm-shield.html` → robinhoodadjusting.com/storm-shield
- Site nav link added in `/site/index.html`
- IG content (May 22 launch): `/content/2026-05-22/social/ig-noaa-belownormal.{html,png}`

## Status (2026-05-22)
- ✅ Marketing page live
- ✅ PBC PM prospect list — 24 firms in `prospects/palm-beach-pm-firms.csv`
- ✅ Deal segmentation — `deal_line` property on deals; existing deals backfilled as `public_adjusting`
- ⏸ Signup flow — not built (no Stripe, no app)
- ⏸ Fulfillment — Concierge specialist not yet trained (Duncan to train a GC at small scale)
- ⏸ Legal review — affiliate-disclosure paragraph needs FL insurance-regulatory attorney sign-off
- ⏸ Soft-pilot pitch script — not drafted yet
- ⏸ Storm Shield prospect import to HubSpot — pending Duncan's CSV review

## HubSpot — Storm Shield deal segmentation
HubSpot account is capped at 1 pipeline (plan limit). We segment with a custom
deal property instead:

- Property: `deal_line` on Deal object
- Values: `public_adjusting` (default for existing deals) | `storm_shield`
- All existing deals (235) backfilled as `public_adjusting` on 2026-05-22
- `enrich_before_upload.py` now stamps new PA deals with `deal_line=public_adjusting`
- Storm Shield deals must be created with `deal_line=storm_shield`
- Storm Shield deals must use **`scripts/create_storm_shield_deal.py`** which
  enforces the visual convention: **dealname prefixed with 🛡** (shield glyph).
  This makes SS cards visually pop on the board even before the saved-view
  filter is applied. Example: `🛡 Storm Shield — Castle Group`

### Saved views to create in HubSpot UI (one-time)
In Deals → Views → Create view:
1. **"PA — Active Pipeline"** — filter `deal_line=public_adjusting` AND stage ≠ closed
2. **"Storm Shield — Active Pipeline"** — filter `deal_line=storm_shield` AND stage ≠ closed

The deal stages themselves are shared between business lines. Map them mentally:

| Stage (shared)              | PA meaning            | Storm Shield meaning           |
|-----------------------------|-----------------------|--------------------------------|
| appointmentscheduled        | New Prospect          | New PM Lead                    |
| qualifiedtobuy              | Outreach Sent         | Intro Sent                     |
| presentationscheduled       | Responded             | Pilot Call Booked              |
| decisionmakerboughtin       | Listed in Directory   | Pilot Call Held                |
| contractsent                | Proposal Sent         | Community Pricing Sent         |
| closedwon                   | Active Partner        | Active Community Partner       |
| closedlost                  | Declined              | Declined / Not a Fit           |
