---
name: Newsletter Send Schedule
description: Daily and weekly send times for subscriber emails via HubSpot
type: project
---

**Daily briefs:** 8:00 AM EDT, every morning (Mon-Sat)
- Sent to all newsletter subscribers
- Content: South Florida property intelligence brief for that day

**Weekly trends articles:** 9:00 AM EDT, every Saturday morning
- Sent to all newsletter subscribers  
- Content: Seven-day market synthesis identifying key industry trends, tactical recommendations for PAs/contractors/property owners

**Automation approach (as of 2026-05-02):**
- HubSpot API sends emails from pre-built templates
- Brief markdown converted to HTML daily, inserted into template
- Trends article created Saturday morning, inserted into email template
- Single website update per day (end of morning batch) to minimize token usage

**Key reminder:** One website update per day at the end of the morning content batch to minimize token consumption.
