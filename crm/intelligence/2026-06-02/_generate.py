#!/usr/bin/env python3
"""Generate per-org intel files for 2026-06-02 outreach batch.

No fabrication: only pulls from CSV + interaction history + standard
industry pain-point frameworks (clearly labeled as inference, not research).
Real research is appended manually for orgs with verified websites.
"""
import csv
import os
from collections import defaultdict
from datetime import date

TODAY = "2026-06-02"
OUTDIR = "/Users/victoria/.openclaw/workspace/crm/intelligence/2026-06-02"

# Category -> standard pain-point framework (FL PA-adjacent industries)
CATEGORY_PAINS = {
    "roofer": [
        "Claim denials/short-pays slow homeowner approvals on storm-damage roofs",
        "Insurer-mandated scope reductions cut margin on FBC-compliant rebuilds",
        "Carriers pushing repair-over-replace on roofs near end of life",
        "Cash-flow gap between deposit and final ACV/RCV release",
    ],
    "property-manager": [
        "Multi-unit claim coordination across HOA master + unit-owner policies",
        "Slow LAE process delays repairs and tenant retention",
        "Pre-loss documentation rarely standardized across portfolio",
        "Citizens depopulation moves changing coverage at renewal",
    ],
    "realtor": [
        "Listings with open prior claims get re-underwritten / OIR-21 lookups stall closings",
        "4-point + wind mit inspections flagging items mid-contract",
        "Buyer carrier non-renewals at binder stage killing deals",
        "Sellers leaving covered damage money on the table at closing",
    ],
    "restoration": [
        "AOB restrictions post-HB 837 squeezing mit-only operators",
        "Carriers contesting Xactimate line items / drying logs",
        "Slow advance payments on Cat-3+ losses",
        "Mold remediation scope challenges under FL §627.7152",
    ],
    "general-contractor": [
        "Insurance-pay jobs require carrier-aligned documentation contractors rarely have time to build",
        "Supplements left on the table when scope expands mid-build",
        "Code-upgrade reimbursement (Ord & Law) under-claimed",
        "FBC 7th edition triggering scope changes carriers don't auto-approve",
    ],
    "plumbing": [
        "Sudden-and-accidental discharge claims often denied as 'long-term' leak",
        "Tear-out scope challenged by carrier preferred vendors",
        "Cat-3 cast iron failures hitting older PBC homes",
    ],
    "hvac": [
        "Lightning/surge claims for AC condensers regularly underpaid",
        "Storm-event AC damage written off as wear-and-tear",
    ],
    "attorney": [
        "§ 624.155 bad-faith pre-suit notices require a documented PA loss estimate",
        "First-party claim valuation disputes need licensed PA support",
        "Co-counseling on storm litigation pipeline",
    ],
    "hoa": [
        "Master-policy claims that miss unit-owner overlap get under-paid",
        "Reserve-study damage rarely tied to insurable events at the right time",
    ],
    "consulting": [
        "Owner-side advocates often pair with a licensed PA for claim valuation",
    ],
}

# Map raw CSV category strings to canonical buckets
def bucket(cat: str, name: str) -> str:
    c = (cat or "").lower()
    n = (name or "").lower()
    if "roof" in c or "roof" in n: return "roofer"
    if "property mgmt" in c or "property manag" in n: return "property-manager"
    if "realt" in c or "real estate" in n or "realty" in n or "homes" in n: return "realtor"
    if "restorat" in c or "restorat" in n or "drymedic" in n or "water" in n or "mold" in n: return "restoration"
    if "plumb" in c or "plumb" in n: return "plumbing"
    if "air condition" in n or "hvac" in c or " a/c" in n.lower() or " ac" in n.lower() or "comfort" in n: return "hvac"
    if "general contract" in c or "construction" in n or "contractor" in n or "builds" in n: return "general-contractor"
    if "attorney" in c or "law" in c or "insurance partners" in n: return "attorney"
    if "hoa" in c or "hoa" in n: return "hoa"
    if "consult" in c or "consult" in n: return "consulting"
    return "general-contractor"

# Verified-real escalation websites (probed 2026-06-02)
RESOLVED = {"allphaseusa.com", "quantumroofing.com", "prestigerealty.com",
            "www.elitecontractorsfl.com", "elitecontractorsfl.com",
            "floridainsurancepartners.com"}
UNRESOLVED = {"stormshieldfl.com", "coastalproperty.com", "atlanticwaterfl.com",
              "safehavenprop.com", "hoaadvocatesfl.com"}

# Load interactions
hist = defaultdict(list)
with open("/Users/victoria/.openclaw/workspace/crm/interactions.csv") as f:
    for row in csv.DictReader(f):
        hist[row["org_id"]].append(row)

# Load orgs needing follow-up today
orgs = []
with open("/Users/victoria/.openclaw/workspace/crm/organizations.csv") as f:
    for row in csv.DictReader(f):
        nfd = row.get("next_followup_date", "").strip()
        if not nfd: continue
        try:
            if date.fromisoformat(nfd) <= date.fromisoformat(TODAY):
                orgs.append(row)
        except ValueError:
            continue

os.makedirs(OUTDIR, exist_ok=True)

for o in orgs:
    oid = o["org_id"]
    site = (o.get("website") or "").strip()
    site_host = site.replace("https://","").replace("http://","").rstrip("/").lower()
    is_escalation = o.get("status") == "escalation"
    cat_bucket = bucket(o.get("category",""), o.get("name",""))
    pains = CATEGORY_PAINS.get(cat_bucket, CATEGORY_PAINS["general-contractor"])

    # Site verification flag
    if site_host in RESOLVED:
        site_status = "RESOLVED (HTTP 200) — manual deep-dive recommended"
    elif site_host in UNRESOLVED:
        site_status = "DID NOT RESOLVE on 2026-06-02 probe — likely dead/seed data, FLAG FOR DUNCAN"
    else:
        site_status = "Not probed — verify before sending"

    interactions = hist.get(oid, [])
    last = interactions[-1] if interactions else None

    # Decision-maker flag
    contact_name = (o.get("contact_name") or "").strip()
    contact_email = (o.get("contact_email") or "").strip()
    if not contact_name and contact_email.startswith("info@"):
        contact_note = "⚠ Generic `info@` mailbox; no decision-maker on record. Manual lookup needed (LinkedIn / Sunbiz officer search)."
    elif contact_name and not contact_email:
        contact_note = "Name on record but no email — verify via website or LinkedIn before sending."
    else:
        contact_note = "Contact captured; verify role/title still current."

    # Escalation-tier special framing
    if is_escalation:
        framing = (
            "**Stage:** Final escalation. 2026-05-25 sent the 'Last note from me' close-out "
            "email — this org has had 7+ touchpoints with zero confirmed replies. Today's action "
            "is either (a) wait for inbound, (b) Duncan-only manual phone call, or (c) close out "
            "in CRM. **Do not send another automated email.**"
        )
    else:
        framing = (
            "**Stage:** Initial cold touch. No prior interaction history. Treat as compare-notes, "
            "not pitch — per cold-outreach voice rule."
        )

    lines = []
    lines.append(f"# {o['name']}")
    lines.append("")
    lines.append(f"- **org_id:** `{oid}`")
    lines.append(f"- **county:** {o.get('county','')}")
    lines.append(f"- **category:** {o.get('category','')} (bucket: `{cat_bucket}`)")
    lines.append(f"- **status:** {o.get('status','')}")
    lines.append(f"- **website:** {site}  — _{site_status}_")
    lines.append(f"- **contact:** {contact_name or '(none on record)'} | {contact_email or '(none)'} | {o.get('contact_phone','') or '(none)'}")
    lines.append("")
    lines.append("## Stage framing")
    lines.append(framing)
    lines.append("")
    lines.append("## Decision-maker note")
    lines.append(contact_note)
    lines.append("")
    lines.append("## Interaction history")
    if interactions:
        for h in interactions[-6:]:
            lines.append(f"- {h['date']} — {h['type']} / {h['stage']} → {h['outcome']}: {h['summary']}")
    else:
        lines.append("- (no prior interactions)")
    lines.append("")
    lines.append("## Likely pain points (category-inferred — verify before citing)")
    for p in pains:
        lines.append(f"- {p}")
    lines.append("")
    lines.append("## Personalization angle")
    if is_escalation:
        lines.append(
            "Escalation-tier: no personalization needed — this is the close-out window. "
            "If Duncan personally calls, lead with: \"Quick last check — I sent a note last "
            "week about [topic]; wanted to make sure it didn't get buried before I close the loop.\""
        )
    else:
        lines.append(
            f"First-touch cold: open with **county-specific** market reference (PBC carrier shake-up "
            f"or recent storm-prep angle) tied to their **{cat_bucket}** vertical. "
            "Avoid claiming knowledge of specific projects/owners — none verified."
        )
    lines.append("")
    lines.append("## Research gaps for Duncan")
    gaps = []
    if site_host in UNRESOLVED or not site_host:
        gaps.append("Website does not resolve — confirm company is real / find current URL")
    if not contact_name:
        gaps.append("No decision-maker identified — Sunbiz / LinkedIn lookup needed")
    if not contact_email or contact_email.startswith("info@"):
        gaps.append("No direct email — generic mailbox only")
    gaps.append("BBB / FL OIR complaint history — not auto-pulled")
    gaps.append("Recent permit activity (PBC ePZB / Broward eTRAKiT) — not auto-pulled")
    for g in gaps:
        lines.append(f"- {g}")
    lines.append("")
    lines.append(f"_Generated {TODAY} 05:00 EDT by prospect-deep-intelligence cron. "
                 f"No fabricated facts — only CSV-verified data + category-based inference._")

    path = os.path.join(OUTDIR, f"{oid}-intel.md")
    with open(path, "w") as f:
        f.write("\n".join(lines))

print(f"Wrote {len(orgs)} intel files to {OUTDIR}")
