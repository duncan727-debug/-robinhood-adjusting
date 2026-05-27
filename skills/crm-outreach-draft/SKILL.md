---
name: crm-outreach-draft
description: "Draft personalized prospect outreach in Duncan's voice — soft on first contact, intent ramps on follow-ups, bounce-aware, channel-aware (no LinkedIn)."
user-invocable: true
---

# CRM outreach draft

For drafting personalized first-touch and follow-up messages. Output is always reviewable before send — never auto-send unless Duncan explicitly delegates.

## Voice rules (memorize)

- **Sounds like a human, not a campaign.** No "I hope this email finds you well." No "synergize." No emoji.
- **Specific over generic.** Reference the prospect's actual business, neighborhood, recent storm activity, a competitor they likely know.
- **Soft on contact 1.** No ask. Offer something (intel, an intro, a referral). Curiosity opener.
- **Intent ramps.** Contact 2 = light ask (15-min call). Contact 3 = direct (specific value prop + calendar link). Contact 4 = breakup ("closing your file unless I hear back").
- **One-man ops are high-fit.** Don't auto-close them for "no website" or "no email"; Duncan calls them in person. Surface to him as a phone-prospect, not a drop.
- **Channel rules**: email first → contact form fallback after 3 bounces → phone if Duncan flags as high-fit. NO LinkedIn (halted 2026-05-19).
- **From address**: always `duncanlittlejohn727@gmail.com`. Never the personal one.
- **BCC**: HubSpot dropbox `246055074@bcc.hubspot.com` on every outbound.
- **Calendar link**: Calendly `/30min` (phone) or `/virtual-review` (video). Pick by context.
- **Firm**: Robinhood Adjusting (Barclays affiliation ends June 2026; do not reference Barclays).

## Workflow

1. Pull prospect record from `crm/organizations.csv` + `crm/interactions.csv`. Confirm: which contact attempt is this? Last touch date? Bounced?
2. If last 3 emails bounced → escalate to contact-form queue (use `contact_form_fallback_workflow`, not email draft).
3. If one-man op + no email → write a HubSpot task on Duncan "Call <name> at <number>" — do NOT draft email.
4. Pick template by stage (1/2/3/4). Personalize 2-3 specifics (business name, neighborhood, recent storm/permit, named competitor).
5. Add Calendly link if stage ≥2. Add referral language if Seth's Restoration partnership ever activates (currently parked until 500 subs).
6. Save draft to `crm/drafts/YYYY-MM-DD/<prospect-id>.eml`. Log to `crm/interactions.csv` with status=draft.
7. Surface for Duncan review (HubSpot task or `ops-review`).

## Listing-reply workflow (subflow)

If the prospect was just added to the provider directory:
- Send the qualifying-questions email (5–7 multi-choice, 60-sec format)
- GATE: only send confirmation email after `directory_listing_status=listed` flips to listed
- Reference: `listing_reply_workflow` memory

## Do not
- Promise referrals before Seth partnership is live (≥500 subs).
- Reuse the same opener within 30 days for the same audience segment.
- Send Friday after 3pm EDT or any time Saturday (Sunday newsletter day instead).
- Auto-send. Always draft → Duncan reviews → he sends or approves bulk.
- Cross-check only one log file. Before bulk mutations, check `interactions.csv`, `outreach_send.log`, and state files (per `feedback_data_truth_sources`).

## Outputs
- `crm/drafts/YYYY-MM-DD/<id>.eml`
- `crm/interactions.csv` row (status=draft)
- HubSpot task for Duncan if action required
