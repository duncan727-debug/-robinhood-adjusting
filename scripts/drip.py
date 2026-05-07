#!/usr/bin/env python3
"""
Email drip sequence: 4-touch welcome series for new newsletter subscribers.
  confirm  (0-24h after signup):  Confirmation + "first brief tomorrow"
  day3     (3-5 days):            Value content + multiple-choice qualifying question
  day7     (7-9 days):            Personal touch from Duncan
  day10    (10-12 days):          Final nurture / call to action

Tracks state in HubSpot contact property 'drip_step'.
Qualifying answers stored in 'qualifying_answer' via the qualify Netlify function.
Sends via Gmail SMTP. Run daily at 9am Mon-Sat.
"""

import json
import os
import re
import smtplib
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

WORKSPACE = Path("/Users/victoria/.openclaw/workspace")
CONFIG_FILE = WORKSPACE / "config" / ".services-config.txt"
LOG_PATH = WORKSPACE / "scripts" / "drip.log"

GMAIL_USER = "duncanlittlejohn727@gmail.com"
FROM_NAME = "Duncan Littlejohn | Robinhood Adjusting"
SITE_URL = "https://robinhoodadjusting.com"
PHONE = "561-772-7528"
QUALIFY_URL = f"{SITE_URL}/.netlify/functions/qualify"

LIST_MAP = {"18": "homeowner", "19": "service-provider", "20": "real-estate"}

_TOKEN = None


# ─── credentials ──────────────────────────────────────────────────────────────

def load_credentials():
    content = CONFIG_FILE.read_text()
    m = re.search(r"Gmail App Password.*?:\s*([a-z]{4} [a-z]{4} [a-z]{4} [a-z]{4})", content)
    gmail_pw = m.group(1) if m else None
    if not gmail_pw:
        sys.exit("ERROR: Gmail App Password not found in config.")
    hs_token = os.environ.get("HUBSPOT_API_KEY", "")
    if not hs_token:
        setup = WORKSPACE / "scripts" / "setup-hubspot-lists.py"
        m2 = re.search(r'TOKEN\s*=\s*"([^"]+)"', setup.read_text())
        hs_token = m2.group(1) if m2 else ""
    if not hs_token:
        sys.exit("ERROR: HUBSPOT_API_KEY not set.")
    return gmail_pw, hs_token


# ─── hubspot helpers ──────────────────────────────────────────────────────────

def hs(method, path, body=None, retries=3):
    url = f"https://api.hubapi.com{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {_TOKEN}")
    req.add_header("Content-Type", "application/json")
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            raw = b""
            try:
                raw = e.read()
            except Exception:
                pass
            if e.code == 429:
                time.sleep(2 ** attempt)
                continue
            try:
                return e.code, json.loads(raw)
            except Exception:
                return e.code, {}
    return 0, {}


def ensure_properties():
    for prop in [
        {"name": "drip_step",           "label": "Drip Step"},
        {"name": "newsletter_category", "label": "Newsletter Category"},
        {"name": "qualifying_answer",   "label": "Qualifying Answer"},
    ]:
        status, _ = hs("GET", f"/crm/v3/properties/contacts/{prop['name']}")
        if status == 404:
            hs("POST", "/crm/v3/properties/contacts", {
                "name":      prop["name"],
                "label":     prop["label"],
                "type":      "string",
                "fieldType": "text",
                "groupName": "contactinformation",
            })


def get_contacts_by_list():
    """Return {contact_id: category} for all subscriber list members."""
    contacts = {}
    for list_id, category in LIST_MAP.items():
        after = None
        while True:
            url = f"/crm/v3/lists/{list_id}/memberships?limit=100"
            if after:
                url += f"&after={after}"
            status, data = hs("GET", url)
            if status != 200:
                break
            for member in data.get("results", []):
                cid = str(member.get("recordId", ""))
                if cid and cid not in contacts:
                    contacts[cid] = category
            paging = data.get("paging", {}).get("next", {})
            after = paging.get("after") if paging else None
            if not after:
                break
            time.sleep(0.05)
    return contacts


def get_contact_props(contact_id):
    props = "email,firstname,newsletter_category,drip_step,createdate"
    status, data = hs("GET", f"/crm/v3/objects/contacts/{contact_id}?properties={props}")
    return data.get("properties", {}) if status == 200 else None


def set_drip_step(contact_id, step):
    hs("PATCH", f"/crm/v3/objects/contacts/{contact_id}",
       {"properties": {"drip_step": step}})


def days_since_signup(createdate_str):
    try:
        ts = int(createdate_str) / 1000
        created = datetime.fromtimestamp(ts, tz=timezone.utc)
        return (datetime.now(tz=timezone.utc) - created).total_seconds() / 86400
    except Exception:
        return None


# ─── email helpers ────────────────────────────────────────────────────────────

def wrap_email(body_html, subject):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{subject}</title>
</head>
<body style="margin:0;padding:0;background:#f5f5f5;font-family:Georgia,'Times New Roman',serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f5f5f5;padding:20px 0;">
  <tr><td align="center">
    <table width="620" cellpadding="0" cellspacing="0" style="background:#fff;max-width:620px;width:100%;">
      <tr><td style="background:#0f2d4a;padding:28px 24px;text-align:center;border-bottom:5px solid #c9922a;">
        <img src="https://robinhoodadjusting.com/logo-dark.svg" alt="Robinhood Adjusting" width="280" height="60" style="display:inline-block;max-width:100%;height:auto;">
      </td></tr>
      <tr><td style="padding:32px 28px;font-size:16px;line-height:1.75;color:#222;">
        {body_html}
      </td></tr>
      <tr><td style="background:#0d1b2e;padding:20px 24px;border-top:4px solid #c41e3a;">
        <p style="color:#999;font-size:12px;margin:0;font-family:Arial,sans-serif;text-align:center;">
          Robinhood Adjusting · Wellington, FL ·
          <a href="{SITE_URL}" style="color:#c41e3a;">{SITE_URL.replace('https://','')}</a>
        </p>
        <p style="color:#666;font-size:11px;margin:8px 0 0;font-family:Arial,sans-serif;text-align:center;">
          You received this because you subscribed at robinhoodadjusting.com.
          Reply with "unsubscribe" to be removed.
        </p>
      </td></tr>
    </table>
  </td></tr>
</table>
</body>
</html>"""


def btn(url, label):
    return (f'<p><a href="{url}" style="display:inline-block;background:#c41e3a;color:#fff;'
            f'padding:12px 24px;text-decoration:none;border-radius:4px;font-family:Arial,sans-serif;'
            f'font-size:14px;font-weight:bold;">{label}</a></p>')


def link(url, label):
    return f'<a href="{url}" style="color:#c41e3a;">{label}</a>'


def mc_buttons(email, choices):
    """Render multiple-choice answer buttons for qualifying question."""
    import urllib.parse
    rows = ""
    for code, label in choices:
        encoded_email = urllib.parse.quote(email, safe="")
        encoded_answer = urllib.parse.quote(code, safe="")
        url = f"{QUALIFY_URL}?email={encoded_email}&answer={encoded_answer}"
        rows += (
            f'<tr><td style="padding:6px 0;">'
            f'<a href="{url}" style="display:block;background:#f0f4f8;border:1px solid #c41e3a;'
            f'color:#0f2d4a;padding:12px 18px;text-decoration:none;border-radius:4px;'
            f'font-family:Arial,sans-serif;font-size:14px;font-weight:bold;">'
            f'&#10003; {label}</a></td></tr>'
        )
    return f'<table cellpadding="0" cellspacing="0" style="width:100%;margin:16px 0;">{rows}</table>'


# ─── email templates ──────────────────────────────────────────────────────────

def TEMPLATES(email):
    """Return template dict keyed by (category, step). email is needed for MC button links."""

    return {
        # ── HOMEOWNERS ──────────────────────────────────────────────────────────

        ("homeowner", "confirm"): {
            "subject": "You're subscribed — South Florida Property Intelligence",
            "body": lambda name: f"""
<p>Hi {name},</p>
<p>You're confirmed. Starting tomorrow morning you'll receive the <strong>South Florida Property Intelligence Brief</strong> — daily market updates, carrier news, and plain-language breakdowns of what's affecting homeowners in our area.</p>
<p>Each brief is built for property owners who want to stay ahead of the market and understand what's happening with their insurance before they need it.</p>
<p>A few things worth bookmarking:</p>
<ul>
  <li>{link(SITE_URL+'/resources/first-48-hours.html','First 48 Hours After Storm Damage — What to Do')}</li>
  <li>{link(SITE_URL+'/providers/index.html','Trusted Provider Directory — Vetted contractors across South Florida')}</li>
</ul>
{btn(SITE_URL, 'Visit Robinhood Adjusting')}
<p>Talk soon,<br>
— Duncan Littlejohn<br>
Public Adjuster, Robinhood Adjusting<br>
Wellington, FL · {PHONE}</p>
""",
        },

        ("homeowner", "day3"): {
            "subject": "The move most homeowners miss after a storm",
            "body": lambda name: f"""
<p>Hi {name},</p>
<p>Most homeowners wait too long to document damage — and it costs them. Insurance carriers send their adjuster within days of a claim. If you haven't documented independently before that visit, you're already behind.</p>
<p>I put together a free guide on exactly what to do in the first 48 hours:</p>
{btn(SITE_URL+'/resources/first-48-hours.html', 'Read: First 48 Hours After Storm Damage')}
<p>One quick question — it helps me send you information that's actually relevant:</p>
<p style="background:#f8f4ee;border-left:4px solid #c41e3a;padding:14px 18px;margin:20px 0;">
  <strong>What best describes your current situation?</strong><br>
  <span style="font-size:14px;color:#555;">Click to answer — takes one second, updates your profile automatically.</span>
</p>
{mc_buttons(email, [
    ("open-claim",    "I have an open claim right now"),
    ("denied-claim",  "My claim was denied or underpaid"),
    ("filing-claim",  "I'm about to file a claim"),
    ("preparing",     "No active claim — just staying informed"),
])}
<p>— Duncan<br>
{PHONE} · <a href="{SITE_URL}" style="color:#c41e3a;">{SITE_URL.replace('https://','')}</a></p>
""",
        },

        ("homeowner", "day7"): {
            "subject": "Checking in — Duncan Littlejohn, Robinhood Adjusting",
            "body": lambda name: f"""
<p>Hi {name},</p>
<p>I wanted to reach out personally.</p>
<p>I work with homeowners across South Florida who feel like they didn't get a fair shake from their insurance company. Some have open claims. Some have had claims denied. Some just want to understand their policy before storm season gets here.</p>
<p>If any of that sounds familiar, I'm just a reply away. No forms, no commitment — just a straight conversation about what I can do for you.</p>
<p><strong>Direct line: {PHONE}</strong><br>
Or reply right here and we'll go from there.</p>
<p>— Duncan Littlejohn<br>
Public Adjuster, Robinhood Adjusting<br>
Wellington, FL</p>
""",
        },

        ("homeowner", "day10"): {
            "subject": "Storm season is here — where do you stand?",
            "body": lambda name: f"""
<p>Hi {name},</p>
<p>Peak season is approaching, and I want to make sure you're not caught flat-footed.</p>
<p>The most common mistake I see: homeowners find out their policy has gaps <em>after</em> a storm hits. By then, it's too late to fix it — and the insurance company knows it.</p>
<p>If you haven't done a policy review recently, I'm happy to walk through it with you. No cost, no obligation. I'll tell you exactly what you have, what you're missing, and what carriers are likely to push back on in your area.</p>
{btn(SITE_URL, 'Learn How We Can Help')}
<p>Or just call me directly: <strong>{PHONE}</strong></p>
<p>— Duncan Littlejohn<br>
Public Adjuster, Robinhood Adjusting<br>
Wellington, FL</p>
""",
        },

        # ── SERVICE PROVIDERS ──────────────────────────────────────────────────

        ("service-provider", "confirm"): {
            "subject": "You're subscribed — South Florida Property & Insurance Intelligence",
            "body": lambda name: f"""
<p>Hi {name},</p>
<p>You're confirmed. Starting tomorrow morning you'll receive the <strong>South Florida Trade Professional Brief</strong> — daily updates on carrier behavior, storm activity, contractor demand, and the insurance-adjacent news that keeps your business ahead of the market.</p>
<p>Our provider directory is live on the site. Vetted professionals listed by county and trade. If you'd like to be listed, reply and let me know your trade and service area.</p>
{btn(SITE_URL+'/providers/index.html', 'View the Provider Directory')}
<p>Talk soon,<br>
— Duncan Littlejohn<br>
Public Adjuster, Robinhood Adjusting<br>
Wellington, FL · {PHONE}</p>
""",
        },

        ("service-provider", "day3"): {
            "subject": "How our referral relationship works (no paperwork)",
            "body": lambda name: f"""
<p>Hi {name},</p>
<p>Quick note on how we work with trade professionals:</p>
<p>When your customer has insurance-covered damage, you refer them to me. I handle everything — the inspection, documentation, and carrier negotiation. If I recover more than the initial offer, I take a percentage of the difference. If I don't, your client owes nothing.</p>
<p><strong>Your customer gets a better outcome. You're the person who made it happen.</strong></p>
<p>No formal agreement, no exclusivity, no paperwork. Just good referrals in both directions.</p>
<p>One quick question — helps me match you with the right opportunities:</p>
<p style="background:#f8f4ee;border-left:4px solid #c41e3a;padding:14px 18px;margin:20px 0;">
  <strong>What are you primarily looking for?</strong><br>
  <span style="font-size:14px;color:#555;">Click to answer — one second, updates your profile automatically.</span>
</p>
{mc_buttons(email, [
    ("homeowner-referrals", "Homeowner referrals from the PA network"),
    ("pa-partnership",      "PA partnership — I'll refer clients with claims"),
    ("both",                "Both referrals and partnerships"),
    ("directory-listing",   "Directory listing and market intelligence only"),
])}
<p>Want to discuss this further before you decide? <a href="https://calendly.com/duncanlittlejohn727/30min" style="color:#c41e3a;">Pick a time to connect.</a></p>
<p>— Duncan<br>
{PHONE} · <a href="{SITE_URL}" style="color:#c41e3a;">{SITE_URL.replace('https://','')}</a></p>
""",
        },

        ("service-provider", "day7"): {
            "subject": "Let's connect — Duncan Littlejohn, Robinhood Adjusting",
            "body": lambda name: f"""
<p>Hi {name},</p>
<p>I'd love to know more about your business and see where there's a natural fit.</p>
<p>Trade professionals who work in insurance-adjacent situations are exactly the partners I want long-term relationships with. When my clients need your services, I want to send them to people I trust. When your clients have a claim situation, I want to be the person you think of first.</p>
<p>If that sounds like a conversation worth having, pick a time that works for you:</p>
<p><a href="https://calendly.com/duncanlittlejohn727/30min" style="display:inline-block;background:#c41e3a;color:#fff;padding:12px 28px;text-decoration:none;border-radius:4px;font-family:Arial,sans-serif;font-size:14px;font-weight:bold;">Book a time to talk</a></p>
<p>Or reach out directly: <strong>{PHONE}</strong></p>
<p>— Duncan Littlejohn<br>
Public Adjuster, Robinhood Adjusting<br>
Wellington, FL</p>
""",
        },

        ("service-provider", "day10"): {
            "subject": "Busy season is starting — are you positioned for it?",
            "body": lambda name: f"""
<p>Hi {name},</p>
<p>Storm season drives more insurance-related work than any other period in South Florida. Roofing, mitigation, restoration, general contracting — demand spikes fast and the insurance process gets complicated.</p>
<p>Contractors who have a PA relationship in their back pocket move faster: they can guide clients through the claim, get scopes approved faster, and close more jobs that would otherwise stall on "the insurance company said no."</p>
<p>If you want to build that relationship before the season hits, let's talk now.</p>
<p><strong>{PHONE}</strong> or just reply here.</p>
{btn(SITE_URL+'/providers/index.html', 'View the Provider Directory')}
<p>— Duncan Littlejohn<br>
Public Adjuster, Robinhood Adjusting<br>
Wellington, FL</p>
""",
        },

        # ── REAL ESTATE PROFESSIONALS ──────────────────────────────────────────

        ("real-estate", "confirm"): {
            "subject": "You're subscribed — South Florida Property Intelligence",
            "body": lambda name: f"""
<p>Hi {name},</p>
<p>You're confirmed. Starting tomorrow morning you'll receive the <strong>South Florida Real Estate & Insurance Brief</strong> — daily coverage of market shifts, carrier behavior, regulatory changes, and property-level intelligence that affects transactions and your clients.</p>
<p>I work with agents and brokers across South Florida who want a PA they can refer clients to when insurance issues surface — before closing, after closing, or during active claims.</p>
{btn(SITE_URL, 'Visit Robinhood Adjusting')}
<p>Talk soon,<br>
— Duncan Littlejohn<br>
Public Adjuster, Robinhood Adjusting<br>
Wellington, FL · {PHONE}</p>
""",
        },

        ("real-estate", "day3"): {
            "subject": "When a client's insurance claim affects the deal",
            "body": lambda name: f"""
<p>Hi {name},</p>
<p>Something I hear from agents regularly: a deal stalls or falls apart because of an open claim, an unresolved denial, or damage that surfaces during inspection.</p>
<p>A public adjuster can often move that needle faster than anyone else in the transaction. Whether your buyer is inheriting a poorly documented loss or your seller needs a claim resolved before closing, I can assess the situation quickly and tell you what's realistic.</p>
<p>One quick question — helps me understand what you're dealing with out there:</p>
<p style="background:#f8f4ee;border-left:4px solid #c41e3a;padding:14px 18px;margin:20px 0;">
  <strong>How often do insurance issues come up with your clients?</strong><br>
  <span style="font-size:14px;color:#555;">Click to answer — one second, updates your profile automatically.</span>
</p>
{mc_buttons(email, [
    ("frequent",          "Frequently — multiple times per month"),
    ("occasional",        "Occasionally — a few times per year"),
    ("active-situation",  "I have an active client situation right now"),
    ("rare",              "Rarely or never"),
])}
<p>— Duncan<br>
{PHONE} · <a href="{SITE_URL}" style="color:#c41e3a;">{SITE_URL.replace('https://','')}</a></p>
""",
        },

        ("real-estate", "day7"): {
            "subject": "A PA you can actually refer your clients to",
            "body": lambda name: f"""
<p>Hi {name},</p>
<p>I work with RE professionals across South Florida who refer their clients to me when insurance issues come up — before closing, after closing, or during active claims.</p>
<p>I make it simple: one call, I assess the situation, I tell your client exactly what I can do and what it costs. No pressure, no obligation. If I can help, great. If I can't, I'll tell you that too.</p>
<p>If this sounds like something useful to have in your back pocket, reply here and let's connect.</p>
<p><strong>{PHONE}</strong></p>
<p>— Duncan Littlejohn<br>
Public Adjuster, Robinhood Adjusting<br>
Wellington, FL</p>
""",
        },

        ("real-estate", "day10"): {
            "subject": "Storm season and your listings — a heads up",
            "body": lambda name: f"""
<p>Hi {name},</p>
<p>As storm season ramps up, insurance issues are going to hit transactions harder and faster. Buyers getting cold feet over carrier options. Sellers with undisclosed claims that surface during inspection. Post-closing disputes that circle back to you.</p>
<p>Having a PA in your corner before those situations hit is a lot easier than scrambling after. I can move quickly when a deal is on the line — I understand timelines and I know how to get answers fast from carriers.</p>
<p>If you want to set up a quick call and see if there's a fit, I'm easy to reach.</p>
<p><strong>{PHONE}</strong> or reply here.</p>
{btn(SITE_URL, 'Learn About Our Work')}
<p>— Duncan Littlejohn<br>
Public Adjuster, Robinhood Adjusting<br>
Wellington, FL</p>
""",
        },
    }


# ─── sending ──────────────────────────────────────────────────────────────────

def send_email(to_email, subject, html, gmail_pw):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{FROM_NAME} <{GMAIL_USER}>"
    msg["To"] = to_email
    msg["Reply-To"] = GMAIL_USER
    msg.attach(MIMEText(html, "html"))
    with smtplib.SMTP("smtp.gmail.com", 587) as smtp:
        smtp.starttls()
        smtp.login(GMAIL_USER, gmail_pw)
        smtp.sendmail(GMAIL_USER, to_email, msg.as_string())


# ─── main ─────────────────────────────────────────────────────────────────────

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_PATH, "a") as f:
        f.write(line + "\n")


def main():
    global _TOKEN
    log("=== Drip sequence run start ===")

    gmail_pw, hs_token = load_credentials()
    _TOKEN = hs_token

    ensure_properties()

    contacts_by_id = get_contacts_by_list()
    log(f"Found {len(contacts_by_id)} subscriber contacts across all lists")

    sent = skipped = errors = 0

    for contact_id, list_category in contacts_by_id.items():
        props = get_contact_props(contact_id)
        if not props:
            errors += 1
            continue

        email = (props.get("email") or "").strip().lower()
        if not email:
            skipped += 1
            continue

        first_name = ((props.get("firstname") or "").strip()) or "there"
        category = ((props.get("newsletter_category") or "").strip()) or list_category
        drip_step = (props.get("drip_step") or "").strip()
        createdate = props.get("createdate") or ""

        age_days = days_since_signup(createdate)
        if age_days is None:
            skipped += 1
            continue

        # Determine which touch to send
        send_step = None
        if drip_step == "" and age_days < 1:
            # Fresh signup — send confirmation
            send_step = "confirm"
        elif drip_step in ("", "confirm") and 3 <= age_days <= 5:
            # Contacts that signed up before confirm step existed skip straight to day3
            send_step = "day3"
        elif drip_step == "day3" and 7 <= age_days <= 9:
            send_step = "day7"
        elif drip_step == "day7" and 10 <= age_days <= 12:
            send_step = "day10"

        if not send_step:
            skipped += 1
            continue

        # Build templates with this contact's email baked in for MC links
        templates = TEMPLATES(email)
        template = templates.get((category, send_step))
        if not template:
            log(f"  No template for ({category}, {send_step}) — skipping {email}")
            skipped += 1
            continue

        subject = template["subject"]
        html = wrap_email(template["body"](first_name), subject)

        try:
            send_email(email, subject, html, gmail_pw)
            set_drip_step(contact_id, send_step)
            log(f"  Sent {send_step} to {email} ({category})")
            sent += 1
        except Exception as e:
            log(f"  ERROR sending to {email}: {e}")
            errors += 1

        time.sleep(0.3)

    log(f"Done — sent: {sent} | skipped: {skipped} | errors: {errors}")
    log("=== Drip run complete ===")
    return errors == 0


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
