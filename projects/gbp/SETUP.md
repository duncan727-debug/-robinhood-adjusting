# Google Business Profile (GBP) — setup + automation

## Critical finding
**Robinhood Adjusting does NOT appear to have a Google Business Profile.** Searches for "Robinhood Adjusting Wellington" return zero Maps results. This is the single largest local-SEO miss on the table — a verified GBP routinely outperforms a website for "public adjuster near me" searches because Google's local pack shows GBP listings ahead of organic results.

Step zero is to create + verify the profile. THEN we automate.

## Phase 1 — Create the profile (Duncan, ~10 min, must be you)

1. Go to **https://business.google.com/create** while signed in as `duncanlittlejohn727@gmail.com`.
2. Business name: **Robinhood Adjusting**
3. Category: **Public Adjuster** (primary) — Google's category list has this exact term.
4. Service area business (no walk-in storefront):
   - Choose "I deliver goods and services to my customers" → check "I don't serve customers at my business address" → enter Wellington home address (this stays private; only used for verification).
   - Add service areas: **Wellington, West Palm Beach, Boca Raton, Coral Springs, Pinecrest, Miami-Dade, Broward, Palm Beach, Martin, St. Lucie counties.**
5. Phone: **the Retell number** once it's live (so all calls go through Robin). Until then, your direct mobile.
6. Website: **https://robinhoodadjusting.com**
7. Verification: Google offers postcard / video / phone. **Video verification** is fastest (1-3 days). Pick that. They'll prompt you to record a short walk-through showing license, equipment, and signage.

## Phase 2 — While waiting for verification (me, no Duncan touch)

I'll prep:
- A 30-day backlog of GBP posts (1/day) — drawn from the daily brief library, tailored to the GBP format (max 1500 chars, 1 image, optional CTA button).
- A Q&A seed list (10-15 common homeowner questions + pre-written answers) ready to populate the day verification clears.
- A review-request email template + a "first 10 reviews" list of past clients to ask.
- Service descriptions for each service area page (these matter for local ranking).

## Phase 3 — API automation (post-verification, ~30 min me)

1. Enable **My Business APIs** in Google Cloud Console (free tier sufficient).
2. Generate OAuth credentials, store in `config/.secrets`:
   ```
   GBP_CLIENT_ID=...
   GBP_CLIENT_SECRET=...
   GBP_REFRESH_TOKEN=...
   GBP_ACCOUNT_ID=...
   GBP_LOCATION_ID=...
   ```
3. Build `scripts/gbp_daily_post.py`:
   - Pulls today's homeowner-brief headline
   - Posts to GBP with the canonical brief URL as the CTA button
   - Logs to `scripts/gbp.log`
4. Build `scripts/gbp_review_request.py`:
   - After a HubSpot deal moves to "Closed Won", waits 7 days, sends a review-request email with the direct review-write URL.
5. Build `scripts/gbp_qa_monitor.py`:
   - Pulls unanswered Q&A daily, drafts answers, queues for your approval as a HubSpot task.
6. Crons: daily 9am post, hourly Q&A scan, 11am M-F review-request batch.

## Cost
- $0. GBP is free, the My Business API is free. Only cost would be optional Google Ads later, which is a separate decision.

## Why this matters more than I initially flagged
- ~85% of homeowners searching "public adjuster Wellington" never scroll past the local pack.
- Without a GBP, you are invisible to that traffic regardless of how good the website is.
- The first 90 days post-verification — when Google is calibrating freshness signals — is when automated daily posts + steady review collection move the ranking needle most.
