import os
import json
import sys
import base64
from pathlib import Path
from datetime import datetime, timezone

import requests

from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    PageBreak,
)


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"

DATA_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# ENVIRONMENT
# ============================================================

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "").strip()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "").strip()
FROM_EMAIL = os.getenv("FROM_EMAIL", "").strip()
RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL", "").strip()


# ============================================================
# CONFIG
# ============================================================

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Keep your working free router.
OPENROUTER_MODEL = "openrouter/free"

YOUTUBE_URL = "https://www.googleapis.com/youtube/v3/videos"

AI_ATTEMPTS = 3


# ============================================================
# PRINT HELPERS
# ============================================================

def print_line():
    print("=" * 60)


def print_section(title):
    print_line()
    print(title)
    print_line()


# ============================================================
# ENVIRONMENT CHECK
# ============================================================

def check_environment():
    print_section("CHECKING ENVIRONMENT")

    required = {
        "OPENROUTER_API_KEY": OPENROUTER_API_KEY,
        "RESEND_API_KEY": RESEND_API_KEY,
        "FROM_EMAIL": FROM_EMAIL,
        "RECIPIENT_EMAIL": RECIPIENT_EMAIL,
        "YOUTUBE_API_KEY": YOUTUBE_API_KEY,
    }

    missing = []

    for name, value in required.items():
        if value:
            print(f"{name}: OK")
        else:
            print(f"{name}: MISSING")
            missing.append(name)

    if missing:
        raise RuntimeError(
            "Missing GitHub Secrets: " + ", ".join(missing)
        )

    print("Environment check: OK")


# ============================================================
# YOUTUBE
# ============================================================

def collect_youtube_most_popular(country_code, max_results=50):

    print(
        f"Collecting YouTube mostPopular data: "
        f"{country_code}"
    )

    params = {
        "part": "snippet,statistics",
        "chart": "mostPopular",
        "regionCode": country_code,
        "maxResults": max_results,
        "key": YOUTUBE_API_KEY,
    }

    response = requests.get(
        YOUTUBE_URL,
        params=params,
        timeout=30,
    )

    print(f"YouTube HTTP status: {response.status_code}")

    response.raise_for_status()

    data = response.json()

    videos = []

    for item in data.get("items", []):

        snippet = item.get("snippet", {})
        stats = item.get("statistics", {})

        video_id = item.get("id", "")

        videos.append({
            "video_id": video_id,
            "title": snippet.get("title", ""),
            "description": snippet.get("description", ""),
            "channel": snippet.get("channelTitle", ""),
            "published_at": snippet.get("publishedAt", ""),
            "category_id": snippet.get("categoryId", ""),
            "view_count": int(
                stats.get("viewCount", 0)
            ),
            "like_count": int(
                stats.get("likeCount", 0)
            ),
            "comment_count": int(
                stats.get("commentCount", 0)
            ),
            "country": country_code,
            "url": (
                f"https://www.youtube.com/watch?v={video_id}"
                if video_id
                else ""
            ),
        })

    print(f"Collected {len(videos)} videos.")

    return videos


# ============================================================
# AI PROMPT
# ============================================================

def build_ai_prompt(india_videos, worldwide_videos):

    now = datetime.now(timezone.utc).isoformat()

    videos = india_videos + worldwide_videos

    compact_data = []

    for video in videos:

        compact_data.append({
            "country": video.get("country"),
            "title": video.get("title"),
            "channel": video.get("channel"),
            "views": video.get("view_count"),
            "likes": video.get("like_count"),
            "comments": video.get("comment_count"),
        })

    data_text = json.dumps(
        compact_data,
        ensure_ascii=False,
    )

    return f"""
You are a professional YouTube entertainment strategist.

Current UTC timestamp:
{now}

Analyze the YouTube trend data below.

Create EXACTLY 24 ORIGINAL YouTube video ideas.

Target audience:
Indian / Telugu entertainment viewers.

Preferred genres:
- Thriller
- Mystery
- Suspense
- Comedy
- Entertainment
- Relatable everyday situations

The ideas must NOT be:
- childish
- random
- silly
- generic
- boring
- copied from existing videos

The ideas should have strong curiosity and click potential.

The creator prefers concepts that can realistically be produced with
simple equipment and preferably one main performer.

For EVERY idea provide:

rank
title
format
genre
hook
concept
why_clickable
thumbnail
twist
difficulty
duration

IMPORTANT JSON RULES:

1. Return ONLY one valid JSON object.
2. Do NOT use Markdown.
3. Do NOT use ```json.
4. Do NOT explain your answer.
5. Do NOT write reasoning.
6. Do NOT write anything before the opening {{.
7. Do NOT write anything after the closing }}.
8. Generate REAL ideas, not placeholder examples.
9. Do not use "..." anywhere.
10. Do not use "current UTC time" as the generated_at value.
11. generated_at must be exactly:
   "{now}"

Required structure:

{{
  "generated_at": "{now}",
  "ideas": [
    {{
      "rank": 1,
      "title": "real title",
      "format": "Short",
      "genre": "Thriller",
      "hook": "real hook",
      "concept": "real story concept",
      "why_clickable": "real reason",
      "thumbnail": "real thumbnail idea",
      "twist": "real twist",
      "difficulty": "Easy",
      "duration": "60 seconds"
    }}
  ]
}}

The above is ONLY a structural example.
Do not copy its placeholder text.

You MUST generate 24 real ideas.

YouTube trend data:

{data_text}
"""


# ============================================================
# CLEAN AI RESPONSE
# ============================================================

def clean_ai_response(text):

    if not text:
        raise RuntimeError(
            "OpenRouter returned empty content."
        )

    text = text.strip()

    # Remove markdown fences.
    if "```" in text:

        text = text.replace(
            "```json",
            "",
        )

        text = text.replace(
            "```JSON",
            "",
        )

        text = text.replace(
            "```",
            "",
        )

        text = text.strip()

    return text


# ============================================================
# EXTRACT JSON
# ============================================================

def extract_json_object(text):

    text = clean_ai_response(text)

    # --------------------------------------------------------
    # First attempt: entire response is JSON.
    # --------------------------------------------------------

    try:
        data = json.loads(text)

        if isinstance(data, dict):
            return data

    except json.JSONDecodeError:
        pass

    # --------------------------------------------------------
    # Second attempt: locate JSON object using JSONDecoder.
    # This handles AI reasoning before/after JSON.
    # --------------------------------------------------------

    decoder = json.JSONDecoder()

    positions = [
        i for i, char in enumerate(text)
        if char == "{"
    ]

    candidates = []

    for position in positions:

        try:
            obj, end = decoder.raw_decode(
                text[position:]
            )

            if isinstance(obj, dict):

                candidates.append(
                    (position, end, obj)
                )

        except json.JSONDecodeError:
            continue

    if not candidates:
        raise RuntimeError(
            "Could not find a valid JSON object in "
            "OpenRouter response.\n\n"
            + text[:5000]
        )

    # Prefer candidate containing ideas.
    for _, _, obj in candidates:

        if isinstance(obj.get("ideas"), list):
            return obj

    # Otherwise return largest dictionary.
    candidates.sort(
        key=lambda item: len(
            json.dumps(item[2])
        ),
        reverse=True,
    )

    return candidates[0][2]


# ============================================================
# VALIDATE AI RESULT
# ============================================================

def validate_ai_result(data):

    if not isinstance(data, dict):
        raise RuntimeError(
            "AI result is not a JSON object."
        )

    ideas = data.get("ideas")

    if not isinstance(ideas, list):
        raise RuntimeError(
            "AI result does not contain an ideas list."
        )

    # We need actual ideas, not the template.
    if len(ideas) < 10:
        raise RuntimeError(
            f"AI returned only {len(ideas)} ideas. "
            "Expected 24."
        )

    required_fields = [
        "rank",
        "title",
        "format",
        "genre",
        "hook",
        "concept",
        "why_clickable",
        "thumbnail",
        "twist",
        "difficulty",
        "duration",
    ]

    valid_ideas = []

    for idea in ideas:

        if not isinstance(idea, dict):
            continue

        # Reject obvious template placeholders.
        values = json.dumps(
            idea,
            ensure_ascii=False,
        )

        if "..." in values:
            continue

        if "real title" in values.lower():
            continue

        if "real hook" in values.lower():
            continue

        if "real story concept" in values.lower():
            continue

        missing = [
            field
            for field in required_fields
            if not idea.get(field)
        ]

        if missing:
            continue

        valid_ideas.append(idea)

    if len(valid_ideas) < 10:
        raise RuntimeError(
            "AI response contains too many invalid/"
            "placeholder ideas."
        )

    # Keep exactly 24 when possible.
    valid_ideas = valid_ideas[:24]

    # Re-number cleanly.
    for index, idea in enumerate(
        valid_ideas,
        start=1,
    ):
        idea["rank"] = index

    data["ideas"] = valid_ideas

    data["generated_at"] = (
        datetime.now(timezone.utc).isoformat()
    )

    return data


# ============================================================
# OPENROUTER
# ============================================================

def generate_high_ctr_ideas(
    india_videos,
    worldwide_videos,
):

    print(
        "Generating HIGH CTR + YouTube ideas..."
    )

    prompt = build_ai_prompt(
        india_videos,
        worldwide_videos,
    )

    headers = {
        "Authorization":
            f"Bearer {OPENROUTER_API_KEY}",

        "Content-Type":
            "application/json",

        "HTTP-Referer":
            "https://github.com/",

        "X-Title":
            "YouTube High CTR Idea Generator",
    }

    for attempt in range(
        1,
        AI_ATTEMPTS + 1,
    ):

        print("OPENROUTER REQUEST")
        print(
            f"Model: {OPENROUTER_MODEL}"
        )
        print(
            f"Attempt: {attempt}"
        )

        payload = {
            "model": OPENROUTER_MODEL,

            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Return ONLY valid JSON. "
                        "Never output reasoning, "
                        "Markdown or explanations."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],

            # Important for OpenRouter JSON output.
            "response_format": {
                "type": "json_object"
            },

            "temperature": 0.7,

            "max_tokens": 14000,
        }

        try:

            response = requests.post(
                OPENROUTER_URL,
                headers=headers,
                json=payload,
                timeout=180,
            )

            print(
                f"HTTP status: "
                f"{response.status_code}"
            )

            if response.status_code != 200:

                print(
                    "OpenRouter error:"
                )

                print(
                    response.text[:3000]
                )

                if attempt == AI_ATTEMPTS:
                    response.raise_for_status()

                continue

            result = response.json()

            print("OpenRouter SUCCESS")

            model_used = result.get(
                "model",
                OPENROUTER_MODEL,
            )

            print(
                f"Model used: {model_used}"
            )

            choices = result.get(
                "choices",
                [],
            )

            if not choices:
                raise RuntimeError(
                    "OpenRouter returned no choices."
                )

            message = choices[0].get(
                "message",
                {},
            )

            content = message.get(
                "content",
                "",
            )

            # Some providers may put output elsewhere.
            if isinstance(content, list):

                content = "".join(
                    item.get("text", "")
                    if isinstance(item, dict)
                    else str(item)
                    for item in content
                )

            print(
                f"AI response length: "
                f"{len(content)} characters"
            )

            data = extract_json_object(
                content
            )

            data = validate_ai_result(
                data
            )

            print(
                f"VALID AI RESULT: "
                f"{len(data['ideas'])} ideas"
            )

            return data

        except Exception as exc:

            print(
                f"AI attempt {attempt} failed: "
                f"{type(exc).__name__}: {exc}"
            )

            if attempt == AI_ATTEMPTS:
                raise RuntimeError(
                    "OpenRouter failed after "
                    f"{AI_ATTEMPTS} attempts: "
                    f"{exc}"
                ) from exc

            print(
                "Retrying OpenRouter..."
            )

    raise RuntimeError(
        "OpenRouter generation failed."
    )


# ============================================================
# SAVE JSON
# ============================================================

def save_json(data):

    output_file = (
        DATA_DIR /
        "youtube_high_ctr_ideas.json"
    )

    with output_file.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2,
        )

    print("RESULT SAVED")
    print(output_file)

    return output_file


# ============================================================
# PDF
# ============================================================

def create_pdf_styles():

    styles = getSampleStyleSheet()

    styles.add(
        ParagraphStyle(
            name="CTRTitle",
            parent=styles["Title"],
            fontSize=21,
            leading=25,
            alignment=TA_CENTER,
            spaceAfter=12,
        )
    )

    styles.add(
        ParagraphStyle(
            name="CTRHeading",
            parent=styles["Heading2"],
            fontSize=14,
            leading=18,
            spaceAfter=8,
        )
    )

    styles.add(
        ParagraphStyle(
            name="CTRBody",
            parent=styles["BodyText"],
            fontSize=9.5,
            leading=13,
            spaceAfter=6,
        )
    )

    return styles


def safe_text(value):

    if value is None:
        return ""

    if isinstance(
        value,
        (dict, list),
    ):
        value = json.dumps(
            value,
            ensure_ascii=False,
        )

    # Prevent ReportLab XML problems.
    value = str(value)

    value = (
        value
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )

    return value


def pdf_field(
    label,
    value,
    styles,
):

    return Paragraph(
        f"<b>{label}:</b> "
        f"{safe_text(value)}",
        styles["CTRBody"],
    )


def create_pdf(data):

    print_section(
        "CREATING PDF"
    )

    pdf_file = (
        OUTPUT_DIR /
        "youtube_high_ctr_ideas.pdf"
    )

    styles = create_pdf_styles()

    document = SimpleDocTemplate(
        str(pdf_file),
        pagesize=A4,
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
        title="YouTube High CTR Ideas",
        author="YouTube High CTR Idea Generator",
    )

    story = []

    story.append(
        Paragraph(
            "YOUTUBE HIGH CTR IDEA GENERATOR",
            styles["CTRTitle"],
        )
    )

    story.append(
        Paragraph(
            "India + Worldwide YouTube Trend Analysis",
            styles["CTRBody"],
        )
    )

    story.append(
        Paragraph(
            "<b>Generated:</b> "
            + safe_text(
                data.get("generated_at")
            ),
            styles["CTRBody"],
        )
    )

    story.append(
        Paragraph(
            "<b>Total Ideas:</b> "
            + str(
                len(
                    data.get(
                        "ideas",
                        [],
                    )
                )
            ),
            styles["CTRBody"],
        )
    )

    story.append(
        Spacer(1, 10)
    )

    ideas = data.get(
        "ideas",
        [],
    )

    for index, idea in enumerate(
        ideas,
        start=1,
    ):

        title = idea.get(
            "title",
            f"Idea {index}",
        )

        story.append(
            Paragraph(
                f"{index}. "
                f"{safe_text(title)}",
                styles["CTRHeading"],
            )
        )

        story.append(
            pdf_field(
                "Format",
                idea.get("format"),
                styles,
            )
        )

        story.append(
            pdf_field(
                "Genre",
                idea.get("genre"),
                styles,
            )
        )

        story.append(
            pdf_field(
                "Hook",
                idea.get("hook"),
                styles,
            )
        )

        story.append(
            pdf_field(
                "Concept",
                idea.get("concept"),
                styles,
            )
        )

        story.append(
            pdf_field(
                "Why Viewers Will Click",
                idea.get(
                    "why_clickable"
                ),
                styles,
            )
        )

        story.append(
            pdf_field(
                "Thumbnail",
                idea.get(
                    "thumbnail"
                ),
                styles,
            )
        )

        story.append(
            pdf_field(
                "Twist / Reveal",
                idea.get("twist"),
                styles,
            )
        )

        story.append(
            pdf_field(
                "Difficulty",
                idea.get(
                    "difficulty"
                ),
                styles,
            )
        )

        story.append(
            pdf_field(
                "Duration",
                idea.get(
                    "duration"
                ),
                styles,
            )
        )

        if index < len(ideas):
            story.append(
                PageBreak()
            )

    document.build(story)

    print("PDF CREATED")
    print(pdf_file)

    return pdf_file


# ============================================================
# RESEND
# ============================================================

def send_email(
    pdf_file,
    json_file,
):

    print_section(
        "SENDING EMAIL"
    )

    resend_url = (
        "https://api.resend.com/emails"
    )

    timestamp = (
        datetime.now(timezone.utc)
        .strftime(
            "%Y-%m-%d %H:%M UTC"
        )
    )

    subject = (
        "YouTube High CTR Ideas - "
        + timestamp
    )

    body = """Hello,

Your latest YouTube High CTR Idea Generator update is ready.

The system analyzed:
- India YouTube trends
- Worldwide proxy trends
- Current entertainment signals
- High-click potential concepts

The generated PDF and JSON files are attached.

Regards,
YouTube High CTR Idea Generator
"""

    with open(
        pdf_file,
        "rb",
    ) as file:
        pdf_base64 = base64.b64encode(
            file.read()
        ).decode("utf-8")

    with open(
        json_file,
        "rb",
    ) as file:
        json_base64 = base64.b64encode(
            file.read()
        ).decode("utf-8")

    payload = {
        "from": FROM_EMAIL,
        "to": [
            RECIPIENT_EMAIL
        ],
        "subject": subject,
        "text": body,
        "attachments": [
            {
                "filename":
                    "youtube_high_ctr_ideas.pdf",
                "content":
                    pdf_base64,
            },
            {
                "filename":
                    "youtube_high_ctr_ideas.json",
                "content":
                    json_base64,
            },
        ],
    }

    headers = {
        "Authorization":
            f"Bearer {RESEND_API_KEY}",

        "Content-Type":
            "application/json",
    }

    response = requests.post(
        resend_url,
        headers=headers,
        json=payload,
        timeout=60,
    )

    print(
        f"Resend HTTP status: "
        f"{response.status_code}"
    )

    if response.status_code not in (
        200,
        201,
    ):

        print(
            "Resend response:"
        )

        print(
            response.text[:5000]
        )

        response.raise_for_status()

    print(
        "EMAIL SENT SUCCESSFULLY"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print_line()

    print(
        "STARTING YOUTUBE HIGH CTR "
        "IDEA GENERATOR"
    )

    print_line()

    # --------------------------------------------------------
    # 1. Environment
    # --------------------------------------------------------

    check_environment()

    # --------------------------------------------------------
    # 2. India
    # --------------------------------------------------------

    print(
        "1. Collecting India trends..."
    )

    india_videos = (
        collect_youtube_most_popular(
            "IN",
            50,
        )
    )

    # --------------------------------------------------------
    # 3. Worldwide proxy
    # --------------------------------------------------------

    print(
        "2. Collecting worldwide "
        "proxy trends..."
    )

    worldwide_videos = (
        collect_youtube_most_popular(
            "US",
            50,
        )
    )

    # --------------------------------------------------------
    # 4. AI
    # --------------------------------------------------------

    print(
        "Generating HIGH CTR + "
        "YouTube ideas..."
    )

    ideas_data = (
        generate_high_ctr_ideas(
            india_videos,
            worldwide_videos,
        )
    )

    # --------------------------------------------------------
    # 5. JSON
    # --------------------------------------------------------

    json_file = save_json(
        ideas_data
    )

    # --------------------------------------------------------
    # 6. PDF
    # --------------------------------------------------------

    pdf_file = create_pdf(
        ideas_data
    )

    # --------------------------------------------------------
    # 7. Email
    # --------------------------------------------------------

    send_email(
        pdf_file,
        json_file,
    )

    # --------------------------------------------------------
    # DONE
    # --------------------------------------------------------

    print_line()

    print(
        "GENERATOR COMPLETED "
        "SUCCESSFULLY"
    )

    print_line()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    try:

        main()

    except KeyboardInterrupt:

        print(
            "\nProcess interrupted."
        )

        sys.exit(130)

    except Exception as exc:

        print_section(
            "FATAL ERROR"
        )

        print(
            f"{type(exc).__name__}: "
            f"{exc}"
        )

        sys.exit(1)
