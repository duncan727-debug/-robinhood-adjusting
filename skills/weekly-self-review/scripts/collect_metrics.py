#!/usr/bin/env python3
"""
Collect last-7-day metrics for the weekly self-review.

Run from workspace root:
    python3 skills/weekly-self-review/scripts/collect_metrics.py

Writes JSON to stdout. The SKILL.md workflow consumes this then writes prose.
"""
from __future__ import annotations
import csv, json, os, re, subprocess, sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

WS = Path(__file__).resolve().parents[3]
LOGS = WS / "scripts"
CRM = WS / "crm"
SITE = WS / "site"
NOW = datetime.now(timezone.utc).astimezone()
SINCE = NOW - timedelta(days=7)

ACRONYM_ALLOWLIST = {
    "HOA","FL","OIR","NOAA","NWS","PA","HVAC","FEMA","NHC","USA","US","RE","HQ","FAQ",
    "FIGA","HB","SB","AFD","DK","CRE","CAI","CSU","BD","AA","AM",
    "PBC","SFL","BNI","CRM","API","CEO","CFO","COO","CTO","TBD","TBA",
    "IRS","DOI","DFS","EDT","EST","UTC","GDP","WSJ","CNN","BBC","NPR",
    "Q1","Q2","Q3","Q4","YOY","YTD","ROI","KPI","P0","P1","P2","P3",
}

ENGLISH_UPPER_WORDS = {
    "TOP","NEW","OLD","HOT","COLD","DRY","WET","BIG","ALL","ANY","FOR","NOT",
    "BUT","AND","THE","WAS","ARE","CAN","HAD","HAS","HER","HIS","HOW","NOW",
    "ONE","TWO","TEN","WHO","WHY","YOU","DAY","WAY","MAN","GET","END","OFF",
    "OUT","SEE","SAY","RUN","LET","PUT","USE","SET","WIN","KEY","JOB","ASK",
    "FAR","GOT","WAR","TRY","LAW","CAR","EYE","CUP","BAD","SIX","SUN","FIT",
    "HALL","HOLD","HOME","HOPE","INTO","KEEP","KIND","KNOW","LAST","LATE",
    "LEAD","LEAVE","LESS","LIFE","LINE","LIST","LIVE","LONG","LOOK","LOSE",
    "MADE","MAKE","MANY","MEAN","MOVE","MUCH","MUST","NEAR","NEED","NEWS",
    "NEXT","NICE","ONCE","ONLY","OPEN","OVER","PART","PAST","PLAN","PLAY",
    "REAL","RIGHT","ROOM","SAME","SAID","SEEM","SHOW","SIDE","SOME","STAY",
    "STEP","STOP","SUCH","SURE","TAKE","TALK","TELL","TERM","THAN","THAT",
    "THIS","TIME","TOLD","TOOK","TURN","UNTO","UPON","USED","VERY","WALK",
    "WANT","WEEK","WELL","WENT","WERE","WHAT","WHEN","WILL","WITH","WORD",
    "WORK","YEAR","YOUR","ACTIVITY","CALENDAR","COMMERCIAL","CONTRACTORS",
    "DEADLINES","DOCTYPE","ESTATE","HO","INDUSTRY","INDUSTRIES","LOCAL",
    "NOTES","OUTLOOK","PRESS","RELEASE","STORIES","WEATHER","WELLINGTON",
    "INSURANCE","REGULATION","SERVICE","CORRECTION","NEGATIVE","LIVE","TODAY",
    "MIATWDAT","XVI","UTF","GUID",
}

def _is_english_word(token: str) -> bool:
    return token in ENGLISH_UPPER_WORDS

def count_log_lines(path: Path, since: datetime, pattern: str | None = None) -> int:
    if not path.exists():
        return -1
    n = 0
    try:
        for line in path.read_text(errors="ignore").splitlines():
            if pattern and not re.search(pattern, line):
                continue
            n += 1
        return n
    except Exception as e:
        return -1

def briefs_last_7():
    """Return per-brief flags: audiences present, acronyms found."""
    out = []
    for i in range(7):
        d = (NOW - timedelta(days=i)).strftime("%Y-%m-%d")
        p = SITE / "briefs" / f"{d}.html"
        if not p.exists():
            out.append({"date": d, "exists": False})
            continue
        raw = p.read_text(errors="ignore")
        text = re.sub(r"<[^>]+>", " ", raw)
        text = re.sub(r"&[a-zA-Z]+;", " ", text)
        audiences = {
            "homeowner": bool(re.search(r"\b[Hh]omeowners?\b", text)),
            "provider": bool(re.search(r"\b(?:[Ss]ervice )?[Pp]roviders?\b", text)),
            "real_estate": bool(re.search(r"[Rr]eal[\s-][Ee]state", text)),
        }
        candidates = set(re.findall(r"\b[A-Z]{2,5}\b", text))
        acronyms = {a for a in candidates if a not in ACRONYM_ALLOWLIST and not _is_english_word(a)}
        out.append({
            "date": d,
            "exists": True,
            "audiences": audiences,
            "stray_acronyms": sorted(acronyms),
            "word_count": len(text.split()),
        })
    return out

def cron_status():
    """Read cron jobs.json directly + extract last-run state per job."""
    p = Path.home() / ".openclaw/cron/jobs.json"
    if not p.exists():
        return {"error": "no jobs.json"}
    d = json.loads(p.read_text())
    jobs = d.get("jobs", [])
    per_job = []
    enabled = 0
    errors_now = 0
    for j in jobs:
        is_enabled = j.get("enabled", True)
        if is_enabled: enabled += 1
        state = j.get("state") or {}
        last_status = state.get("lastRunStatus")
        consec_err = state.get("consecutiveErrors", 0)
        if is_enabled and consec_err >= 1: errors_now += 1
        last_ms = state.get("lastRunAtMs")
        last_iso = None
        if last_ms:
            last_iso = datetime.fromtimestamp(last_ms/1000, tz=timezone.utc).isoformat()
        per_job.append({
            "name": j.get("name"),
            "enabled": is_enabled,
            "last_status": last_status,
            "consecutive_errors": consec_err,
            "last_run": last_iso,
            "last_duration_ms": state.get("lastDurationMs"),
            "model": (j.get("payload") or {}).get("model"),
        })
    return {
        "total": len(jobs),
        "enabled": enabled,
        "currently_erroring": errors_now,
        "per_job": per_job,
    }

def hubspot_task_queue():
    """Count open HubSpot tasks for Duncan. Reads HUBSPOT_API_KEY from .secrets."""
    secrets = WS / "config" / ".secrets"
    token = os.environ.get("HUBSPOT_API_KEY", "").strip()
    if not token and secrets.exists():
        for line in secrets.read_text().splitlines():
            if "HUBSPOT_API_KEY=" in line and not line.strip().startswith("#"):
                token = line.split("HUBSPOT_API_KEY=",1)[1].strip().strip('"').strip("'")
                break
    if not token:
        return {"error": "no HUBSPOT_API_KEY"}
    import urllib.request, urllib.error
    body = json.dumps({
        "filterGroups": [{"filters": [
            {"propertyName": "hs_task_status", "operator": "EQ", "value": "NOT_STARTED"}
        ]}],
        "properties": ["hs_task_subject","hs_task_priority","hs_timestamp"],
        "limit": 100,
    }).encode()
    req = urllib.request.Request(
        "https://api.hubapi.com/crm/v3/objects/tasks/search",
        data=body, method="POST",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
    except Exception as e:
        return {"error": str(e)}
    tasks = data.get("results", [])
    now_ms = int(NOW.timestamp() * 1000)
    overdue = 0
    by_priority = {"HIGH":0,"MEDIUM":0,"LOW":0,"":0}
    for t in tasks:
        props = t.get("properties") or {}
        ts = props.get("hs_timestamp")
        try:
            if ts and int(ts) < now_ms: overdue += 1
        except Exception: pass
        by_priority[props.get("hs_task_priority","") or ""] = by_priority.get(props.get("hs_task_priority","") or "", 0) + 1
    return {
        "open_tasks": len(tasks),
        "overdue": overdue,
        "by_priority": by_priority,
        "total_from_api": data.get("total", len(tasks)),
    }

def interactions_summary():
    p = CRM / "interactions.csv"
    if not p.exists():
        return {"error": "no interactions.csv"}
    sent = replies = bounces = 0
    with p.open(newline="", errors="ignore") as f:
        reader = csv.DictReader(f)
        for row in reader:
            date_str = (row.get("date") or "")[:10]
            try:
                d = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            except Exception:
                continue
            if d < SINCE: continue
            kind = (row.get("type") or "").lower()
            outcome = (row.get("outcome") or "").lower()
            if "bounce" in kind or "bounce" in outcome: bounces += 1
            elif "reply" in kind: replies += 1
            elif "sent" in kind or "outreach" in kind or "email" in kind: sent += 1
    return {"sent_7d": sent, "replies_7d": replies, "bounces_7d": bounces,
            "reply_rate_pct": round(100*replies/sent,1) if sent else None}

def health_summary():
    p = LOGS / "health-check.log"
    if not p.exists():
        return {"error": "no health-check.log"}
    ok = fail = 0
    for line in p.read_text(errors="ignore").splitlines()[-2000:]:
        if "OK" in line: ok += 1
        if "FAIL" in line or "ERROR" in line: fail += 1
    return {"ok_lines": ok, "fail_lines": fail,
            "uptime_pct": round(100*ok/(ok+fail),1) if (ok+fail) else None}

def main():
    data = {
        "generated_at": NOW.isoformat(),
        "window_start": SINCE.isoformat(),
        "cron": cron_status(),
        "briefs": briefs_last_7(),
        "interactions": interactions_summary(),
        "health": health_summary(),
        "hubspot_tasks": hubspot_task_queue(),
        "token_usage": {"status": "not_collected",
                        "source_hint": "Anthropic Console → Usage tab; gateway logs at /tmp/openclaw/ do not carry per-request token counts"},
        "cache_hit_rate": {"status": "not_collected",
                           "source_hint": "Anthropic Console → Usage → cache_read_input_tokens vs input_tokens"},
        "log_lines_last_7d": {
            "outreach_send": count_log_lines(LOGS/"outreach_send.log", SINCE),
            "imap_bridge": count_log_lines(LOGS/"imap_bridge.log", SINCE),
            "contact_form_queue": count_log_lines(LOGS/"contact_form_queue.log", SINCE),
            "newsletter_send": count_log_lines(LOGS/"newsletter-send.log", SINCE),
            "drip": count_log_lines(LOGS/"drip.log", SINCE),
            "catchup": count_log_lines(LOGS/"catchup.log", SINCE),
        },
    }
    print(json.dumps(data, indent=2))

if __name__ == "__main__":
    main()
