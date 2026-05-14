# Free Virtual Property Review — Setup Checklist

**Status as of 2026-05-14:** Landing page + newsletter footer wired in code. Two manual setup steps remain in Calendly and HubSpot.

---

## ✅ Already done (in code, deployed via git)

- `site/free-review.html` — full landing page with hero, what's included/not, how-it-works, Calendly embed slot, FL §626.854 compliance disclaimer, trust bar, footer
- `site/index.html` — new "Talk to a Public Adjuster — Free" card section featured above the existing "Free with Signup" checklists (both the main resources block and the Guides tab panel)
- `scripts/send-daily-brief.py` — newsletter footer now includes a gold CTA panel ("Got damage or a denial letter? Show us on video.") above the existing footer, linking to `robinhoodadjusting.com/free-review.html`

---

## 🔧 Manual setup — Calendly

The landing page embeds Calendly at this URL:

```
https://calendly.com/duncanlittlejohn727/virtual-review
```

Create a **new event type** with that exact slug so the embed resolves. Settings:

| Field | Value |
|---|---|
| Event name | Free Virtual Property Review |
| Slug | `virtual-review` |
| Duration | 15 minutes |
| Location | Zoom (auto-link) |
| Buffer time | 15 min before & after |
| Min notice | 4 hours |
| Max bookings/day | 2 |
| Max bookings/week | 4 |
| Date range | Rolling 30 days |
| Available hours | Tue 2:00–4:00 PM EDT, Thu 2:00–4:00 PM EDT (adjust to taste) |

### Screening questions (in this order)

1. **Property address** *(required, short text)* — "Street address of the property in question."
2. **What brings you here?** *(required, multi-select)*
   - Visible damage (roof, water, wind, etc.)
   - Insurer denial or low offer
   - Renewal / coverage question
   - Other
3. **Describe the issue** *(required, paragraph)* — "1–3 sentences on what happened, when, and what the insurer (if any) has said so far."
4. **Photos** *(optional, file upload, max 3)* — "Optional but speeds the call up significantly."
5. **Have you signed anything with another PA, attorney, or contractor on this loss?** *(required, yes/no)* — disclosure to avoid §626.854 conflict.

### Confirmation email (Calendly side)

Use this body so expectations match the landing page:

> Thanks for booking your free 15-minute virtual property review. A Zoom link is in this confirmation.
>
> **What to have ready:**
> - The damage or letter you want to discuss
> - Your declarations page (if you have it handy — not required)
>
> **What this call is:** a free, no-obligation read on whether your loss is likely a covered insurable event under your policy.
>
> **What this call is NOT:** a representation contract. We will not ask you to sign anything on the call. Florida Statute §626.854 prohibits us from soliciting representation on this call, and we don't want to.
>
> If your situation is straightforward, we'll tell you exactly how to handle it yourself. If we think it's worth pursuing with our help, we'll send you information to read on your own time.
>
> See you soon —
> Duncan, Robinhood Adjusting

---

## 🔧 Manual setup — HubSpot

### A. Verify Calendly → HubSpot integration is active

Per the existing memory (`hubspot_calendly_integrations.md`), Calendly is already syncing into HubSpot with calendar write enabled. Confirm in Settings → Integrations → Calendly that the new "Free Virtual Property Review" event type appears and is set to **create contact + log activity + create deal**.

### B. Create the deal pipeline stages

Add these stages to the **Partner Outreach** pipeline (or whichever you use for warm leads) so we can track virtual-review flow separately from cold outreach:

| Order | Stage label | Purpose |
|---|---|---|
| 1 | Virtual Review Booked | Calendly booking received |
| 2 | Virtual Review Held | Call completed (set manually after the call) |
| 3 | Recommended Self-Help | Owner can DIY — won't engage further |
| 4 | Recommended PA Engagement | Owner needs us — material to send |
| 5 | Engagement Active | Signed representation contract |
| 6 | No Show / Cancelled | Closed-lost reason |

### C. Welcome-email workflow (optional, recommended)

Build a HubSpot workflow:

- **Trigger:** Contact enrolled in any of the 3 segment lists (Homeowner, Service Provider, Real Estate)
- **Delay:** 3 days after enrollment
- **Action:** Send email "Did you know you can talk to a public adjuster for free?" — short, links to `/free-review.html` and Calendly.
- **Suppression:** Don't send if contact has `hs_lead_status = IN_PROGRESS` or already booked (deal exists in Virtual Review Booked).

I can draft the email copy when you're ready; not critical for launch.

---

## 📊 What I'll be tracking

Once Calendly is live and bookings start flowing, I'll add these to the daily ops-review:

- Bookings made (today / week / total)
- Bookings completed vs. no-show rate
- Conversion split: Self-Help / PA Engagement / Closed
- Source attribution: which segment list / referrer drove the booking

---

## 🚦 Order of operations to go live

1. Duncan creates Calendly event type with slug `virtual-review` (above settings) — ~10 min
2. Duncan adds 6 deal stages in HubSpot — ~5 min
3. Duncan opens `https://robinhoodadjusting.com/free-review.html` and tests the Calendly embed loads + a test booking shows up in HubSpot
4. (Optional) Duncan asks me to draft the day-3 welcome email when ready

Once step 1 completes, the existing landing page + newsletter footer will start funneling bookings immediately — no additional code changes needed.
