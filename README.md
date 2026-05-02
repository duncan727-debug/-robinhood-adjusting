# Robinhood Adjusting - Workspace

## Directory Structure

```
/config/        Configuration & credentials (.services-config.txt)
/content/       Newsletter content: briefs/, articles/, trends/, weekly/, monthly/
/docs/          Documentation: user guides, setup guides, analysis reports
/operations/    Operations: daily reviews, schedules, dashboards
/business/      Business planning: ventures, market analysis, strategy
/crm/           CRM: contact intelligence, templates, company data
/scripts/       Automation: cron scripts, logs, state files
/site/          Website: PA-WEBSITE.html, index.html, providers/
/memory/        Session memory (auto-persisted by Claude Code)

IDENTITY.md     Agent Smith identity (at root, authoritative)
README.md       This file
netlify.toml    Netlify deployment config (at root—required)
.netlify/       Netlify functions (managed by Netlify)
```

## Key Workflows

- **Daily Brief Generation** (4am EDT Mon-Sat): Generates 3 audience segments, stored in `/content/briefs/`
- **Website Deployment** (morning upload window): All changes batched and deployed together via `/site/PA-WEBSITE.html`
- **CRM Intelligence** (8:30am EDT Mon-Sat): Daily consolidation into HubSpot via `/crm/`
- **Operations Reviews**: End-of-day summaries in `/operations/ops-review/`

## Site & Deployment

- **Live Site**: robinhoodadjusting.com (deployed from `/site/PA-WEBSITE.html`)
- **Newsletter Signup**: Via `.netlify/functions/subscribe-newsletter.js` → HubSpot
- **Auto-Deploy**: Changes to `/site/` → GitHub → Netlify (2-5 min turnaround)
