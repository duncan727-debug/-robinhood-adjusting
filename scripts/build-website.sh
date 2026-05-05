#!/bin/bash

# Build and update site HTML with the latest briefs
# Runs after daily content generation to refresh the website

set -euo pipefail
cd /Users/victoria/.openclaw/workspace

# Sync any new brief HTML files from content/briefs/ into site/briefs/
mkdir -p site/briefs
cp content/briefs/2026-*.html site/briefs/ 2>/dev/null || true

# Find 5 most recent brief dates from site/briefs/ (authoritative source)
LATEST_BRIEFS=($(find site/briefs -maxdepth 1 -name "*.html" \
  -not -name "template-*" -not -name "style-*" -not -name "NEWSLETTER-*" -not -name "*WEEKLY*" | \
  sed 's|site/briefs/||; s|\.html||' | \
  grep -E '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' | \
  sort -r | head -5))

if [[ ${#LATEST_BRIEFS[@]} -lt 1 ]]; then
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: No briefs found in site/briefs/"
  exit 1
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Found ${#LATEST_BRIEFS[@]} briefs: ${LATEST_BRIEFS[*]}"

# Use Python to inject the briefs block — preserves tab structure
python3 - "${LATEST_BRIEFS[@]}" << 'PYEOF'
import sys, re

dates = sys.argv[1:]

months = ["January","February","March","April","May","June",
          "July","August","September","October","November","December"]

def fmt(d):
    y, m, day = d.split("-")
    return f"{months[int(m)-1]} {int(day)}, {y}"

links = "\n".join(
    f'        <a href="briefs/{d}.html" class="brief-item">\n'
    f'          <div>\n'
    f'            <div class="brief-date">{fmt(d)}</div>\n'
    f'            <h4>South Florida Insurance Brief</h4>\n'
    f'            <p>Market updates, regulatory news, carrier developments, and claim environment across South Florida.</p>\n'
    f'          </div>\n'
    f'          <div class="brief-arrow">→</div>\n'
    f'        </a>'
    for d in dates
)

# Preserves the tab-briefs panel wrapper so the tab system stays intact
NEW_BLOCK = (
    "    <!-- BRIEFS -->\n"
    '    <div id="tab-briefs" class="tab-panel active">\n'
    '      <div class="briefs-list">\n'
    + links + "\n"
    "      </div>\n"
    "    </div>\n\n"
    "    <!-- WEEKLY -->"
)

for path in ["site/index.html", "site/PA-WEBSITE.html"]:
    try:
        with open(path) as f:
            content = f.read()
        updated = re.sub(
            r'[ \t]*<!-- BRIEFS -->.*?<!-- WEEKLY -->',
            NEW_BLOCK,
            content,
            flags=re.DOTALL
        )
        if updated != content:
            with open(path, "w") as f:
                f.write(updated)
            print(f"[OK] Updated {path}")
        else:
            print(f"[SKIP] No BRIEFS block found in {path}")
    except FileNotFoundError:
        print(f"[SKIP] {path} not found")
PYEOF

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Done."
