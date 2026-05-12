#!/bin/bash

# Build and update site HTML with the latest briefs, trends, and guides.
# Runs automatically after daily content generation (git-sync-daily.sh).
# Also run manually any time: bash scripts/build-website.sh

set -euo pipefail
cd /Users/victoria/.openclaw/workspace

# ── Sync brief HTML files ────────────────────────────────────────────────────
mkdir -p site/briefs
cp content/briefs/2026-*.html site/briefs/ 2>/dev/null || true

# ── Sync trends HTML files ───────────────────────────────────────────────────
mkdir -p site/trends
cp content/trends/2026-*.html site/trends/ 2>/dev/null || true

# ── Find 5 most recent brief dates ───────────────────────────────────────────
LATEST_BRIEFS=($(find site/briefs -maxdepth 1 -name "*.html" \
  -not -name "template-*" -not -name "style-*" -not -name "NEWSLETTER-*" -not -name "*WEEKLY*" | \
  sed 's|site/briefs/||; s|\.html||' | \
  grep -E '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' | \
  sort -r | head -5))

if [[ ${#LATEST_BRIEFS[@]} -lt 1 ]]; then
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: No briefs found in site/briefs/"
  exit 1
fi

# ── Find 4 most recent trend dates ───────────────────────────────────────────
LATEST_TRENDS=($(find site/trends -maxdepth 1 -name "*.html" | \
  sed 's|site/trends/||; s|\.html||' | \
  grep -E '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' | \
  sort -r | head -4))

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Briefs: ${LATEST_BRIEFS[*]}"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Trends: ${#LATEST_TRENDS[@]} found"

# ── Inject briefs + trends blocks via Python ─────────────────────────────────
python3 - "${#LATEST_TRENDS[@]}" "${LATEST_BRIEFS[@]}" "---" "${LATEST_TRENDS[@]}" << 'PYEOF'
import sys, re

args = sys.argv[1:]
trend_count = int(args[0])
sep = args.index("---")
brief_dates = args[1:sep]
trend_dates = args[sep+1:]

months = ["January","February","March","April","May","June",
          "July","August","September","October","November","December"]

def fmt_brief(d):
    y, m, day = d.split("-")
    return f"{months[int(m)-1]} {int(day)}, {y}"

def fmt_trend(d):
    y, m, day = d.split("-")
    return f"Week of {months[int(m)-1]} {int(day)}, {y}"

# ── Build brief links ────────────────────────────────────────────────────────
brief_links = "\n".join(
    f'        <a href="briefs/{d}.html" class="brief-item">\n'
    f'          <div>\n'
    f'            <div class="brief-date">{fmt_brief(d)}</div>\n'
    f'            <h4>South Florida Insurance Brief</h4>\n'
    f'            <p>Market updates, regulatory news, carrier developments, and claim environment across South Florida.</p>\n'
    f'          </div>\n'
    f'          <div class="brief-arrow">→</div>\n'
    f'        </a>'
    for d in brief_dates
)

NEW_BRIEFS = (
    "    <!-- BRIEFS -->\n"
    '    <div id="tab-briefs" class="tab-panel active">\n'
    '      <div class="briefs-list">\n'
    + brief_links + "\n"
    "      </div>\n"
    "    </div>\n\n"
    "    <!-- WEEKLY -->"
)

# ── Build trend links ────────────────────────────────────────────────────────
if trend_dates:
    trend_links = "\n".join(
        f'        <a href="trends/{d}.html" class="brief-item">\n'
        f'          <div>\n'
        f'            <div class="brief-date">{fmt_trend(d)}</div>\n'
        f'            <h4>South Florida Service Provider Trends — Weekly Analysis</h4>\n'
        f'            <p>Market intelligence, regulatory developments, carrier movements, and emerging claim patterns across South Florida.</p>\n'
        f'          </div>\n'
        f'          <div class="brief-arrow">→</div>\n'
        f'        </a>'
        for d in trend_dates
    )
else:
    trend_links = '        <p style="color:#999;padding:20px 0;">Weekly trends are published each Saturday.</p>'

NEW_WEEKLY = (
    "    <!-- WEEKLY -->\n"
    '    <div id="tab-weekly" class="tab-panel">\n'
    '      <div class="briefs-list">\n'
    + trend_links + "\n"
    "      </div>\n"
    "    </div>\n\n"
    "    <!-- GUIDES -->"
)

for path in ["site/PA-WEBSITE.html", "site/index.html"]:
    try:
        with open(path) as f:
            content = f.read()

        updated = re.sub(
            r'[ \t]*<!-- BRIEFS -->.*?<!-- WEEKLY -->',
            NEW_BRIEFS,
            content,
            flags=re.DOTALL
        )
        updated = re.sub(
            r'[ \t]*<!-- WEEKLY -->.*?<!-- GUIDES -->',
            NEW_WEEKLY,
            updated,
            flags=re.DOTALL
        )

        if updated != content:
            with open(path, "w") as f:
                f.write(updated)
            print(f"[OK] Updated {path} — {len(brief_dates)} briefs, {len(trend_dates)} trends")
        else:
            print(f"[SKIP] No template markers found in {path}")
    except FileNotFoundError:
        print(f"[SKIP] {path} not found")
PYEOF

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Done."
