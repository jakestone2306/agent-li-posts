"""
Pure Python graphic generator using Pillow — no Playwright/browser required.
Generates branded 1080x1080 LinkedIn quote card PNGs.
"""
import textwrap
from PIL import Image, ImageDraw, ImageFont
import os

THEMES = [
    {"bg": (15, 15, 26), "accent": (124, 58, 237), "light": (167, 139, 250)},   # purple
    {"bg": (10, 22, 40), "accent": (37, 99, 235),  "light": (147, 197, 253)},   # blue
    {"bg": (10, 31, 20), "accent": (5,  150, 105),  "light": (52, 211, 153)},   # green
    {"bg": (26, 10, 0),  "accent": (217, 119, 6),   "light": (251, 191, 36)},   # amber
    {"bg": (26, 15, 40), "accent": (124, 58, 237),  "light": (196, 181, 253)},  # violet
]


def hex_to_rgb(hex_str):
    h = hex_str.lstrip('#')
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def draw_gradient_bg(draw, width, height, bg_color, accent_color):
    """Draw a dark gradient background with soft glow circles."""
    # Fill base color
    img_base = Image.new("RGB", (width, height), bg_color)

    # Add soft glow blobs
    glow = Image.new("RGB", (width, height), bg_color)
    glow_draw = ImageDraw.Draw(glow)

    # Top-right glow
    ar, ag, ab = accent_color
    for radius in range(300, 0, -10):
        alpha = int(30 * (radius / 300) ** 2)
        color = (
            min(255, bg_color[0] + int((ar - bg_color[0]) * alpha / 255)),
            min(255, bg_color[1] + int((ag - bg_color[1]) * alpha / 255)),
            min(255, bg_color[2] + int((ab - bg_color[2]) * alpha / 255)),
        )
        glow_draw.ellipse([width - 50 - radius, -50 - radius,
                           width - 50 + radius, -50 + radius], fill=color)

    # Bottom-left glow
    for radius in range(220, 0, -10):
        alpha = int(20 * (radius / 220) ** 2)
        color = (
            min(255, bg_color[0] + int((ar - bg_color[0]) * alpha / 255)),
            min(255, bg_color[1] + int((ag - bg_color[1]) * alpha / 255)),
            min(255, bg_color[2] + int((ab - bg_color[2]) * alpha / 255)),
        )
        glow_draw.ellipse([-50 - radius, height - 50 - radius,
                           -50 + radius, height - 50 + radius], fill=color)

    return Image.blend(img_base, glow, 0.6)


def get_font(size, bold=False):
    """Get best available font."""
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    ]
    regular_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    ]
    paths = font_paths if bold else regular_paths
    for path in paths:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def generate_graphic(headline, subtext, cta, day_num=0, output_path="/tmp/li_asset.png"):
    W, H = 1080, 1080
    theme = THEMES[day_num % len(THEMES)]
    bg = theme["bg"]
    accent = theme["accent"]
    light = theme["light"]

    img = draw_gradient_bg(None, W, H, bg, accent)
    draw = ImageDraw.Draw(img)

    # ── TAG pill ──
    tag_text = "JAKE STONE  ·  ADAPT API"
    tag_font = get_font(22, bold=True)
    tag_bbox = draw.textbbox((0, 0), tag_text, font=tag_font)
    tag_w = tag_bbox[2] - tag_bbox[0]
    tag_h = tag_bbox[3] - tag_bbox[1]
    tag_pad_x, tag_pad_y = 32, 14
    tag_x = (W - tag_w - tag_pad_x * 2) // 2
    tag_y = 200

    # pill background
    r = (tag_h + tag_pad_y * 2) // 2
    pill_rect = [tag_x, tag_y, tag_x + tag_w + tag_pad_x * 2, tag_y + tag_h + tag_pad_y * 2]
    draw.rounded_rectangle(pill_rect, radius=r,
                            fill=(*accent, 40), outline=(*accent, 100), width=1)
    draw.text((tag_x + tag_pad_x, tag_y + tag_pad_y), tag_text,
              font=tag_font, fill=light)

    # ── HEADLINE ──
    headline_font = get_font(90, bold=True)
    max_chars = 18
    lines = textwrap.wrap(headline, width=max_chars)
    line_h = 100
    total_h = len(lines) * line_h
    headline_y = (H - total_h) // 2 - 60

    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=headline_font)
        lw = bbox[2] - bbox[0]
        draw.text(((W - lw) // 2, headline_y + i * line_h),
                  line, font=headline_font, fill=(255, 255, 255))

    # ── DIVIDER BAR ──
    bar_y = headline_y + total_h + 40
    bar_w, bar_h = 60, 5
    bar_x = (W - bar_w) // 2
    draw.rounded_rectangle([bar_x, bar_y, bar_x + bar_w, bar_y + bar_h],
                            radius=3, fill=accent)

    # ── SUBTEXT ──
    sub_font = get_font(30, bold=False)
    sub_lines = textwrap.wrap(subtext, width=42)
    sub_y = bar_y + 50
    for line in sub_lines:
        bbox = draw.textbbox((0, 0), line, font=sub_font)
        lw = bbox[2] - bbox[0]
        draw.text(((W - lw) // 2, sub_y), line,
                  font=sub_font, fill=(180, 180, 200))
        sub_y += 42

    # ── CTA ──
    cta_text = f"👇 {cta.upper()}"
    cta_font = get_font(26, bold=True)
    cta_bbox = draw.textbbox((0, 0), cta_text, font=cta_font)
    cta_w = cta_bbox[2] - cta_bbox[0]
    draw.text(((W - cta_w) // 2, sub_y + 40), cta_text,
              font=cta_font, fill=light)

    # ── BRAND FOOTER ──
    brand_font = get_font(20, bold=True)
    brand_text = "JAKE STONE  •  ADAPT API"
    brand_bbox = draw.textbbox((0, 0), brand_text, font=brand_font)
    brand_w = brand_bbox[2] - brand_bbox[0]
    draw.text(((W - brand_w) // 2, H - 60), brand_text,
              font=brand_font, fill=(60, 60, 80))

    img.save(output_path, "PNG", quality=95)
    return output_path


if __name__ == "__main__":
    generate_graphic(
        headline="Winners use AI deeper, not wider",
        subtext="Only 24% of sales reps hit quota with shallow AI adoption",
        cta="Drop your take below",
        day_num=1,
        output_path="/tmp/test_graphic.png"
    )
    print("Generated:", __import__('os').path.getsize('/tmp/test_graphic.png'), "bytes")
