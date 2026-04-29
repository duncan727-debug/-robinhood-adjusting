#!/bin/bash

# Build and update PA-WEBSITE.html with the latest briefs
# Runs after daily content generation to refresh the website

cd /Users/victoria/.openclaw/workspace

# Find 5 most recent brief files (*.html) by date in filename
# Briefs are named like: briefs/2026-04-29.html
LATEST_BRIEFS=($(find briefs -maxdepth 1 -name "*.html" -not -name "template-*" -not -name "style-*" | \
  sed 's|briefs/||; s|\.html||' | \
  grep -E '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' | \
  sort -r | \
  head -5))

if [[ ${#LATEST_BRIEFS[@]} -lt 5 ]]; then
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: Not enough briefs found (found ${#LATEST_BRIEFS[@]}, need 5)"
  exit 1
fi

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

# Generate briefs HTML
BRIEFS_HTML='    <!-- BRIEFS -->\n      <div class="briefs-list">'

for i in "${!LATEST_BRIEFS[@]}"; do
  DATE="${LATEST_BRIEFS[$i]}"
  DISPLAY_DATE=$(format_date "$DATE")

  BRIEFS_HTML+="\\n        <a href=\"briefs/${DATE}.html\" class=\"brief-item\">\\n"
  BRIEFS_HTML+="          <div>\\n"
  BRIEFS_HTML+="            <div class=\"brief-date\">$DISPLAY_DATE</div>\\n"
  BRIEFS_HTML+="            <h4>South Florida Insurance Brief</h4>\\n"
  BRIEFS_HTML+="            <p>Market updates, regulatory news, carrier developments, and claim environment across South Florida.</p>\\n"
  BRIEFS_HTML+="          </div>\\n"
  BRIEFS_HTML+="          <div class=\"brief-arrow\">→</div>\\n"
  BRIEFS_HTML+="        </a>"
done

BRIEFS_HTML+="\\n      </div>\\n\\n    <!-- WEEKLY -->"

# Update PA-WEBSITE.html with new briefs section
sed -i "" "
  /<!-- BRIEFS -->/,/<!-- WEEKLY -->/c\\
$BRIEFS_HTML
" PA-WEBSITE.html

if [[ $? -eq 0 ]]; then
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Website updated with 5 latest briefs: ${LATEST_BRIEFS[0]}, ${LATEST_BRIEFS[1]}, ${LATEST_BRIEFS[2]}, ${LATEST_BRIEFS[3]}, ${LATEST_BRIEFS[4]}"
  exit 0
else
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: Failed to update website"
  exit 1
fi
