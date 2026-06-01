#!/usr/bin/env python3
"""Render the latest weekly trends markdown to HTML and place it in content/trends/.

Saturday trends are hand-written to `trends/YYYY-MM-DD.md`. The site builder
reads from `content/trends/YYYY-MM-DD.html`, and the Sunday email script reads
from the same path. Nothing was bridging the two — the 2026-05-30 trends
markdown was written but never HTML-ized, so the Sunday email re-sent the
2026-05-23 trends and the site card never updated. This script closes that gap.

Usage:
    python3 scripts/build_weekly_trends_html.py                # builds latest
    python3 scripts/build_weekly_trends_html.py 2026-05-30     # builds a specific date
"""
from __future__ import annotations

import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

import markdown

WORKSPACE = Path(__file__).resolve().parent.parent
SRC_DIR = WORKSPACE / "trends"
DST_DIR = WORKSPACE / "content" / "trends"


def find_template() -> Path:
    """Use the most recent existing trends HTML as the template."""
    candidates = sorted(DST_DIR.glob("2026-*.html"), reverse=True)
    if not candidates:
        raise SystemExit("no template trends HTML found in content/trends/")
    return candidates[0]


def week_range_label(date_str: str) -> str:
    """Saturday trends cover Sun-Sat (7 days ending Saturday) or Mon-Sat."""
    end = datetime.strptime(date_str, "%Y-%m-%d")
    start = end - timedelta(days=6)
    if start.month == end.month:
        return f"Week of {start.strftime('%B')} {start.day}–{end.day}, {end.year}"
    return f"Week of {start.strftime('%B %-d')}–{end.strftime('%B %-d, %Y')}"


def published_label(date_str: str) -> str:
    d = datetime.strptime(date_str, "%Y-%m-%d")
    return d.strftime("%B %-d, %Y")


def build(md_path: Path) -> Path:
    date_str = md_path.stem
    src_md = md_path.read_text()
    body_md = re.sub(
        r"^# .*\n+\*\*[^\n]+\*\*[^\n]*\n+(---\n+)?",
        "",
        src_md,
        count=1,
    )
    body_html = markdown.markdown(body_md, extensions=["tables", "fenced_code"])

    template = find_template().read_text()
    out = re.sub(
        r"(<main>)(.*?)(</main>)",
        lambda m: m.group(1) + "\n" + body_html + "\n" + m.group(3),
        template,
        count=1,
        flags=re.DOTALL,
    )

    week = week_range_label(date_str)
    pub = published_label(date_str)
    out = re.sub(
        r"<div class=\"date-info\">[^<]*</div>",
        f'<div class="date-info">{week} | Published {pub}</div>',
        out,
        count=1,
    )
    out = re.sub(
        r"<title>[^<]*</title>",
        f"<title>South Florida Market Intelligence | {pub}</title>",
        out,
        count=1,
    )

    DST_DIR.mkdir(parents=True, exist_ok=True)
    dst = DST_DIR / f"{date_str}.html"
    dst.write_text(out)

    md_copy = DST_DIR / f"{date_str}.md"
    if not md_copy.exists():
        md_copy.write_text(src_md)

    return dst


def latest_md() -> Path:
    candidates = sorted(SRC_DIR.glob("2026-*.md"), reverse=True)
    if not candidates:
        raise SystemExit("no trends markdown found in trends/")
    return candidates[0]


def main() -> int:
    if len(sys.argv) > 1:
        date_str = sys.argv[1]
        md_path = SRC_DIR / f"{date_str}.md"
        if not md_path.exists():
            print(f"no markdown at {md_path}", file=sys.stderr)
            return 2
    else:
        md_path = latest_md()
    out = build(md_path)
    print(f"built {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
