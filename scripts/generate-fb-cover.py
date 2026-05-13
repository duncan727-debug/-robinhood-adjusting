#!/usr/bin/env python3
"""Generate Robinhood Adjusting FB cover photo (820x312) and IG profile (500x500)."""

from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

NAVY  = (15, 45, 74)
NAVY2 = (26, 58, 92)
GOLD  = (201, 146, 42)
WHITE = (255, 255, 255)
WHITE_DIM = (255, 255, 255, 200)

SITE = Path("/Users/victoria/.openclaw/workspace/site")
F_GEORGIA      = "/System/Library/Fonts/Supplemental/Georgia.ttf"
F_GEORGIA_BOLD = "/System/Library/Fonts/Supplemental/Georgia Bold.ttf"
F_ARIAL        = "/System/Library/Fonts/Supplemental/Arial.ttf"
F_ARIAL_BOLD   = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"


def draw_shield(img, cx, cy, size, draw_arrow=True):
    """Draw the Robinhood shield centered at (cx, cy) with given size (height in px)."""
    # Shield silhouette proportions match shield-dark.svg viewBox 56x60 (logical units)
    # Outer shield path: M28 2 L54 11 L54 32 C... → bounding box ~52x58
    scale = size / 60.0

    def s(x, y):
        return (cx - 28*scale + x*scale, cy - 30*scale + y*scale)

    # Outer shield (navy2 fill + gold stroke)
    outer = [
        s(28, 2), s(54, 11), s(54, 32),
        s(52, 38), s(48, 45), s(42, 52),
        s(36, 56), s(28, 60),
        s(20, 56), s(14, 52), s(8, 45), s(4, 38), s(2, 32),
        s(2, 11)
    ]
    ImageDraw.Draw(img).polygon(outer, fill=NAVY2, outline=GOLD)
    # Beef up the stroke
    for w in range(1, max(2, int(2.5*scale))):
        ImageDraw.Draw(img).line(outer + [outer[0]], fill=GOLD, width=w)
    ImageDraw.Draw(img).line(outer + [outer[0]], fill=GOLD, width=max(2, int(2.5*scale)))

    # Inner shield (deeper navy)
    inner = [
        s(28, 9), s(47, 17), s(47, 32),
        s(46, 37), s(43, 43), s(38, 48),
        s(33, 52), s(28, 54),
        s(23, 52), s(18, 48), s(13, 43), s(10, 37), s(9, 32),
        s(9, 17)
    ]
    ImageDraw.Draw(img).polygon(inner, fill=NAVY)

    if draw_arrow:
        # Arrow shaft (28,43 → 28,20)
        ImageDraw.Draw(img).line(
            [s(28, 43), s(28, 20)],
            fill=GOLD, width=max(3, int(3.2*scale))
        )
        # Arrow head: 21,28 → 28,20 → 35,28
        ImageDraw.Draw(img).line(
            [s(21, 28), s(28, 20), s(35, 28)],
            fill=GOLD, width=max(3, int(3.2*scale)), joint="curve"
        )
        # Fletching: 23,40 → 28,43 and 33,40 → 28,43
        ImageDraw.Draw(img).line([s(23, 40), s(28, 43)], fill=GOLD, width=max(2, int(2.2*scale)))
        ImageDraw.Draw(img).line([s(33, 40), s(28, 43)], fill=GOLD, width=max(2, int(2.2*scale)))


def make_fb_cover():
    W, H = 1640, 624  # 2x for retina; FB downsizes from 820x312 source
    img = Image.new("RGB", (W, H), NAVY)
    d = ImageDraw.Draw(img)

    # Subtle navy gradient overlay (lighter at top-left)
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    for i in range(180):
        a = int(40 * (1 - i/180))
        od.ellipse([-200 + i, -200 + i, 600 - i, 600 - i],
                   fill=(40, 75, 110, a))
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    d = ImageDraw.Draw(img)

    # Gold accent bar at bottom
    d.rectangle([0, H-16, W, H], fill=GOLD)

    # Subtle gold accent bar at top
    d.rectangle([0, 0, W, 6], fill=GOLD)

    # Shield on left side
    draw_shield(img, cx=300, cy=H//2 - 10, size=440)

    # Wordmark + tagline on right side
    text_x = 600
    f_brand = ImageFont.truetype(F_GEORGIA_BOLD, 76)
    f_sub   = ImageFont.truetype(F_ARIAL,        22)
    f_h1    = ImageFont.truetype(F_GEORGIA,      52)
    f_h1b   = ImageFont.truetype(F_GEORGIA_BOLD, 52)
    f_url   = ImageFont.truetype(F_ARIAL_BOLD,   26)

    # Brand name
    d.text((text_x, 110), "Robinhood Adjusting", font=f_brand, fill=WHITE)
    # Sub eyebrow
    d.text((text_x + 6, 195), "S O U T H   F L O R I D A   P U B L I C   A D J U S T E R S",
           font=f_sub, fill=GOLD)

    # Tagline (two lines, gold emphasis)
    d.text((text_x, 260), "Your Insurance Company Has an Adjuster.",
           font=f_h1, fill=WHITE)
    d.text((text_x, 330), "Now You Have One Too.",
           font=f_h1b, fill=GOLD)

    # URL
    d.text((text_x, 440), "robinhoodadjusting.com   ·   (561) 316-6455",
           font=f_url, fill=WHITE_DIM[:3])

    # Resize down to FB recommended source size with high-quality
    final = img.resize((1640, 624), Image.LANCZOS)
    out = SITE / "fb-cover.png"
    final.save(out, "PNG", optimize=True)
    print(f"[OK] FB cover: {out} ({final.size})")
    return out


def make_profile_picture():
    """500x500 profile picture: shield on navy with gold ring."""
    S = 1000  # 2x for retina
    img = Image.new("RGB", (S, S), NAVY)
    d = ImageDraw.Draw(img)

    # Outer gold ring
    d.ellipse([20, 20, S-20, S-20], outline=GOLD, width=14)

    # Shield centered
    draw_shield(img, cx=S//2, cy=S//2 + 10, size=620)

    final = img.resize((1000, 1000), Image.LANCZOS)
    out = SITE / "profile-picture.png"
    final.save(out, "PNG", optimize=True)
    print(f"[OK] Profile picture: {out} ({final.size})")
    return out


if __name__ == "__main__":
    make_fb_cover()
    make_profile_picture()
