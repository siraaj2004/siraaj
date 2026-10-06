import os
import json
import sys
from pathlib import Path
from datetime import datetime, timezone

import requests

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
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

# OpenRouter free router
OPENROUTER_MODEL = "openrouter/free"

YOUTUBE_URL = "https://www.googleapis.com/youtube/v3/videos"


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

    missing = []

    checks = {
        "OPENROUTER_API_KEY": OPENROUTER_API_KEY,
        "RESEND_API_KEY": RESEND_API_KEY,
        "FROM_EMAIL": FROM_EMAIL,
        "RECIPIENT_EMAIL": RECIPIENT_EMAIL,
        "YOUTUBE_API_KEY": YOUTUBE_API_KEY,
    }

    for name, value in checks.items():
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
# YOUTUBE TREND COLLECTION
# ============================================================

def collect_youtube_most_popular(country_code, max_results=50):
    print(f"Collecting YouTube mostPopular data: {country_code}")

    params = {
        "part": "snippet,statistics,contentDetails",
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
        statistics = item.get("statistics", {})

        videos.append({
            "video_id": item.get("id"),
            "title": snippet.get("title", ""),
            "description": snippet.get("description", ""),
            "channel": snippet.get("channelTitle", ""),
            "published_at": snippet.get("publishedAt", ""),
            "category_id": snippet.get("categoryId", ""),
            "view_count": int(statistics.get("viewCount", 0)),
            "like_count": int(statistics.get("likeCount", 0)),
            "comment_count": int(statistics.get("commentCount", 0)),
            "country": country_code,
            "url": (
                f"https://www.youtube.com/watch?v={item.get('id')}"
                if item.get("id")
                else ""
            ),
        })

    print(f"Collected {len(videos)} videos.")

    return videos


# ============================================================
# OPENROUTER AI
# ============================================================

def generate_high_ctr_ideas(india_videos, worldwide_videos):
    print("Generating HIGH CTR + YouTube ideas...")
    print("OPENROUTER REQUEST")
    print(f"Model: {OPENROUTER_MODEL}")
    print("Attempt: 1")

    # Keep the prompt reasonably sized.
    all_videos = india_videos + worldwide_videos

    video_data = []

    for video in all_videos:
        video_data.append({
            "country": video.get("country"),
            "title": video.get("title"),
            "channel": video.get("channel"),
            "views": video.get("view_count"),
            "likes": video.get("like_count"),
            "comments": video.get("comment_count"),
            "published": video.get("published_at"),
        })

    prompt = f"""
You are a professional YouTube entertainment strategist.

Analyze the current YouTube trending data below and generate HIGH-CTR
YouTube video ideas for an Indian creator.

The creator wants:
- Entertainment videos
- Thriller
- Mystery
- Suspense
- Comedy
- Relatable everyday situations
- Strong curiosity
- Simple production
- Ideas that can be shot by one person
- Ideas suitable for Indian/Telugu audiences
- Both YouTube Shorts and 8-10 minute videos

IMPORTANT:
Do NOT generate childish, silly, random, generic or boring concepts.

Every idea should have:
1. Title
2. Format
3. Genre
4. Hook
5. Story concept
6. Why viewers will click
7. Thumbnail idea
8. Twist/reveal
9. Difficulty
10. Estimated duration

Generate 24 strong ideas.

Return ONLY valid JSON.

Use exactly this structure:

{{
  "generated_at": "current UTC time",
  "ideas": [
    {{
      "rank": 1,
      "title": "...",
      "format": "Short / 8-10 Minute",
      "genre": "...",
      "hook": "...",
      "concept": "...",
      "why_clickable": "...",
      "thumbnail": "...",
      "twist": "...",
      "difficulty": "Easy / Medium / Hard",
      "duration": "..."
    }}
  ]
}}

CURRENT YOUTUBE DATA:

{json.dumps(video_data, ensure_ascii=False)}
"""

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/",
        "X-Title": "YouTube High CTR Idea Generator",
    }

    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are an expert YouTube entertainment strategist. "
                    "Return only valid JSON."
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

    response = requests.post(
        OPENROUTER_URL,
        headers=headers,
        json=payload,
        timeout=180,
    )

    print(f"HTTP status: {response.status_code}")

    if response.status_code != 200:
        print("OpenRouter response:")
        print(response.text[:5000])
        response.raise_for_status()

    result = response.json()

    print("OpenRouter SUCCESS")

    model_used = result.get("model", OPENROUTER_MODEL)
    print(f"Model used: {model_used}")

    choices = result.get("choices", [])

    if not choices:
        raise RuntimeError("OpenRouter returned no choices.")

    content = choices[0].get("message", {}).get("content", "")

    if not content:
        raise RuntimeError("OpenRouter returned empty content.")

    return parse_ai_json(content)


# ============================================================
# JSON PARSER
# ============================================================

def parse_ai_json(content):
    content = content.strip()

    # Remove Markdown code fences if AI accidentally returns them.
    if content.startswith("```"):
        lines = content.splitlines()

        if lines:
            lines = lines[1:]

        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        content = "\n".join(lines).strip()

    # Find JSON object if extra text exists.
    start = content.find("{")
    end = content.rfind("}")

    if start == -1 or end == -1:
        raise RuntimeError(
            "OpenRouter did not return valid JSON.\n"
            + content[:3000]
        )

    content = content[start:end + 1]

    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Could not parse OpenRouter JSON: {exc}\n\n"
            f"Response:\n{content[:5000]}"
        ) from exc

    if not isinstance(data, dict):
        raise RuntimeError("AI JSON result is not an object.")

    if not isinstance(data.get("ideas"), list):
        raise RuntimeError("AI JSON does not contain an ideas list.")

    return data


# ============================================================
# SAVE JSON
# ============================================================

def save_json(data):
    output_file = DATA_DIR / "youtube_high_ctr_ideas.json"

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
# PDF STYLES
# ============================================================

def create_pdf_styles():
    styles = getSampleStyleSheet()

    styles.add(
        ParagraphStyle(
            name="CustomTitle",
            parent=styles["Title"],
            fontSize=22,
            leading=26,
            alignment=TA_CENTER,
            spaceAfter=12,
        )
    )

    styles.add(
        ParagraphStyle(
            name="IdeaTitle",
            parent=styles["Heading2"],
            fontSize=15,
            leading=19,
            spaceAfter=8,
        )
    )

    styles.add(
        ParagraphStyle(
            name="BodyCustom",
            parent=styles["BodyText"],
            fontSize=9.5,
            leading=14,
            spaceAfter=6,
        )
    )

    styles.add(
        ParagraphStyle(
            name="SmallCustom",
            parent=styles["BodyText"],
            fontSize=8,
            leading=11,
            spaceAfter=4,
        )
    )

    return styles


# ============================================================
# PDF HELPERS
# ============================================================

def safe_text(value):
    if value is None:
        return ""

    if isinstance(value, (dict, list)):
        return json.dumps(
            value,
            ensure_ascii=False,
        )

    return str(value)


def make_paragraph(label, value, styles):
    text = (
        f"<b>{label}:</b> "
        f"{safe_text(value)}"
    )

    return Paragraph(
        text,
        styles["BodyCustom"],
    )


# ============================================================
# CREATE PDF
# ============================================================

def create_pdf(data):
    print_section("CREATING PDF")

    pdf_file = OUTPUT_DIR / "youtube_high_ctr_ideas.pdf"

    styles = create_pdf_styles()

    doc = SimpleDocTemplate(
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

    # --------------------------------------------------------
    # TITLE
    # --------------------------------------------------------

    story.append(
        Paragraph(
            "YOUTUBE HIGH CTR IDEA GENERATOR",
            styles["CustomTitle"],
        )
    )

    story.append(
        Paragraph(
            "India + Worldwide YouTube Trend Analysis",
            styles["BodyCustom"],
        )
    )

    generated_at = data.get(
        "generated_at",
        datetime.now(timezone.utc).isoformat(),
    )

    story.append(
        Paragraph(
            f"<b>Generated:</b> {safe_text(generated_at)}",
            styles["SmallCustom"],
        )
    )

    story.append(Spacer(1, 8))

    ideas = data.get("ideas", [])

    story.append(
        Paragraph(
            f"<b>Total Ideas:</b> {len(ideas)}",
            styles["BodyCustom"],
        )
    )

    story.append(Spacer(1, 10))

    # --------------------------------------------------------
    # IDEAS
    # --------------------------------------------------------

    for index, idea in enumerate(ideas, start=1):

        if not isinstance(idea, dict):
            continue

        rank = idea.get("rank", index)
        title = idea.get(
            "title",
            f"Idea {rank}",
        )

        story.append(
            Paragraph(
                f"{rank}. {safe_text(title)}",
                styles["IdeaTitle"],
            )
        )

        story.append(
            make_paragraph(
                "Format",
                idea.get("format"),
                styles,
            )
        )

        story.append(
            make_paragraph(
                "Genre",
                idea.get("genre"),
                styles,
            )
        )

        story.append(
            make_paragraph(
                "Hook",
                idea.get("hook"),
                styles,
            )
        )

        story.append(
            make_paragraph(
                "Concept",
                idea.get("concept"),
                styles,
            )
        )

        story.append(
            make_paragraph(
                "Why Viewers Will Click",
                idea.get("why_clickable"),
                styles,
            )
        )

        story.append(
            make_paragraph(
                "Thumbnail",
                idea.get("thumbnail"),
                styles,
            )
        )

        story.append(
            make_paragraph(
                "Twist / Reveal",
                idea.get("twist"),
                styles,
            )
        )

        story.append(
            make_paragraph(
                "Difficulty",
                idea.get("difficulty"),
                styles,
            )
        )

        story.append(
            make_paragraph(
                "Duration",
                idea.get("duration"),
                styles,
            )
        )

        story.append(Spacer(1, 8))

        # ----------------------------------------------------
        # PAGE BREAK
        # ----------------------------------------------------

        if index < len(ideas):
            story.append(PageBreak())

    # --------------------------------------------------------
    # BUILD PDF
    # --------------------------------------------------------

    doc.build(story)

    print("PDF CREATED")
    print(pdf_file)

    return pdf_file


# ============================================================
# RESEND EMAIL
# ============================================================

def send_email(pdf_file, json_file):
    print_section("SENDING EMAIL")

    resend_url = "https://api.resend.com/emails"

    subject = (
        "YouTube High CTR Ideas - "
        + datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    )

    body = """
Hello,

Your latest YouTube High CTR Idea Generator update is ready.

The system analyzed:
- India YouTube trends
- Worldwide proxy trends
- Current entertainment signals
- High-click potential concepts

The generated PDF contains the latest video ideas.

Regards,
YouTube High CTR Idea Generator
"""

    # Read PDF
    with open(pdf_file, "rb") as file:
        pdf_bytes = file.read()

    import base64

    pdf_base64 = base64.b64encode(pdf_bytes).decode("utf-8")

    # Read JSON
    with open(json_file, "rb") as file:
        json_bytes = file.read()

    json_base64 = base64.b64encode(json_bytes).decode("utf-8")

    payload = {
        "from": FROM_EMAIL,
        "to": [RECIPIENT_EMAIL],
        "subject": subject,
        "text": body,
        "attachments": [
            {
                "filename": "youtube_high_ctr_ideas.pdf",
                "content": pdf_base64,
            },
            {
                "filename": "youtube_high_ctr_ideas.json",
                "content": json_base64,
            },
        ],
    }

    headers = {
        "Authorization": f"Bearer {RESEND_API_KEY}",
        "Content-Type": "application/json",
    }

    response = requests.post(
        resend_url,
        headers=headers,
        json=payload,
        timeout=60,
    )

    print(f"Resend HTTP status: {response.status_code}")

    if response.status_code not in (200, 201):
        print("Resend response:")
        print(response.text[:5000])
        response.raise_for_status()

    print("EMAIL SENT SUCCESSFULLY")


# ============================================================
# MAIN
# ============================================================

def main():
    print_line()
    print("STARTING YOUTUBE HIGH CTR IDEA GENERATOR")
    print_line()

    # 1. Environment
    check_environment()

    # 2. India trends
    print("1. Collecting India trends...")
    india_videos = collect_youtube_most_popular(
        "IN",
        50,
    )

    # 3. Worldwide trends
    print("2. Collecting worldwide proxy trends...")
    worldwide_videos = collect_youtube_most_popular(
        "US",
        50,
    )

    # 4. AI generation
    print("Generating HIGH CTR + YouTube ideas...")

    ideas_data = generate_high_ctr_ideas(
        india_videos,
        worldwide_videos,
    )

    # Add generation timestamp if missing.
    if not ideas_data.get("generated_at"):
        ideas_data["generated_at"] = (
            datetime.now(timezone.utc).isoformat()
        )

    # 5. Save JSON
    json_file = save_json(ideas_data)

    # 6. Create PDF
    pdf_file = create_pdf(ideas_data)

    # 7. Send email
    send_email(
        pdf_file,
        json_file,
    )

    print_line()
    print("GENERATOR COMPLETED SUCCESSFULLY")
    print_line()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    try:
        main()

    except KeyboardInterrupt:
        print("\nProcess interrupted by user.")
        sys.exit(130)

    except Exception as exc:
        print_section("FATAL ERROR")
        print(f"{type(exc).__name__}: {exc}")
        sys.exit(1)
