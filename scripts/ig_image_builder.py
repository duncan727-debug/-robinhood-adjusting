#!/usr/bin/env python3
"""
Build the daily Instagram post image for @robinhoodadjusting.

Reads content/<date>/instagram.md, picks a base photo from
site/assets/ig/library/ by topic keyword scoring, and composites a
1080x1080 branded image at site/assets/ig/<date>.jpg.

Usage:
    python3 ig_image_builder.py                # today
    python3 ig_image_builder.py 2026-06-01     # specific date
    python3 ig_image_builder.py --force        # rebuild even if file exists
"""
import re
import sys
import random
from datetime import datetime
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

WORKSPACE = Path("/Users/victoria/.openclaw/workspace")
CONTENT_DIR = WORKSPACE / "content"
LIBRARY = WORKSPACE / "site" / "assets" / "ig" / "library"
OUT_DIR = WORKSPACE / "site" / "assets" / "ig"

NAVY = (15, 45, 74)
GOLD = (201, 146, 42)
CRIMSON = (196, 30, 58)
WHITE = (255, 255, 255)

GEORGIA_BOLD = "/System/Library/Fonts/Supplemental/Georgia Bold.ttf"
HELVETICA = "/System/Library/Fonts/Helvetica.ttc"

# Topic vocab → matches against library filename prefix
TOPIC_KEYWORDS = {
    "roof":         ["roof", "shingle", "tile", "wind-mit", "1802", "hb 815", "hb815", "re-roof"],
    "ac":           ["ac ", "a/c", "hvac", "air conditioning", "condenser", "compressor", "freon"],
    "plumbing":     ["plumb", "leak", "pipe", "burst", "supply line", "drain"],
    "water-damage": ["water damage", "ceiling", "mold", "flood", "seepage", "mitigation", "drying"],
    "storm":        ["storm", "hurricane", "wind", "rain", "tropical", "cone", "named storm"],
    "real-estate":  ["real estate", "realtor", "listing", "buyer", "seller", "closing", "4-point", "wind-mit"],
    "contractor":   ["contractor", "remodel", "rebuild", "general contractor", "gc ", "build"],
    "paperwork":    ["claim", "denial", "policy", "endorsement", "deductible", "premium", "renewal"],
    "insurance":    ["insurance", "carrier", "citizens", "agent", "broker", "underwriting"],
    "palm-florida": ["wellington", "palm beach", "south florida", "florida", "pbc"],
}


def parse_brief(md_path):
    """Extract a headline (~6-10 words) and full body text for scoring."""
    text = md_path.read_text()
    # Headline: first **bold** sentence in the body, else first non-heading line
    body_lines = [ln for ln in text.splitlines() if ln.strip() and not ln.startswith("#")]
    headline = None
    for ln in body_lines:
        m = re.search(r"\*\*(.+?)\*\*", ln)
        if m:
            headline = m.group(1).strip().rstrip(":.!?")
            break
    if not headline and body_lines:
        headline = re.sub(r"[*_`]", "", body_lines[0]).strip()
    headline = re.sub(r"\s+", " ", headline or "Today's brief")
    # Trim emojis off the headline
    headline = re.sub(r"[\U0001F300-\U0001FAFF\U00002600-\U000027BF]", "", headline).strip()
    return headline, text


def pick_image(body_text):
    """Score each library file by topic keyword match in body; pick highest."""
    body_lower = body_text.lower()
    scores = {topic: 0 for topic in TOPIC_KEYWORDS}
    for topic, kws in TOPIC_KEYWORDS.items():
        for kw in kws:
            scores[topic] += body_lower.count(kw)
    # Top topic; ties broken by topic order in dict
    ranked = sorted(scores.items(), key=lambda x: -x[1])
    for topic, score in ranked:
        candidates = sorted(LIBRARY.glob(f"{topic}__*.jpg"))
        if candidates and score > 0:
            return random.choice(candidates), topic, score
    # Fallback: paperwork or whatever exists
    for fallback in ("paperwork", "insurance", "palm-florida"):
        c = sorted(LIBRARY.glob(f"{fallback}__*.jpg"))
        if c:
            return random.choice(c), fallback, 0
    all_imgs = sorted(LIBRARY.glob("*.jpg"))
    return random.choice(all_imgs), "any", 0


def fit_cover(img, size):
    """Resize+center-crop to size (a square)."""
    w, h = img.size
    target = size[0]
    scale = max(target / w, target / h)
    new = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    nw, nh = new.size
    left = (nw - target) // 2
    top = (nh - target) // 2
    return new.crop((left, top, left + target, top + target))


def wrap_text(text, font, max_width, draw):
    """Word-wrap text to fit within max_width pixels."""
    words = text.split()
    lines = []
    current = []
    for w in words:
        trial = " ".join(current + [w])
        bbox = draw.textbbox((0, 0), trial, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current.append(w)
        else:
            if current:
                lines.append(" ".join(current))
            current = [w]
    if current:
        lines.append(" ".join(current))
    return lines


def compose(base_path, headline, out_path):
    size = (1080, 1080)
    base = Image.open(base_path).convert("RGB")
    canvas = fit_cover(base, size)

    # Bottom gradient overlay: transparent at top, navy at bottom
    overlay = Image.new("RGBA", size, (0, 0, 0, 0))
    grad_h = 560
    for y in range(grad_h):
        alpha = int(255 * (y / grad_h) ** 1.2)
        ImageDraw.Draw(overlay).line(
            [(0, size[1] - grad_h + y), (size[0], size[1] - grad_h + y)],
            fill=(NAVY[0], NAVY[1], NAVY[2], alpha),
        )
    canvas = Image.alpha_composite(canvas.convert("RGBA"), overlay).convert("RGB")

    draw = ImageDraw.Draw(canvas)

    # Gold accent bar above headline
    bar_y = size[1] - 360
    draw.rectangle([(72, bar_y), (152, bar_y + 8)], fill=GOLD)

    # Headline (Georgia Bold, white)
    font_size = 64
    while font_size >= 38:
        font = ImageFont.truetype(GEORGIA_BOLD, font_size)
        lines = wrap_text(headline, font, size[0] - 144, draw)
        # max 4 lines
        if len(lines) <= 4:
            break
        font_size -= 4
    y = bar_y + 36
    for ln in lines:
        draw.text((72, y), ln, fill=WHITE, font=font)
        y += int(font_size * 1.15)

    # Footer: handle (gold, small) + crimson rule
    handle_font = ImageFont.truetype(HELVETICA, 26)
    draw.text((72, size[1] - 64), "@robinhoodadjusting", fill=GOLD, font=handle_font)
    draw.rectangle([(0, size[1] - 8), (size[0], size[1])], fill=CRIMSON)

    canvas.save(out_path, "JPEG", quality=88, optimize=True)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    force = "--force" in sys.argv
    date_str = args[0] if args else datetime.now().strftime("%Y-%m-%d")

    md_path = CONTENT_DIR / date_str / "instagram.md"
    if not md_path.exists():
        print(f"ERROR: {md_path} not found")
        sys.exit(1)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / f"{date_str}.jpg"
    if out_path.exists() and not force:
        print(f"SKIP: {out_path} already exists (use --force to rebuild)")
        return

    headline, body = parse_brief(md_path)
    base_path, topic, score = pick_image(body)
    print(f"  headline: {headline}")
    print(f"  topic:    {topic} (score {score})")
    print(f"  base:     {base_path.name}")
    compose(base_path, headline, out_path)
    print(f"  wrote:    {out_path}")


if __name__ == "__main__":
    main()
