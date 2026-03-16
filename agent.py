"""
LinkedIn Daily Post Agent for Jake Stone
Generates post + branded graphic, sends both to Slack at 7am PT.
"""

import os
import re
import json
import time
import logging
import requests
from datetime import datetime, timezone
from anthropic import Anthropic
from image_gen import generate_image

logger = logging.getLogger(__name__)

ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
SLACK_TOKEN = os.environ["SLACK_TOKEN"]
SLACK_USER_ID = os.environ.get("SLACK_USER_ID", "U08357HEYJF")

client = Anthropic(api_key=ANTHROPIC_API_KEY)

JAKE_VOICE = """
You are writing LinkedIn posts for Jake Stone, VP of Sales at Adapt API — InsurTech that automates
P&C insurance agency workflows.

Jake's voice:
- Direct, punchy, zero corporate fluff
- Mix of bold hot takes AND personal storytelling moments
- Short lines. Lots of white space. No walls of text.
- Strong opening hook — a bold claim, surprising number, or personal moment
- Ends with a question to drive comments
- 3-5 hashtags at the bottom only
- Max 260 words

NEVER: press release language, buzzwords like "synergy" or "leverage", more than 5 hashtags.

Topics to rotate through:
- AI + automation in insurance agencies (what's working vs. hype)
- Building a high-performance SDR/AE team from scratch
- InsurTech modernization — who's winning, who's falling behind
- SDR tech stacks and why cutting budget kills performance
- Personal stories from growing Adapt's sales team
- Bold takes on the future of P&C insurance distribution
- What insurance agencies get wrong about technology
"""

ASSET_TYPES = ["quote_card", "stat_card", "poll_card"]

TOPICS = [
    "AI and automation in insurance agencies — what's actually working vs hype right now",
    "Building a high-performance SDR team from scratch — personal lessons from Adapt",
    "The InsurTech modernization wave — who's winning and who's getting left behind",
    "Why cutting SDR tech budget is the most expensive mistake a sales leader makes",
    "Personal story about a milestone, a rep's growth, or a hard lesson at Adapt",
    "Bold take on the future of P&C insurance distribution in 2026",
    "What most insurance agencies get completely wrong about adopting new technology",
]


def get_news_hooks():
    hooks = []
    try:
        r = requests.get(
            "https://newsapi.org/v2/everything",
            params={
                "q": "(insurtech OR insurance automation OR B2B sales OR SDR) AND (AI OR technology)",
                "language": "en", "sortBy": "publishedAt", "pageSize": 5,
                "apiKey": os.environ.get("NEWS_API_KEY", "")
            }, timeout=8
        )
        if r.status_code == 200:
            hooks = [f"- {a['title']}" for a in r.json().get("articles", [])[:4]]
    except Exception:
        pass
    return "\n".join(hooks) if hooks else ""


def generate_post_and_asset(day_num=0):
    asset_type = ASSET_TYPES[day_num % len(ASSET_TYPES)]
    topic = TOPICS[day_num % len(TOPICS)]
    news = get_news_hooks()
    news_section = f"\nRecent news to optionally riff off (pick 1 if relevant, don't be literal):\n{news}" if news else ""

    prompt = f"""{JAKE_VOICE}

Today's topic: {topic}{news_section}

Write ONE LinkedIn post for Jake. Make it feel fresh and human.

Then create a visual asset of type: {asset_type}
- quote_card: A bold quote pulled from the post (max 10 words)
- stat_card: A punchy stat or data point with brief context
- poll_card: A "Drop your answer below: X or Y?" engagement prompt

Respond in this exact JSON (no markdown fences, no extra text):
{{
  "post": "full linkedin post text",
  "asset_type": "{asset_type}",
  "asset_headline": "big bold graphic text, max 10 words",
  "asset_subtext": "1 supporting line for context",
  "asset_cta": "short action CTA for the graphic button"
}}"""

    r = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}]
    )
    text = r.content[0].text.strip()
    m = re.search(r'\{.*\}', text, re.DOTALL)
    return json.loads(m.group()) if m else json.loads(text)


def upload_image_to_slack(file_path):
    """Upload PNG to Slack, return file permalink."""
    with open(file_path, "rb") as f:
        data = f.read()

    # Step 1: get upload URL
    r = requests.post(
        "https://slack.com/api/files.getUploadURLExternal",
        headers={"Authorization": f"Bearer {SLACK_TOKEN}"},
        data={"filename": "li_asset.png", "length": len(data)}
    )
    r.raise_for_status()
    resp = r.json()
    if not resp.get("ok"):
        raise Exception(f"Slack upload URL error: {resp.get('error')}")

    upload_url = resp["upload_url"]
    file_id = resp["file_id"]

    # Step 2: upload bytes
    requests.post(upload_url, data=data, headers={"Content-Type": "image/png"})

    # Step 3: complete upload — share to DM channel
    r2 = requests.post(
        "https://slack.com/api/files.completeUploadExternal",
        headers={"Authorization": f"Bearer {SLACK_TOKEN}", "Content-Type": "application/json"},
        json={"files": [{"id": file_id}], "channel_id": SLACK_USER_ID, "initial_comment": "🖼️ *Today's LinkedIn asset* — post this as your first comment to drive engagement 👇"}
    )
    r2.raise_for_status()
    return file_id


def send_slack_message(post_text, asset_type, image_ok):
    today = datetime.now().strftime("%A, %B %d")
    asset_label = {"quote_card": "Quote Card 💬", "stat_card": "Stat Card 📊", "poll_card": "Poll Card 🗳️"}.get(asset_type, "Asset")
    image_note = "🖼️ *Asset image sent separately above* — drop it as your first comment to tease engagement." if image_ok else "_(Image generation unavailable today — asset sent as text above)_"

    msg = f"""📝 *Your LinkedIn post for {today}*

{post_text}

---
{image_note}

_Copy the post above, paste to LinkedIn, then add the {asset_label} as your first comment. Takes 30 seconds. 🚀_"""

    r = requests.post(
        "https://slack.com/api/chat.postMessage",
        headers={"Authorization": f"Bearer {SLACK_TOKEN}", "Content-Type": "application/json"},
        json={"channel": SLACK_USER_ID, "text": msg}
    )
    r.raise_for_status()
    return r.json()


def run_daily_post(day_num=None):
    if day_num is None:
        day_num = datetime.now().timetuple().tm_yday

    logger.info(f"Generating LinkedIn post (day_num={day_num})")

    result = generate_post_and_asset(day_num)
    post_text = result["post"]
    asset_type = result["asset_type"]
    headline = result["asset_headline"]
    subtext = result["asset_subtext"]
    cta = result["asset_cta"]

    logger.info(f"Post generated ({len(post_text)} chars). Asset: {asset_type} — '{headline}'")

    # Generate image
    img_path = generate_image(asset_type, headline, subtext, cta, day_num, "/tmp/li_asset.png")
    image_ok = False

    if img_path:
        try:
            upload_image_to_slack(img_path)
            image_ok = True
            logger.info("Image uploaded to Slack successfully")
            time.sleep(1)  # let the image message land first
        except Exception as e:
            logger.error(f"Image upload failed: {e}")

    # Send post text message
    resp = send_slack_message(post_text, asset_type, image_ok)
    logger.info(f"Post message sent: {resp.get('ok')}")

    return {
        "status": "success",
        "post_length": len(post_text),
        "asset_type": asset_type,
        "asset_headline": headline,
        "image_generated": image_ok,
        "slack_ok": resp.get("ok"),
        "post_preview": post_text[:150] + "..."
    }
