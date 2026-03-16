"""
LinkedIn Daily Post Agent for Jake Stone
- Scrapes recent industry news for fresh hooks
- Uses Claude to generate a post in Jake's voice
- Generates a visual asset (quote card or stat card) as HTML → PNG
- Slacks the post + image to Jake at 7am PT daily
"""

import os
import re
import json
import time
import base64
import logging
import requests
import textwrap
from datetime import datetime, timezone
from anthropic import Anthropic

logger = logging.getLogger(__name__)

ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
SLACK_TOKEN = os.environ["SLACK_TOKEN"]
SLACK_USER_ID = os.environ.get("SLACK_USER_ID", "U08357HEYJF")  # Jake Stone

client = Anthropic(api_key=ANTHROPIC_API_KEY)

JAKE_VOICE_PROMPT = """
You are writing LinkedIn posts for Jake Stone, VP of Sales at Adapt API — an InsurTech company
automating workflows for P&C insurance agencies.

Jake's voice:
- Direct, punchy, no corporate fluff
- Mix of bold takes ("There will be 2 types of B2B companies...") and personal storytelling
- Uses short punchy lines. Lots of line breaks. No walls of text.
- Opens with a hook — a bold statement, a surprising stat, or a personal moment
- Numbered lists or bullet points are fine but not overused
- Ends with a question or CTA to drive comments ("What do you think?" / "Drop your take below.")
- Hashtags: 3-5 max, relevant, at the bottom
- Topics: InsurTech, AI in sales/insurance, building a sales team, SDR tech stacks, 
  closing deals, insurance agency modernization, founder stories
- Tone: Confident, occasionally irreverent, always authentic

NEVER:
- Sound like a press release
- Use "synergy", "leverage", "paradigm shift", "game-changing"
- Write more than 280 words
- Use more than 5 hashtags
"""

ASSET_TYPES = ["quote_card", "stat_card", "poll_card"]

def get_trending_hooks():
    """Fetch recent insurance/sales/AI news for post hooks."""
    hooks = []
    try:
        r = requests.get(
            "https://newsapi.org/v2/everything",
            params={
                "q": "(insurance OR insurtech OR \"sales AI\" OR \"SDR\" OR \"B2B sales\") AND (technology OR automation OR AI)",
                "language": "en",
                "sortBy": "publishedAt",
                "pageSize": 5,
                "apiKey": os.environ.get("NEWS_API_KEY", "")
            },
            timeout=10
        )
        if r.status_code == 200:
            articles = r.json().get("articles", [])
            hooks = [f"- {a['title']} ({a['source']['name']})" for a in articles[:5]]
    except Exception as e:
        logger.warning(f"News fetch failed: {e}")

    # Fallback evergreen hooks if news API unavailable
    if not hooks:
        hooks = [
            "- AI is replacing 30% of SDR tasks in 2026 according to Gartner",
            "- Insurance agencies still manually re-keying data 50% of the time",
            "- 95% of corporate AI initiatives deliver zero measurable ROI",
            "- The average SDR tech stack now costs $1,000/month per rep",
            "- P&C carriers racing to modernize legacy systems before 2027",
        ]
    return "\n".join(hooks)


def generate_post_and_asset(day_num=0):
    """Generate a LinkedIn post + visual asset concept using Claude."""

    asset_type = ASSET_TYPES[day_num % len(ASSET_TYPES)]
    hooks = get_trending_hooks()

    # Rotate topic focus
    topics = [
        "AI and automation in insurance agencies — what's actually working vs hype",
        "Building a high-performance SDR team from scratch — lessons learned",
        "The InsurTech modernization wave — who's winning and who's getting left behind",
        "Why cutting SDR tech budget is the most expensive mistake a sales leader makes",
        "Personal story about growing Adapt's sales function / hitting a milestone",
        "Bold take on the future of P&C insurance distribution",
        "What most insurance agencies get wrong about technology adoption",
    ]
    topic_focus = topics[day_num % len(topics)]

    prompt = f"""
{JAKE_VOICE_PROMPT}

Today's topic focus: {topic_focus}

Recent industry news you can reference or riff off (pick 1-2 if relevant, don't be literal):
{hooks}

Write ONE LinkedIn post for Jake Stone. It should feel fresh and timely.

Then, suggest a visual asset of type: {asset_type}
- quote_card: A bold quote pulled from the post (max 15 words) that stands alone as a graphic
- stat_card: A key stat or data point (can be made up but plausible) with brief context
- poll_card: A "Drop your answer below: X or Y?" style engagement prompt

Respond in this exact JSON format:
{{
  "post": "full linkedin post text here",
  "asset_type": "{asset_type}",
  "asset_headline": "the big bold text for the graphic (max 12 words)",
  "asset_subtext": "1-2 line supporting text for the graphic",
  "asset_cta": "short CTA at bottom of graphic e.g. 'Drop your take below 👇'",
  "image_search_query": "3-5 word query to find a relevant background/supporting image"
}}
"""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}]
    )

    text = response.content[0].text.strip()
    # Strip markdown code fences if present
    text = re.sub(r"^```json\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    return json.loads(text)


def generate_graphic_html(asset_type, headline, subtext, cta, day_num=0):
    """Generate a branded HTML graphic as a string."""

    # Rotate accent colors
    colors = [
        ("1a1a2e", "e94560"),   # dark navy / red
        ("0f3460", "16213e"),   # deep blue
        ("1b4332", "52b788"),   # forest green
        ("2d1b69", "7c3aed"),   # purple
        ("1c1c1c", "f59e0b"),   # dark / amber
    ]
    bg_dark, accent = colors[day_num % len(colors)]

    icon = {"quote_card": "💬", "stat_card": "📊", "poll_card": "🗳️"}.get(asset_type, "💡")

    # Wrap headline to avoid overflow
    wrapped = textwrap.fill(headline, width=28)
    headline_html = "<br>".join(wrapped.split("\n"))

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    width: 1080px; height: 1080px;
    background: linear-gradient(135deg, #{bg_dark} 0%, #0a0a1a 100%);
    display: flex; flex-direction: column;
    justify-content: center; align-items: center;
    font-family: 'Arial Black', 'Helvetica Neue', Arial, sans-serif;
    color: white;
    position: relative;
    overflow: hidden;
  }}
  .bg-circle {{
    position: absolute;
    border-radius: 50%;
    background: #{accent}22;
  }}
  .circle1 {{ width: 600px; height: 600px; top: -200px; right: -200px; }}
  .circle2 {{ width: 400px; height: 400px; bottom: -150px; left: -100px; }}
  .card {{
    position: relative; z-index: 10;
    text-align: center;
    padding: 80px;
    max-width: 900px;
  }}
  .icon {{ font-size: 64px; margin-bottom: 32px; }}
  .headline {{
    font-size: 72px;
    font-weight: 900;
    line-height: 1.1;
    margin-bottom: 40px;
    color: white;
    text-shadow: 2px 2px 20px rgba(0,0,0,0.5);
  }}
  .accent-line {{
    width: 80px; height: 6px;
    background: #{accent};
    margin: 0 auto 40px;
    border-radius: 3px;
  }}
  .subtext {{
    font-size: 32px;
    font-weight: 400;
    color: #cccccc;
    line-height: 1.5;
    margin-bottom: 48px;
  }}
  .cta {{
    font-size: 28px;
    font-weight: 700;
    color: #{accent};
    letter-spacing: 1px;
  }}
  .brand {{
    position: absolute;
    bottom: 40px;
    right: 60px;
    font-size: 22px;
    color: #666;
    font-weight: 700;
    letter-spacing: 2px;
  }}
  .brand span {{ color: #{accent}; }}
</style>
</head>
<body>
  <div class="bg-circle circle1"></div>
  <div class="bg-circle circle2"></div>
  <div class="card">
    <div class="icon">{icon}</div>
    <div class="headline">{headline_html}</div>
    <div class="accent-line"></div>
    <div class="subtext">{subtext}</div>
    <div class="cta">{cta}</div>
  </div>
  <div class="brand">JAKE STONE <span>•</span> ADAPT</div>
</body>
</html>"""
    return html


def html_to_png(html_content, output_path):
    """Convert HTML to PNG using playwright."""
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1080, "height": 1080})
            page.set_content(html_content)
            page.wait_for_timeout(500)
            page.screenshot(path=output_path, full_page=False)
            browser.close()
        return True
    except Exception as e:
        logger.error(f"Playwright screenshot failed: {e}")
        return False


def upload_to_slack(file_path, filename="li_asset.png"):
    """Upload file to Slack and return file ID."""
    with open(file_path, "rb") as f:
        data = f.read()

    # Get upload URL
    r = requests.post(
        "https://slack.com/api/files.getUploadURLExternal",
        headers={"Authorization": f"Bearer {SLACK_TOKEN}"},
        data={"filename": filename, "length": len(data)}
    )
    r.raise_for_status()
    resp = r.json()
    upload_url = resp["upload_url"]
    file_id = resp["file_id"]

    # Upload file
    requests.post(upload_url, data=data, headers={"Content-Type": "image/png"})

    # Complete upload
    requests.post(
        "https://slack.com/api/files.completeUploadExternal",
        headers={"Authorization": f"Bearer {SLACK_TOKEN}", "Content-Type": "application/json"},
        json={"files": [{"id": file_id}], "channel_id": SLACK_USER_ID}
    )
    return file_id


def send_slack_post(post_text, asset_type, file_id=None):
    """Send the daily LinkedIn post to Jake via Slack DM."""
    today = datetime.now().strftime("%A, %B %d")
    asset_label = {"quote_card": "Quote Card", "stat_card": "Stat Card", "poll_card": "Poll Card"}.get(asset_type, "Asset")

    msg = f"""📝 *Your LinkedIn post for {today}*

{post_text}

---
🖼️ *{asset_label} attached* — post it as your first comment or tease it in the post to drive engagement.

_Reply to this message with edits, or just copy + post!_"""

    payload = {
        "channel": SLACK_USER_ID,
        "text": msg,
    }
    if file_id:
        payload["blocks"] = [
            {"type": "section", "text": {"type": "mrkdwn", "text": msg}},
            {"type": "image", "slack_file": {"id": file_id}, "alt_text": "LinkedIn asset"}
        ]

    r = requests.post(
        "https://slack.com/api/chat.postMessage",
        headers={"Authorization": f"Bearer {SLACK_TOKEN}", "Content-Type": "application/json"},
        json=payload
    )
    r.raise_for_status()
    return r.json()


def run_daily_post(day_num=None):
    """Main function: generate post + asset + send to Slack."""
    if day_num is None:
        day_num = datetime.now().timetuple().tm_yday  # use day of year to rotate topics

    logger.info(f"Generating LinkedIn post (day_num={day_num})")

    # Step 1: Generate post + asset concept
    result = generate_post_and_asset(day_num)
    post_text = result["post"]
    asset_type = result["asset_type"]
    headline = result["asset_headline"]
    subtext = result["asset_subtext"]
    cta = result["asset_cta"]

    logger.info(f"Post generated ({len(post_text)} chars). Asset: {asset_type}")

    # Step 2: Generate HTML graphic
    html = generate_graphic_html(asset_type, headline, subtext, cta, day_num)
    html_path = "/tmp/li_asset.html"
    png_path = "/tmp/li_asset.png"

    with open(html_path, "w") as f:
        f.write(html)

    png_ok = html_to_png(html, png_path)

    # Step 3: Upload image to Slack
    file_id = None
    if png_ok:
        try:
            file_id = upload_to_slack(png_path, f"li_asset_{day_num}.png")
            logger.info(f"Image uploaded: {file_id}")
        except Exception as e:
            logger.error(f"Image upload failed: {e}")

    # Step 4: Send DM to Jake
    resp = send_slack_post(post_text, asset_type, file_id)
    logger.info(f"Slack message sent: {resp.get('ok')}")

    return {
        "status": "success",
        "post_length": len(post_text),
        "asset_type": asset_type,
        "image_generated": png_ok,
        "slack_ok": resp.get("ok"),
        "post_preview": post_text[:200] + "..."
    }
