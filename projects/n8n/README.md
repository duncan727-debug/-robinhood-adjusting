# n8n — local workflow automation

Running locally on this Mac at **http://localhost:5678**.

## What it is
Open-source visual workflow builder. Lets us replace tangled Python crons with drag-and-drop pipelines, with 400+ pre-built integrations (HubSpot, Gmail, Slack, Meta, Calendly, OpenAI/Claude, webhooks, schedule triggers, etc.).

## First-time access
1. Open http://localhost:5678 in browser.
2. Set up the owner account (email + password) — local-only, no cloud.
3. Confirm you can see the empty workflow canvas.

## What's installed
- **Binary:** `~/.local/n8n/node_modules/.bin/n8n` (v2.22.6)
- **Data dir:** `~/.n8n/` — workflows, credentials, SQLite DB
- **Logs:** `~/.local/n8n/n8n.log`
- **Port:** 5678

## Daemon
LaunchAgent at `~/Library/LaunchAgents/com.openclaw.n8n.plist` — starts on login, auto-restart if it crashes.

Manual commands:
- Stop:   `launchctl unload ~/Library/LaunchAgents/com.openclaw.n8n.plist`
- Start:  `launchctl load   ~/Library/LaunchAgents/com.openclaw.n8n.plist`
- Status: `launchctl list | grep openclaw.n8n`

## First workflows to migrate
Candidates from our current Python cron pile that would be easier as visual n8n flows:
1. **Contact-form queue → HubSpot contact creation** (`scripts/contact_form_queue.log`)
2. **IMAP bridge bounce/reply → HubSpot deal stage update** (currently `scripts/imap_bridge.py`)
3. **Calendly webhook → HubSpot task creation**
4. **Reply queue triage** (route inbound emails by intent)
5. **Phone agent webhook (Retell) → HubSpot contact + Duncan notification**

Pick one to prototype first — recommend (5) since it's net-new and pairs with the phone agent.

## Note on cost
Free. Self-hosted. No subscription. Uses your Claude/OpenAI API key when the workflow calls an LLM node; nothing else metered.
