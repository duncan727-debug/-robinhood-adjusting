#!/usr/bin/env python3
"""Scrape each prospect website for FB Page URL + IG handle in footer/links."""
import csv, re, sys, urllib.request, ssl

INPUT = "/Users/victoria/.openclaw/workspace/crm/social_outreach_targets_seed.csv"
OUTPUT = "/Users/victoria/.openclaw/workspace/crm/social_outreach_targets.csv"
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605"}
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

EXCLUDE_FB = {"pages","groups","sharer","tr","help","login","watch","events","plugins","dialog","photo.php","permalink.php","sharing","share","privacy","policies","l.php","reg","recover","careers","business"}
EXCLUDE_IG = {"p","reel","explore","direct","accounts","tv","developer","about"}

def fetch(url):
    if not url.startswith("http"):
        url = "https://" + url
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=12, context=CTX) as r:
            return r.read().decode("utf-8", errors="ignore")
    except Exception as e:
        return ""

def find_fb(html):
    for m in re.finditer(r'(?:https?:)?//(?:www\.|m\.|web\.)?facebook\.com/([A-Za-z0-9._-]{3,80})/?', html, re.I):
        h = m.group(1).split("?")[0].split("/")[0]
        if h.lower() in EXCLUDE_FB or h.isdigit() and len(h) > 12:
            continue
        return f"https://facebook.com/{h}"
    return ""

def find_ig(html):
    for m in re.finditer(r'(?:https?:)?//(?:www\.)?instagram\.com/([A-Za-z0-9._]{2,40})/?', html, re.I):
        h = m.group(1).split("?")[0].split("/")[0]
        if h.lower() in EXCLUDE_IG:
            continue
        return "@" + h
    return ""

out = []
with open(INPUT) as f:
    rd = csv.reader(f)
    for row in rd:
        if len(row) < 9: continue
        company = row[0][:45]
        website = row[6]
        html = fetch(website)
        fb = find_fb(html)
        ig = find_ig(html)
        # If homepage didn't have it, try /contact and /about
        if not (fb and ig):
            for path in ("/contact", "/about", "/contact-us", "/about-us"):
                if fb and ig: break
                html2 = fetch(website.rstrip("/") + path)
                if not fb: fb = find_fb(html2)
                if not ig: ig = find_ig(html2)
        flag = ("FB✓" if fb else "  ") + ("IG✓" if ig else "  ")
        print(f"  {flag} [{company}]", file=sys.stderr, flush=True)
        out.append(row + [fb, ig])

cols = ["company_name","contact_email","contact_name","phone","county","category","website","first_contact_date","status","fb_page","ig_handle"]
with open(OUTPUT, "w") as f:
    wr = csv.writer(f)
    wr.writerow(cols)
    wr.writerows(out)
fb_count = sum(1 for r in out if r[9])
ig_count = sum(1 for r in out if r[10])
print(f"\nDone: {len(out)} rows | {fb_count} FB | {ig_count} IG | -> {OUTPUT}", file=sys.stderr)
