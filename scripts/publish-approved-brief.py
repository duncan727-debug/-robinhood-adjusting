#!/usr/bin/env python3
"""Publish an approved daily brief draft to the static website.

This is intentionally conservative:
- it reads publication/briefs/YYYY-MM-DD/README.md
- it writes static website files only when --write is passed
- it commits/pushes only when --commit-push is passed with --write
- it never sends email, posts to HubSpot, or touches subscriber systems
"""

from __future__ import annotations

import argparse
import html
import re
import subprocess
import sys
import textwrap
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from publication_guard import assert_publication_safe


ROOT = Path(__file__).resolve().parents[1]
SITE_URL = "https://robinhoodadjusting.com"


@dataclass
class Story:
    title: str
    paragraphs: list[str] = field(default_factory=list)


@dataclass
class Brief:
    date: str
    display_date: str
    title: str
    lead: str
    stories: list[Story]
    segment_notes: list[Story]
    sources: list[str]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Publish an approved publication/briefs/YYYY-MM-DD draft to site/briefs."
    )
    parser.add_argument("date", help="Brief date in YYYY-MM-DD format.")
    parser.add_argument("--write", action="store_true", help="Write site files.")
    parser.add_argument(
        "--commit-push",
        action="store_true",
        help="Commit generated site files, push to origin/main, and run live URL checks. Requires --write.",
    )
    parser.add_argument(
        "--headline",
        help="Override the archive/homepage card headline. Defaults to the first Top Stories heading.",
    )
    parser.add_argument(
        "--summary",
        help="Override the archive/homepage summary. Defaults to the lead sentence.",
    )
    parser.add_argument(
        "--tags",
        help="Comma-separated card tags. Defaults to three inferred tags from story headings.",
    )
    return parser.parse_args()


def validate_date(date_text: str) -> str:
    try:
        return datetime.strptime(date_text, "%Y-%m-%d").strftime("%Y-%m-%d")
    except ValueError as exc:
        raise SystemExit(f"Date must be YYYY-MM-DD, got {date_text!r}") from exc


def read_draft(date_text: str) -> str:
    draft_path = ROOT / "publication" / "briefs" / date_text / "README.md"
    if not draft_path.exists():
        raise SystemExit(f"Draft not found: {draft_path}")
    return draft_path.read_text(encoding="utf-8")


def split_sections(markdown: str) -> tuple[str, dict[str, str]]:
    title_match = re.search(r"^#\s+(.+)$", markdown, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else "South Florida Property Intelligence"
    matches = list(re.finditer(r"^##\s+(.+)$", markdown, re.MULTILINE))
    sections: dict[str, str] = {}
    for idx, match in enumerate(matches):
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(markdown)
        sections[match.group(1).strip().lower()] = markdown[start:end].strip()
    return title, sections


def parse_story_block(block: str) -> list[Story]:
    matches = list(re.finditer(r"^###\s+(.+)$", block, re.MULTILINE))
    stories: list[Story] = []
    for idx, match in enumerate(matches):
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(block)
        body = block[start:end].strip()
        paragraphs = [part.strip() for part in re.split(r"\n\s*\n", body) if part.strip()]
        stories.append(Story(match.group(1).strip(), paragraphs))
    return stories


def parse_sources(block: str) -> list[str]:
    sources: list[str] = []
    for line in block.splitlines():
        line = line.strip()
        if line.startswith("- "):
            sources.append(line[2:].strip())
    return sources


def parse_brief(date_text: str, markdown: str) -> Brief:
    title, sections = split_sections(markdown)
    display_date = datetime.strptime(date_text, "%Y-%m-%d").strftime("%B %-d, %Y")
    lead_block = sections.get("lead", "")
    lead = " ".join(line.strip() for line in lead_block.splitlines() if line.strip())
    stories = parse_story_block(sections.get("top stories", ""))
    segment_notes = parse_story_block(sections.get("segment notes", ""))
    sources = parse_sources(sections.get("sources", ""))
    if not lead:
        raise SystemExit("Draft is missing a ## Lead section.")
    if not stories:
        raise SystemExit("Draft is missing ### stories under ## Top Stories.")
    return Brief(date_text, display_date, title, lead, stories, segment_notes, sources)


def inline_markdown(text: str) -> str:
    escaped = html.escape(text)
    escaped = re.sub(
        r"\*\*(.+?)\*\*",
        r"<strong>\1</strong>",
        escaped,
    )
    escaped = re.sub(
        r"\[([^\]]+)\]\((https?://[^)]+)\)",
        lambda m: f'<a href="{m.group(2)}" style="color:#c41e3a;">{m.group(1)}</a>',
        escaped,
    )
    return escaped


def paragraph_html(text: str) -> str:
    if text.startswith("- "):
        items = [line[2:].strip() for line in text.splitlines() if line.strip().startswith("- ")]
        rendered = "\n".join(
            f'<li style="margin-bottom:6px;">{inline_markdown(item)}</li>' for item in items
        )
        return f'<ul style="margin:0 0 12px;padding-left:20px;">\n{rendered}\n</ul>'
    return f'<p style="margin:0 0 12px;">{inline_markdown(text)}</p>'


def story_html(story: Story) -> str:
    parts = [
        f'<h3 style="font-size:16px;color:#0f2d4a;margin:16px 0 8px;">{html.escape(story.title)}</h3>'
    ]
    parts.extend(paragraph_html(paragraph) for paragraph in story.paragraphs)
    return "\n".join(parts)


def segment_notes_html(notes: list[Story]) -> str:
    if not notes:
        return ""
    items = []
    for note in notes:
        body = " ".join(note.paragraphs)
        items.append(
            f'<li style="margin-bottom:6px;"><strong>{html.escape(note.title)}:</strong> {inline_markdown(body)}</li>'
        )
    return (
        '<h2 style="font-size:19px;color:#0f2d4a;margin:24px 0 12px;padding-bottom:6px;'
        'border-bottom:3px solid #c41e3a;">SEGMENT NOTES</h2>\n'
        '<ul style="margin:0 0 12px;padding-left:20px;">\n'
        + "\n".join(items)
        + "\n</ul>"
    )


def render_brief_page(brief: Brief) -> str:
    stories = "\n\n".join(story_html(story) for story in brief.stories)
    segment_html = segment_notes_html(brief.segment_notes)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(brief.title)}</title>
</head>
<body style="margin:0;padding:0;background:#f5f5f5;font-family:Georgia,'Times New Roman',serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f5f5f5;padding:20px 0;">
  <tr><td align="center">
    <table width="680" cellpadding="0" cellspacing="0" style="background:#ffffff;max-width:680px;width:100%;">
      <tr><td style="background:#0f2d4a;padding:28px 20px;text-align:center;border-bottom:5px solid #c9922a;">
        <img src="{SITE_URL}/logo-dark.svg" alt="Robinhood Adjusting" width="280" height="60" style="display:inline-block;max-width:100%;height:auto;">
        <div style="color:rgba(255,255,255,0.5);font-family:Arial,sans-serif;font-size:12px;letter-spacing:1px;margin-top:12px;">{html.escape(brief.display_date)}</div>
      </td></tr>
      <tr><td style="padding:30px 24px;">
        <div style="font-family:Georgia,'Times New Roman',serif;color:#333;line-height:1.7;max-width:640px;">
<h1 style="font-size:22px;color:#0f2d4a;margin:0 0 16px;">South Florida Property &amp; Insurance Industry Brief</h1>
<p style="margin:0 0 12px;"><strong>{html.escape(brief.display_date)}</strong> | Palm Beach, Miami-Dade, Broward, Martin, St. Lucie</p>

<p style="margin:0 0 12px;"><strong>Today's signal:</strong> {inline_markdown(brief.lead)}</p>

<h2 style="font-size:19px;color:#0f2d4a;margin:24px 0 12px;padding-bottom:6px;border-bottom:3px solid #c41e3a;">TOP STORIES</h2>

{stories}

{segment_html}

<p style="margin:0 0 12px;"><em>Brief prepared by Robinhood Intelligence | Research date: {html.escape(brief.display_date)}</em></p>
</div>
      </td></tr>
      <tr><td style="background:#fff8ea;padding:20px;text-align:center;border-top:1px solid #eee;border-bottom:1px solid #eee;">
        <p style="color:#0f2d4a;font-size:13px;font-weight:bold;margin:0 0 6px;">Got a claim question, referral, or property-risk issue?</p>
        <p style="color:#555;font-size:12px;margin:0 0 10px;line-height:1.55;">Start with a free virtual review or send the link to a homeowner who needs a straight read on damage, denial, or coverage questions.</p>
        <a href="{SITE_URL}/free-review.html" style="display:inline-block;background:#c9922a;color:#0f2d4a;padding:10px 22px;text-decoration:none;border-radius:4px;font-family:Arial,sans-serif;font-size:13px;font-weight:bold;">Book a Free Virtual Review</a>
      </td></tr>
      <tr><td style="background:#1a1a1a;padding:20px;text-align:center;border-top:4px solid #c41e3a;">
        <p style="color:#999;font-size:12px;margin:0;">Robinhood Adjusting &middot; Wellington, FL &middot; <a href="{SITE_URL}" style="color:#c41e3a;">robinhoodadjusting.com</a></p>
      </td></tr>
    </table>
  </td></tr>
</table>
</body>
</html>
"""


def first_sentence(text: str) -> str:
    sentence = re.split(r"(?<=[.!?])\s+", text.strip(), maxsplit=1)[0]
    return sentence[:180].rstrip()


def infer_tags(brief: Brief) -> list[str]:
    words = " ".join(story.title for story in brief.stories).lower()
    candidates = [
        ("Luxury", "luxury"),
        ("Deal tape", "deal"),
        ("Storm risk", "storm"),
        ("Insurance", "insurance"),
        ("Documentation", "document"),
        ("Rate transparency", "rate"),
        ("Real estate", "estate"),
        ("Permits", "permit"),
    ]
    tags = [label for label, needle in candidates if needle in words]
    return (tags + ["Claims", "South Florida", "Brief"])[:3]


def card_html(date_text: str, display_date: str, headline: str, summary: str, tags: list[str]) -> str:
    tag_html = "".join(f'<span class="tag">{html.escape(tag)}</span>' for tag in tags)
    return textwrap.dedent(
        f"""\
        <a class="card" href="/briefs/{date_text}">
          <div class="date">{html.escape(display_date)}</div>
          <h2>{html.escape(headline)}</h2>
          <p>{html.escape(summary)}</p>
          <div class="tagrow">{tag_html}</div>
        </a>"""
    )


def archive_html(date_text: str, display_date: str, headline: str) -> str:
    return f'<a href="/briefs/{date_text}"><span>{html.escape(headline)}</span><span>{html.escape(display_date)}</span></a>'


def home_item_html(date_text: str, display_date: str, headline: str, summary: str) -> str:
    return textwrap.dedent(
        f"""\
        <a href="briefs/{date_text}.html" class="brief-item">
          <div>
            <div class="brief-date">{html.escape(display_date)}</div>
            <h4>{html.escape(headline)}</h4>
            <p>{html.escape(summary)}</p>
          </div>
          <div class="brief-arrow">&rarr;</div>
        </a>"""
    )


def replace_card_block(index_html: str, date_text: str, new_card: str, max_cards: int = 4) -> str:
    start = index_html.index('    <div class="grid">')
    end = index_html.index("\n    </div>\n\n    <h2 class=\"section-title\">Recent Archive</h2>", start)
    block = index_html[start:end]
    cards = re.findall(r'      <a class="card" href="/briefs/[^"]+">.*?\n      </a>', block, flags=re.S)
    cards = [card for card in cards if f'href="/briefs/{date_text}"' not in card]
    cards.insert(0, textwrap.indent(new_card, "      ").lstrip())
    cards = cards[:max_cards]
    new_block = '    <div class="grid">\n' + "\n".join(cards) + "\n"
    return index_html[:start] + new_block + index_html[end:]


def replace_archive_block(index_html: str, date_text: str, new_archive: str) -> str:
    start = index_html.index('    <div class="archive">')
    end = index_html.index("\n    </div>\n\n    <section class=\"cta\">", start)
    block = index_html[start:end]
    rows = re.findall(r'      <a href="/briefs/[^"]+">.*?</a>', block, flags=re.S)
    rows = [row for row in rows if f'href="/briefs/{date_text}"' not in row]
    rows.insert(0, "      " + new_archive)
    new_block = '    <div class="archive">\n' + "\n".join(rows) + "\n"
    return index_html[:start] + new_block + index_html[end:]


def replace_home_brief_items(home_html: str, date_text: str, new_item: str, max_items: int = 4) -> str:
    start_marker = '    <div id="tab-briefs" class="tab-panel active">\n      <div class="briefs-list">\n'
    end_marker = '        <a href="briefs/" class="brief-item">'
    start = home_html.index(start_marker) + len(start_marker)
    archive_start = home_html.index(end_marker, start)
    items_block = home_html[start:archive_start]
    items = re.findall(r'        <a href="briefs/[^"]+\.html" class="brief-item">.*?\n        </a>', items_block, flags=re.S)
    items = [item for item in items if f'href="briefs/{date_text}.html"' not in item]
    items.insert(0, textwrap.indent(new_item, "        ").lstrip())
    items = items[:max_items]
    new_block = "\n".join(items) + "\n"
    return home_html[:start] + new_block + home_html[archive_start:]


def update_sitemap(sitemap: str, date_text: str) -> str:
    loc = f"{SITE_URL}/briefs/{date_text}"
    if loc in sitemap:
        return sitemap
    entry = textwrap.dedent(
        f"""\
          <url>
            <loc>{loc}</loc>
            <priority>0.8</priority>
          </url>
        """
    )
    insert_at = sitemap.index("  <url>\n    <loc>https://robinhoodadjusting.com/briefs/</loc>")
    return sitemap[:insert_at] + entry + sitemap[insert_at:]


def build_updates(brief: Brief, args: argparse.Namespace) -> dict[Path, str]:
    headline = args.headline or brief.stories[0].title
    summary = args.summary or first_sentence(brief.lead)
    tags = [tag.strip() for tag in args.tags.split(",")] if args.tags else infer_tags(brief)
    brief_page = render_brief_page(brief)

    brief_path = ROOT / "site" / "briefs" / f"{brief.date}.html"
    index_path = ROOT / "site" / "briefs" / "index.html"
    home_path = ROOT / "site" / "index.html"
    sitemap_path = ROOT / "site" / "sitemap.xml"

    index_html = index_path.read_text(encoding="utf-8")
    index_html = replace_card_block(
        index_html, brief.date, card_html(brief.date, brief.display_date, headline, summary, tags)
    )
    index_html = replace_archive_block(index_html, brief.date, archive_html(brief.date, brief.display_date, headline))

    home_html = home_path.read_text(encoding="utf-8")
    home_html = replace_home_brief_items(
        home_html, brief.date, home_item_html(brief.date, brief.display_date, headline, summary)
    )

    sitemap = update_sitemap(sitemap_path.read_text(encoding="utf-8"), brief.date)

    return {
        brief_path: brief_page,
        index_path: index_html,
        home_path: home_html,
        sitemap_path: sitemap,
    }


def write_updates(updates: dict[Path, str]) -> list[Path]:
    changed: list[Path] = []
    for path, content in updates.items():
        current = path.read_text(encoding="utf-8") if path.exists() else ""
        if current != content:
            path.write_text(content, encoding="utf-8")
            changed.append(path)
    return changed


def run(cmd: list[str]) -> None:
    print("+", " ".join(cmd))
    subprocess.run(cmd, cwd=ROOT, check=True)


def commit_push(paths: list[Path], date_text: str) -> None:
    if not paths:
        print("No site changes to commit.")
        return
    rel_paths = [str(path.relative_to(ROOT)) for path in paths]
    run(["git", "add", *rel_paths])
    run(["git", "commit", "-m", f"Publish approved brief for {date_text}"])
    run(["git", "push", "origin", "main"])


def live_check(date_text: str) -> None:
    urls = [
        f"{SITE_URL}/briefs/{date_text}",
        f"{SITE_URL}/briefs/",
        SITE_URL + "/",
        f"{SITE_URL}/sitemap.xml",
    ]
    for url in urls:
        with urllib.request.urlopen(url, timeout=20) as response:
            print(f"{response.status} {url}")


def main() -> int:
    args = parse_args()
    date_text = validate_date(args.date)
    if args.commit_push and not args.write:
        raise SystemExit("--commit-push requires --write")

    draft = read_draft(date_text)
    assert_publication_safe(draft, f"publication/briefs/{date_text}/README.md")
    brief = parse_brief(date_text, draft)
    updates = build_updates(brief, args)
    for path, content in updates.items():
        assert_publication_safe(content, path)
    changed = [
        path for path, content in updates.items()
        if not path.exists() or path.read_text(encoding="utf-8") != content
    ]

    print(f"Draft: publication/briefs/{date_text}/README.md")
    print(f"Headline: {args.headline or brief.stories[0].title}")
    print("Files that would change:" if not args.write else "Files changed:")
    for path in changed:
        print(f"- {path.relative_to(ROOT)}")

    if not args.write:
        print("\nDry run only. Re-run with --write after approval.")
        return 0

    changed = write_updates(updates)
    if args.commit_push:
        commit_push(changed, date_text)
        live_check(date_text)
    elif changed:
        print("\nWrote files. Review them, then commit/push separately or re-run with --commit-push.")
    else:
        print("\nNo changes needed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
