````python
import os
import re
import json
import base64
import html
import time
from pathlib import Path
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv
from reportlab.lib import colors
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
DATA_DIR.mkdir(parents=True, exist_ok=True)

JSON_FILE = DATA_DIR / "youtube_high_ctr_ideas.json"
PDF_FILE = DATA_DIR / "youtube_high_ctr_ideas.pdf"


# ============================================================
# LOAD ENVIRONMENT
# ============================================================

load_dotenv(BASE_DIR / ".env")

OPENROUTER_API_KEY = os.getenv(
    "OPENROUTER_API_KEY",
    ""
).strip()

RESEND_API_KEY = os.getenv(
    "RESEND_API_KEY",
    ""
).strip()

FROM_EMAIL = os.getenv(
    "FROM_EMAIL",
    ""
).strip()

RECIPIENT_EMAIL = os.getenv(
    "RECIPIENT_EMAIL",
    ""
).strip()

YOUTUBE_API_KEY = os.getenv(
    "YOUTUBE_API_KEY",
    ""
).strip()


# ============================================================
# SETTINGS
# ============================================================

OPENROUTER_URL = (
    "https://openrouter.ai/api/v1/chat/completions"
)

OPENROUTER_MODEL = os.getenv(
    "OPENROUTER_MODEL",
    "openrouter/free"
).strip()

REQUEST_TIMEOUT = 90

MAX_OPENROUTER_RETRIES = 4

TREND_LIMIT = 50


# ============================================================
# PRINT HELPERS
# ============================================================

def print_section(title):
    print()
    print("=" * 70)
    print(title)
    print("=" * 70)


# ============================================================
# ENVIRONMENT CHECK
# ============================================================

def validate_environment():

    print_section("ENVIRONMENT CHECK")

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
            "Missing required GitHub Secrets: "
            + ", ".join(missing)
        )

    print()
    print("Environment check: OK")


# ============================================================
# YOUTUBE API
# ============================================================

def youtube_most_popular(region_code, max_results=50):

    print(
        f"Collecting YouTube mostPopular data: "
        f"{region_code}"
    )

    url = (
        "https://www.googleapis.com/youtube/v3/videos"
    )

    params = {
        "part": "snippet,statistics,contentDetails",
        "chart": "mostPopular",
        "regionCode": region_code,
        "maxResults": min(max_results, 50),
        "key": YOUTUBE_API_KEY,
    }

    response = requests.get(
        url,
        params=params,
        timeout=REQUEST_TIMEOUT,
    )

    if response.status_code != 200:

        print(
            "YouTube API ERROR:"
        )

        print(
            response.text[:2000]
        )

        raise RuntimeError(
            f"YouTube API failed: "
            f"{response.status_code}"
        )

    data = response.json()

    videos = []

    for item in data.get("items", []):

        snippet = item.get(
            "snippet",
            {}
        )

        statistics = item.get(
            "statistics",
            {}
        )

        content_details = item.get(
            "contentDetails",
            {}
        )

        video_id = item.get(
            "id",
            ""
        )

        videos.append(
            {
                "video_id": video_id,

                "title": snippet.get(
                    "title",
                    ""
                ),

                "channel": snippet.get(
                    "channelTitle",
                    ""
                ),

                "category_id": snippet.get(
                    "categoryId",
                    ""
                ),

                "published_at": snippet.get(
                    "publishedAt",
                    ""
                ),

                "description": snippet.get(
                    "description",
                    ""
                )[:500],

                "views": int(
                    statistics.get(
                        "viewCount",
                        0
                    )
                    or 0
                ),

                "likes": int(
                    statistics.get(
                        "likeCount",
                        0
                    )
                    or 0
                ),

                "comments": int(
                    statistics.get(
                        "commentCount",
                        0
                    )
                    or 0
                ),

                "duration": content_details.get(
                    "duration",
                    ""
                ),
            }
        )

    print(
        f"Collected {len(videos)} videos."
    )

    return videos


# ============================================================
# TREND CLEANER
# ============================================================

def clean_trends(videos):

    cleaned = []

    for video in videos:

        title = str(
            video.get(
                "title",
                ""
            )
        ).strip()

        if not title:
            continue

        cleaned.append(
            {
                "title": title,

                "channel": str(
                    video.get(
                        "channel",
                        ""
                    )
                ),

                "views": video.get(
                    "views",
                    0
                ),

                "likes": video.get(
                    "likes",
                    0
                ),

                "comments": video.get(
                    "comments",
                    0
                ),

                "published_at": video.get(
                    "published_at",
                    ""
                ),

                "description": str(
                    video.get(
                        "description",
                        ""
                    )
                )[:300],
            }
        )

    return cleaned


# ============================================================
# JSON EXTRACTION
# ============================================================

def extract_json(text):

    if not text:
        raise ValueError(
            "AI returned an empty response."
        )

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
        flags=re.IGNORECASE,
    )

    text = text.strip()

    # Direct JSON
    try:
        return json.loads(text)
    except Exception:
        pass

    # Find first object
    start_object = text.find("{")
    end_object = text.rfind("}")

    if (
        start_object != -1
        and end_object != -1
        and end_object > start_object
    ):
        candidate = text[
            start_object:end_object + 1
        ]

        try:
            return json.loads(candidate)
        except Exception:
            pass

    # Find first array
    start_array = text.find("[")
    end_array = text.rfind("]")

    if (
        start_array != -1
        and end_array != -1
        and end_array > start_array
    ):
        candidate = text[
            start_array:end_array + 1
        ]

        try:
            return json.loads(candidate)
        except Exception:
            pass

    raise ValueError(
        "AI returned invalid JSON."
    )


# ============================================================
# NORMALIZE AI RESULT
# ============================================================

def normalize_report(report):

    if isinstance(report, list):

        report = {
            "ideas": report
        }

    if not isinstance(report, dict):

        report = {
            "ideas": []
        }

    ideas = report.get(
        "ideas",
        []
    )

    if not isinstance(ideas, list):

        ideas = []

    normalized_ideas = []

    for idea in ideas:

        if not isinstance(
            idea,
            dict
        ):
            continue

        normalized_ideas.append(
            {
                "title": str(
                    idea.get(
                        "title",
                        ""
                    )
                ),

                "genre": str(
                    idea.get(
                        "genre",
                        ""
                    )
                ),

                "format": str(
                    idea.get(
                        "format",
                        ""
                    )
                ),

                "english": str(
                    idea.get(
                        "english",
                        ""
                    )
                ),

                "roman_telugu": str(
                    idea.get(
                        "roman_telugu",
                        ""
                    )
                ),

                "hook": str(
                    idea.get(
                        "hook",
                        ""
                    )
                ),

                "why_best": str(
                    idea.get(
                        "why_best",
                        ""
                    )
                ),

                "viral_reason": str(
                    idea.get(
                        "viral_reason",
                        ""
                    )
                ),

                "shorts_angle": str(
                    idea.get(
                        "shorts_angle",
                        ""
                    )
                ),

                "long_video_angle": str(
                    idea.get(
                        "long_video_angle",
                        ""
                    )
                ),

                "score": idea.get(
                    "score",
                    0
                ),
            }
        )

    final_best = report.get(
        "final_best_idea",
        {}
    )

    if not isinstance(
        final_best,
        dict
    ):
        final_best = {}

    # If AI did not provide final_best_idea,
    # use the first idea.
    if not final_best and normalized_ideas:

        final_best = normalized_ideas[0]

    report["ideas"] = normalized_ideas

    report["final_best_idea"] = final_best

    report["generated_at"] = datetime.now(
        timezone.utc
    ).isoformat()

    return report


# ============================================================
# OPENROUTER REQUEST
# ============================================================

def openrouter_request(
    prompt,
    attempt=1
):

    print()
    print("=" * 70)
    print("OPENROUTER REQUEST")
    print("=" * 70)

    print(
        f"Trying OpenRouter model: "
        f"{OPENROUTER_MODEL}"
    )

    print(
        f"Attempt: {attempt}"
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

    payload = {
        "model": OPENROUTER_MODEL,

        "messages": [
            {
                "role": "system",
                "content": (
                    "You are an expert YouTube "
                    "content strategist. "
                    "Return ONLY valid JSON. "
                    "Never use Markdown fences."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],

        "temperature": 0.8,

        "max_tokens": 12000,
    }

    response = requests.post(
        OPENROUTER_URL,
        headers=headers,
        json=payload,
        timeout=REQUEST_TIMEOUT,
    )

    print(
        f"HTTP status: "
        f"{response.status_code}"
    )

    if response.status_code >= 400:

        print(
            "OpenRouter ERROR:"
        )

        print(
            response.text[:4000]
        )

        raise RuntimeError(
            f"OpenRouter HTTP "
            f"{response.status_code}"
        )

    data = response.json()

    actual_model = data.get(
        "model",
        OPENROUTER_MODEL
    )

    print(
        "OpenRouter SUCCESS"
    )

    print(
        f"Model used: {actual_model}"
    )

    choices = data.get(
        "choices",
        []
    )

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

    if isinstance(
        content,
        list
    ):

        parts = []

        for item in content:

            if isinstance(
                item,
                dict
            ):

                text = item.get(
                    "text",
                    ""
                )

                if text:
                    parts.append(text)

        content = "".join(parts)

    if not content:

        raise RuntimeError(
            "OpenRouter returned empty content."
        )

    return content


# ============================================================
# GENERATE IDEAS
# ============================================================

def generate_ideas(
    india_trends,
    worldwide_trends
):

    india_text = json.dumps(
        india_trends,
        ensure_ascii=False,
        indent=2
    )

    worldwide_text = json.dumps(
        worldwide_trends,
        ensure_ascii=False,
        indent=2
    )

    prompt = f"""
Create a high-quality YouTube entertainment
trend report using the India and worldwide
trend data below.

IMPORTANT:

The ideas must NOT be boring.

Do NOT create generic ideas such as:

- daily vlog
- random prank
- simple reaction
- generic challenge
- random comedy
- copied movie plot

The concepts should have a strong curiosity gap,
clear viewer payoff and high CTR potential.

The creator is based in India and wants content
that can work for Indian/Telugu viewers while
also having universal entertainment value.

Generate:

1. 10 strong YouTube ideas.
2. 5 Shorts ideas.
3. 1 final best idea.
4. Give English title/concept.
5. Give Roman Telugu version.
6. Give a strong hook.
7. Explain why the concept can attract viewers.
8. Give a viral reason.
9. Give Shorts angle.
10. Give 8-10 minute video angle.
11. Give a score from 1-100.

Prioritize:

- curiosity
- suspense
- mystery
- comedy
- unexpected reveal
- relatable situations
- simple production
- strong thumbnail potential
- strong title potential
- no expensive production requirement

For the final_best_idea, select the strongest
concept from all generated ideas.

RETURN ONLY THIS JSON STRUCTURE:

{{
  "market_summary": {{
    "india": [],
    "worldwide": []
  }},

  "ideas": [
    {{
      "title": "",
      "genre": "",
      "format": "",
      "english": "",
      "roman_telugu": "",
      "hook": "",
      "why_best": "",
      "viral_reason": "",
      "shorts_angle": "",
      "long_video_angle": "",
      "score": 0
    }}
  ],

  "shorts_ideas": [
    {{
      "title": "",
      "hook": "",
      "concept": "",
      "score": 0
    }}
  ],

  "final_best_idea": {{
    "title": "",
    "genre": "",
    "format": "",
    "english": "",
    "roman_telugu": "",
    "hook": "",
    "why_best": "",
    "viral_reason": "",
    "shorts_angle": "",
    "long_video_angle": "",
    "score": 0
  }}
}}

INDIA TRENDS:

{india_text}

WORLDWIDE TRENDS:

{worldwide_text}
"""

    last_error = None

    for attempt in range(
        1,
        MAX_OPENROUTER_RETRIES + 1
    ):

        try:

            raw = openrouter_request(
                prompt,
                attempt
            )

            try:

                report = extract_json(
                    raw
                )

                return normalize_report(
                    report
                )

            except Exception as json_error:

                print()
                print(
                    "Initial JSON parsing failed:"
                )

                print(
                    str(json_error)
                )

                print()
                print(
                    "Attempting JSON repair..."
                )

                repair_prompt = f"""
Convert the following AI output into valid JSON.

Rules:

- Return ONLY JSON.
- No Markdown.
- No ``` fences.
- Do not explain anything.
- Preserve the useful information.
- Follow the exact schema below.

SCHEMA:

{{
  "market_summary": {{
    "india": [],
    "worldwide": []
  }},
  "ideas": [],
  "shorts_ideas": [],
  "final_best_idea": {{}}
}}

AI OUTPUT:

{raw[:30000]}
"""

                repaired = openrouter_request(
                    repair_prompt,
                    attempt
                )

                report = extract_json(
                    repaired
                )

                return normalize_report(
                    report
                )

        except Exception as error:

            last_error = error

            print()
            print(
                f"OpenRouter attempt "
                f"{attempt} failed:"
            )

            print(
                str(error)
            )

            if attempt < MAX_OPENROUTER_RETRIES:

                wait_seconds = (
                    attempt * 5
                )

                print(
                    f"Waiting "
                    f"{wait_seconds} seconds..."
                )

                time.sleep(
                    wait_seconds
                )

    raise RuntimeError(
        "OpenRouter generation failed "
        f"after {MAX_OPENROUTER_RETRIES} attempts. "
        f"Last error: {last_error}"
    )


# ============================================================
# SAVE JSON
# ============================================================

def save_json(report):

    with open(
        JSON_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            report,
            file,
            ensure_ascii=False,
            indent=2
        )

    print()
    print("=" * 70)
    print("RESULT SAVED")
    print("=" * 70)

    print(
        JSON_FILE
    )


# ============================================================
# PDF HELPERS
# ============================================================

def safe_pdf_text(value):

    if value is None:
        return ""

    if isinstance(
        value,
        (dict, list)
    ):

        value = json.dumps(
            value,
            ensure_ascii=False,
            indent=2
        )

    value = str(value)

    # ReportLab Paragraph needs basic
    # HTML escaping.
    value = html.escape(
        value
    )

    value = value.replace(
        "\n",
        "<br/>"
    )

    return value


# ============================================================
# CREATE PDF
# ============================================================

def create_pdf(report):

    print()
    print("=" * 70)
    print("CREATING PDF")
    print("=" * 70)

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        fontSize=22,
        leading=28,
        alignment=TA_CENTER,
        spaceAfter=18,
    )

    heading_style = ParagraphStyle(
        "ReportHeading",
        parent=styles["Heading2"],
        fontSize=15,
        leading=19,
        spaceBefore=12,
        spaceAfter=8,
    )

    body_style = ParagraphStyle(
        "ReportBody",
        parent=styles["BodyText"],
        fontSize=10,
        leading=15,
        spaceAfter=8,
    )

    small_style = ParagraphStyle(
        "ReportSmall",
        parent=styles["BodyText"],
        fontSize=8,
        leading=11,
    )

    document = SimpleDocTemplate(
        str(PDF_FILE),
        pagesize=A4,
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
        title="YouTube High CTR Idea Report",
        author="YouTube High CTR Idea Generator",
    )

    story = []

    story.append(
        Paragraph(
            "YouTube High CTR Idea Report",
            title_style
        )
    )

    story.append(
        Paragraph(
            datetime.now().strftime(
                "%d %B %Y"
            ),
            body_style
        )
    )

    story.append(
        Spacer(
            1,
            10
        )
    )

    # --------------------------------------------------------
    # FINAL BEST IDEA
    # --------------------------------------------------------

    final_idea = report.get(
        "final_best_idea",
        {}
    )

    story.append(
        Paragraph(
            "FINAL BEST IDEA",
            heading_style
        )
    )

    final_fields = [
        ("Title", "title"),
        ("Genre", "genre"),
        ("Format", "format"),
        ("English Concept", "english"),
        ("Roman Telugu", "roman_telugu"),
        ("Hook", "hook"),
        ("Why Best", "why_best"),
        ("Viral Reason", "viral_reason"),
        ("Shorts Angle", "shorts_angle"),
        ("8-10 Minute Angle", "long_video_angle"),
        ("Score", "score"),
    ]

    for label, key in final_fields:

        value = final_idea.get(
            key,
            ""
        )

        story.append(
            Paragraph(
                f"<b>{html.escape(label)}</b>",
                body_style
            )
        )

        story.append(
            Paragraph(
                safe_pdf_text(value),
                body_style
            )
        )

    story.append(
        PageBreak()
    )

    # --------------------------------------------------------
    # ALL IDEAS
    # --------------------------------------------------------

    story.append(
        Paragraph(
            "ALL HIGH CTR IDEAS",
            heading_style
        )
    )

    ideas = report.get(
        "ideas",
        []
    )

    if not ideas:

        story.append(
            Paragraph(
                "No ideas were returned.",
                body_style
            )
        )

    for index, idea in enumerate(
        ideas,
        start=1
    ):

        story.append(
            Paragraph(
                f"{index}. "
                f"{safe_pdf_text(idea.get('title', ''))}",
                heading_style
            )
        )

        for label, key in [
            ("Genre", "genre"),
            ("Format", "format"),
            ("English", "english"),
            ("Roman Telugu", "roman_telugu"),
            ("Hook", "hook"),
            ("Why Best", "why_best"),
            ("Viral Reason", "viral_reason"),
            ("Shorts Angle", "shorts_angle"),
            ("Long Video Angle", "long_video_angle"),
            ("Score", "score"),
        ]:

            value = idea.get(
                key,
                ""
            )

            story.append(
                Paragraph(
                    f"<b>{html.escape(label)}:</b> "
                    f"{safe_pdf_text(value)}",
                    body_style
                )
            )

        story.append(
            Spacer(
                1,
                10
            )
        )

    # --------------------------------------------------------
    # SHORTS
    # --------------------------------------------------------

    shorts = report.get(
        "shorts_ideas",
        []
    )

    if shorts:

        story.append(
            PageBreak()
        )

        story.append(
            Paragraph(
                "CURRENT SHORTS IDEAS",
                heading_style
            )
        )

        for index, short in enumerate(
            shorts,
            start=1
        ):

            if not isinstance(
                short,
                dict
            ):
                continue

            story.append(
                Paragraph(
                    f"{index}. "
                    f"{safe_pdf_text(short.get('title', ''))}",
                    heading_style
                )
            )

            story.append(
                Paragraph(
                    f"<b>Hook:</b> "
                    f"{safe_pdf_text(short.get('hook', ''))}",
                    body_style
                )
            )

            story.append(
                Paragraph(
                    f"<b>Concept:</b> "
                    f"{safe_pdf_text(short.get('concept', ''))}",
                    body_style
                )
            )

            story.append(
                Paragraph(
                    f"<b>Score:</b> "
                    f"{safe_pdf_text(short.get('score', ''))}",
                    body_style
                )
            )

    # --------------------------------------------------------
    # MARKET SUMMARY
    # --------------------------------------------------------

    story.append(
        PageBreak()
    )

    story.append(
        Paragraph(
            "MARKET SUMMARY",
            heading_style
        )
    )

    market_summary = report.get(
        "market_summary",
        {}
    )

    story.append(
        Paragraph(
            "<b>India</b>",
            heading_style
        )
    )

    story.append(
        Paragraph(
            safe_pdf_text(
                market_summary.get(
                    "india",
                    []
                )
            ),
            small_style
        )
    )

    story.append(
        Spacer(
            1,
            10
        )
    )

    story.append(
        Paragraph(
            "<b>Worldwide</b>",
            heading_style
        )
    )

    story.append(
        Paragraph(
            safe_pdf_text(
                market_summary.get(
                    "worldwide",
                    []
                )
            ),
            small_style
        )
    )

    document.build(
        story
    )

    if not PDF_FILE.exists():

        raise RuntimeError(
            "PDF was not created."
        )

    size = PDF_FILE.stat().st_size

    if size < 1000:

        raise RuntimeError(
            "PDF was created but appears invalid."
        )

    print(
        f"PDF created successfully: "
        f"{PDF_FILE}"
    )

    print(
        f"PDF size: {size} bytes"
    )


# ============================================================
# SEND EMAIL THROUGH RESEND
# ============================================================

def send_email(report):

    print()
    print("=" * 70)
    print("SENDING EMAIL THROUGH RESEND")
    print("=" * 70)

    if not RESEND_API_KEY:
        raise RuntimeError(
            "RESEND_API_KEY is missing."
        )

    if not FROM_EMAIL:
        raise RuntimeError(
            "FROM_EMAIL is missing."
        )

    if not RECIPIENT_EMAIL:
        raise RuntimeError(
            "RECIPIENT_EMAIL is missing."
        )

    if not PDF_FILE.exists():

        raise RuntimeError(
            f"PDF not found: {PDF_FILE}"
        )

    final_idea = report.get(
        "final_best_idea",
        {}
    )

    title = final_idea.get(
        "title",
        "YouTube High CTR Idea Report"
    )

    pdf_bytes = PDF_FILE.read_bytes()

    encoded_pdf = base64.b64encode(
        pdf_bytes
    ).decode(
        "utf-8"
    )

    email_html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
</head>

<body style="
    font-family: Arial, sans-serif;
    line-height: 1.6;
">

<h2>
YouTube High CTR Idea Generator
</h2>

<p>
Your latest YouTube trend report has been generated.
</p>

<p>
<strong>Best Idea:</strong>
{html.escape(str(title))}
</p>

<p>
The complete report is attached as a PDF.
</p>

<hr>

<p>
Generated automatically by GitHub Actions.
</p>

</body>
</html>
"""

    payload = {
        "from": FROM_EMAIL,

        "to": [
            RECIPIENT_EMAIL
        ],

        "subject": (
            "YouTube High CTR Ideas - "
            + datetime.now().strftime(
                "%d %B %Y"
            )
        ),

        "html": email_html,

        "attachments": [
            {
                "filename":
                    "youtube_high_ctr_ideas.pdf",

                "content":
                    encoded_pdf,
            }
        ],
    }

    headers = {
        "Authorization":
            f"Bearer {RESEND_API_KEY}",

        "Content-Type":
            "application/json",
    }

    print(
        f"From: {FROM_EMAIL}"
    )

    print(
        f"To: {RECIPIENT_EMAIL}"
    )

    print(
        "Attachment: "
        f"{PDF_FILE.name}"
    )

    print(
        "Connecting to Resend..."
    )

    response = requests.post(
        "https://api.resend.com/emails",
        headers=headers,
        json=payload,
        timeout=60,
    )

    print()
    print(
        f"Resend HTTP status: "
        f"{response.status_code}"
    )

    print(
        "Resend response:"
    )

    print(
        response.text[:5000]
    )

    if response.status_code >= 400:

        raise RuntimeError(
            "RESEND EMAIL FAILED: "
            f"HTTP {response.status_code} - "
            f"{response.text}"
        )

    try:

        result = response.json()

    except Exception:

        result = {}

    resend_id = result.get(
        "id",
        "unknown"
    )

    print()
    print("=" * 70)
    print("EMAIL SENT SUCCESSFULLY")
    print("=" * 70)

    print(
        f"Resend ID: {resend_id}"
    )

    print(
        f"Recipient: {RECIPIENT_EMAIL}"
    )

    return result


# ============================================================
# DISPLAY FINAL IDEA
# ============================================================

def display_final_idea(report):

    final = report.get(
        "final_best_idea",
        {}
    )

    print()
    print("=" * 70)
    print("HIGH CTR IDEA")
    print("=" * 70)

    print()
    print(
        "TITLE:",
        final.get(
            "title",
            ""
        )
    )

    print(
        "GENRE:",
        final.get(
            "genre",
            ""
        )
    )

    print(
        "FORMAT:",
        final.get(
            "format",
            ""
        )
    )

    print()

    print(
        "ENGLISH:",
        final.get(
            "english",
            ""
        )
    )

    print()

    print(
        "ROMAN TELUGU:",
        final.get(
            "roman_telugu",
            ""
        )
    )

    print()

    print(
        "HOOK:",
        final.get(
            "hook",
            ""
        )
    )

    print()

    print(
        "WHY BEST:",
        final.get(
            "why_best",
            ""
        )
    )

    print()

    print(
        "SCORE:",
        final.get(
            "score",
            ""
        )
    )


# ============================================================
# MAIN
# ============================================================

def main():

    start_time = time.time()

    print()
    print("=" * 70)
    print("STARTING YOUTUBE HIGH CTR IDEA GENERATOR")
    print("=" * 70)

    # --------------------------------------------------------
    # 1. ENVIRONMENT
    # --------------------------------------------------------

    validate_environment()

    print()
    print(
        f"OpenRouter primary model: "
        f"{OPENROUTER_MODEL}"
    )

    # --------------------------------------------------------
    # 2. INDIA TRENDS
    # --------------------------------------------------------

    print()
    print(
        "1. Collecting India trends..."
    )

    india_videos = youtube_most_popular(
        "IN",
        TREND_LIMIT
    )

    india_trends = clean_trends(
        india_videos
    )

    # --------------------------------------------------------
    # 3. WORLDWIDE / US PROXY
    # --------------------------------------------------------

    print()
    print(
        "2. Collecting worldwide proxy trends..."
    )

    worldwide_videos = youtube_most_popular(
        "US",
        TREND_LIMIT
    )

    worldwide_trends = clean_trends(
        worldwide_videos
    )

    # --------------------------------------------------------
    # 4. GENERATE IDEAS
    # --------------------------------------------------------

    print()
    print(
        "3. Generating monetization strategy..."
    )

    print()
    print(
        "4. Generating HIGH CTR + YouTube ideas..."
    )

    report = generate_ideas(
        india_trends,
        worldwide_trends
    )

    # Add raw collection information
    report["collection"] = {
        "india_video_count":
            len(india_trends),

        "worldwide_video_count":
            len(worldwide_trends),

        "india_region":
            "IN",

        "worldwide_proxy_region":
            "US",
    }

    # --------------------------------------------------------
    # 5. SAVE JSON
    # --------------------------------------------------------

    save_json(
        report
    )

    # --------------------------------------------------------
    # 6. DISPLAY IDEA
    # --------------------------------------------------------

    display_final_idea(
        report
    )

    # --------------------------------------------------------
    # 7. CREATE PDF
    # --------------------------------------------------------

    create_pdf(
        report
    )

    # --------------------------------------------------------
    # 8. SEND EMAIL
    # --------------------------------------------------------

    send_email(
        report
    )

    # --------------------------------------------------------
    # 9. FINISH
    # --------------------------------------------------------

    elapsed = round(
        time.time() - start_time,
        2
    )

    print()
    print("=" * 70)
    print("GENERATED FILES")
    print("=" * 70)

    print(
        JSON_FILE
    )

    print(
        PDF_FILE
    )

    print()
    print(
        f"Total runtime: {elapsed} seconds"
    )

    print()
    print("=" * 70)
    print("YOUTUBE HIGH CTR IDEA GENERATOR COMPLETED")
    print("=" * 70)


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    try:

        main()

    except KeyboardInterrupt:

        print()
        print(
            "Process interrupted by user."
        )

        raise SystemExit(130)

    except Exception as error:

        print()
        print("=" * 70)
        print("GENERATOR FAILED")
        print("=" * 70)

        print()
        print(
            f"ERROR: {error}"
        )

        print()

        raise
````
