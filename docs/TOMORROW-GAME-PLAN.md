# Tomorrow's Game Plan — May 11, 2026
**Duncan: Read this first. Everything below is prepped and ready for your approval.**

---

## The Day in Three Phases

| Time | Phase | Goal |
|------|-------|------|
| 7:00–8:30am | Morning Approvals | Review and greenlight the big items |
| 8:30–11:00am | Execution Sprint | Social launch, HubSpot, outreach |
| 11:00am–1pm | Partner Outreach | 1-on-1 with highest-value contacts |

---

## PHASE 1: YOUR APPROVALS (7–8:30am)
*These are the items that need your eyes and your go-ahead before they go live.*

### A1 — Investor Deck (HIGH PRIORITY)
**File:** `docs/INVESTOR-DECK.html`
**What it is:** A full professional investor presentation covering what we've built, 30/60/90-day plan, revenue model, and projected returns.
**Your decision:** Review and tell me what to change. If you want to share it with anyone today, I'll export a shareable version.

### A2 — Social Calendar
**File:** `docs/SOCIAL-CALENDAR-30DAY.md`
**What it is:** 30-day Facebook + Instagram posting calendar, copy ready to paste, one post per platform per day.
**Your decision:** Approve as-is, or flag posts you want to change. Once you hand me credentials, I'll load it into Meta Business Suite.

### A3 — Facebook Groups Strategy
**File:** `docs/FACEBOOK-GROUPS.md`
**What it is:** Researched list of groups to join, with engagement strategy per group type.
**Your decision:** Review the list. Some groups require in-app search (Facebook doesn't expose them publicly). In the morning, spend 20 minutes in Facebook searching and joining 10–15 groups using the manual search terms in the document.

### A4 — Website Review
**Status:** All changes live at robinhoodadjusting.com (deployed last night)
**What went live:**
- Hurricane checklist signup now correctly routes to HubSpot (bug fixed)
- Insurance Policy Review Checklist — signup page + printable resource
- Contractor Vetting Guide — signup page + printable resource
- Free Guides section on homepage now has "Free with Signup" badges
**Your decision:** Browse the live site and confirm everything looks right. Flag any issues.

---

## PHASE 2: EXECUTION SPRINT (8:30–11:00am)

### E1 — Facebook/Instagram Launch (FIRST PRIORITY)
**What you need:** FB/IG credentials → hand to me
**What I'll do:**
1. Set up Meta Business Suite if not already configured
2. Connect both platforms
3. Upload Week 1 posts (May 10–16) with scheduling
4. Set up profile bios with links to: robinhoodadjusting.com + newsletter CTA
5. Upload profile photos / cover images (you'll need to provide or I'll pull from the site)
**Timeline:** 45–60 minutes once I have credentials

### E2 — HubSpot Deal Pipeline
**Status:** `scripts/setup_deal_pipeline.py` exists but hasn't been run
**What it does:** Sets up a deal pipeline in HubSpot specifically for PA claims workflow:
- Stage 1: Initial Contact
- Stage 2: Policy Review Requested
- Stage 3: Claim Filed
- Stage 4: Active Negotiation
- Stage 5: Settlement Reached
**Your decision:** Approve → I'll run the script and configure the pipeline
**Why it matters:** When partner referrals come in, they need a trackable home in HubSpot

### E3 — Newsletter Welcome Email
**Status:** Not built yet
**What it is:** Automated HubSpot email sequence for new subscribers:
- Email 1 (immediate): Welcome + deliver the checklist they signed up for
- Email 2 (Day 3): "Did you know your deductible might be higher than you think?" — policy tip
- Email 3 (Day 7): Introduce Robinhood Adjusting + free consultation offer
**Your decision:** Approve the concept → I'll write all three emails and configure in HubSpot today
**Why it matters:** Right now subscribers get a thank-you page but no follow-up. This converts subscribers to consultations.

### E4 — Daily Brief for May 11
**Status:** Today's brief is scheduled via cron at 4am — should already be generating
**Your action:** Check `ops-review/2026-05-11.md` when it's ready (~4am or catchup if Mac was off). If it generated properly, no action needed.

---

## PHASE 3: PARTNER OUTREACH (11am–1pm)

This is where you personally execute. Everything above has been automated. This can't be.

### P1 — Top 5 Outreach Targets Today
Based on the Palm Beach County prospecting list, these profile types are the highest-leverage 1-on-1 contacts:

**Priority 1: Roofing contractors (3–5 calls)**
- Script: "Hey [name], I'm Duncan Littlejohn with Robinhood Adjusting. We're a public adjusting firm in Palm Beach County. We work with homeowners after storm damage to make sure their insurance claims are properly documented and paid. We like to know which contractors in the area are doing honest work — we think you might be one of them. Is there a good time to grab 15 minutes?"
- Follow-up: Send them the contractor vetting guide and position it as "here's what your customers use to vet contractors like you — if you pass all 12 checks, this is actually good for your business"

**Priority 2: Property managers (2–3 calls)**
- Script: "Hey [name], we work with property managers across Palm Beach County as their go-to public adjuster. Anytime one of your properties takes storm damage and the insurance claim comes back low, we fight that on your behalf. We only collect if we win. Is that something worth a quick conversation?"
- Follow-up: Insurance policy review checklist tailored to commercial/property management

**Priority 3: Real estate attorneys (1–2 contacts)**
- Script: "Hi, I'm Duncan Littlejohn, a licensed public adjuster in Palm Beach County. I work with real estate attorneys when transactions involve open insurance claims or storm-damaged properties. I wanted to introduce myself — a lot of what I do is resolving the claim disputes that create title problems. Would you be open to a quick call?"

### P2 — LinkedIn Outreach
While making calls, run parallel LinkedIn outreach to:
- RE attorneys in Palm Beach County
- Property managers (connect with a note, not a pitch)
- Roofing company owners

**Message template:**
> "Hi [name] — I run Robinhood Adjusting, a public adjuster practice in Palm Beach County. Hurricane season starts June 1 and I'm building relationships with the contractors and property professionals who do honest work in South Florida. I'd like to connect. —Duncan"

---

## WHAT'S ALREADY PREPARED FOR TOMORROW MORNING

Everything below is done. You don't need to build it — just review and approve.

| Item | Status | Location |
|------|--------|----------|
| 30-Day Social Calendar | ✅ Ready | docs/SOCIAL-CALENDAR-30DAY.md |
| Facebook Groups Research | ✅ Ready | docs/FACEBOOK-GROUPS.md |
| Investor Deck | ✅ Ready | docs/INVESTOR-DECK.html |
| Hurricane Checklist Signup (fixed) | ✅ Live | robinhoodadjusting.com/hurricane-checklist |
| Insurance Policy Review | ✅ Live | robinhoodadjusting.com/insurance-policy-review |
| Contractor Vetting Guide | ✅ Live | robinhoodadjusting.com/contractor-vetting-guide |
| Printable Checklists | ✅ Live | site/resources/*.html |
| subscribe-newsletter.js | ✅ Deployed | netlify/functions/subscribe-newsletter.js |

---

## METRICS TO TRACK THIS WEEK

Set a 5-minute morning check on these:

| Metric | Where to Check | Target (30 days) |
|--------|---------------|------------------|
| Newsletter subscribers | HubSpot → Lists | 500 |
| Social followers (FB + IG) | Meta Business Suite | 200+ |
| Lead magnet signups | HubSpot → Contacts (source: lead magnet) | 50+ |
| Provider directory inquiries | get-listed@robinhoodadjusting.com | 10+ |
| Direct consultation requests | Contact form / phone | 5+ |
| HubSpot deal pipeline entries | HubSpot → Deals | 2–3 |

---

## END-OF-DAY GOAL FOR TOMORROW

By 1pm, you should have:
- [ ] Social calendar live and scheduling
- [ ] At least 10 FB groups joined
- [ ] HubSpot deal pipeline configured
- [ ] 3+ welcome email drafts approved
- [ ] 5–10 partner outreach calls made or scheduled
- [ ] Investor deck reviewed and ready to share

That's a full morning. Don't overload the afternoon. Partner relationships are built over weeks — plant the seeds tomorrow and let them grow.

---

*Prepared overnight by Agent Smith. All systems ready. See you at 7am.*
