#!/bin/bash

# Daily git sync: commit and push generated content to GitHub
# Runs after all daily cron jobs complete (briefs, content, trends, etc.)

cd /Users/victoria/.openclaw/workspace

# Check if there are any changes
if git diff --quiet && git diff --cached --quiet; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] No changes to commit"
    exit 0
fi

# Stage all changes
git add -A

# Create commit message with timestamp and summary
BRIEF_COUNT=$(find briefs -name "$(date +%Y-%m-%d).md" 2>/dev/null | wc -l)
CONTENT_COUNT=$(find content -type f -name "*.md" -mtime -1 2>/dev/null | wc -l)
TREND_COUNT=$(find trends -name "$(date +%Y-%m-%d).md" 2>/dev/null | wc -l)

SUMMARY="Daily content sync: "
[[ $BRIEF_COUNT -gt 0 ]] && SUMMARY+="$BRIEF_COUNT brief(s) "
[[ $CONTENT_COUNT -gt 0 ]] && SUMMARY+="$CONTENT_COUNT content piece(s) "
[[ $TREND_COUNT -gt 0 ]] && SUMMARY+="$TREND_COUNT trend(s) "

if [[ -z "$SUMMARY" ]]; then
    SUMMARY="Daily content sync"
fi

# Commit with message
git commit -m "$SUMMARY

Generated $(date '+%Y-%m-%d at %H:%M EDT')

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>" 2>&1

# Push to GitHub
git push origin main 2>&1

# Build website with latest briefs
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Building website..."
/Users/victoria/.openclaw/workspace/scripts/build-website.sh

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Sync complete"
