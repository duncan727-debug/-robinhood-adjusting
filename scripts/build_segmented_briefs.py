#!/usr/bin/env python3
"""
Split today's generic brief HTML into 3 audience-segmented variants.

Reads:  content/briefs/{date}.html
Writes: content/briefs/{date}-{homeowner|service-provider|real-estate}.html

Strategy: each story section has up to three "What it means for X" callout
paragraphs (homeowners, service providers, real estate professionals). For
each segment variant, strip the two non-matching callouts and drop any story
section that has no callout for the target audience.

Title and H1 are rewritten per segment so the open-rate-driving subject
matches the audience.
"""
from __future__ import annotations

import re
import sys
from datetime import date
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent
BRIEFS_DIR = WORKSPACE / "content" / "briefs"

SEGMENTS = [
    {
        "key": "homeowner",
        "title": "South Florida Property Intelligence",
        "h1": "South Florida Property & Insurance — Homeowner Brief",
        "match": "homeowners",
    },
    {
        "key": "service-provider",
        "title": "South Florida Trade Professional Brief",
        "h1": "South Florida Property & Insurance — Trade Professional Brief",
        "match": "service providers",
    },
    {
        "key": "real-estate",
        "title": "South Florida Real Estate & Insurance Brief",
        "h1": "South Florida Property & Insurance — Real Estate & Insurance Brief",
        "match": "real estate",
    },
]

CALLOUT_RE = re.compile(
    r"<p[^>]*>\s*<strong>\s*What it means for ([^:<]+?)\s*:\s*</strong>",
    re.IGNORECASE,
)


def callout_audience(p_html: str) -> str | None:
    """Return the lowercased audience name from a 'What it means for X:' paragraph, or None."""
    m = CALLOUT_RE.search(p_html)
    return m.group(1).strip().lower() if m else None


def split_into_blocks(html: str) -> list[str]:
    """Split body HTML into top-level block elements while preserving order.

    We split on the boundaries between <h1|h2|h3|p|ul|ol|hr|div|table> tags at
    the start of a line. Whitespace between blocks is retained on the
    following block. Good enough for our hand-rendered HTML.
    """
    # Insert a sentinel before each block-level opening tag, then split.
    pattern = re.compile(
        r"(?=<(?:h[1-6]|p|ul|ol|hr|div|table)\b)", re.IGNORECASE
    )
    parts = pattern.split(html)
    return [p for p in parts if p.strip()]


def filter_for_segment(body_html: str, match_token: str) -> str:
    """Return body HTML with non-matching callouts removed and story sections
    that have no matching callout dropped entirely.

    A 'story section' is everything from an <h3> up to (but not including) the
    next <h3>, <h2>, or <hr>.
    """
    blocks = split_into_blocks(body_html)

    # First pass: drop non-matching callout paragraphs.
    kept: list[str] = []
    for block in blocks:
        aud = callout_audience(block)
        if aud is None:
            kept.append(block)
        elif match_token in aud:
            kept.append(block)
        # else: non-matching callout — skip

    # Second pass: walk story sections (<h3> ... up to next <h3>|<h2>|<hr>).
    # Drop a section if it contains no "What it means for {match_token}" callout.
    result: list[str] = []
    i = 0
    n = len(kept)
    while i < n:
        block = kept[i]
        if re.match(r"\s*<h3\b", block, re.IGNORECASE):
            # collect this story section
            section = [block]
            j = i + 1
            while j < n and not re.match(
                r"\s*<(h3|h2|hr)\b", kept[j], re.IGNORECASE
            ):
                section.append(kept[j])
                j += 1
            # has a callout for our audience?
            has_match = any(
                (a := callout_audience(b)) and match_token in a for b in section
            )
            if has_match:
                result.extend(section)
            # else: drop entire story
            i = j
        else:
            result.append(block)
            i += 1

    return "".join(result)


def split_doc(html: str) -> tuple[str, str, str]:
    """Return (head_html, body_inner_html, tail_html) so we can rewrite title/h1
    and replace the body inner content.
    """
    body_open = re.search(r"<body[^>]*>", html, re.IGNORECASE)
    body_close = re.search(r"</body\s*>", html, re.IGNORECASE)
    if not body_open or not body_close:
        # No body wrapper — treat the whole thing as body.
        return "", html, ""
    head = html[: body_open.end()]
    body = html[body_open.end() : body_close.start()]
    tail = html[body_close.start() :]
    return head, body, tail


def rewrite_titles(head_html: str, body_html: str, title: str, h1: str) -> tuple[str, str]:
    head_html = re.sub(
        r"<title>[^<]*</title>",
        f"<title>{title} — {date.today().strftime('%B %d, %Y')}</title>",
        head_html,
        count=1,
        flags=re.IGNORECASE,
    )
    body_html = re.sub(
        r"(<h1[^>]*>)[^<]*(</h1>)",
        lambda m: f"{m.group(1)}{h1}{m.group(2)}",
        body_html,
        count=1,
    )
    return head_html, body_html


def build_segment(src_html: str, segment: dict, date_str: str) -> str:
    head, body, tail = split_doc(src_html)
    body = filter_for_segment(body, segment["match"])

    # Rewrite title/h1 using the brief's own date if we can parse it from the
    # source, otherwise fall back to date_str.
    title = f"{segment['title']} — {date_str}"
    head = re.sub(
        r"<title>[^<]*</title>", f"<title>{title}</title>", head,
        count=1, flags=re.IGNORECASE,
    )
    body = re.sub(
        r"(<h1[^>]*>)[^<]*(</h1>)",
        lambda m: f"{m.group(1)}{segment['h1']}{m.group(2)}",
        body, count=1,
    )
    return head + body + tail


def main() -> int:
    date_str = sys.argv[1] if len(sys.argv) > 1 else date.today().isoformat()
    src = BRIEFS_DIR / f"{date_str}.html"
    if not src.exists():
        print(f"ERROR: {src} not found", file=sys.stderr)
        return 1

    src_html = src.read_text(encoding="utf-8")

    for seg in SEGMENTS:
        out = BRIEFS_DIR / f"{date_str}-{seg['key']}.html"
        out.write_text(build_segment(src_html, seg, date_str), encoding="utf-8")
        size = out.stat().st_size
        print(f"  wrote {out.relative_to(WORKSPACE)} ({size:,} bytes)")

    print(f"OK: 3 segmented variants written for {date_str}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
