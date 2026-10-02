````python
import os
import sys
import json
import time
import re
from pathlib import Path

import requests
from dotenv import load_dotenv


# ============================================================
# SETUP
# ============================================================

ROOT_DIR = Path(__file__).resolve().parent.parent
REPORTS_DIR = ROOT_DIR / "reports"

REPORTS_DIR.mkdir(parents=True, exist_ok=True)

load_dotenv(ROOT_DIR / ".env")


# ============================================================
# ENVIRONMENT
# ============================================================

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()

OPENROUTER_MODEL = os.getenv(
    "OPENROUTER_MODEL",
    "openai/gpt-4.1-mini"
).strip()


if not OPENROUTER_API_KEY:
    print("ERROR: OPENROUTER_API_KEY is missing.")
    sys.exit(1)


# ============================================================
# OPENROUTER
# ============================================================

def ask_ai(prompt):

    url = "https://openrouter.ai/api/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/",
        "X-Title": "YouTube Trend Idea Generator",
    }

    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are an expert YouTube entertainment "
                    "idea generator. Create original, realistic, "
                    "high-retention concepts."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        "temperature": 0.8,
        "max_tokens": 10000,
    }

    for attempt in range(1, 5):

        print(
            f"    AI request attempt {attempt}/4..."
        )

        try:

            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=120,
            )

            if response.status_code == 200:

                data = response.json()

                choices = data.get("choices", [])

                if not choices:

                    raise RuntimeError(
                        "OpenRouter returned no choices."
                    )

                message = choices[0].get(
                    "message",
                    {}
                )

                content = message.get(
                    "content",
                    ""
                )

                if not content:

                    raise RuntimeError(
                        "OpenRouter returned empty content."
                    )

                print("    AI response received.")

                return content

            if response.status_code in (
                429,
                500,
                502,
                503,
                504,
            ):

                print(
                    f"    Temporary API error: "
                    f"{response.status_code}"
                )

                time.sleep(
                    min(attempt * 5, 20)
                )

                continue

            raise RuntimeError(
                "OpenRouter error "
                f"{response.status_code}: "
                f"{response.text[:1000]}"
            )

        except requests.RequestException as error:

            print(
                f"    Network error: {error}"
            )

            time.sleep(
                min(attempt * 5, 20)
            )

    raise RuntimeError(
        "OpenRouter failed after 4 attempts."
    )


# ============================================================
# JSON EXTRACTION
# ============================================================

def parse_json(text):

    text = text.strip()

    # Remove Markdown fences if AI adds them
    text = re.sub(
        r"^```json\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"^```\s*",
        "",
        text,
    )

    text = re.sub(
        r"\s*```$",
        "",
        text,
    )

    text = text.strip()

    try:

        return json.loads(text)

    except json.JSONDecodeError:
        pass

    # Find JSON object
    start = text.find("{")
    end = text.rfind("}")

    if start != -1 and end > start:

        try:

            return json.loads(
                text[start:end + 1]
            )

        except json.JSONDecodeError:
            pass

    # Find JSON array
    start = text.find("[")
    end = text.rfind("]")

    if start != -1 and end > start:

        try:

            return json.loads(
                text[start:end + 1]
            )

        except json.JSONDecodeError:
            pass

    raise RuntimeError(
        "Could not parse AI response as JSON."
    )


# ============================================================
# YOUTUBE DATA
# ============================================================

def get_youtube_data():

    try:

        from youtube_agent import (
            get_trending_videos
        )

        videos = get_trending_videos()

        return videos

    except ImportError:

        pass

    try:

        from youtube_agent import get_videos

        return get_videos()

    except ImportError as error:

        raise RuntimeError(
            "Cannot import youtube_agent.py. "
            "Check that src/youtube_agent.py exists."
        ) from error


# ============================================================
# TREND TEXT
# ============================================================

def make_trend_text(videos):

    lines = []

    for number, video in enumerate(
        videos,
        start=1
    ):

        if not isinstance(video, dict):

            title = str(video)

            lines.append(
                f"{number}. {title}"
            )

            continue

        title = video.get(
            "title",
            ""
        )

        channel = video.get(
            "channel",
            video.get(
                "channel_title",
                ""
            )
        )

        views = video.get(
            "views",
            video.get(
                "view_count",
                0
            )
        )

        url = video.get(
            "url",
            video.get(
                "video_url",
                ""
            )
        )

        lines.append(
            f"{number}. {title}\n"
            f"Channel: {channel}\n"
            f"Views: {views}\n"
            f"URL: {url}"
        )

    return "\n\n".join(lines)


# ============================================================
# GENERATE IDEAS
# ============================================================

def generate_ideas(videos):

    trend_text = make_trend_text(videos)

    prompt = f"""
Generate exactly 24 original YouTube entertainment ideas.

Use the YouTube trends below only as inspiration.

Do NOT copy any existing video.

Target audience:
Indian and Telugu viewers.

Style:
- mystery
- suspense
- thriller
- comedy
- relatable everyday situations
- strong curiosity
- realistic endings
- simple production

Every idea needs:

title
hook
story_log
investigation
clues
wrong_theory
escalation
reveal
comedy_payoff
short_version
long_version

The final reveal must logically explain the mystery.

Avoid:

- random ghosts
- random dreams
- random coincidences
- meaningless prank endings
- childish comedy
- copied movies
- copied YouTube videos
- impossible technology

Prefer locations such as:

terrace
apartment
room
lobby
stairs
street
shop
office
parking area

Return ONLY JSON.

Required format:

{{
  "ideas": [
    {{
      "id": 1,
      "title": "Title",
      "hook": "Hook",
      "story_log": "Complete story",
      "investigation": "Investigation",
      "clues": [
        "Clue 1",
        "Clue 2"
      ],
      "wrong_theory": "Wrong theory",
      "escalation": "Escalation",
      "reveal": "Logical reveal",
      "comedy_payoff": "Comedy ending",
      "short_version": "Shorts version",
      "long_version": "8-10 minute version"
    }}
  ]
}}

TREND DATA:

{trend_text}
"""

    response = ask_ai(prompt)

    data = parse_json(response)

    if isinstance(data, dict):

        ideas = data.get(
            "ideas",
            []
        )

    elif isinstance(data, list):

        ideas = data

    else:

        raise RuntimeError(
            "Invalid AI response format."
        )

    if not ideas:

        raise RuntimeError(
            "AI generated zero ideas."
        )

    return ideas


# ============================================================
# SAVE JSON
# ============================================================

def save_json(ideas):

    path = REPORTS_DIR / "ideas.json"

    with open(
        path,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            {
                "model": OPENROUTER_MODEL,
                "count": len(ideas),
                "ideas": ideas,
            },
            file,
            indent=2,
            ensure_ascii=False,
        )

    print(
        f"    JSON saved: {path}"
    )


# ============================================================
# PDF
# ============================================================

def save_pdf(ideas):

    try:

        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import (
            SimpleDocTemplate,
            Paragraph,
            Spacer,
            PageBreak,
        )
        from reportlab.lib.styles import (
            getSampleStyleSheet
        )

    except ImportError:

        print(
            "WARNING: reportlab is not installed."
        )

        return

    path = (
        REPORTS_DIR /
        "youtube_high_engagement_ideas.pdf"
    )

    styles = getSampleStyleSheet()

    document = SimpleDocTemplate(
        str(path),
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40,
    )

    story = []

    story.append(
        Paragraph(
            "YOUTUBE HIGH-ENGAGEMENT IDEAS",
            styles["Title"]
        )
    )

    story.append(
        Spacer(1, 20)
    )

    for index, idea in enumerate(
        ideas,
        start=1
    ):

        title = str(
            idea.get(
                "title",
                "Untitled"
            )
        )

        story.append(
            Paragraph(
                f"{index}. {title}",
                styles["Heading2"]
            )
        )

        fields = [
            ("HOOK", "hook"),
            ("STORY LOG", "story_log"),
            ("INVESTIGATION", "investigation"),
            ("WRONG THEORY", "wrong_theory"),
            ("ESCALATION", "escalation"),
            ("REVEAL", "reveal"),
            ("COMEDY PAYOFF", "comedy_payoff"),
            ("SHORT VERSION", "short_version"),
            ("8-10 MIN VERSION", "long_version"),
        ]

        for label, key in fields:

            value = str(
                idea.get(
                    key,
                    ""
                )
            )

            value = (
                value
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
            )

            story.append(
                Paragraph(
                    f"<b>{label}</b><br>{value}",
                    styles["BodyText"]
                )
            )

            story.append(
                Spacer(1, 8)
            )

        clues = idea.get(
            "clues",
            []
        )

        if isinstance(clues, list):

            clue_text = "<br>".join(
                f"• {str(clue)}"
                for clue in clues
            )

            story.append(
                Paragraph(
                    f"<b>CLUES</b><br>{clue_text}",
                    styles["BodyText"]
                )
            )

        if index < len(ideas):

            story.append(
                PageBreak()
            )

    document.build(story)

    print(
        f"    PDF saved: {path}"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 72)
    print(
        "YOUTUBE HIGH-ENGAGEMENT IDEA GENERATOR"
    )
    print("=" * 72)

    print()
    print(
        "[1/5] Connecting to YouTube..."
    )

    print()
    print(
        "[2/5] Collecting India + "
        "worldwide-proxy trends..."
    )

    videos = get_youtube_data()

    if not videos:

        raise RuntimeError(
            "No YouTube videos were collected."
        )

    print(
        f"    Videos collected: {len(videos)}"
    )

    print()
    print(
        "[3/5] Generating 24 candidate concepts..."
    )

    ideas = generate_ideas(videos)

    print(
        f"    Generated {len(ideas)} ideas."
    )

    print()
    print(
        "[4/5] Creating files..."
    )

    save_json(ideas)

    save_pdf(ideas)

    print()
    print(
        "[5/5] Complete."
    )

    print()
    print("=" * 72)
    print("SUCCESS")
    print("=" * 72)


if __name__ == "__main__":

    try:

        main()

    except Exception as error:

        print()
        print("=" * 72)
        print("ERROR")
        print("=" * 72)
        print()
        print(str(error))
        print()

        sys.exit(1)
````
