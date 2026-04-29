#!/bin/bash

# Build and update PA-WEBSITE.html with the latest briefs
# Runs after daily content generation to refresh the website

cd /Users/victoria/.openclaw/workspace

# Find 3 most recent brief files (*.html) by date in filename
# Briefs are named like: briefs/2026-04-29.html
LATEST_BRIEFS=($(find briefs -maxdepth 1 -name "*.html" -not -name "template-*" -not -name "style-*" | \
  sed 's|briefs/||; s|\.html||' | \
  grep -E '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' | \
  sort -r | \
  head -3))

if [[ ${#LATEST_BRIEFS[@]} -lt 3 ]]; then
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: Not enough briefs found (found ${#LATEST_BRIEFS[@]}, need 3)"
  exit 1
fi

# Extract date components for display
DATE1="${LATEST_BRIEFS[0]}"
DATE2="${LATEST_BRIEFS[1]}"
DATE3="${LATEST_BRIEFS[2]}"

# Convert dates to human-readable format (e.g., 2026-04-29 -> April 29, 2026)
format_date() {
  local date=$1
  local year="${date:0:4}"
  local month="${date:5:2}"
  local day="${date:8:2}"

  # Remove leading zero from day for display
  day=$((10#$day))

  local months=("January" "February" "March" "April" "May" "June"
                "July" "August" "September" "October" "November" "December")
  local month_idx=$((10#$month - 1))

  echo "${months[$month_idx]} $day, $year"
}

DISPLAY_DATE1=$(format_date "$DATE1")
DISPLAY_DATE2=$(format_date "$DATE2")
DISPLAY_DATE3=$(format_date "$DATE3")

# Create temporary file with updated briefs section
TEMP_FILE="/tmp/pa-website-update.html"

# Read the original file and replace the briefs list
sed "
  /<!-- BRIEFS -->/,/<!-- WEEKLY -->/c\\
    <!-- BRIEFS -->\\
      <div class=\"briefs-list\">\\
        <a href=\"briefs/${DATE1}.html\" class=\"brief-item\">\\
          <div>\\
            <div class=\"brief-date\">$DISPLAY_DATE1</div>\\
            <h4>South Florida Insurance Brief</h4>\\
            <p>Today's market updates, regulatory news, and claim environment across Miami-Dade, Broward, Palm Beach, Martin, St. Lucie, Indian River, and Brevard.</p>\\
          </div>\\
          <div class=\"brief-arrow\">→</div>\\
        </a>\\
        <a href=\"briefs/${DATE2}.html\" class=\"brief-item\">\\
          <div>\\
            <div class=\"brief-date\">$DISPLAY_DATE2</div>\\
            <h4>South Florida Insurance Brief</h4>\\
            <p>Carrier updates, legislative developments, and local loss environment summary.</p>\\
          </div>\\
          <div class=\"brief-arrow\">→</div>\\
        </a>\\
        <a href=\"briefs/${DATE3}.html\" class=\"brief-item\">\\
          <div>\\
            <div class=\"brief-date\">$DISPLAY_DATE3</div>\\
            <h4>South Florida Insurance Brief</h4>\\
            <p>Market snapshot, weather watch, and key claim topics for South Florida property owners.</p>\\
          </div>\\
          <div class=\"brief-arrow\">→</div>\\
        </a>\\
      </div>\\
\\
    <!-- WEEKLY -->
" PA-WEBSITE.html > "$TEMP_FILE"

if [[ $? -eq 0 ]]; then
  mv "$TEMP_FILE" PA-WEBSITE.html
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Website updated with latest briefs: $DATE1, $DATE2, $DATE3"
  exit 0
else
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: Failed to update website"
  rm -f "$TEMP_FILE"
  exit 1
fi
