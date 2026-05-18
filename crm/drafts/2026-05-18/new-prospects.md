# New Prospect Candidates — 2026-05-18

**Source:** Real estate deal activity + market structure shifts from week of May 11–15
**Action required:** Duncan reviews; if approved, add to `crm/organizations.csv` manually (or queue for next prospecting cron run)
**Do NOT auto-add** — these need a Duncan-eye check before entering active outreach

---

## 1. Native Realty (Broward — commercial / multi-family portfolio operator)

**Why now:** Native Realty has been named repeatedly in this week's transaction flow as an active Fort Lauderdale/Broward commercial operator. Multi-family portfolios = aggregated claim exposure = high-value referral source.

**Category:** Property Manager (commercial / multi-family)
**County:** Broward
**Suggested approach:** Listing-first initial template; commercial multi-family angle (claims operations rather than homeowner referrals)
**Risk note:** Larger operators have in-house claims teams; confirm Duncan's positioning fits before reaching out.

---

## 2. Cascades at the Hammocks Ownership Group (Miami-Dade — $65.5M, 264 units)

**Why now:** Recently closed $65.5M acquisition (264 units) in Miami-Dade. New ownership = fresh property-management decisions = window for referral relationships before lock-in.

**Category:** Property Manager / Multi-family Operator
**County:** Miami-Dade
**Suggested approach:** Initial outreach to whoever bought it — congratulations frame + claim-readiness offer for hurricane season (T-14 days)
**Research needed:** Identify acquiring entity from deed/CRE press; HubSpot CRM, ALN Apartment Data, or county property appraiser

---

## 3. Uptown Boca / Residences at Uptown Boca Ownership (Palm Beach — $240M, 456 units)

**Why now:** Largest multi-family residential transaction in Palm Beach County this month — 456 units, 643K sq ft. New ownership of this scale is exactly the kind of property-management decision-maker Duncan wants in his network.

**Category:** Property Manager / Multi-family Operator
**County:** Palm Beach (Duncan's home turf)
**Suggested approach:** High-priority. Listing-first template + Wellington-local angle (Duncan is geographically proximate). Open with congratulations + pre-season claim-readiness offer.
**Research needed:** Identify operating partner / property management company for the residences

---

## 4. Miami & South Florida REALTORS (post-merger Realtor association)

**Why now:** As of May 11, the merged association is the **world's largest local Realtor association** at 93,000 members. The 30–60 day integration window is when partnership and sponsor-listing positioning is most accessible. After integration locks, the partnership funnel will harden.

**Category:** Trade association / Referral concentrator
**Counties:** Miami-Dade, Broward, Palm Beach, St. Lucie (all of Duncan's footprint)
**Suggested approach:**
- LinkedIn outreach to **Teresa King Kinney** (Co-CEO) and **Dionna Hall** (Co-CEO)
- Angle: provider-directory partnership / preferred-vendor positioning / educational content sponsorship for the unified MLS audience
- One relationship here = visibility to 93,000 agents = compounding referral lane
**Risk note:** Senior co-CEOs of the largest Realtor association in the U.S. — outreach quality matters more than speed. Suggest Duncan reviews messaging line-by-line before sending.

---

## How to add these manually (if approved)

For each approved prospect, append a row to `crm/organizations.csv` with this shape:

```
<county>-<short-slug>,<Org Name>,<category>,<county>,<website>,<contact_name>,<title>,<email>,<phone>,<linkedin>,initial,2026-05-18,,2026-05-19,<notes>
```

Leave `last_touch_date` blank until first outreach; set `next_followup_date` to 2026-05-19 to queue for tomorrow's run.

---

## Strategic note

The pipeline is thinning (KLR pausing today, Atlantic and SafeHaven escalating). Adding 2–4 fresh prospects this week keeps the funnel healthy. **#3 (Uptown Boca)** and **#4 (Realtor association)** are the highest leverage of the four — recommend Duncan prioritize those for research.
