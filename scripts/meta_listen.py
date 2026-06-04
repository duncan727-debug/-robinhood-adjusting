#!/usr/bin/env python3
"""
Poll FB Page + IG for new comments + DMs. Log new activity, fire desktop alert + push.

State files in scripts/state/meta_listen/:
    last_seen.json — { "fb_comments": "<comment_id>", "ig_comments": "<id>", "ig_msgs": "<conv_id_msg_ts>" }
Log: scripts/meta_listen.log
Alerts: scripts/meta_alerts.log (Duncan-readable summary)
"""
import os, sys, json, urllib.parse, urllib.request, subprocess
from datetime import datetime
from pathlib import Path

WORKSPACE = Path("/Users/victoria/.openclaw/workspace")
SECRETS = WORKSPACE / "config" / ".secrets"
STATE_DIR = WORKSPACE / "scripts" / "state" / "meta_listen"
STATE_DIR.mkdir(parents=True, exist_ok=True)
STATE_FILE = STATE_DIR / "last_seen.json"
LOG = WORKSPACE / "scripts" / "meta_listen.log"
ALERTS = WORKSPACE / "scripts" / "meta_alerts.log"


def load_secrets():
    env = {}
    for line in SECRETS.read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


def log(msg, alert=False):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}\n"
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG, "a") as f:
        f.write(line)
    if alert:
        with open(ALERTS, "a") as f:
            f.write(line)
        # macOS notification — non-blocking
        try:
            subprocess.run([
                "osascript", "-e",
                f'display notification "{msg[:200]}" with title "Robinhood Social Alert"'
            ], timeout=3)
        except Exception:
            pass


def gget(path, params):
    url = f"https://graph.facebook.com/v25.0/{path}?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        log(f"API ERROR {path}: {e}")
        return {"data": [], "error": str(e)}


def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {}


def save_state(s):
    STATE_FILE.write_text(json.dumps(s, indent=2))


def check_fb_post_comments(page_id, token, state):
    """Pull recent FB Page posts and their comments. Alert on new ones since last_seen."""
    posts = gget(f"{page_id}/posts", {"fields": "id", "limit": 10, "access_token": token})
    last = state.get("fb_comment_ids", [])
    last_set = set(last)
    new_ids = []
    for p in posts.get("data", []):
        c = gget(f"{p['id']}/comments", {
            "fields": "id,from,message,created_time",
            "limit": 25, "access_token": token,
        })
        for cm in c.get("data", []):
            if cm["id"] not in last_set:
                new_ids.append(cm["id"])
                author = cm.get("from", {}).get("name", "user")
                msg = cm.get("message", "")[:160]
                log(f"NEW FB COMMENT from {author}: {msg} (post {p['id']})", alert=True)
    state["fb_comment_ids"] = list(last_set | set(new_ids))[-500:]


def check_ig_comments(ig_id, token, state):
    media = gget(f"{ig_id}/media", {"fields": "id", "limit": 10, "access_token": token})
    last = set(state.get("ig_comment_ids", []))
    new_ids = []
    for m in media.get("data", []):
        c = gget(f"{m['id']}/comments", {
            "fields": "id,username,text,timestamp",
            "limit": 25, "access_token": token,
        })
        for cm in c.get("data", []):
            if cm["id"] not in last:
                new_ids.append(cm["id"])
                log(f"NEW IG COMMENT from @{cm.get('username','?')}: {cm.get('text','')[:160]} (media {m['id']})", alert=True)
    state["ig_comment_ids"] = list(last | set(new_ids))[-500:]


def check_ig_dms(page_id, token, state):
    convs = gget(f"{page_id}/conversations", {
        "platform": "instagram",
        "fields": "id,updated_time,participants",
        "access_token": token,
    })
    last = state.get("ig_conv_seen", {})
    for c in convs.get("data", []):
        cid = c["id"]
        upd = c.get("updated_time", "")
        if last.get(cid) != upd:
            msgs = gget(f"{cid}/messages", {"fields": "from,message,created_time", "limit": 5, "access_token": token})
            for m in msgs.get("data", []):
                sender = m.get("from", {}).get("username") or m.get("from", {}).get("name", "?")
                if sender != "Robinhood Adjusting" and sender != "robinhoodadjusting":
                    log(f"NEW IG DM from @{sender}: {m.get('message','')[:200]}", alert=True)
            last[cid] = upd
    state["ig_conv_seen"] = last


def main():
    secrets = load_secrets()
    page_id = secrets["META_PAGE_ID"]
    page_token = secrets["META_PAGE_TOKEN"]
    ig_id = secrets.get("META_IG_BUSINESS_ID")

    state = load_state()
    first_run = not bool(state)

    check_fb_post_comments(page_id, page_token, state)
    if ig_id:
        check_ig_comments(ig_id, page_token, state)
        check_ig_dms(page_id, page_token, state)

    save_state(state)
    if first_run:
        log("first-run baseline established (no alerts fired)")


if __name__ == "__main__":
    main()
