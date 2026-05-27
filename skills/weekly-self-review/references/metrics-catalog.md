# Metrics catalog — where to find what

| Metric | Source | Parse hint |
|---|---|---|
| Outreach sent | `scripts/outreach_send.log` | grep `SENT` lines, count by date |
| Replies received | `crm/interactions.csv` | column `interaction_type=reply`, group by date |
| Reply rate | derived | replies / sent (lagged 3-7 days) |
| Bounces | `crm/email_enrichment.log` + `scripts/imap_bridge.log` | `BOUNCE` events |
| Contact-form fallback submits | `crm/contact_form_queue/YYYY-MM-DD.csv` + manual logs | count rows where submitted=true |
| HubSpot task queue depth | HubSpot API `crm.objects.tasks` | filter by assignee=Duncan, status=open |
| Cron runs | `mcp__openclaw__cron action=runs` | per jobId, last 7 days |
| Cron failures | same | status=failed |
| Brief acronyms | `site/briefs/YYYY-MM-DD.html` | regex `[A-Z]{2,}` excluding allowlist (HOA, FL, OIR, NOAA, etc) |
| Brief audiences | same | check for "Homeowner:" "Provider:" "Real estate pro:" headers |
| Brief dedup | compare topics across last 4 days |
| Token usage | `/tmp/openclaw/openclaw-YYYY-MM-DD.log` | grep usage lines, sum input+output |
| Time-to-completion | cron `runs` startedAt vs endedAt |
| Health uptime | `scripts/health-check.log` | OK vs FAIL ratio |
| Service status | `scripts/health-check.log` (daily) | Gmail/GitHub/Netlify/HubSpot/Namecheap |
| Newsletter send count | `scripts/newsletter-send.log` |
| Provider directory adds | `site/directory/` git log |

## Allowlist for acronyms in briefs
HOA, FL, OIR, NOAA, NWS, PA, RE, A/C, HVAC, HQ, FAQ, USA, US, NHC, FEMA
