#!/bin/bash
# Regenerates the "Model Usage" JSON snapshot embedded in MISSION-CONTROL.html.
# Called ad-hoc or from a LaunchAgent / cron. Reads ~/.openclaw/cron/jobs.json.

set -euo pipefail

JOBS_FILE="$HOME/.openclaw/cron/jobs.json"
HTML_FILE="$HOME/.openclaw/workspace/MISSION-CONTROL.html"

if [ ! -f "$JOBS_FILE" ] || [ ! -f "$HTML_FILE" ]; then
    echo "missing jobs.json or MISSION-CONTROL.html" >&2
    exit 1
fi

SNAPSHOT="$(python3 - "$JOBS_FILE" <<'PY'
import json, sys, datetime, time

path = sys.argv[1]
with open(path) as f:
    raw = json.load(f)
jobs = raw.get("jobs") if isinstance(raw, dict) else raw

# Midnight EDT (America/New_York = UTC-4 in April); simple offset avoids tzdata dep.
now = time.time()
today_midnight_utc = datetime.datetime.utcfromtimestamp(now).replace(
    hour=4, minute=0, second=0, microsecond=0
).timestamp()
if today_midnight_utc > now:
    today_midnight_utc -= 86400

def bucket(model: str) -> str:
    if not model:
        return "other"
    if model.startswith("claude-cli/"):
        if "haiku" in model: return "claude-haiku"
        if "sonnet" in model: return "claude-sonnet"
        if "opus" in model: return "claude-opus"
        return "claude-other"
    if model.startswith("google/"):
        return "gemini"
    if model.startswith("codex"):
        return "codex"
    return "other"

counts = {"claude-haiku": {"sched": 0, "done": 0},
          "gemini":       {"sched": 0, "done": 0},
          "codex":        {"sched": 0, "done": 0}}

for j in jobs or []:
    if not j.get("enabled", True):
        continue
    model = (j.get("payload") or {}).get("model", "")
    b = bucket(model)
    if b in counts:
        counts[b]["sched"] += 1
        last = (j.get("state") or {}).get("lastRunAtMs")
        status = (j.get("state") or {}).get("lastRunStatus")
        if last and status == "ok" and last / 1000 >= today_midnight_utc:
            counts[b]["done"] += 1

def pct(done, sched):
    if sched <= 0: return 0
    return min(100, int(round(100 * done / sched)))

def state(p, sched):
    if sched <= 0: return "idle"
    if p > 85: return "hot"
    if p > 60: return "warn"
    return "ok"

lanes = [
    {
        "label": "Claude Haiku 4.5",
        "sub": "cron — heavy jobs (ops review, trends, partnerships, rollup, monthly)",
        "jobsScheduled": counts["claude-haiku"]["sched"],
        "jobsCompletedToday": counts["claude-haiku"]["done"],
        "percent": pct(counts["claude-haiku"]["done"], counts["claude-haiku"]["sched"]),
        "state": state(pct(counts["claude-haiku"]["done"], counts["claude-haiku"]["sched"]), counts["claude-haiku"]["sched"]),
        "note": "subscription — resets ~2pm EDT daily",
    },
    {
        "label": "Gemini 2.0 Flash",
        "sub": "cron — light jobs (brief, content, intel, outreach, response, linkedin)",
        "jobsScheduled": counts["gemini"]["sched"],
        "jobsCompletedToday": counts["gemini"]["done"],
        "percent": pct(counts["gemini"]["done"], counts["gemini"]["sched"]),
        "state": state(pct(counts["gemini"]["done"], counts["gemini"]["sched"]), counts["gemini"]["sched"]),
        "note": "free tier — ~1500 req/day",
    },
    {
        "label": "Codex GPT-5.4-mini",
        "sub": "backstop — not yet wired into fallback chain",
        "jobsScheduled": counts["codex"]["sched"],
        "jobsCompletedToday": counts["codex"]["done"],
        "percent": pct(counts["codex"]["done"], counts["codex"]["sched"]),
        "state": "idle" if counts["codex"]["sched"] == 0 else state(pct(counts["codex"]["done"], counts["codex"]["sched"]), counts["codex"]["sched"]),
        "note": "free via chatgpt.com login — ready to wire",
    },
    {
        "label": "Claude Opus 4.7",
        "sub": "this chat (Agent Smith) — heaviest model; swap with /model haiku",
        "jobsScheduled": 0,
        "jobsCompletedToday": 0,
        "percent": 0,
        "state": "idle",
        "note": "not used by cron — only by live chat",
    },
]

snapshot = {
    "updatedAt": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    "lanes": lanes,
}
print(json.dumps(snapshot, indent=2))
PY
)"

python3 - "$HTML_FILE" "$SNAPSHOT" <<'PY'
import sys, re
html_path, snapshot = sys.argv[1], sys.argv[2]
with open(html_path) as f:
    html = f.read()
new_block = (
    '<script id="usage-data" type="application/json">\n'
    + snapshot
    + '\n    </script>'
)
pattern = re.compile(
    r'<script id="usage-data"[^>]*>.*?</script>',
    re.DOTALL,
)
if not pattern.search(html):
    print("usage-data script block not found", file=sys.stderr)
    sys.exit(2)
html = pattern.sub(lambda _m: new_block, html, count=1)
with open(html_path, "w") as f:
    f.write(html)
PY

echo "updated $HTML_FILE"
