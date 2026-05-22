# Template: 30-day check-in — field-met service provider

**Use when:** 30 days have passed since Duncan met this service provider in person (set as `partner_onboarded_at`). `partner_type = field_met`. Automated by `partner_lifecycle.py`.

**Format rule:** Personal, reminds them of the in-person meeting, no sales pitch. Warm and short. Treats this as a person Duncan actually knows — not a CRM record.

**Parameters to fill in:**
- `{FIRSTNAME}` — partner first name
- `{COMPANY}` — business name (or trade if unknown)
- `{MET_CONTEXT}` — short reminder of where/how they met (e.g. "at the Smith roof job last month" / "on that Wellington water-damage call"). If unknown, defaults to "out in the field".

---

**Subject:** Wanted to check in — month since we crossed paths

Hi {FIRSTNAME},

It's been about a month since we crossed paths {MET_CONTEXT}, and I wanted to drop a quick note before too much time passes.

No agenda — just keeping the line open. If you've got a homeowner who needs a Public Adjuster (or you're not sure if they need one), shoot me a text, doesn't matter the hour. Same goes the other way: when one of my homeowners needs {COMPANY}'s kind of work, I want to know I can reach you.

Hurricane season starts June 1 — going to be a busy stretch for both of us. Stay in touch.

Best,
Duncan Littlejohn
Licensed Public Adjuster · Robinhood Adjusting · Wellington, FL
561-772-7528 · robinhoodadjusting.com
