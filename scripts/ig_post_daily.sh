#!/bin/bash
# Daily IG post pipeline for @robinhoodadjusting.
#   1. Build today's branded 1080x1080 image from content/<date>/instagram.md
#   2. Commit + push to GitHub (Netlify auto-deploys site/ → robinhoodadjusting.com)
#   3. Wait for deploy
#   4. Post to IG via Graph API using the public image URL
#
# Scheduled at 08:45am Mon-Sat (after the daily content sync that writes instagram.md).

set -e
cd /Users/victoria/.openclaw/workspace

DATE=$(date +%Y-%m-%d)
LOG=scripts/ig_post_daily.log
IMG_PATH=site/assets/ig/${DATE}.jpg
IMG_URL=https://robinhoodadjusting.com/assets/ig/${DATE}.jpg
MD=content/${DATE}/instagram.md

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG"; }

log "=== IG post pipeline: $DATE ==="

if [ ! -f "$MD" ]; then
  log "no instagram.md for $DATE — abort"
  exit 0
fi

# Build image (idempotent)
if [ ! -f "$IMG_PATH" ]; then
  log "building $IMG_PATH"
  python3 scripts/ig_image_builder.py "$DATE" 2>&1 | tee -a "$LOG"
else
  log "$IMG_PATH already exists"
fi

# Commit + push if untracked or modified
if ! git diff --quiet "$IMG_PATH" 2>/dev/null || ! git ls-files --error-unmatch "$IMG_PATH" >/dev/null 2>&1; then
  log "committing + pushing $IMG_PATH"
  git add "$IMG_PATH"
  git commit -m "ig: daily image $DATE" -m "Auto-built by ig_post_daily.sh" 2>&1 | tee -a "$LOG"
  git push 2>&1 | tee -a "$LOG"
  log "waiting 180s for Netlify deploy"
  sleep 180
else
  log "$IMG_PATH already committed — skipping push/wait"
fi

# Verify the image is reachable on the public URL
if ! curl -sfI "$IMG_URL" | head -1 | grep -q "200"; then
  log "ERROR: $IMG_URL not reachable yet — abort post"
  exit 1
fi
log "verified $IMG_URL is live"

# Post
log "posting to IG"
python3 scripts/meta_post.py "$DATE" --ig-only --image "$IMG_URL" 2>&1 | tee -a "$LOG"

log "=== done ==="
