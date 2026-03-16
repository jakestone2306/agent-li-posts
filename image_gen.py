"""
Generates LinkedIn asset graphics using HTMLCSStoImage API (no browser needed).
Falls back to a base64-encoded SVG if the API is unavailable.
"""

import os
import textwrap
import requests
import logging

logger = logging.getLogger(__name__)

HCTI_USER_ID = os.environ.get("HCTI_USER_ID", "")
HCTI_API_KEY = os.environ.get("HCTI_API_KEY", "")


def build_html(asset_type, headline, subtext, cta, day_num=0):
    colors = [
        ("0d0d1a", "e94560", "ffffff"),
        ("0a1628", "3b82f6", "ffffff"),
        ("0d1f0f", "22c55e", "ffffff"),
        ("1a0a2e", "a855f7", "ffffff"),
        ("1a1200", "f59e0b", "ffffff"),
        ("1a0000", "ef4444", "ffffff"),
        ("001a1a", "06b6d4", "ffffff"),
    ]
    bg, accent, text_color = colors[day_num % len(colors)]

    icon = {"quote_card": "&#x275D;", "stat_card": "&#x1F4CA;", "poll_card": "&#x1F5F3;"}.get(asset_type, "&#x1F4A1;")

    # Wrap long headline
    words = headline.split()
    lines = []
    current = []
    for w in words:
        current.append(w)
        if len(" ".join(current)) > 22:
            lines.append(" ".join(current[:-1]))
            current = [w]
    if current:
        lines.append(" ".join(current))
    headline_html = "<br>".join(lines) if lines else headline

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;900&display=swap');
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{
    width:1080px; height:1080px;
    background: radial-gradient(ellipse at top right, #1a1a2e 0%, #{bg} 60%);
    font-family: 'Inter', Arial Black, sans-serif;
    color:#{text_color};
    display:flex; flex-direction:column;
    justify-content:center; align-items:center;
    position:relative; overflow:hidden;
  }}
  .ring {{
    position:absolute; border-radius:50%;
    border: 2px solid #{accent}33;
  }}
  .ring1 {{ width:700px; height:700px; top:-200px; right:-200px; }}
  .ring2 {{ width:500px; height:500px; bottom:-200px; left:-200px; }}
  .ring3 {{ width:300px; height:300px; top:50%; left:50%; transform:translate(-50%,-50%); border-color:#{accent}22; }}
  .bar {{
    position:absolute; top:0; left:0;
    width:8px; height:100%;
    background: linear-gradient(to bottom, #{accent}, #{accent}00);
  }}
  .inner {{
    position:relative; z-index:10;
    text-align:center; padding:80px 100px;
    max-width:1000px;
  }}
  .icon {{
    font-size:56px; margin-bottom:28px;
    color:#{accent};
  }}
  .headline {{
    font-size:80px; font-weight:900;
    line-height:1.05; margin-bottom:36px;
    letter-spacing:-2px;
  }}
  .divider {{
    width:60px; height:5px;
    background:#{accent};
    border-radius:3px;
    margin:0 auto 36px;
  }}
  .subtext {{
    font-size:32px; font-weight:400;
    color:#aaaaaa; line-height:1.5;
    margin-bottom:44px;
  }}
  .cta {{
    display:inline-block;
    font-size:26px; font-weight:700;
    color:#{bg};
    background:#{accent};
    padding:16px 40px; border-radius:50px;
    letter-spacing:0.5px;
  }}
  .brand {{
    position:absolute; bottom:36px; right:52px;
    font-size:20px; font-weight:700;
    color:#444; letter-spacing:3px;
    text-transform:uppercase;
  }}
  .brand span {{ color:#{accent}; }}
</style>
</head>
<body>
  <div class="ring ring1"></div>
  <div class="ring ring2"></div>
  <div class="ring ring3"></div>
  <div class="bar"></div>
  <div class="inner">
    <div class="icon">{icon}</div>
    <div class="headline">{headline_html}</div>
    <div class="divider"></div>
    <div class="subtext">{subtext}</div>
    <div class="cta">{cta}</div>
  </div>
  <div class="brand">Jake Stone <span>·</span> Adapt</div>
</body>
</html>"""


def generate_image(asset_type, headline, subtext, cta, day_num=0, output_path="/tmp/li_asset.png"):
    """Generate image via htmlcsstoimage.com API or fallback."""
    html = build_html(asset_type, headline, subtext, cta, day_num)

    # Try htmlcsstoimage API (free tier available)
    if HCTI_USER_ID and HCTI_API_KEY:
        try:
            r = requests.post(
                "https://hcti.io/v1/image",
                auth=(HCTI_USER_ID, HCTI_API_KEY),
                json={"html": html, "viewport_width": 1080, "viewport_height": 1080},
                timeout=30
            )
            if r.status_code == 200:
                img_url = r.json().get("url", "")
                if img_url:
                    img_r = requests.get(img_url, timeout=20)
                    with open(output_path, "wb") as f:
                        f.write(img_r.content)
                    logger.info(f"Image generated via HCTI: {img_url}")
                    return output_path
        except Exception as e:
            logger.warning(f"HCTI failed: {e}")

    # Fallback: use playwright if installed
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1080, "height": 1080})
            page.set_content(html)
            page.wait_for_timeout(800)
            page.screenshot(path=output_path)
            browser.close()
        logger.info("Image generated via Playwright")
        return output_path
    except Exception as e:
        logger.warning(f"Playwright failed: {e}")

    # Final fallback: save HTML as-is, return None for image
    html_path = output_path.replace(".png", ".html")
    with open(html_path, "w") as f:
        f.write(html)
    logger.info(f"Saved HTML fallback: {html_path}")
    return None
