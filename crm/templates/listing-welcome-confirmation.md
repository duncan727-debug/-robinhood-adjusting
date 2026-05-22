# Template: Listing welcome / confirmation

**Use when:** Partner has replied with their qualifying-questions answers (Q1–6). Automated send by `parse_listing_answers.py` after HubSpot properties are populated.

**Format rule:** Warm, brief, sets expectations. No questions — this is a confirmation, not another ask.

**Parameters to fill in:**
- `{FIRSTNAME}` — partner first name
- `{COMPANY}` — business name
- `{COUNTIES_LIST}` — comma-joined counties they selected (e.g. "Palm Beach, Martin")
- `{JOB_SIZE_LABEL}` — friendly version of job_size_focus (e.g. "Residential and Commercial")
- `{EMERGENCY_LABEL}` — "24/7 emergency calls" or "Business hours only"
- `{CHANNEL_LABEL}` — "text" / "phone" / "email" / "any of the three"

---

**Subject:** You're all set — here's how referrals will reach you

Hi {FIRSTNAME},

Thanks — got your details. {COMPANY} is fully dialed in.

**Quick recap of how I have you set up:**
- Service area: {COUNTIES_LIST}
- Job fit: {JOB_SIZE_LABEL}
- Availability: {EMERGENCY_LABEL}
- Preferred lead channel: {CHANNEL_LABEL}

**Here's what to expect:**

When a homeowner comes through me with a situation that fits, I'll reach out via {CHANNEL_LABEL} with the basics — name, address, what's going on, and the best time to reach them. I vet the situation first so you're not chasing tire-kickers. If a lead isn't a fit for any reason, just say so — no hard feelings, I'll route it elsewhere.

You don't have to be exclusive with me, and I don't expect a kickback. The exchange is simple: I send qualified homeowners to people I trust, and over time hope you'll think of me when one of yours needs a Public Adjuster.

If anything changes on your end (coverage area, availability, who handles incoming leads), shoot me a note and I'll update the directory.

Hurricane season starts June 1 — we'll likely both be busy. Glad to have you on the network.

Best,
Duncan Littlejohn
Licensed Public Adjuster · Robinhood Adjusting · Wellington, FL
561-772-7528 · robinhoodadjusting.com
