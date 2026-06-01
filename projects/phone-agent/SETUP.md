# Phone agent setup — 15 minutes total

## Recommendation: Retell AI over Vapi

- Retell: cleaner LLM bring-your-own (we can point at Claude), sub-600ms latency, SOC 2 + HIPAA, $0.07/min, no platform fee. Good docs.
- Vapi: also strong, $10 free trial, slightly more dev-heavy.

Going Retell unless you'd rather Vapi.

## What I need from Duncan (5 min)

1. Go to **https://www.retellai.com/** → Sign up with `duncanlittlejohn727@gmail.com`.
2. Verify email, complete onboarding.
3. Add payment method (no monthly fee — pay per minute only).
4. Buy a local PBC number (561 area code if available) — usually ~$1.15/mo.
5. Paste the **API key** + the **phone number** into `config/.secrets` under:
   ```
   RETELL_API_KEY=...
   RETELL_PHONE_NUMBER=+1561xxxxxxx
   ```

## What I do (10 min, after you hand over keys)

1. Upload the system prompt from `AGENT-PROMPT.md` to Retell as a new agent.
2. Configure agent voice (default: Sarah/warm-female; change if you'd rather a male voice).
3. Wire the **post-call webhook** to a new script `scripts/retell_webhook.py` that:
   - parses the call summary payload
   - creates/updates the HubSpot contact (existing helper)
   - logs urgent calls to `crm/urgent_calls.jsonl` and pings you on this channel
   - confirms the SMS Calendly link
4. Add a "test call" cron entry (manual-only) so we can dial in to verify.
5. Print the test call transcript here so you can audit the voice + flow.

## Where to put the number

- Robinhood website header + footer ("Talk to us: (561) XXX-XXXX — 24/7 intake")
- Email signature
- IG/FB bio
- HubSpot outreach templates (touch 2+)
- Calendly confirmation pages

## Ongoing cost ballpark

- Number: $1.15/mo
- Minutes: $0.07/min — 50 calls/mo × 4 min avg = ~$14/mo
- LLM: routed through Retell's pool (free) OR our Claude budget if we BYO
- **Realistic total: $15-20/mo for first 3 months, scales with call volume**

## Risk to flag

- The agent will get edge-case calls (wrong number, telemarketers, confused homeowners). The post-call review for the first 2 weeks should be daily. I'll surface anomalies.
- If the agent fumbles a real call, the cost isn't $0.28 — it's the lost lead. Build in a "Robin couldn't help → Duncan callback within 1 hour" failsafe (already in the prompt).
