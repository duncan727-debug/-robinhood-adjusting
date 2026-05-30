#!/usr/bin/env python3
"""Verification gate for prospect records before they're written to HubSpot or
turned into Duncan-facing drafts.

Background: 2026-05-06 prospecting subagent fabricated company names + contact
names + `info@<fake-domain>` emails. We caught 5 of 35 only when they bounced;
2 of those were entirely invented. Per Duncan 2026-05-27, no prospect record
flows into HubSpot or into a personalized draft without passing these checks.

Checks run per record:
  1. Email domain has an MX record (`dig +short MX <domain>`).
  2. Company exists in FL Sunbiz (search by name; soft check — absent doesn't
     prove fake, but absent + bogus email is conclusive).
  3. Email is sourced (`source` field set to "scraped" or "verified_url" or
     "directory"). "best-guess" / "info@" patterns without a source = reject.

CLI:
  python3 scripts/verify_prospect.py <input.json> [--out <output.json>]

Input JSON: [{"name":"...","email":"...","company":"...","website":"...","source":"..."}, ...]

Output JSON augments each row with:
  verdict: "verified" | "phone-only" | "rejected"
  reasons: ["mx_fail", "sunbiz_missing", "email_unsourced", ...]
  mx_ok: true|false
  sunbiz_found: true|false|null  (null = check skipped/failed)

Only `verified` rows are safe to upload + use in personalized drafts.
`phone-only` (no email but co + person verifiable) → CRM yes, CALL task yes,
   email no.
`rejected` → do not write to CRM at all.
"""
import json, subprocess, sys, re, urllib.request, urllib.parse, ssl, time
from pathlib import Path

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

ALLOWED_SOURCES = {"scraped", "verified_url", "directory", "bbb", "sunbiz", "press_release"}


def mx_resolves(domain):
    if not domain:
        return False
    try:
        r = subprocess.run(["dig", "+short", "MX", domain],
                           capture_output=True, text=True, timeout=6)
        return bool(r.stdout.strip())
    except Exception:
        return False


def sunbiz_has(company_name):
    """Returns True if Sunbiz returns at least one match for the company name.
    Returns None on lookup failure (don't conclude either way)."""
    if not company_name:
        return None
    try:
        q = urllib.parse.quote(company_name.upper())
        url = f"https://search.sunbiz.org/Inquiry/CorporationSearch/SearchResults?searchNameOrder={q}&searchTerm={q}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10, context=SSL_CTX) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
        # The results page shows entity links; "No Records Found" appears when empty
        if "No Records Found" in html or "No matching" in html.lower():
            return False
        # crude positive signal: results table contains tr.SearchResultsTableRow or detail links
        return "InquiryType=EntityName" in html or "/Inquiry/CorporationSearch/SearchResultDetail" in html
    except Exception:
        return None


def domain_from(email_or_url):
    if not email_or_url:
        return ""
    s = email_or_url.lower().strip()
    if "@" in s:
        return s.split("@", 1)[1]
    s = re.sub(r"^https?://", "", s)
    return s.split("/")[0].lstrip("www.")


INFO_PATTERN = re.compile(r"^(info|contact|hello|admin|office|sales)@", re.I)


def classify(row):
    reasons = []
    email = (row.get("email") or "").strip().lower()
    company = (row.get("company") or "").strip()
    source = (row.get("source") or "").strip().lower()

    mx_ok = None
    sunbiz_found = None

    if email:
        dom = domain_from(email)
        mx_ok = mx_resolves(dom)
        if not mx_ok:
            reasons.append("mx_fail")
        if INFO_PATTERN.match(email) and source not in ALLOWED_SOURCES:
            reasons.append("email_unsourced_infoat_pattern")

    if company:
        sunbiz_found = sunbiz_has(company)
        if sunbiz_found is False:
            reasons.append("sunbiz_missing")

    # Verdict logic
    if not email:
        # phone-only path is okay IF company and contact name are present and
        # company has SOME positive signal (sunbiz_found True or unknown)
        if company and sunbiz_found is not False:
            verdict = "phone-only"
        else:
            verdict = "rejected"
            reasons.append("no_email_and_no_company_verification")
    elif "mx_fail" in reasons:
        verdict = "rejected"
    elif "email_unsourced_infoat_pattern" in reasons:
        verdict = "rejected"
    elif sunbiz_found is False:
        # Email resolves but company isn't in FL — could be out-of-state OK,
        # but flag for human review
        verdict = "rejected"
    else:
        verdict = "verified"

    out = dict(row)
    out.update({
        "verdict": verdict,
        "reasons": reasons,
        "mx_ok": mx_ok,
        "sunbiz_found": sunbiz_found,
    })
    return out


def main():
    if len(sys.argv) < 2:
        print("usage: verify_prospect.py <input.json> [--out <output.json>]", file=sys.stderr)
        sys.exit(2)
    inp = Path(sys.argv[1])
    out_path = None
    if "--out" in sys.argv:
        out_path = Path(sys.argv[sys.argv.index("--out") + 1])

    rows = json.load(inp.open())
    results = []
    counts = {"verified": 0, "phone-only": 0, "rejected": 0}
    for i, r in enumerate(rows):
        c = classify(r)
        counts[c["verdict"]] += 1
        results.append(c)
        print(f"  [{i+1}/{len(rows)}] {r.get('name','?')[:30]:30s} | {r.get('email','-')[:35]:35s} | {c['verdict']:10s} | {','.join(c['reasons'])}")
        time.sleep(0.4)  # be polite to Sunbiz

    print(f"\nVerdicts: verified={counts['verified']}  phone-only={counts['phone-only']}  rejected={counts['rejected']}")
    if out_path:
        out_path.write_text(json.dumps(results, indent=2))
        print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
