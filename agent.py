"""
LinkedIn Daily Post Agent for Jake Stone
- Uses Claude to generate a post in Jake's voice
- Generates a branded visual asset as PNG via Playwright
- Uploads image + sends Slack DM to Jake at 7am PT daily
"""

import os
import re
import json
import time
import base64
import logging
import textwrap
import requests
from datetime import datetime, timezone
from anthropic import Anthropic

logger = logging.getLogger(__name__)

ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
SLACK_TOKEN = os.environ["SLACK_TOKEN"]
SLACK_USER_ID = os.environ.get("SLACK_USER_ID", "U08357HEYJF")

client = Anthropic(api_key=ANTHROPIC_API_KEY)

ASSET_TYPES = ["quote_card", "stat_card", "poll_card"]
TOPICS = [
    "The two types of insurance agencies in 2026 — those embracing AI/automation and those falling behind",
    "Why cutting SDR tech budget is the most expensive mistake a sales leader makes",
    "What most insurance agencies get wrong about technology adoption",
    "Building a high-performance SDR team from scratch — real lessons, no fluff",
    "Bold take on where P&C insurance distribution is headed in the next 3 years",
    "Personal story about growing Adapt's sales function and hitting a milestone",
    "AI is changing how agencies quote, bind, and service — what's actually working vs hype",
]
COLORS = [
    ("0f0f1a", "1a1a2e", "7c3aed", "a78bfa"),   # purple
    ("0a1628", "1e3a5f", "2563eb", "60a5fa"),   # blue
    ("0a1f14", "1a3a28", "059669", "34d399"),   # green
    ("1a0f28", "2d1b69", "7c3aed", "c4b5fd"),   # violet
    ("1a0a00", "3d1f00", "d97706", "fbbf24"),   # amber
]


def get_trending_hooks():
    hooks = []
    api_key = os.environ.get("NEWS_API_KEY", "")
    if api_key:
        try:
            r = requests.get(
                "https://newsapi.org/v2/everything",
                params={
                    "q": "(insurtech OR insurance automation OR SDR AI OR B2B sales)",
                    "language": "en", "sortBy": "publishedAt", "pageSize": 5,
                    "apiKey": api_key
                }, timeout=8
            )
            if r.status_code == 200:
                hooks = [f"- {a['title']}" for a in r.json().get("articles", [])[:4]]
        except Exception:
            pass

    if not hooks:
        hooks = [
            "- 95% of corporate AI initiatives deliver zero measurable ROI (MLQ report)",
            "- Insurance agencies still manually re-keying data 50% of the time",
            "- The average SDR tech stack now costs $1,000/month per rep",
            "- P&C carriers racing to modernize legacy systems before 2027",
            "- AI is replacing 30% of SDR tasks — reps who use it are 40% more productive",
        ]
    return "\n".join(hooks)


def generate_post_and_asset(day_num=0):
    asset_type = ASSET_TYPES[day_num % len(ASSET_TYPES)]
    topic = TOPICS[day_num % len(TOPICS)]
    hooks = get_trending_hooks()

    prompt = f"""You are writing LinkedIn posts for Jake Stone, VP of Sales at Adapt API — an InsurTech company automating workflows for P&C insurance agencies.

Jake's voice:
- Direct, punchy, zero corporate fluff
- Short punchy lines with lots of line breaks — no walls of text
- Mix of bold takes ("There will be 2 types...") and personal storytelling
- Strong hook in the first line
- Ends with a question to drive comments
- 3-5 hashtags max at the bottom
- Max 260 words

Today's topic: {topic}

Recent industry context (use 1-2 if relevant, don't copy directly):
{hooks}

Write ONE LinkedIn post. Then create a visual asset of type: {asset_type}
- quote_card: pull a bold statement from the post (max 10 words)
- stat_card: a punchy stat or data point with brief context
- poll_card: an "Adapters vs Resisters" or binary choice for comments

Respond ONLY in this JSON (no markdown fences):
{{
  "post": "full linkedin post text",
  "asset_type": "{asset_type}",
  "headline": "bold text for graphic max 10 words",
  "subtext": "1 supporting line for graphic",
  "cta": "short engagement CTA for graphic"
}}"""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}]
    )
    text = response.content[0].text.strip()
    m = re.search(r'\{.*\}', text, re.DOTALL)
    return json.loads(m.group())


def generate_graphic_html(headline, subtext, cta, day_num=0):
    bg1, bg2, accent, light = COLORS[day_num % len(COLORS)]
    wrapped = "<br>".join(textwrap.fill(headline, width=22).split("\n"))

    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{
    width:1080px; height:1080px;
    background: linear-gradient(145deg, #{bg1} 0%, #{bg2} 100%);
    display:flex; flex-direction:column;
    justify-content:center; align-items:center;
    font-family:'Arial Black', Arial, sans-serif;
    color:white; position:relative; overflow:hidden;
  }}
  .glow {{
    position:absolute; border-radius:50%; filter:blur(90px); opacity:0.18;
  }}
  .g1 {{ width:700px; height:700px; background:#{accent}; top:-300px; right:-200px; }}
  .g2 {{ width:500px; height:500px; background:#{accent}; bottom:-200px; left:-150px; }}
  .card {{
    position:relative; z-index:10;
    text-align:center; padding:80px 100px; max-width:960px;
  }}
  .tag {{
    display:inline-block;
    background:#{accent}22; border:1px solid #{accent}55;
    color:#{light}; font-size:18px; font-weight:700;
    letter-spacing:3px; text-transform:uppercase;
    padding:10px 24px; border-radius:100px; margin-bottom:52px;
  }}
  .headline {{
    font-size:82px; font-weight:900; line-height:1.05;
    margin-bottom:44px; color:white; letter-spacing:-1px;
  }}
  .bar {{
    width:60px; height:4px;
    background:linear-gradient(90deg, #{accent}, #{light});
    margin:0 auto 44px; border-radius:2px;
  }}
  .subtext {{
    font-size:30px; font-weight:400; color:#94a3b8;
    line-height:1.6; margin-bottom:52px;
    font-family:Arial, sans-serif;
  }}
  .cta {{
    font-size:26px; font-weight:800; color:#{light};
    letter-spacing:1px; text-transform:uppercase;
  }}
  .brand {{
    position:absolute; bottom:44px;
    font-size:20px; font-weight:900; color:#374151;
    letter-spacing:3px; text-transform:uppercase;
  }}
  .brand span {{ color:#{accent}; }}
</style>
</head>
<body>
  <div class="glow g1"></div>
  <div class="glow g2"></div>
  <div class="card">
    <div class="tag">Jake Stone · Adapt API</div>
    <div class="headline">{wrapped}</div>
    <div class="bar"></div>
    <div class="subtext">{subtext}</div>
    <div class="cta">👇 {cta}</div>
  </div>
  <div class="brand">Jake Stone <span>•</span> Adapt API</div>
</body></html>"""


def render_png(html_content, output_path):
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1080, "height": 1080})
            page.set_content(html_content)
            page.wait_for_timeout(600)
            page.screenshot(path=output_path, full_page=False)
            browser.close()
        return True
    except Exception as e:
        logger.error(f"PNG render failed: {e}")
        return False


def get_dm_channel_id():
    """Get or open the DM channel with the user."""
    r = requests.post(
        "https://slack.com/api/conversations.open",
        headers={"Authorization": f"Bearer {SLACK_TOKEN}", "Content-Type": "application/json"},
        json={"users": SLACK_USER_ID}
    )
    return r.json().get("channel", {}).get("id", SLACK_USER_ID)


def upload_image_to_slack(file_path):
    """Upload image inline to Slack DM using the new files API."""
    with open(file_path, "rb") as f:
        img_data = f.read()

    dm_channel = get_dm_channel_id()

    # Step 1: Get upload URL
    r1 = requests.post(
        "https://slack.com/api/files.getUploadURLExternal",
        headers={"Authorization": f"Bearer {SLACK_TOKEN}"},
        data={"filename": "li_asset.png", "length": len(img_data)}
    )
    resp1 = r1.json()
    if not resp1.get("ok"):
        return False, "", resp1.get("error", "")

    upload_url = resp1["upload_url"]
    file_id = resp1["file_id"]

    # Step 2: Upload bytes
    requests.post(upload_url, data=img_data, headers={"Content-Type": "image/png"})

    # Step 3: Complete and share to DM
    r3 = requests.post(
        "https://slack.com/api/files.completeUploadExternal",
        headers={"Authorization": f"Bearer {SLACK_TOKEN}", "Content-Type": "application/json"},
        json={
            "files": [{"id": file_id, "title": "LinkedIn Quote Card"}],
            "channel_id": dm_channel,
            "initial_comment": "🖼️ *Your LinkedIn graphic* — drop this as your *first comment* right after posting to spike engagement 🚀"
        }
    )
    resp3 = r3.json()
    return resp3.get("ok"), file_id, resp3.get("error", "")


def send_slack_message(post_text, asset_type):
    today = datetime.now().strftime("%A, %B %d")
    label = {"quote_card": "Quote Card", "stat_card": "Stat Card", "poll_card": "Poll Card"}.get(asset_type, "Asset")
    dm_channel = get_dm_channel_id()

    msg = f"""📝 *Your LinkedIn post for {today}*

{post_text}

---
🖼️ *{label} sent above* — post it as your *first comment* right after publishing to spike engagement 🚀"""

    r = requests.post(
        "https://slack.com/api/chat.postMessage",
        headers={"Authorization": f"Bearer {SLACK_TOKEN}", "Content-Type": "application/json"},
        json={"channel": dm_channel, "text": msg}
    )
    return r.json()


def run_daily_post(day_num=None):
    if day_num is None:
        day_num = datetime.now().timetuple().tm_yday

    logger.info(f"Generating LinkedIn post (day={day_num})")

    # Generate post + asset concept
    result = generate_post_and_asset(day_num)
    post_text = result["post"]
    asset_type = result["asset_type"]

    # Render graphic
    html = generate_graphic_html(result["headline"], result["subtext"], result["cta"], day_num)
    png_path = "/tmp/li_asset.png"
    png_ok = render_png(html, png_path)

    # Upload image inline to Slack DM
    image_ok = False
    if png_ok:
        ok, file_id, err = upload_image_to_slack(png_path)
        image_ok = ok
        if not ok:
            logger.error(f"Image upload failed: {err}")

    # Send post text
    resp = send_slack_message(post_text, asset_type)
    logger.info(f"Slack sent: {resp.get('ok')}")

    return {
        "status": "success",
        "post_length": len(post_text),
        "asset_type": asset_type,
        "png_generated": png_ok,
        "image_uploaded": image_ok,
        "slack_ok": resp.get("ok"),
        "preview": post_text[:150]
    }
