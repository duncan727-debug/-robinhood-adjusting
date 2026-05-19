# Template: Listing-reply qualifying questions

**Use when:** a contractor replies YES to our listing-outreach email. We've added them to the directory; this email collects the data we need to route referrals correctly.

**Format rule:** Low-friction multi-choice. Reply-by-letter so they can answer in 60 seconds on phone. Never use forms or open-ended questions unless absolutely necessary.

**Parameters to fill in:**
- `{COMPANY}` — business name
- `{CATEGORY_FILED_UNDER}` — directory category (e.g. "General Contractors", "Roofing")
- `{TRADE_OPTIONS}` — list of trades to choose from (defaults below if multi-licensed; single if single-trade)
- `{COUNTIES_OFFERED}` — counties to offer (default all 5: Palm Beach, Martin, St. Lucie, Broward, Miami-Dade)

---

**Subject:** You're live on the directory — quick details so I send you the right referrals

Hi,

Just made it official — {COMPANY} is now live on the Robinhood Adjusting provider directory:

https://robinhoodadjusting.com/providers (filed under {CATEGORY_FILED_UNDER} with a ✓ Verified badge)

I want to make sure we route you the right kind of referrals. Just reply with the letter/number for each — should take about 60 seconds:

**1) Best name + cell for hot referrals**
   → Reply with name + phone

**2) Counties you'll actively take jobs in** (check all that apply)
   a. Palm Beach
   b. Martin
   c. St. Lucie
   d. Broward
   e. Miami-Dade

**3) Primary trade you'd like featured under** (pick one — we'll cross-list you in the others)
   {TRADE_OPTIONS}
   (default options for multi-trade: a. General Contractor · b. Roofing · c. HVAC · d. Plumbing · e. Restoration)

**4) Job-size sweet spot** (pick one)
   a. Residential only
   b. Commercial only
   c. Both — happy with either
   d. Insurance-claim repairs specifically

**5) Emergency / 24-7 calls?**
   a. Yes — call anytime
   b. Business hours only

**6) Best way to send you a hot lead** (pick one)
   a. Text
   b. Phone call
   c. Email
   d. Anything works

That's it. Once you reply, I'll update your listing so the right homeowners find you.

Thanks for being part of the network — hurricane season starts June 1.

Best,
Duncan Littlejohn
Licensed Public Adjuster · Robinhood Adjusting · Wellington, FL
561-772-7528 · robinhoodadjusting.com

---

## Where the answers land in HubSpot

| Question | HubSpot contact property |
|---|---|
| 1. Name + cell | `firstname` / `lastname` / `phone` |
| 2. Counties | `service_counties` (multi-checkbox) |
| 3. Primary trade | `primary_trade` (dropdown) |
| 3. Cross-list trades | `secondary_trades` (multi-checkbox) |
| 4. Job size | `job_size_focus` (dropdown) |
| 5. Emergency | `emergency_availability` (single checkbox Yes/No) |
| 6. Referral channel | `referral_channel_pref` (dropdown) |

Properties are created idempotently by `scripts/hubspot_setup_listing_properties.py`.
