# Prepare a Daily Brief Send Package

Use this after a brief is approved and published to the website, but before any subscriber send.

## What it does

- Confirms the published brief page exists in `site/briefs/YYYY-MM-DD.html`.
- Reads HubSpot newsletter lists 18, 19, and 20.
- Applies the same subscriber guardrails as the older send script.
- Builds `publication/briefs/YYYY-MM-DD/send-package.html` for browser review.
- Builds `publication/briefs/YYYY-MM-DD/send-package.json` with recipient counts and skipped contacts.

## What it does not do

- It does not send email.
- It does not write to HubSpot.
- It does not create tasks.
- It does not commit, push, deploy, or post anywhere.

## Commands

Dry run with live HubSpot recipient counts:

```bash
python3 scripts/prepare-brief-send-package.py 2026-07-07
```

Write review files:

```bash
python3 scripts/prepare-brief-send-package.py 2026-07-07 --write
```

Build the shell package without HubSpot:

```bash
python3 scripts/prepare-brief-send-package.py 2026-07-07 --offline --write
```

## Operating rule

This is the approval checkpoint for subscriber sending. The actual send step should stay separate until Duncan explicitly approves the package.
