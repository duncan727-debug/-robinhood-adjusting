#!/usr/bin/env python3
"""One-off: email Duncan the FAPIA membership brief."""

import re
import smtplib
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

CONFIG = Path("/Users/victoria/.openclaw/workspace/config/.services-config.txt")
GMAIL_USER = "duncanlittlejohn727@gmail.com"
TO_ADDR    = "duncanlittlejohnjr@gmail.com"

m = re.search(r"Gmail App Password.*?:\s*([a-z]{4} [a-z]{4} [a-z]{4} [a-z]{4})", CONFIG.read_text())
if not m:
    sys.exit("ERROR: Gmail App Password not found in config.")
GMAIL_PW = m.group(1)

SUBJECT = "FAPIA — apply now, conference is in 2 weeks (CE math + checklist)"

TEXT = """\
Hey Duncan —

Quick brief on FAPIA per your ask, with the CE math you raised. Honest answer up
top: dues alone do NOT cover CE — but member rates on the two annual conferences
make hitting your 24 hours by August both feasible and cheaper than buying CE
courses a la carte. Read below for the full picture.

================================================================
TL;DR
================================================================
- Apply NOW under your individual FL PA license (license is portable; firm
  affiliation is a separate field you can update July 1).
- Cost: $250 first year ($21/mo).
- FAPIA LIVE 2026 is June 2-3 at Hawks Cay Resort in the Florida Keys — this
  is the deciding factor. Miss it and the next conference is fall.
- Bylaws don't show a sponsor requirement; confirm by phone when they call back.
- Net: yes, join.

================================================================
The CE question — important correction
================================================================
You asked: "if dues cover CE, it pays for itself, right?"

Honest answer: dues do not directly cover CE credits. The two annual FAPIA
conferences carry separate registration fees — but members get significantly
discounted rates, and the courses are PA-specific (legislative updates, ethics,
advanced adjusting strategies) rather than the generic insurance CE you'd get
from a webinar mill.

The math that DOES work in your favor:
- FL PA license requires 24 CE hours per 2-year renewal cycle
- FAPIA LIVE 2026 (June 2-3) is the year's primary conference — historically
  these 2-day events deliver 12-16 CE hours
- A second conference in the fall typically rounds out the full 24
- Member registration rates run materially below non-member rates
- One conference doesn't single-handedly hit your 24 hours, but two does —
  with much higher quality content than $200 online CE bundles

So: dues + two member-rate conferences = your 24 hours covered with
high-signal, PA-specific content + networking + lobbying briefings. Worth more
than the cheapest path to compliance, but not "free CE."

I'd ask the secretary for two specific numbers when they call back:
  1. Exact CE credit hours for FAPIA LIVE 2026 (June 2-3)
  2. Member vs. non-member registration fee for that conference

================================================================
Costs
================================================================
Year 1 dues:         $250  (or $21/mo)
Renewal (Yr 2+):     $495  (or $42/mo)
FAPIA LIVE 2026:     [confirm when they call back — separate registration]
Hawks Cay lodging:   book ASAP if attending; Keys properties fill fast
Travel (Wellington → Hawks Cay): ~3 hrs each way by car

================================================================
Strategic call: apply now under Barclays, transition affiliation July 1
================================================================
Your FL PA license is individual — FAPIA membership attaches to you, not
Barclays. Firm affiliation is a separate field on the member roster and
directory listing. You can update it July 1 when you cut over to Robinhood
Adjusting. The 4-week window of your directory listing showing Barclays is
fine — you're legitimately there until end of June.

Only thing to weigh: if Barclays leadership doesn't know you're leaving yet,
joining FAPIA isn't really a "tell" (most serious FL PAs are members) — but
that's your read on the internal dynamic to make, not mine.

================================================================
Pre-flight checklist for the callback
================================================================
Have ready:
  [ ] FL PA license number + issue date
  [ ] Personal NPN (National Producer Number)
  [ ] Business address (your Wellington address)
  [ ] Current firm: Barclays Public Adjusters
  [ ] Years licensed as PA in FL
  [ ] Headshot for directory listing (high-res, professional)
  [ ] Payment: $250 annual (cleaner than monthly)

Ask the secretary / membership coordinator:
  1. Is a current-member sponsor required to apply?
  2. Can firm affiliation be updated mid-year? (You'll switch July 1.)
  3. Exact CE credit hours for FAPIA LIVE 2026 + member registration cost.
  4. Is FAPIA LIVE registration still open?
  5. Anything else needed beyond active FL PA license + dues payment?

================================================================
Draft bio for Find-an-Adjuster directory (~80 words)
================================================================
Duncan Littlejohn — Licensed Florida Public Insurance Adjuster serving Palm
Beach County and surrounding South Florida communities. Specializing in
residential and commercial property claims including hurricane, wind, water,
roof, and hail damage. Committed to honest, transparent advocacy for
policyholders navigating the claims process. Bilingual service available.
Currently affiliated with Barclays Public Adjusters. Member, Florida
Association of Public Insurance Adjusters. Wellington, FL.

(Swap the Barclays line to "Founder, Robinhood Adjusting" on July 1.)

================================================================
Key links
================================================================
Application portal:   https://fapia.memberclicks.net/public-adjuster-membership
FAPIA LIVE 2026:      https://www.fapia.net/live2026.html
Registration:         https://fapia.memberclicks.net/livereg2026
Apply / Renew page:   https://www.fapia.net/apply.html
Benefits page:        https://www.fapia.net/benefits.html
Bylaws:               https://www.fapia.net/bylaws.html
Main phone:           866-235-6489

================================================================
What I'll handle on my side
================================================================
- July 1 reminder cron: update FAPIA member affiliation to Robinhood Adjusting
  + swap directory bio.
- "Member, FAPIA" badge added to robinhoodadjusting.com footer (queued for
  July push so it goes live with the firm transition).
- Save full FAPIA membership state to project memory so future sessions know
  status, renewal date, and CE hours logged.

Reply with anything to add or change.

— Agent Smith
"""

msg = MIMEMultipart("alternative")
msg["Subject"] = SUBJECT
msg["From"]    = f"Duncan Littlejohn <{GMAIL_USER}>"
msg["To"]      = TO_ADDR
msg.attach(MIMEText(TEXT, "plain"))

with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
    s.login(GMAIL_USER, GMAIL_PW.replace(" ", ""))
    s.sendmail(GMAIL_USER, [TO_ADDR], msg.as_string())

print(f"Sent FAPIA brief to {TO_ADDR}")
