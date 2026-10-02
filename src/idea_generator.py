````python
"""
YouTube High-Engagement Idea Generator
--------------------------------------

Pipeline:
YouTube trends
    ↓
AI idea generation through OpenRouter
    ↓
JSON parsing
    ↓
PDF report
    ↓
Optional Resend email

Required .env:
    YOUTUBE_API_KEY=
    OPENROUTER_API_KEY=
    RESEND_API_KEY=
    FROM_EMAIL=
    RECIPIENT_EMAIL=

Optional:
    OPENROUTER_MODEL=openai/gpt-4.1-mini
"""

import os
import sys
import json
import time
import re
from pathlib import Path

import requests
from dotenv import load_dotenv


# ============================================================
# PATHS
# ============================================================

ROOT_DIR = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT_DIR / "src"
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


# ============================================================
# VALIDATION
# ============================================================

if not OPENROUTER_API_KEY:
    raise RuntimeError(
        "OPENROUTER_API_KEY is missing from .env"
    )


# ============================================================
# OPENROUTER
# ============================================================

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


def call_openrouter(prompt, max_retries=4):
    """
    Send prompt to OpenRouter with retry handling.

    Handles:
    - 429 rate limits
    - 500 server errors
    - 502 gateway errors
    - 503 unavailable
    - temporary network errors
    """

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/",
        "X-Title": "YouTube High Engagement Idea Generator",
    }

    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are an expert YouTube entertainment story "
                    "concept developer. Create highly engaging, realistic, "
                    "relatable concepts with strong curiosity and logical "
                    "payoffs."
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

    last_error = None

    for attempt in range(1, max_retries + 1):

        try:

            print(
                f"    OpenRouter attempt {attempt}/{max_retries}..."
            )

            response = requests.post(
                OPENROUTER_URL,
                headers=headers,
                json=payload,
                timeout=120,
            )

            # ------------------------------------------------
            # SUCCESS
            # ------------------------------------------------

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

                return content

            # ------------------------------------------------
            # TEMPORARY ERRORS
            # ------------------------------------------------

            if response.status_code in {
                429,
                500,
                502,
                503,
                504,
            }:

                last_error = (
                    f"HTTP {response.status_code}: "
                    f"{response.text[:500]}"
                )

                wait_seconds = min(5 * attempt, 20)

                print(
                    f"    Temporary API error "
                    f"({response.status_code}). "
                    f"Retrying in {wait_seconds}s..."
                )

                time.sleep(wait_seconds)
                continue

            # ------------------------------------------------
            # PERMANENT ERROR
            # ------------------------------------------------

            raise RuntimeError(
                f"OpenRouter API error "
                f"{response.status_code}: "
                f"{response.text[:1000]}"
            )

        except requests.RequestException as exc:

            last_error = str(exc)

            wait_seconds = min(5 * attempt, 20)

            print(
                f"    Network error: {exc}"
            )

            print(
                f"    Retrying in {wait_seconds}s..."
            )

            time.sleep(wait_seconds)

    raise RuntimeError(
        "OpenRouter failed after all retries.\n"
        f"Last error: {last_error}"
    )


# ============================================================
# JSON CLEANER
# ============================================================

def extract_json(text):
    """
    Extract JSON from AI response.

    Handles:
    ```json
    {...}
    ```

    and plain JSON.
    """

    text = text.strip()

    # Remove markdown fences
    text = re.sub(
        r"^```(?:json)?\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"\s*```$",
        "",
        text,
    )

    text = text.strip()

    # Direct JSON
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Find first JSON object
    start = text.find("{")
    end = text.rfind("}")

    if start != -1 and end != -1 and end > start:

        candidate = text[start:end + 1]

        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    # Find JSON array
    start = text.find("[")
    end = text.rfind("]")

    if start != -1 and end != -1 and end > start:

        candidate = text[start:end + 1]

        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    raise ValueError(
        "Could not extract valid JSON from AI response."
    )


# ============================================================
# VIDEO NORMALIZER
# ============================================================

def normalize_video(video):
    """
    Prevents errors when YouTube data contains unexpected
    structures.
    """

    if isinstance(video, dict):
        return {
            "title": str(video.get("title", "")),
            "channel": str(
                video.get("channel")
                or video.get("channel_title")
                or ""
            ),
            "url": str(
                video.get("url")
                or video.get("video_url")
                or ""
            ),
            "views": video.get("views", 0),
            "published": str(
                video.get("published")
                or video.get("published_at")
                or ""
            ),
        }

    return {
        "title": str(video),
        "channel": "",
        "url": "",
        "views": 0,
        "published": "",
    }


# ============================================================
# BUILD TREND TEXT
# ============================================================

def build_trend_context(videos):

    normalized = [
        normalize_video(video)
        for video in videos
    ]

    lines = []

    for index, video in enumerate(normalized, 1):

        lines.append(
            f"{index}. {video['title']}\n"
            f"   Channel: {video['channel']}\n"
            f"   Views: {video['views']}\n"
            f"   URL: {video['url']}\n"
        )

    return "\n".join(lines)


# ============================================================
# GENERATE IDEAS
# ============================================================

def generate_ideas(videos, number_of_ideas=24):

    trend_context = build_trend_context(videos)

    prompt = f"""
Create exactly {number_of_ideas} ORIGINAL YouTube entertainment
video concepts inspired by the trend signals below.

IMPORTANT:

Do NOT simply copy the videos.

Use the trends only as inspiration for:
- curiosity
- viewer psychology
- hooks
- formats
- situations
- themes
- entertainment patterns

The concepts must work for an Indian/Telugu audience while remaining
understandable to normal viewers.

QUALITY REQUIREMENTS:

Every concept should have:

1. A relatable everyday setup.
2. A specific unusual contradiction/problem.
3. A strong curiosity question.
4. A reason for the protagonist to investigate.
5. At least 2 meaningful clues.
6. A believable wrong theory.
7. Escalation.
8. A logical final reveal.
9. A satisfying payoff.
10. Potential for strong audience retention.

Avoid:

- random ghosts
- dreams as the twist
- random coincidences
- meaningless prank endings
- supernatural explanations without setup
- childish/silly comedy
- generic "something strange happened"
- copied movie plots
- copied YouTube videos
- impossible technology
- expensive production requirements

The concepts should feel like:

"Wait... why is this happening?"

followed by:

"I need to know what is actually going on."

Then the ending should make the viewer think:

"Ohhh... THAT'S why!"

The ideas should be suitable for:
- YouTube Shorts
- 8–10 minute videos

Prefer realistic locations such as:
- terrace
- apartment
- room
- lobby
- street
- shop
- office
- parking area
- staircase

Give each concept:

- title
- hook
- story_log
- investigation
- clues
- wrong_theory
- escalation
- reveal
- comedy_payoff
- production_level
- short_version
- long_version

Return ONLY valid JSON.

Required JSON structure:

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
        f"    Sending {len(videos)} trend videos to "
        f"{OPENROUTER_MODEL}..."
    )

    raw_response = call_openrouter(prompt)

    print("    AI response received.")

    data = extract_json(raw_response)

    # --------------------------------------------------------
    # Normalize output
    # --------------------------------------------------------

    if isinstance(data, dict):
        ideas = data.get("ideas", [])

    elif isinstance(data, list):
        ideas = data

    else:
        raise ValueError(
            "AI returned an unexpected JSON structure."
        )

    if not isinstance(ideas, list):
        raise ValueError(
            "'ideas' must be a list."
        )

    cleaned_ideas = []

    for index, idea in enumerate(ideas, 1):

        if not isinstance(idea, dict):
            continue

        cleaned_ideas.append({
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
            "clues": (
                idea.get("clues", [])
                if isinstance(
                    idea.get("clues", []),
                    list
                )
                else []
            ),
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
        })

    if not cleaned_ideas:
        raise ValueError(
            "AI returned zero valid ideas."
        )

    return cleaned_ideas


# ============================================================
# SAVE JSON
# ============================================================

def save_json(ideas):

    output_file = REPORTS_DIR / "ideas.json"

    with open(
        output_file,
        "w",
        encoding="utf-8",
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
        f"    JSON saved: {output_file}"
    )

    return output_file


# ============================================================
# PDF
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
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.enums import TA_CENTER

    except ImportError:

        print(
            "    reportlab is not installed."
        )

        print(
            "    Run: pip install reportlab"
        )

        return None

    output_file = (
        REPORTS_DIR /
        "youtube_high_engagement_ideas.pdf"
    )

    styles = getSampleStyleSheet()

    title_style = styles["Title"]
    title_style.alignment = TA_CENTER

    heading = styles["Heading2"]
    body = styles["BodyText"]

    doc = SimpleDocTemplate(
        str(output_file),
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
            title_style,
        )
    )

    story.append(
        Spacer(1, 20)
    )

    for index, idea in enumerate(ideas, 1):

        story.append(
            Paragraph(
                f"{index}. {idea['title']}",
                heading,
            )
        )

        fields = [
            ("HOOK", idea["hook"]),
            ("STORY LOG", idea["story_log"]),
            ("INVESTIGATION", idea["investigation"]),
            (
                "CLUES",
                "<br/>".join(
                    f"• {c}"
                    for c in idea["clues"]
                ),
            ),
            (
                "WRONG THEORY",
                idea["wrong_theory"],
            ),
            (
                "ESCALATION",
                idea["escalation"],
            ),
            (
                "REVEAL",
                idea["reveal"],
            ),
            (
                "COMEDY PAYOFF",
                idea["comedy_payoff"],
            ),
            (
                "PRODUCTION LEVEL",
                idea["production_level"],
            ),
            (
                "SHORT VERSION",
                idea["short_version"],
            ),
            (
                "8–10 MIN VERSION",
                idea["long_version"],
            ),
        ]

        for label, value in fields:

            safe_value = str(value).replace(
                "&",
                "&amp;"
            )

            story.append(
                Paragraph(
                    f"<b>{label}</b><br/>{safe_value}",
                    body,
                )
            )

            story.append(
                Spacer(1, 7)
            )

        if index != len(ideas):

            story.append(
                PageBreak()
            )

    doc.build(story)

    print(
        f"    PDF saved: {output_file}"
    )

    return output_file


# ============================================================
# RESEND EMAIL
# ============================================================

def send_email(pdf_path):

    if not RESEND_API_KEY:
        print(
            "    RESEND_API_KEY not configured. "
            "Skipping email."
        )
        return False

    if not FROM_EMAIL:
        print(
            "    FROM_EMAIL not configured. "
            "Skipping email."
        )
        return False

    if not RECIPIENT_EMAIL:
        print(
            "    RECIPIENT_EMAIL not configured. "
            "Skipping email."
        )
        return False

    try:

        import base64

        with open(
            pdf_path,
            "rb",
        ) as file:

            encoded_pdf = base64.b64encode(
                file.read()
            ).decode()

        payload = {
            "from": FROM_EMAIL,
            "to": [RECIPIENT_EMAIL],
            "subject": (
                "YouTube High-Engagement Ideas"
            ),
            "html": """
            <h2>YouTube High-Engagement Ideas</h2>
            <p>Your latest trend-based idea report
            is attached.</p>
            """,
            "attachments": [
                {
                    "filename": (
                        "youtube_high_engagement_ideas.pdf"
                    ),
                    "content": encoded_pdf,
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

        if response.status_code in {200, 201}:

            print(
                "    Email sent successfully."
            )

            return True

        print(
            "    Email failed:"
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
# MAIN
# ============================================================

def main():

    print()
    print("=" * 72)
    print(
        "YOUTUBE HIGH-ENGAGEMENT IDEA GENERATOR"
    )
    print("=" * 72)

    # --------------------------------------------------------
    # Import YouTube agent
    # --------------------------------------------------------

    try:

        from youtube_agent import get_trending_videos

    except ImportError:

        try:

            from youtube_agent import get_videos

            get_trending_videos = get_videos

        except ImportError as exc:

            print()
            print(
                "ERROR: Could not import youtube_agent."
            )

            print(exc)

            sys.exit(1)

    # --------------------------------------------------------
    # Collect videos
    # --------------------------------------------------------

    print()
    print("[1/5] Connecting to YouTube...")

    print()
    print(
        "[2/5] Collecting India + worldwide-proxy trends..."
    )

    try:

        videos = get_trending_videos()

    except TypeError:

        # Compatibility with older youtube_agent.py
        videos = []

        try:

            india = get_trending_videos(
                keyword="India",
                limit=50,
            )

            if india:
                videos.extend(india)

        except Exception as exc:

            print(
                f"    India collection warning: {exc}"
            )

        try:

            worldwide = get_trending_videos(
                keyword="worldwide",
                limit=50,
            )

            if worldwide:
                videos.extend(worldwide)

        except Exception as exc:

            print(
                f"    Worldwide collection warning: {exc}"
            )

    if not videos:

        raise RuntimeError(
            "No YouTube videos were collected."
        )

    # --------------------------------------------------------
    # Print counts
    # --------------------------------------------------------

    india_count = min(
        49,
        len(videos)
    )

    worldwide_count = max(
        0,
        len(videos) - india_count
    )

    print(
        f"    Total videos: {len(videos)}"
    )

    # --------------------------------------------------------
    # Generate
    # --------------------------------------------------------

    print()
    print(
        "[3/5] Generating 24 candidate concepts..."
    )

    ideas = generate_ideas(
        videos,
        number_of_ideas=24,
    )

    print(
        f"    Generated {len(ideas)} ideas."
    )

    # --------------------------------------------------------
    # JSON
    # --------------------------------------------------------

    print()
    print(
        "[4/5] Saving JSON + PDF..."
    )

    json_file = save_json(ideas)

    pdf_file = create_pdf(ideas)

    # --------------------------------------------------------
    # Email
    # --------------------------------------------------------

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

    print()
    print(
        f"Ideas generated: {len(ideas)}"
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
    main()
````
