# Newsletter List Hygiene

Use this to review HubSpot newsletter list membership before sends.

## Purpose

Daily and weekly senders skip contacts whose lifecycle stage does not show subscriber-style consent. The audit shows exactly who is eligible and who is skipped, without changing HubSpot.

## Command

Dry run:

```bash
python3 scripts/audit-newsletter-lists.py
```

Write local review files:

```bash
python3 scripts/audit-newsletter-lists.py --write
```

Outputs:

- `ops/newsletter-list-audits/YYYY-MM-DD-HHMM/audit.html`
- `ops/newsletter-list-audits/YYYY-MM-DD-HHMM/audit.json`

## Guardrails

- Read-only HubSpot access.
- No contact updates.
- No list changes.
- No email sends.
- Generated audit files may include email addresses, so do not commit them.
