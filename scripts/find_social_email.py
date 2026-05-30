#!/usr/bin/env python3
"""Social-profile email fallback for prospect enrichment.

Used by enrich_before_upload.py + enrich_emails_from_websites.py as the LAST
ditch before giving up on email discovery. Replaces the old `info@{domain}`
best-guess fallback (killed 2026-05-29) because franchise sites
(allstate.com, brightway.com) route info@ to corporate, not the local agent.

Strategy — for franchise/agency cases, the operator's email often lives on
their public Facebook page About section. Instagram bios occasionally too.
We try a few candidate URLs and regex emails out of the rendered HTML.

Public API:
    find_email_via_social(company_name, website=None) -> (email, source) | (None, None)
        source ∈ {"facebook", "instagram"}

This is intentionally NOT a guesser — it only returns emails it actually
finds in publicly-rendered profile HTML. No `info@` fabrication.
"""
import re
import ssl
import time
import urllib.parse
import urllib.request

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
SKIP_EMAIL = re.compile(
    r"noreply|no-reply|donotreply|example\.com|sentry\.|wix\.|squarespace|"
    r"wordpress|godaddy|hubspot|facebook\.com|instagram\.com|fb\.com|"
    r"@w3\.org|@schema|@sentry|fbcdn|cdninstagram",
    re.I,
)
PREFER_EMAIL = re.compile(r"^(info|contact|hello|office|admin|sales|estimates?|quotes?)@", re.I)

_ssl_ctx = ssl.create_default_context()
_ssl_ctx.check_hostname = False
_ssl_ctx.verify_mode = ssl.CERT_NONE

UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1"


def _fetch(url, timeout=8):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"})
        with urllib.request.urlopen(req, timeout=timeout, context=_ssl_ctx) as r:
            return r.read().decode("utf-8", errors="ignore")
    except Exception:
        return ""


def _slugs(company_name):
    """Generate candidate URL slugs from a company name.
    "AAA Roofing & Repair, Inc." → ["aaaroofingrepair", "aaaroofingrepairinc", "aaa-roofing-repair"]
    """
    if not company_name:
        return []
    n = company_name.lower()
    # Strip corporate suffixes
    n = re.sub(r"[,.]\s*(llc|inc|corp|co|ltd|pa|llp)\.?\s*$", "", n)
    n = re.sub(r"&", " and ", n)
    # Keep only letters/numbers/spaces/dashes
    n = re.sub(r"[^a-z0-9\s\-]", "", n)
    words = n.split()
    if not words:
        return []
    return list(dict.fromkeys([
        "".join(words),                       # aaaroofingrepair
        "-".join(words),                      # aaa-roofing-repair
        ".".join(words),                      # aaa.roofing.repair
        words[0],                             # aaa
        words[0] + (words[1] if len(words) > 1 else ""),
    ]))


def _extract_emails(html, company_domain=None):
    """Pull email candidates, filtered + ranked. Returns best email or None."""
    if not html:
        return None
    raw = [m.group(0).lower() for m in EMAIL_RE.finditer(html)]
    candidates = [e for e in raw if not SKIP_EMAIL.search(e)]
    if not candidates:
        return None
    # Prefer emails matching the company's own website domain
    if company_domain:
        dom_match = [e for e in candidates if company_domain in e]
        if dom_match:
            preferred = [e for e in dom_match if PREFER_EMAIL.match(e)]
            return (preferred or sorted(dom_match))[0]
    # Then prefer typical business-contact patterns
    preferred = [e for e in candidates if PREFER_EMAIL.match(e)]
    if preferred:
        return preferred[0]
    return sorted(set(candidates))[0]


def _company_domain(website):
    if not website:
        return None
    d = re.sub(r"^https?://", "", website).split("/")[0].strip()
    d = re.sub(r"^www\.", "", d, flags=re.IGNORECASE)
    return d.lower() if d and "." in d and "google" not in d else None


def _try_facebook(company_name, company_domain):
    """Walk FB candidate URLs (mobile site renders less JS) and parse About for email."""
    for slug in _slugs(company_name)[:3]:
        for path in [f"/{slug}/about", f"/{slug}"]:
            html = _fetch(f"https://m.facebook.com{path}")
            time.sleep(0.4)
            if not html or "Page Not Found" in html or "isn't available" in html:
                continue
            email = _extract_emails(html, company_domain)
            if email:
                return email
    return None


def _try_instagram(company_name, company_domain):
    """IG profiles render contact email via the static profile HTML rarely; try anyway."""
    for slug in _slugs(company_name)[:3]:
        html = _fetch(f"https://www.instagram.com/{slug}/")
        time.sleep(0.4)
        if not html or "Sorry, this page" in html or "Page Not Found" in html:
            continue
        email = _extract_emails(html, company_domain)
        if email:
            return email
    return None


def find_email_via_social(company_name, website=None):
    """Public entry point. Returns (email, source) or (None, None)."""
    domain = _company_domain(website)

    fb = _try_facebook(company_name, domain)
    if fb:
        return fb, "facebook"

    ig = _try_instagram(company_name, domain)
    if ig:
        return ig, "instagram"

    return None, None


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("usage: find_social_email.py <company_name> [website]", file=sys.stderr)
        sys.exit(2)
    name = sys.argv[1]
    site = sys.argv[2] if len(sys.argv) > 2 else None
    email, source = find_email_via_social(name, site)
    if email:
        print(f"{source}: {email}")
    else:
        print("not found")
