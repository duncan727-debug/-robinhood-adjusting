#!/usr/bin/env bash
# catchup.sh — run missing OpenClaw operations jobs for today.
# Idempotent; safe to invoke every 15 min and at wake/boot.
# Checks today's expected outputs and triggers missing jobs in dependency order.

set -u
export PATH="/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:$PATH"

WORKSPACE="/Users/victoria/.openclaw/workspace"
SCRIPTDIR="$WORKSPACE/scripts"
LOG="$SCRIPTDIR/catchup.log"
LOCK="$SCRIPTDIR/catchup.lock"

mkdir -p "$SCRIPTDIR"

# Source workspace secrets so child scripts inherit HUBSPOT_API_KEY,
# GOOGLE_PLACES_API_KEY, GMAIL_APP_PASSWORD, etc. This matches what cron
# gets via its inline env vars but covers LaunchAgent and manual invocations.
if [ -f "$WORKSPACE/config/.secrets" ]; then
  set -a
  # shellcheck disable=SC1091
  . "$WORKSPACE/config/.secrets"
  set +a
fi

log() { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*" >>"$LOG"; }

# Single-instance guard via pidfile
if [ -f "$LOCK" ]; then
  OTHER=$(cat "$LOCK" 2>/dev/null || true)
  if [ -n "${OTHER:-}" ] && kill -0 "$OTHER" 2>/dev/null; then
    log "already running (pid=$OTHER), exiting"
    exit 0
  fi
fi
echo $$ >"$LOCK"
trap 'rm -f "$LOCK"' EXIT

# Wait up to 60s for openclaw gateway to accept connections (in case we ran at boot)
for _ in $(seq 1 30); do
  if openclaw cron status >/dev/null 2>&1; then break; fi
  sleep 2
done

if ! openclaw cron status >/dev/null 2>&1; then
  log "gateway not reachable after 60s, aborting"
  exit 1
fi

TODAY=$(TZ=America/New_York date +%Y-%m-%d)
DOW=$(TZ=America/New_York date +%u)     # 1=Mon..7=Sun
DOM=$(TZ=America/New_York date +%d | sed 's/^0//')
ISOWEEK=$(TZ=America/New_York date +%G-%V)
MONTHKEY=$(TZ=America/New_York date +%Y-%m)
MINS=$(TZ=America/New_York date +"%H %M" | awk '{print $1*60 + $2}')

log "=== catchup start: today=$TODAY dow=$DOW dom=$DOM mins=$MINS ==="

JOBS_JSON="/Users/victoria/.openclaw/cron/jobs.json"
TODAY_MIDNIGHT_MS=$(TZ=America/New_York date -j -f "%Y-%m-%d %H:%M:%S" "$TODAY 00:00:00" +%s)000

# Look up a job's lastRunAtMs and lastRunStatus from jobs.json.
# Prints: "<lastRunAtMs> <lastRunStatus>" (0 "-" if missing).
job_last_run() {
  local id="$1"
  python3 - "$id" "$JOBS_JSON" <<'PY'
import json, sys
job_id, path = sys.argv[1], sys.argv[2]
try:
    data = json.load(open(path))
except Exception:
    print("0 -"); sys.exit(0)
for j in data.get("jobs", []):
    if j.get("id") == job_id:
        st = j.get("state") or {}
        print(f"{st.get('lastRunAtMs', 0)} {st.get('lastRunStatus', '-')}")
        sys.exit(0)
print("0 -")
PY
}

# Wait for a path to exist, polling every 20s up to $2 minutes.
wait_for() {
  local path="$1" max_min="${2:-30}" waited=0
  while [ ! -e "$path" ] && [ "$waited" -lt $((max_min*60)) ]; do
    sleep 20
    waited=$((waited+20))
  done
  [ -e "$path" ]
}

# check_and_run <job_id> <label> <scheduled_min> <output_path> [max_wait_min]
# Skips when: (1) scheduled time hasn't passed, (2) output already exists, OR
# (3) the job already ran successfully today (captures runs that legitimately
# produced no output, e.g. empty CRM). Otherwise triggers via cron run and
# waits for the output to appear up to max_wait_min.
check_and_run() {
  local id="$1" label="$2" sched="$3" out="$4" maxw="${5:-30}"
  if [ "$MINS" -lt "$sched" ]; then
    log "  $label: not yet scheduled (sched_min=$sched now=$MINS), skip"
    return 1
  fi
  if [ -e "$out" ]; then
    log "  $label: output exists ($out), skip"
    return 0
  fi
  read -r last_ms last_status <<<"$(job_last_run "$id")"
  if [ "$last_ms" -ge "$TODAY_MIDNIGHT_MS" ] && [ "$last_status" = "ok" ]; then
    log "  $label: already ran today at ${last_ms}ms (status=ok), skip"
    return 0
  fi
  log "  $label: MISSING output=$out lastRun=${last_ms} status=${last_status} — triggering openclaw cron run $id"
  if openclaw cron run "$id" >>"$LOG" 2>&1; then
    log "  $label: submitted; waiting up to ${maxw}m for $out"
    if wait_for "$out" "$maxw"; then
      log "  $label: OK (output present)"
      return 0
    else
      log "  $label: output still absent after ${maxw}m (may be a no-op run), continuing"
      return 0
    fi
  else
    log "  $label: ERROR submitting run"
    return 3
  fi
}

# Job IDs (read from ~/.openclaw/cron/jobs.json)
ID_BRIEF="8a47ce9a-b505-4247-a0cb-84ac817f588c"
ID_CONTENT="0abcf54e-9628-4e0c-b6ff-3ddc3aac1a02"
ID_INTEL="9bc7dbc3-9138-4819-a495-3606eb3129c5"
ID_OUTREACH="bd327112-f77e-4030-8d60-89c0374a01ed"
ID_RESP="3a2c2f9a-967a-457a-974d-f575143e695e"
ID_OPS="89b2d286-f9bb-4f61-ac56-4cb5e9bddb48"
ID_LINKEDIN="614a7216-f906-464e-be2a-5638984f4366"
ID_PARTNER="f1543d82-ddfb-4d6f-b964-e11831c40656"
ID_TRENDS="7c1d6347-a536-4dc6-8a1f-7991b9bf35f3"
ID_ROLLUP="5b05ef73-296b-44c5-8fc2-3de1957f1129"
ID_MONTHLY="f044781f-8930-451f-ada7-f4f444fb1955"

# Weekday chain (Mon-Fri)
if [ "$DOW" -le 5 ]; then
  # 4:00am brief — upstream of content
  check_and_run "$ID_BRIEF"    "daily-research-brief"      240 "$WORKSPACE/briefs/$TODAY.md"              45

  # 4:30am content — depends on brief
  if [ -e "$WORKSPACE/briefs/$TODAY.md" ]; then
    check_and_run "$ID_CONTENT"  "daily-content"             270 "$WORKSPACE/content/$TODAY/blog.md"         20
  fi

  # 5:00am intelligence — upstream of outreach
  check_and_run "$ID_INTEL"    "prospect-deep-intelligence" 300 "$WORKSPACE/crm/intelligence/$TODAY"        20

  # 6:00am outreach (sequential after intel; no hard file dep — intel may legitimately skip when CRM is empty)
  check_and_run "$ID_OUTREACH" "weekday-crm-outreach"      360 "$WORKSPACE/crm/drafts/$TODAY"              20

  # 7:00am response-handler
  check_and_run "$ID_RESP"     "response-handler"          420 "$WORKSPACE/crm/responses/$TODAY"           15

  # 7:30am ops-review
  check_and_run "$ID_OPS"      "weekday-ops-review"        450 "$WORKSPACE/ops-review/$TODAY.md"          15

  # 9:00am prospecting — Google Places API pulls 25 PBC contacts
  PROSPECT_MARKER_LINE=$(grep "^\[$TODAY.*Run complete" "$WORKSPACE/crm/prospect_palm_beach.log" 2>/dev/null | tail -1)
  if [ "$MINS" -ge 540 ] && [ -z "$PROSPECT_MARKER_LINE" ]; then
    log "  prospect_palm_beach: running"
    if /usr/bin/python3 "$WORKSPACE/scripts/prospect_palm_beach.py" >>"$WORKSPACE/crm/prospect_palm_beach.log" 2>&1; then
      log "  prospect_palm_beach: done"
    else
      log "  prospect_palm_beach: ERROR (see prospect_palm_beach.log)"
    fi
  elif [ -n "$PROSPECT_MARKER_LINE" ]; then
    log "  prospect_palm_beach: already ran today, skip"
  fi

  # 9:00am drip — follow-up sequence on warm contacts
  DRIP_MARKER_LINE=$(grep "^\[$TODAY.*=== Drip run complete ===" "$WORKSPACE/scripts/drip.log" 2>/dev/null | tail -1)
  if [ "$MINS" -ge 540 ] && [ -z "$DRIP_MARKER_LINE" ]; then
    log "  drip: running"
    if /usr/bin/python3 "$WORKSPACE/scripts/drip.py" >>"$WORKSPACE/scripts/drip.log" 2>&1; then
      log "  drip: done"
    else
      log "  drip: ERROR (see drip.log)"
    fi
  elif [ -n "$DRIP_MARKER_LINE" ]; then
    log "  drip: already ran today, skip"
  fi

  # 10:00am enrichment gate — scrape emails, upload NEW to HubSpot, route guesses to review
  ENRICH_MARKER_LINE=$(grep "^\[$TODAY.*=== Done ===" "$WORKSPACE/crm/email_enrichment.log" 2>/dev/null | tail -1)
  if [ "$MINS" -ge 600 ] && [ -z "$ENRICH_MARKER_LINE" ]; then
    log "  enrich_before_upload: running"
    if /usr/bin/python3 "$WORKSPACE/scripts/enrich_before_upload.py" >>"$WORKSPACE/crm/email_enrichment.log" 2>&1; then
      log "  enrich_before_upload: done"
    else
      log "  enrich_before_upload: ERROR (see email_enrichment.log)"
    fi
  elif [ -n "$ENRICH_MARKER_LINE" ]; then
    log "  enrich_before_upload: already ran today, skip"
  fi

  # Outreach send batches — 8am, 10:30am, 12:30pm, 3pm
  # Marker pattern: "[YYYY-MM-DD HH:MM] === Batch N complete ==="
  run_outreach_batch() {
    local batch="$1"
    local sched_min="$2"
    local label="batch $batch"
    if [ "$MINS" -lt "$sched_min" ]; then
      return 0
    fi
    local marker
    marker=$(grep "^\[$TODAY.*=== Batch $batch complete ===" "$WORKSPACE/scripts/outreach_send.log" 2>/dev/null | tail -1)
    if [ -n "$marker" ]; then
      log "  outreach $label: already ran today, skip"
      return 0
    fi
    log "  outreach $label: running"
    if OUTREACH_BATCH="$batch" /usr/bin/python3 "$WORKSPACE/scripts/send_outreach.py" >>"$WORKSPACE/scripts/outreach_send.log" 2>&1; then
      log "  outreach $label: done"
    else
      log "  outreach $label: ERROR (see outreach_send.log)"
    fi
  }
  run_outreach_batch 1 480   #  8:00 AM
  run_outreach_batch 2 630   # 10:30 AM
  run_outreach_batch 3 750   # 12:30 PM
  run_outreach_batch 4 900   #  3:00 PM
fi

# IMAP bridge — hourly at :05. Catch up if the most recent run is > 75 min old.
# Log timestamp format: [YYYY-MM-DDTHH:MM:SS] (ISO). Runs every day.
IMAP_LAST_LINE=$(grep -E "^\[[0-9-]+T[0-9:]+\]" "$WORKSPACE/scripts/imap_bridge.log" 2>/dev/null | tail -1)
if [ -n "$IMAP_LAST_LINE" ]; then
  IMAP_LAST_TS=$(echo "$IMAP_LAST_LINE" | sed -E 's/^\[([0-9-]+)T([0-9:]+)\].*/\1 \2/')
  IMAP_LAST_EPOCH=$(TZ=America/New_York date -j -f "%Y-%m-%d %H:%M:%S" "$IMAP_LAST_TS" +%s 2>/dev/null || echo 0)
  IMAP_NOW_EPOCH=$(date +%s)
  IMAP_AGE_MIN=$(( (IMAP_NOW_EPOCH - IMAP_LAST_EPOCH) / 60 ))
else
  IMAP_AGE_MIN=9999
fi
if [ "$IMAP_AGE_MIN" -gt 75 ]; then
  log "  imap_bridge: last run was ${IMAP_AGE_MIN}m ago, running"
  if /usr/bin/python3 "$WORKSPACE/scripts/imap_bridge.py" >>"$WORKSPACE/scripts/imap_bridge.log" 2>&1; then
    log "  imap_bridge: done"
  else
    log "  imap_bridge: ERROR (see imap_bridge.log)"
  fi
else
  log "  imap_bridge: ran ${IMAP_AGE_MIN}m ago, skip"
fi

# Weekday-only jobs that run after the daily IMAP check.
if [ "$DOW" -le 5 ]; then
  # 5:45am newsletter send — after brief is ready
  SEND_MARKER="$WORKSPACE/scripts/.newsletter-sent-$TODAY"
  if [ "$MINS" -ge 345 ] && [ ! -f "$SEND_MARKER" ] && [ -e "$WORKSPACE/briefs/$TODAY.md" ]; then
    log "  newsletter-send: sending brief for $TODAY"
    if /usr/bin/python3 "$WORKSPACE/scripts/send-daily-brief.py" "$TODAY" >>"$WORKSPACE/scripts/newsletter-send.log" 2>&1; then
      touch "$SEND_MARKER"
      log "  newsletter-send: done"
    else
      log "  newsletter-send: ERROR (see newsletter-send.log)"
    fi
  elif [ -f "$SEND_MARKER" ]; then
    log "  newsletter-send: already sent today, skip"
  fi

  # 6:30am build-website — regenerate site HTML, commit, push to Netlify.
  # Skip if today's brief HTML is already on site/. Re-run if it's missing
  # (happens when the daily brief was generated late and 6:30 build missed it).
  if [ "$MINS" -ge 390 ] && [ ! -e "$WORKSPACE/site/briefs/$TODAY.html" ] && [ -e "$WORKSPACE/content/briefs/$TODAY.html" ]; then
    log "  build-website: running (site/briefs/$TODAY.html missing)"
    if bash "$WORKSPACE/scripts/build-website.sh" >>"$LOG" 2>&1; then
      log "  build-website: build OK, committing + pushing"
      git -C "$WORKSPACE" add site/ >>"$LOG" 2>&1 || true
      if ! git -C "$WORKSPACE" diff --cached --quiet; then
        git -C "$WORKSPACE" commit -m "site: catchup sync $TODAY (build-website rerun)" >>"$LOG" 2>&1 \
          && git -C "$WORKSPACE" push origin main >>"$LOG" 2>&1 \
          && log "  build-website: pushed" \
          || log "  build-website: commit/push ERROR"
      else
        log "  build-website: nothing to commit"
      fi
    else
      log "  build-website: ERROR (see catchup.log)"
    fi
  elif [ -e "$WORKSPACE/site/briefs/$TODAY.html" ]; then
    log "  build-website: site/briefs/$TODAY.html exists, skip"
  fi
fi

# Mon 11am linkedin-sequencing
if [ "$DOW" -eq 1 ]; then
  check_and_run "$ID_LINKEDIN" "linkedin-sequencing"       660 "$WORKSPACE/crm/linkedin-queue/$TODAY"     15
fi

# Wed 1pm partnership-network-builder
if [ "$DOW" -eq 3 ]; then
  check_and_run "$ID_PARTNER"  "partnership-network-builder" 780 "$WORKSPACE/crm/partnerships/$ISOWEEK"    20
fi

# Fri 5pm weekly rollup
if [ "$DOW" -eq 5 ]; then
  check_and_run "$ID_ROLLUP"   "friday-weekly-rollup"     1020 "$WORKSPACE/weekly/$ISOWEEK.md"           20
fi

# Sat 10am trends
if [ "$DOW" -eq 6 ]; then
  check_and_run "$ID_TRENDS"   "daily-trends"              600 "$WORKSPACE/trends/$TODAY.md"              30
fi

# 1st of month 9am velocity review
if [ "$DOM" -eq 1 ]; then
  check_and_run "$ID_MONTHLY"  "monthly-velocity-review"   540 "$WORKSPACE/monthly/$MONTHKEY-overview.md" 30
fi

# Catchup for daily-git-sync (8am cron). If the openclaw main-session wake
# didn't land or didn't actually push, ensure today's content reaches GitHub
# so Netlify rebuilds the live site. Only fires after 8am local, once per day.
SYNC_MARKER="$WORKSPACE/scripts/.git-sync-done-$TODAY"
if [ "$MINS" -ge 480 ] && [ ! -f "$SYNC_MARKER" ]; then
  TODAY_COMMITS=$(git -C "$WORKSPACE" log --since="midnight" --oneline 2>/dev/null | wc -l | tr -d ' ')
  if [ "$TODAY_COMMITS" -eq 0 ]; then
    log "  daily-git-sync: no commit today, running git-sync-daily.sh"
    if bash "$WORKSPACE/scripts/git-sync-daily.sh" >>"$LOG" 2>&1; then
      log "  daily-git-sync: OK, pushed"
      touch "$SYNC_MARKER"
    else
      log "  daily-git-sync: ERROR (see catchup.log)"
    fi
  else
    log "  daily-git-sync: $TODAY_COMMITS commit(s) already today, skip"
    touch "$SYNC_MARKER"
  fi
fi

log "=== catchup end ==="
