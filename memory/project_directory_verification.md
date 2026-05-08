---
name: Directory listing verification badge
description: When a prospect replies confirming their listing, add a verification mark to their entry on the robinhoodadjusting.com provider directory
type: project
---

When a company responds to the outreach email and confirms their directory listing details (service area, phone, website), their listing on robinhoodadjusting.com/providers should be updated with a verification badge/mark to indicate they are a confirmed, responsive provider.

**Why:** Duncan wants to differentiate confirmed responders from unverified scraped listings — builds trust for homeowners browsing the directory.

**How to apply:** Build a flag in the provider data (e.g. `verified: true` + `verified_date`) that the website template renders as a visual badge on the listing card. When CRM status updates to "confirmed" or similar, trigger the website data update.
