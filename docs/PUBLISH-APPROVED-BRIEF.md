# Publish an Approved Daily Brief

Use this only after Duncan has reviewed the daily brief draft and approved it for the website.

## What it does

- Reads `publication/briefs/YYYY-MM-DD/README.md`.
- Generates `site/briefs/YYYY-MM-DD.html`.
- Updates the daily briefs archive page.
- Updates the homepage Property Intelligence list.
- Adds the brief URL to `site/sitemap.xml`.

## What it does not do

- It does not send emails.
- It does not post to HubSpot.
- It does not contact subscribers.
- It does not publish unless `--write` is passed.
- It does not commit or push unless `--commit-push` is passed.

## Commands

Dry run:

```bash
python3 scripts/publish-approved-brief.py 2026-07-07
```

Write site files after approval:

```bash
python3 scripts/publish-approved-brief.py 2026-07-07 --write
```

Write, commit, push, and check live URLs:

```bash
python3 scripts/publish-approved-brief.py 2026-07-07 --write --commit-push
```

Optional headline, summary, and tags:

```bash
python3 scripts/publish-approved-brief.py 2026-07-07 --write \
  --headline "Hard Assets, Ordinary Storms, and Claim-Ready Documentation" \
  --summary "Deal tape shows capital still buying logistics land and luxury waterfront while daily storms remain the practical claims risk." \
  --tags "Deal tape,Storm risk,Documentation"
```

## Operating rule

The morning cron should keep creating review drafts only. This helper is the approval step after Duncan says the draft is ready for the website.
