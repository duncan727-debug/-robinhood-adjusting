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

log "=== catchup end ==="
