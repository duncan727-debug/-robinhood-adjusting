# Daily Brief Generation Spec

Each day (Mon–Sat), generate **3 segment-specific HTML brief files**.

## File naming

```
content/briefs/YYYY-MM-DD-homeowner.html
content/briefs/YYYY-MM-DD-service-provider.html
content/briefs/YYYY-MM-DD-real-estate.html
```

Also generate the matching `.md` source file for each segment.

## Audience profiles

### homeowner (`-homeowner`)
**Who:** South Florida property owners, renters concerned about coverage.
**Tone:** Plain-language, protective. Help them understand what's happening before they need to act.
**Content focus:**
- Carrier rate changes, coverage restrictions, non-renewal notices in FL
- Storm activity, NHC outlooks, active weather threats
- Claim trends, adjuster behavior, denial patterns
- Policy tips, documentation best practices
- Legislative/regulatory changes affecting homeowners
- Local contractor demand, tariff impact on repair costs

### service-provider (`-service-provider`)
**Who:** Roofers, restoration contractors, mitigation companies, general contractors, plumbers — anyone doing insurance-adjacent work in South Florida.
**Tone:** Peer-to-peer, market-intel. Treat them as business owners who want an edge.
**Content focus:**
- Storm season outlook and project pipeline implications
- Carrier approval patterns, scope-of-loss disputes, supplement trends
- Tariff/materials cost updates
- Contractor licensing, lien law, SB-2D/assignment of benefits updates
- Permit activity, building department news
- Referral opportunities and PA partnership context

### real-estate (`-real-estate`)
**Who:** Agents, brokers, investors, property managers active in South Florida.
**Tone:** Transaction-aware, market intelligence. Show them the insurance layer that affects their deals.
**Content focus:**
- Carrier withdrawal/re-entry in FL markets
- Insurance costs affecting affordability, buyer hesitation, deal flow
- Claims that surface during inspection or post-closing
- Condo association insurance issues (milestone inspections, SIRS)
- Property value implications of storm damage or coverage gaps
- Reinsurance market updates that ripple into policy pricing

## Format (HTML)

Each brief is a standalone HTML fragment (no `<html>`/`<head>`/`<body>` tags — just the content block that gets injected into the email template).

Structure:
```html
<h2 style="color:#0f2d4a;font-size:20px;margin:0 0 8px;">BRIEF TITLE — Segment Name</h2>
<p style="color:#888;font-size:13px;font-family:Arial,sans-serif;margin:0 0 28px;">Date · South Florida Property Intelligence</p>

<!-- 3–5 story blocks -->
<h3 style="color:#0f2d4a;font-size:17px;margin:24px 0 8px;">Story Headline</h3>
<p>Body paragraph...</p>

<!-- Optional CTA at bottom -->
<hr style="border:none;border-top:1px solid #eee;margin:32px 0;">
<p style="font-size:14px;">...</p>
```

## Deduplication rule

Do not cover the same story in the same segment's brief if it was covered in the past **4 days** for that segment. Cross-segment repetition is fine — a carrier withdrawal may appear in all 3 briefs with different angles.

## Website

After generating all 3 briefs, update `site/briefs/` with the HTML files and add all 3 to the website's brief index. The website shows the homeowner brief as the "featured" brief for general visitors.
