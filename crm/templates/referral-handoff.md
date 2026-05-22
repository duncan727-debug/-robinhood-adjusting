# Template: First-referral handoff

**Use when:** Duncan sends a partner an actual homeowner referral. Event-driven (not cron). Triggered manually or by a future "send referral" workflow.

**Format rule:** Same structure every time — partners should learn the pattern. Lead with the homeowner's situation, not pleasantries. Phone-readable in 30 seconds.

**Parameters to fill in:**
- `{FIRSTNAME}` — partner first name
- `{HOMEOWNER_NAME}` — homeowner's name
- `{HOMEOWNER_PHONE}` — best contact number
- `{HOMEOWNER_ADDRESS}` — street + city
- `{SITUATION}` — 1–2 sentence summary (e.g. "Roof leak in master bedroom after last week's storm, has been catching water with buckets, no insurance claim filed yet")
- `{WANT}` — what they want from you (e.g. "Inspection + estimate this week, decide on claim filing after")
- `{BEST_TIME}` — when to reach them (e.g. "Weekdays after 4pm, weekends anytime")
- `{URGENCY}` — "Standard" / "Urgent — active leak" / "Emergency — call today" / etc.

---

**Subject:** Referral for {COMPANY_FIRSTNAME_OR_COMPANY} — {URGENCY}

Hi {FIRSTNAME},

Sending {HOMEOWNER_NAME} your way:

- **Phone:** {HOMEOWNER_PHONE}
- **Address:** {HOMEOWNER_ADDRESS}
- **Situation:** {SITUATION}
- **What they're looking for:** {WANT}
- **Best time to reach them:** {BEST_TIME}
- **Urgency:** {URGENCY}

They know you're coming — I told them to expect your call. If it's not a fit on your end (wrong scope, booked out, whatever), just shoot me a one-liner back and I'll route to someone else, no worries.

If you take the job, no need to update me unless you want to. If there's a claim component down the road and they need a Public Adjuster, you know where to find me.

Best,
Duncan
561-772-7528
