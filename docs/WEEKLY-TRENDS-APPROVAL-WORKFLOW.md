# Weekly Trends Approval Workflow

Use this after the weekly trends report has been drafted and published to the website.

## Preflight package

```bash
python3 scripts/prepare-weekly-trends-send-package.py 2026-05-30 --write
```

This creates:

- `publication/trends/YYYY-MM-DD/send-package.html`
- `publication/trends/YYYY-MM-DD/send-package.json`

The package reads HubSpot lists 18, 19, and 20, dedupes recipients, and sends nothing.

## No-send sender check

```bash
python3 scripts/send-weekly-trends.py 2026-05-30
```

## Internal test send after approval

```bash
python3 scripts/send-weekly-trends.py 2026-05-30 --send-approved --test-to duncan@example.com
```

## Subscriber send after approval

```bash
python3 scripts/send-weekly-trends.py 2026-05-30 --send-approved
```

## Guardrails

- Without `--send-approved`, the weekly sender only reports what it would do.
- With `--send-approved`, `publication/trends/YYYY-MM-DD/send-package.json` must exist.
- `--test-to` sends only to the internal test address and does not create the weekly sent marker.
- Weekly trends remain review-first; no cron should send them automatically yet.
- Watchlist items and internal operational notes are private only. Remove them before building the public trends HTML or preparing a subscriber send package.
