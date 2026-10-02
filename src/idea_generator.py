````python
import os
import sys
import json
import time
import re
import base64
from pathlib import Path

import requests
from dotenv import load_dotenv


# ============================================================
# PATHS
# ============================================================

ROOT_DIR = Path(__file__).resolve().parent.parent
REPORTS_DIR = ROOT_DIR / "reports"

REPORTS_DIR.mkdir(parents=True, exist_ok=True)

load_dotenv(ROOT_DIR / ".env")


# ============================================================
# CONFIG
# ============================================================

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()

OPENROUTER_MODEL = os.getenv(
    "OPENROUTER_MODEL",
    "openai/gpt-4.1-mini"
).strip()

RESEND_API_KEY = os.getenv("RESEND_API_KEY", "").strip()
FROM_EMAIL = os.getenv("FROM_EMAIL", "").strip()
RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL", "").strip()

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


# ============================================================
# CHECK CONFIG
# ============================================================

if not OPENROUTER_API_KEY:
    print("ERROR: OPENROUTER_API_KEY is missing.")
    sys.exit(1)


# ============================================================
# OPENROUTER CALL
# ============================================================

def call_openrouter(prompt, max_retries=4):

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/",
        "X-Title": "Siraaj YouTube Idea Generator",
    }

    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are an expert YouTube entertainment "
                    "content strategist. Create original, "
                    "high-retention and realistic video concepts."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        "temperature": 0.85,
        "max_tokens": 12000,
    }

    last_error = ""

    for attempt in range(1, max_retries + 1):

        print(
            f"    OpenRouter attempt "
            f"{attempt}/{max_retries}..."
        )

        try:

            response = requests.post(
                OPENROUTER_URL,
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

                content = (
                    choices[0]
                    .get("message", {})
                    .get("content", "")
                )

                if not content:
                    raise RuntimeError(
                        "OpenRouter returned empty content."
                    )

                print("    OpenRouter response received.")

                return content

            if response.status_code in (
                429,
                500,
                502,
                503,
                504,
            ):

                last_error = (
                    f"HTTP {response.status_code}: "
                    f"{response.text[:500]}"
                )

                wait_time = min(
                    attempt * 5,
                    20
                )

                print(
                    f"    Temporary API error "
                    f"{response.status_code}."
                )

                print(
                    f"    Retrying in {wait_time} seconds..."
                )

                time.sleep(wait_time)

                continue

            raise RuntimeError(
                f"OpenRouter API error "
                f"{response.status_code}: "
                f"{response.text[:1000]}"
            )

        except requests.RequestException as exc:

            last_error = str(exc)

            wait_time = min(
                attempt * 5,
                20
            )

            print(
                f"    Network error: {exc}"
            )

            print(
                f"    Retrying in {wait_time} seconds..."
            )

            time.sleep(wait_time)

    raise RuntimeError(
        "OpenRouter failed after all retries.\n"
        f"Last error: {last_error}"
    )


# ============================================================
# EXTRACT JSON
# ============================================================

def extract_json(text):

    text = text.strip()

    # Remove Markdown code fences if AI adds them
    text = re.sub(
        r"^```(?:json|JSON)?\s*",
        "",
        text
    )

    text = re.sub(
        r"\s*```$",
        "",
        text
    )

    text = text.strip()

    # Try direct JSON
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Find JSON object
    start = text.find("{")
    end = text.rfind("}")

    if start >= 0 and end > start:

        candidate = text[start:end + 1]

        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    # Find JSON array
    start = text.find("[")
    end = text.rfind("]")

    if start >= 0 and end > start:

        candidate = text[start:end + 1]

        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    raise ValueError(
        "AI response did not contain valid JSON."
    )


# ============================================================
# NORMALIZE YOUTUBE DATA
# ============================================================

def normalize_video(video):

    if not isinstance(video, dict):

        return {
            "title": str(video),
            "channel": "",
            "views": 0,
            "url": "",
            "published": "",
        }

    return {
        "title": str(
            video.get("title", "")
        ),
        "channel": str(
            video.get("channel")
            or video.get("channel_title")
            or ""
        ),
        "views": video.get(
            "views",
            video.get("view_count", 0)
        ),
        "url": str(
            video.get("url")
            or video.get("video_url")
            or ""
        ),
        "published": str(
            video.get("published")
            or video.get("published_at")
            or ""
        ),
    }


# ============================================================
# TREND CONTEXT
# ============================================================

def build_trend_context(videos):

    lines = []

    for index, video in enumerate(videos, 1):

        item = normalize_video(video)

        lines.append(
            f"{index}. {item['title']}\n"
            f"Channel: {item['channel']}\n"
            f"Views: {item['views']}\n"
            f"URL: {item['url']}\n"
        )

    return "\n".join(lines)


# ============================================================
# GENERATE IDEAS
# ============================================================

def generate_ideas(videos, number_of_ideas=24):

    trend_context = build_trend_context(videos)

    prompt = f"""
Create exactly {number_of_ideas} original YouTube entertainment
video concepts based on the trend signals below.

Do NOT copy the existing videos.

The concepts should be suitable for an Indian/Telugu audience.

Focus on:

- curiosity
- suspense
- mystery
- comedy
- relatable situations
- strong hooks
- retention
- logical reveals
- simple production

Each idea must contain:

1. title
2. hook
3. story_log
4. investigation
5. clues
6. wrong_theory
7. escalation
8. reveal
9. comedy_payoff
10. production_level
11. short_version
12. long_version

The stories should feel realistic.

Avoid:

- random ghosts
- random dreams
- meaningless prank endings
- random coincidences
- childish stories
- copied movie plots
- copied YouTube videos
- impossible technology

Prefer locations such as:

- terrace
- apartment
- room
- lobby
- staircase
- street
- shop
- office
- parking area

The final reveal must logically explain the mystery.

Return ONLY valid JSON.

Use exactly this structure:

{{
  "ideas": [
    {{
      "id": 1,
      "title": "...",
      "hook": "...",
      "story_log": "...",
      "investigation": "...",
      "clues": [
        "...",
        "..."
      ],
      "wrong_theory": "...",
      "escalation": "...",
      "reveal": "...",
      "comedy_payoff": "...",
      "production_level": "Low",
      "short_version": "...",
      "long_version": "..."
    }}
  ]
}}

TREND DATA:

{trend_context}
"""

    print(
        f"    Generating {number_of_ideas} ideas "
        f"using {OPENROUTER_MODEL}..."
    )

    response = call_openrouter(prompt)

    data = extract_json(response)

    if isinstance(data, dict):

        ideas = data.get("ideas", [])

    elif isinstance(data, list):

        ideas = data

    else:

        raise ValueError(
            "Unexpected AI response format."
        )

    if not ideas:

        raise ValueError(
            "AI returned zero ideas."
        )

    cleaned = []

    for index, idea in enumerate(ideas, 1):

        if not isinstance(idea, dict):
            continue

        clues = idea.get(
            "clues",
            []
        )

        if not isinstance(clues, list):
            clues = [str(clues)]

        cleaned.append(
            {
                "id": index,
                "title": str(
                    idea.get("title", "")
                ),
                "hook": str(
                    idea.get("hook", "")
                ),
                "story_log": str(
                    idea.get("story_log", "")
                ),
                "investigation": str(
                    idea.get("investigation", "")
                ),
                "clues": [
                    str(x) for x in clues
                ],
                "wrong_theory": str(
                    idea.get("wrong_theory", "")
                ),
                "escalation": str(
                    idea.get("escalation", "")
                ),
                "reveal": str(
                    idea.get("reveal", "")
                ),
                "comedy_payoff": str(
                    idea.get("comedy_payoff", "")
                ),
                "production_level": str(
                    idea.get(
                        "production_level",
                        "Low"
                    )
                ),
                "short_version": str(
                    idea.get("short_version", "")
                ),
                "long_version": str(
                    idea.get("long_version", "")
                ),
            }
        )

    if not cleaned:

        raise ValueError(
            "No valid ideas were returned."
        )

    return cleaned


# ============================================================
# SAVE JSON
# ============================================================

def save_json(ideas):

    output = REPORTS_DIR / "ideas.json"

    with open(
        output,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            {
                "model": OPENROUTER_MODEL,
                "idea_count": len(ideas),
                "ideas": ideas,
            },
            file,
            indent=2,
            ensure_ascii=False,
        )

    print(
        f"    JSON saved: {output}"
    )

    return output


# ============================================================
# CREATE PDF
# ============================================================

def create_pdf(ideas):

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

        print(
            "Run: pip install reportlab"
        )

        return None

    output = (
        REPORTS_DIR /
        "youtube_high_engagement_ideas.pdf"
    )

    styles = getSampleStyleSheet()

    document = SimpleDocTemplate(
        str(output),
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

    for index, idea in enumerate(ideas, 1):

        story.append(
            Paragraph(
                f"{index}. {idea['title']}",
                styles["Heading2"]
            )
        )

        fields = [
            ("HOOK", idea["hook"]),
            ("STORY LOG", idea["story_log"]),
            (
                "INVESTIGATION",
                idea["investigation"]
            ),
            (
                "CLUES",
                "<br/>".join(
                    "• " + str(x)
                    for x in idea["clues"]
                )
            ),
            (
                "WRONG THEORY",
                idea["wrong_theory"]
            ),
            (
                "ESCALATION",
                idea["escalation"]
            ),
            (
                "REVEAL",
                idea["reveal"]
            ),
            (
                "COMEDY PAYOFF",
                idea["comedy_payoff"]
            ),
            (
                "PRODUCTION LEVEL",
                idea["production_level"]
            ),
            (
                "SHORT VERSION",
                idea["short_version"]
            ),
            (
                "8–10 MIN VERSION",
                idea["long_version"]
            ),
        ]

        for label, value in fields:

            value = str(value)

            value = (
                value
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
            )

            story.append(
                Paragraph(
                    f"<b>{label}</b><br/>{value}",
                    styles["BodyText"]
                )
            )

            story.append(
                Spacer(1, 8)
            )

        if index < len(ideas):

            story.append(
                PageBreak()
            )

    document.build(story)

    print(
        f"    PDF saved: {output}"
    )

    return output


# ============================================================
# SEND EMAIL USING RESEND
# ============================================================

def send_email(pdf_path):

    if not RESEND_API_KEY:
        print(
            "    RESEND_API_KEY not configured."
        )
        return False

    if not FROM_EMAIL:
        print(
            "    FROM_EMAIL not configured."
        )
        return False

    if not RECIPIENT_EMAIL:
        print(
            "    RECIPIENT_EMAIL not configured."
        )
        return False

    try:

        with open(
            pdf_path,
            "rb"
        ) as file:

            encoded = base64.b64encode(
                file.read()
            ).decode()

        payload = {
            "from": FROM_EMAIL,
            "to": [RECIPIENT_EMAIL],
            "subject": (
                "YouTube High-Engagement Ideas"
            ),
            "html": (
                "<h2>"
                "YouTube High-Engagement Ideas"
                "</h2>"
                "<p>"
                "Your latest trend-based "
                "YouTube idea report is attached."
                "</p>"
            ),
            "attachments": [
                {
                    "filename":
                        "youtube_high_engagement_ideas.pdf",
                    "content": encoded,
                }
            ],
        }

        response = requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization":
                    f"Bearer {RESEND_API_KEY}",
                "Content-Type":
                    "application/json",
            },
            json=payload,
            timeout=60,
        )

        if response.status_code in (
            200,
            201
        ):

            print(
                "    Email sent successfully."
            )

            return True

        print(
            "    Resend email error:"
        )

        print(
            response.text
        )

        return False

    except Exception as exc:

        print(
            f"    Email error: {exc}"
        )

        return False


# ============================================================
# IMPORT YOUTUBE AGENT
# ============================================================

def collect_youtube_videos():

    try:

        from youtube_agent import (
            get_trending_videos
        )

        return get_trending_videos()

    except ImportError:

        try:

            from youtube_agent import (
                get_videos
            )

            return get_videos()

        except ImportError as exc:

            raise RuntimeError(
                "Could not import youtube_agent.py"
            ) from exc


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

    videos = collect_youtube_videos()

    if not videos:

        raise RuntimeError(
            "YouTube returned zero videos."
        )

    print(
        f"    Total videos collected: "
        f"{len(videos)}"
    )

    print()
    print(
        "[3/5] Generating 24 candidate concepts..."
    )

    ideas = generate_ideas(
        videos,
        number_of_ideas=24
    )

    print(
        f"    Generated {len(ideas)} concepts."
    )

    print()
    print(
        "[4/5] Creating report..."
    )

    json_file = save_json(ideas)

    pdf_file = create_pdf(ideas)

    print()
    print(
        "[5/5] Sending report..."
    )

    if pdf_file:

        send_email(pdf_file)

    print()
    print("=" * 72)
    print("SUCCESS")
    print("=" * 72)

    print(
        f"Ideas: {len(ideas)}"
    )

    print(
        f"JSON: {json_file}"
    )

    if pdf_file:

        print(
            f"PDF: {pdf_file}"
        )

    print()


if __name__ == "__main__":

    try:

        main()

    except KeyboardInterrupt:

        print(
            "\nProcess cancelled."
        )

        sys.exit(1)

    except Exception as exc:

        print()
        print("=" * 72)
        print("ERROR")
        print("=" * 72)
        print()
        print(str(exc))
        print()

        sys.exit(1)
````
