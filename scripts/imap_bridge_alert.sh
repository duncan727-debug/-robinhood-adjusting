#!/bin/bash
# IMAP bridge + push alert (Option A — 5-min poll for prospect replies).
# Runs imap_bridge.py, then if the latest run logged Replies > 0, wakes the
# main agent session via `openclaw system event` so I can draft responses.

set -u
WORKSPACE="/Users/victoria/.openclaw/workspace"
LOG="$WORKSPACE/scripts/imap_bridge.log"
WRAPPER_LOG="$WORKSPACE/scripts/imap_bridge_alert.log"
PYTHON="/usr/bin/python3"
OPENCLAW="/usr/local/bin/openclaw"

ts() { TZ=America/New_York date "+%Y-%m-%d %H:%M:%S %Z"; }

# Mark log offset before run so we can scan just this run's output.
BEFORE_BYTES=$(wc -c < "$LOG" 2>/dev/null || echo 0)

"$PYTHON" "$WORKSPACE/scripts/imap_bridge.py" >>"$LOG" 2>&1
RC=$?

# Pull just the new lines from this run.
NEW=$(tail -c +$((BEFORE_BYTES + 1)) "$LOG" 2>/dev/null)

DONE_LINE=$(printf '%s\n' "$NEW" | grep -E '^=== Done\.' | tail -1)
REPLIES=$(printf '%s' "$DONE_LINE" | sed -nE 's/.*Replies: ([0-9]+).*/\1/p')
BOUNCES=$(printf '%s' "$DONE_LINE" | sed -nE 's/.*Hard bounces: ([0-9]+).*/\1/p')
SOFT=$(printf '%s' "$DONE_LINE" | sed -nE 's/.*Soft bounces: ([0-9]+).*/\1/p')
CALENDLY=$(printf '%s' "$DONE_LINE" | sed -nE 's/.*Calendly deals: ([0-9]+).*/\1/p')

REPLIES=${REPLIES:-0}
BOUNCES=${BOUNCES:-0}
SOFT=${SOFT:-0}
CALENDLY=${CALENDLY:-0}

echo "[$(ts)] rc=$RC replies=$REPLIES bounces=$BOUNCES soft=$SOFT calendly=$CALENDLY" >> "$WRAPPER_LOG"

if [ "$REPLIES" -gt 0 ] || [ "$CALENDLY" -gt 0 ]; then
  # Find today's reply queue file for context.
  TODAY=$(TZ=America/New_York date +%Y-%m-%d)
  QUEUE_FILE="$WORKSPACE/crm/reply_queue/$TODAY.jsonl"
  CONTEXT=""
  if [ -f "$QUEUE_FILE" ]; then
    # Last N queued reply senders/subjects (most recent first).
    CONTEXT=$($PYTHON - "$QUEUE_FILE" "$REPLIES" <<'PYEOF'
import json, sys
path, n = sys.argv[1], int(sys.argv[2])
n = max(n, 1)
lines = []
try:
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                lines.append(line)
except Exception:
    sys.exit(0)
recent = lines[-n:]
for raw in recent:
    try:
        r = json.loads(raw)
        sender = r.get("sender", "?")
        subject = (r.get("subject") or "(no subject)")[:80]
        print(f"- {sender} | {subject}")
    except Exception:
        pass
PYEOF
)
  fi

  TEXT="📬 New prospect reply detected (replies=$REPLIES, calendly=$CALENDLY). Review queue: crm/reply_queue/$TODAY.jsonl"
  if [ -n "$CONTEXT" ]; then
    TEXT="$TEXT
$CONTEXT"
  fi
  TEXT="$TEXT

EMAIL-RESPONSE WORKFLOW (per Duncan 2026-05-19):
1. Read the reply body from crm/reply_queue/$TODAY.jsonl
2. Classify intent: interested / question / negative / ambiguous
3. If you can handle it directly: draft a reply that schedules next step
   - Calendly /30min phone: https://calendly.com/duncanlittlejohn727/30min
   - Calendly /virtual-review video: https://calendly.com/duncanlittlejohn727/virtual-review
   - In-person where appropriate
4. If it needs Duncan's voice (judgment, pricing, relationship, ambiguous): create a HubSpot task
   - Run: python3 scripts/hubspot_task.py --subject \"...\" --body \"...\" --company-name \"<org>\" --priority HIGH --due $TODAY
5. Update organizations.csv stage + append interactions.csv
6. Hot leads → crm/hot-leads/$TODAY/<org_id>-HOT.md
7. NEVER use LinkedIn (not set up). Email / phone / Calendly / contact-form only."

  "$OPENCLAW" system event --mode now --text "$TEXT" >> "$WRAPPER_LOG" 2>&1
  echo "[$(ts)] wake event sent to main session" >> "$WRAPPER_LOG"
fi

exit $RC
