#!/usr/bin/env python3
"""Extract verifiable claims from a daily brief and write an audit checklist.

A "claim" = a sentence containing at least one of:
  - a dollar figure ($X, $X million, $X billion)
  - a percentage (X% / X.X%)
  - an explicit count (N storms, N homes, N carriers)
  - a named carrier / agency / bill / statute
  - a hard date or deadline

The verifier sub-agent fills in verdicts against the checklist.
"""

import re
import sys
from pathlib import Path
from datetime import datetime

CARRIER_TERMS = [
    "Citizens", "Heritage", "FLOIR", "NOAA", "NWS", "NHC", "FEMA",
    "NFIP", "OIR", "HB ", "SB ", "House Bill", "Senate Bill",
]

CLAIM_PATTERNS = [
    re.compile(r"\$[\d,.]+\s*(million|billion|thousand|k|m|b)?", re.I),
    re.compile(r"\b\d+(\.\d+)?\s*%"),
    re.compile(r"\b(about|roughly|approximately|nearly|over|under)?\s*\d{1,3}(,\d{3})+\b"),
    re.compile(r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}(,?\s+20\d{2})?\b"),
    re.compile(r"\b20\d{2}\b"),
]


def split_sentences(text: str) -> list[str]:
    text = re.sub(r"\n+", " ", text)
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z*\"\[])", text)
    return [p.strip() for p in parts if p.strip()]


def is_claim(sentence: str) -> bool:
    if any(term in sentence for term in CARRIER_TERMS):
        return True
    for pat in CLAIM_PATTERNS:
        if pat.search(sentence):
            return True
    return False


def clean(sentence: str) -> str:
    s = re.sub(r"\s+", " ", sentence)
    s = re.sub(r"^[-*>\s]+", "", s)
    return s.strip()


def extract(brief_path: Path) -> list[str]:
    raw = brief_path.read_text()
    body = re.sub(r"^#.*$", "", raw, flags=re.MULTILINE)
    body = re.sub(r"\|.*\|", "", body)
    sentences = split_sentences(body)
    claims = []
    seen = set()
    for s in sentences:
        c = clean(s)
        if len(c) < 25 or len(c) > 400:
            continue
        if not is_claim(c):
            continue
        key = re.sub(r"[^a-z0-9]", "", c.lower())[:80]
        if key in seen:
            continue
        seen.add(key)
        claims.append(c)
    return claims


def write_checklist(brief_path: Path, claims: list[str]) -> Path:
    date = brief_path.stem
    out = brief_path.parent / f"{date}-verify.md"
    lines = [
        f"# Verification checklist — {brief_path.name}",
        f"_Generated {datetime.now().isoformat(timespec='seconds')}_",
        f"_Total claims: {len(claims)}_",
        "",
        "Verifier sub-agent: for each claim, mark `[x]` if verified against a primary or major-publisher source within the last 30 days. Mark `[!]` if contradicted. Mark `[?]` if not findable. Add the source URL inline.",
        "",
    ]
    for i, c in enumerate(claims, 1):
        lines.append(f"- [ ] **C{i}.** {c}")
        lines.append(f"      _source:_ ")
        lines.append("")
    out.write_text("\n".join(lines))
    return out


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: extract_brief_claims.py <brief.md> [more.md ...]", file=sys.stderr)
        sys.exit(2)
    for arg in sys.argv[1:]:
        p = Path(arg)
        if not p.exists():
            print(f"skip: {p} not found", file=sys.stderr)
            continue
        claims = extract(p)
        out = write_checklist(p, claims)
        print(f"{p.name}: {len(claims)} claims -> {out.name}")
