#!/usr/bin/env python3
"""Guardrails for outward-facing publication artifacts."""

from __future__ import annotations

import re
from pathlib import Path


INTERNAL_PATTERNS = [
    (re.compile(r"^\s*#{1,6}\s+watchlist\b", re.IGNORECASE | re.MULTILINE), "watchlist section"),
    (re.compile(r"\bwatchlist\b", re.IGNORECASE), "watchlist reference"),
    (re.compile(r"\binternal\s+(?:only|note|notes|info|memo|review|test)\b", re.IGNORECASE), "internal-only marker"),
    (re.compile(r"\bCRM\b", re.IGNORECASE), "CRM reference"),
    (re.compile(r"\bHubSpot\b", re.IGNORECASE), "HubSpot reference"),
    (re.compile(r"\boutreach\b", re.IGNORECASE), "outreach reference"),
    (re.compile(r"\bno-send\b", re.IGNORECASE), "no-send workflow reference"),
]


def strip_html_tags(text: str) -> str:
    text = re.sub(r"<script[^>]*>.*?</script>", " ", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.IGNORECASE | re.DOTALL)
    return re.sub(r"<[^>]+>", " ", text)


def internal_publication_hits(text: str) -> list[str]:
    plain = strip_html_tags(text)
    hits: list[str] = []
    for pattern, label in INTERNAL_PATTERNS:
        match = pattern.search(plain)
        if not match:
            continue
        start = max(match.start() - 70, 0)
        end = min(match.end() + 70, len(plain))
        snippet = re.sub(r"\s+", " ", plain[start:end]).strip()
        hits.append(f"{label}: {snippet}")
    return hits


def assert_publication_safe(text: str, source: str | Path) -> None:
    hits = internal_publication_hits(text)
    if not hits:
        return
    detail = "\n".join(f"- {hit}" for hit in hits)
    raise SystemExit(
        f"ERROR: outward-facing publication contains internal-only content in {source}.\n"
        "Remove watchlist/internal operational material before publishing or sending.\n"
        f"{detail}"
    )
