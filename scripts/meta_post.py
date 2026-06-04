#!/usr/bin/env python3
"""
Post today's content (or a specified date) to FB Page and IG via Meta Graph API.

Usage:
    python3 meta_post.py                    # post today's content/<YYYY-MM-DD>/facebook.md
    python3 meta_post.py 2026-06-01         # post specific date
    python3 meta_post.py 2026-06-01 --fb-only
    python3 meta_post.py 2026-06-01 --ig-only --image /path/to/img.jpg

Requires /Users/victoria/.openclaw/workspace/config/.secrets with:
    META_PAGE_TOKEN, META_PAGE_ID, META_IG_BUSINESS_ID
"""
import os
import sys
import re
import json
import urllib.parse
import urllib.request
import argparse
from datetime import datetime
from pathlib import Path

WORKSPACE = Path("/Users/victoria/.openclaw/workspace")
SECRETS = WORKSPACE / "config" / ".secrets"
LOG = WORKSPACE / "scripts" / "meta_post.log"
SENT_DIR = WORKSPACE / "scripts" / "state" / "meta_posted"
SENT_DIR.mkdir(parents=True, exist_ok=True)


def load_secrets():
    env = {}
    for line in SECRETS.read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG, "a") as f:
        f.write(line + "\n")


def md_to_post(md_text):
    """Strip MD header, convert **bold** to plain, normalize whitespace."""
    lines = md_text.splitlines()
    # Drop leading '# ...' header lines and blanks
    while lines and (lines[0].startswith("#") or not lines[0].strip()):
        lines.pop(0)
    body = "\n".join(lines).strip()
    body = re.sub(r"\*\*(.+?)\*\*", r"\1", body)
    body = re.sub(r"\*(.+?)\*", r"\1", body)
    return body


def graph_post(path, params, method="POST"):
    url = f"https://graph.facebook.com/v25.0/{path}"
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(url, data=data, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            body = json.loads(e.read().decode())
        except Exception:
            body = {"raw_error": str(e)}
        body["_http_status"] = e.code
        return body


def graph_get(path, params):
    url = f"https://graph.facebook.com/v25.0/{path}?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def post_fb(message, page_id, token):
    return graph_post(f"{page_id}/feed", {"message": message, "access_token": token})


def post_ig(caption, image_url, ig_id, token):
    # Two-step: create media container, then publish
    container = graph_post(f"{ig_id}/media", {
        "image_url": image_url,
        "caption": caption,
        "access_token": token,
    })
    if "id" not in container:
        return container
    return graph_post(f"{ig_id}/media_publish", {
        "creation_id": container["id"],
        "access_token": token,
    })


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("date", nargs="?", default=datetime.now().strftime("%Y-%m-%d"))
    ap.add_argument("--fb-only", action="store_true")
    ap.add_argument("--ig-only", action="store_true")
    ap.add_argument("--image", help="image URL or local path for IG post")
    ap.add_argument("--force", action="store_true", help="re-post even if already sent")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    secrets = load_secrets()
    page_id = secrets["META_PAGE_ID"]
    page_token = secrets["META_PAGE_TOKEN"]
    ig_id = secrets.get("META_IG_BUSINESS_ID")

    content_dir = WORKSPACE / "content" / args.date
    fb_file = content_dir / "facebook.md"
    ig_file = content_dir / "instagram.md"

    fb_body = None
    if not args.ig_only:
        if not fb_file.exists():
            log(f"NO CONTENT: {fb_file}")
            sys.exit(1)
        fb_body = md_to_post(fb_file.read_text())
        log(f"loaded {fb_file.name} ({len(fb_body)} chars)")

    ig_body = None
    if not args.fb_only:
        # Prefer IG-specific copy; fall back to FB body if missing.
        if ig_file.exists():
            ig_body = md_to_post(ig_file.read_text())
            log(f"loaded {ig_file.name} ({len(ig_body)} chars)")
        elif fb_file.exists():
            ig_body = md_to_post(fb_file.read_text())
            log(f"loaded {fb_file.name} as IG fallback ({len(ig_body)} chars)")
        else:
            log(f"NO IG CONTENT: {ig_file} or {fb_file}")
            sys.exit(1)

    if args.dry_run:
        print("--- DRY RUN ---")
        if fb_body: print("== FB =="); print(fb_body)
        if ig_body: print("== IG =="); print(ig_body)
        return

    sent_marker = SENT_DIR / f"{args.date}.json"
    sent = json.loads(sent_marker.read_text()) if sent_marker.exists() else {}

    # ---- FB ----
    if not args.ig_only:
        if sent.get("fb") and not args.force:
            log(f"SKIP fb: already posted ({sent['fb']})")
        else:
            res = post_fb(fb_body, page_id, page_token)
            if "id" in res:
                sent["fb"] = res["id"]
                log(f"FB POSTED: {res['id']}")
            else:
                log(f"FB ERROR: {res}")
                sys.exit(2)

    # ---- IG ----
    if not args.fb_only and ig_id and args.image:
        if sent.get("ig") and not args.force:
            log(f"SKIP ig: already posted ({sent['ig']})")
        else:
            # IG requires publicly-accessible image URL
            img = args.image
            if img.startswith("/") or img.startswith("./"):
                log(f"IG ERROR: image must be public URL, got local path {img}")
            else:
                res = post_ig(ig_body[:2200], img, ig_id, page_token)  # IG caption limit
                if "id" in res:
                    sent["ig"] = res["id"]
                    log(f"IG POSTED: {res['id']}")
                else:
                    log(f"IG ERROR: {res}")

    sent_marker.write_text(json.dumps(sent, indent=2))


if __name__ == "__main__":
    main()
