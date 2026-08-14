import os
import sys
import json
import base64
from pathlib import Path
from datetime import datetime
from collections import Counter

import requests
from dotenv import load_dotenv
from googleapiclient.discovery import build
from google import genai
from google.genai import types

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
    Table,
    TableStyle,
    HRFlowable,
)
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics


# ============================================================
# PROJECT PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

ENV_FILE = BASE_DIR / ".env"

OUTPUT_DIR = BASE_DIR / "reports"
OUTPUT_DIR.mkdir(exist_ok=True)

ORIGINAL_REPORT_FILE = (
    BASE_DIR / "YouTube_Trend_Intelligence_Original.txt"
)

DATE_STRING = datetime.now().strftime("%Y%m%d_%H%M%S")

PDF_FILE = (
    OUTPUT_DIR /
    f"YouTube_Trend_Intelligence_{DATE_STRING}.pdf"
)

JSON_FILE = (
    OUTPUT_DIR /
    f"YouTube_Trend_Intelligence_{DATE_STRING}.json"
)


# ============================================================
# LOAD ENV
# ============================================================

print()
print("=" * 70)
print("YOUTUBE TREND INTELLIGENCE GENERATOR")
print("=" * 70)
print()

print("Project folder:")
print(BASE_DIR)

print()

print("Looking for .env:")
print(ENV_FILE)

if not ENV_FILE.exists():

    print()
    print("ERROR: .env file was not found.")
    print()
    print("Create:")
    print(ENV_FILE)
    print()

    sys.exit(1)

load_dotenv(
    dotenv_path=ENV_FILE,
    override=True
)

print()
print(".env loaded successfully.")


# ============================================================
# ENV VARIABLES
# ============================================================

YOUTUBE_API_KEY = os.getenv(
    "YOUTUBE_API_KEY",
    ""
).strip()

GEMINI_API_KEY = os.getenv(
    "GEMINI_API_KEY",
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


# ============================================================
# VALIDATE ENV
# ============================================================

def validate_environment():

    variables = {
        "YOUTUBE_API_KEY": YOUTUBE_API_KEY,
        "GEMINI_API_KEY": GEMINI_API_KEY,
        "RESEND_API_KEY": RESEND_API_KEY,
        "FROM_EMAIL": FROM_EMAIL,
        "RECIPIENT_EMAIL": RECIPIENT_EMAIL,
    }

    missing = [
        key
        for key, value in variables.items()
        if not value
    ]

    if missing:

        print()
        print("=" * 70)
        print("ENVIRONMENT VARIABLE ERROR")
        print("=" * 70)
        print()

        for item in missing:
            print(f"❌ {item}")

        print()

        raise RuntimeError(
            "Missing environment variables: "
            + ", ".join(missing)
        )

    print()
    print("Environment variables loaded:")

    for key in variables:
        print(f"  ✅ {key}")

    print()


# ============================================================
# ORIGINAL REPORT
# ============================================================

def load_original_report():

    if not ORIGINAL_REPORT_FILE.exists():

        print()
        print("No original report found.")
        print("Continuing with a new report.")
        print()

        return ""

    try:

        content = ORIGINAL_REPORT_FILE.read_text(
            encoding="utf-8"
        )

        print()
        print("Original report loaded:")
        print(ORIGINAL_REPORT_FILE)
        print(
            f"Characters: {len(content):,}"
        )
        print()

        return content

    except Exception as error:

        print(
            f"Could not read original report: {error}"
        )

        return ""


# ============================================================
# YOUTUBE API
# ============================================================

def get_youtube_client():

    return build(
        "youtube",
        "v3",
        developerKey=YOUTUBE_API_KEY
    )


def fetch_trending_videos(
    youtube,
    region_code,
    max_results=50
):

    response = youtube.videos().list(
        part="snippet,statistics,contentDetails",
        chart="mostPopular",
        regionCode=region_code,
        maxResults=max_results
    ).execute()

    videos = []

    for item in response.get(
        "items",
        []
    ):

        snippet = item.get(
            "snippet",
            {}
        )

        statistics = item.get(
            "statistics",
            {}
        )

        videos.append({

            "video_id":
                item.get(
                    "id",
                    ""
                ),

            "title":
                snippet.get(
                    "title",
                    ""
                ),

            "channel":
                snippet.get(
                    "channelTitle",
                    ""
                ),

            "category_id":
                snippet.get(
                    "categoryId",
                    ""
                ),

            "published_at":
                snippet.get(
                    "publishedAt",
                    ""
                ),

            "views":
                int(
                    statistics.get(
                        "viewCount",
                        0
                    )
                ),

            "likes":
                int(
                    statistics.get(
                        "likeCount",
                        0
                    )
                ),

            "comments":
                int(
                    statistics.get(
                        "commentCount",
                        0
                    )
                ),

            "description":
                snippet.get(
                    "description",
                    ""
                )[:1000],
        })

    return videos


def fetch_category_names(
    youtube,
    category_ids
):

    category_ids = list(
        set(
            str(x)
            for x in category_ids
            if x
        )
    )

    if not category_ids:
        return {}

    response = youtube.videoCategories().list(
        part="snippet",
        id=",".join(category_ids)
    ).execute()

    mapping = {}

    for item in response.get(
        "items",
        []
    ):

        mapping[
            str(item["id"])
        ] = item["snippet"]["title"]

    return mapping


def enrich_videos_with_categories(
    youtube,
    videos
):

    category_ids = [
        video.get(
            "category_id"
        )
        for video in videos
    ]

    category_map = fetch_category_names(
        youtube,
        category_ids
    )

    for video in videos:

        video["category"] = (
            category_map.get(
                str(
                    video.get(
                        "category_id",
                        ""
                    )
                ),
                "Unknown"
            )
        )

    return videos


# ============================================================
# TREND SUMMARY
# ============================================================

def build_trend_summary(videos):

    categories = Counter(
        video.get(
            "category",
            "Unknown"
        )
        for video in videos
    )

    total_views = sum(
        video.get(
            "views",
            0
        )
        for video in videos
    )

    top_videos = sorted(
        videos,
        key=lambda x: x.get(
            "views",
            0
        ),
        reverse=True
    )[:20]

    return {

        "total_videos":
            len(videos),

        "total_views":
            total_views,

        "top_categories":
            categories.most_common(),

        "top_videos":
            top_videos,
    }


# ============================================================
# GEMINI PROMPT
# ============================================================

def build_prompt(
    india_videos,
    worldwide_videos,
    original_report
):

    india_summary = build_trend_summary(
        india_videos
    )

    worldwide_summary = build_trend_summary(
        worldwide_videos
    )

    original_section = ""

    if original_report.strip():

        original_section = f"""

============================================================
ORIGINAL REPORT
============================================================

IMPORTANT:

Preserve 100% of the original information.

DO NOT:

- delete
- summarize
- shorten
- rewrite
- remove
- merge away
- change

any original information.

Preserve:

- titles
- ideas
- numbers
- statistics
- names
- hooks
- descriptions
- audiences
- durations
- viral potential
- analysis
- loglines
- content points

ONLY improve organization and readability.

ORIGINAL REPORT:

{original_report}

============================================================
END ORIGINAL REPORT
============================================================
"""

    prompt = f"""
You are a professional YouTube Trend Intelligence analyst.

Create a professional YouTube Trend Intelligence Report.

The report must cover:

1. What are trending in India/worldwide on YouTube?

2. What genres are trending in India/worldwide?

3. YouTube Shorts ideas and loglines based on trends.

4. Long-form 8–10 minute video ideas and loglines.

5. Shorts crime-comedy ideas based on trends and normal ideas.

6. Thriller/Comedy ideas based on trends and normal ideas.

============================================================
GOAL
============================================================

The creator wants:

- YouTube monetization in 5 months
- strong content
- high CTR
- strong audience curiosity

Do NOT give generic content strategy.

Give ideas and loglines.

============================================================
CREATOR FIT
============================================================

Prioritize concepts that can naturally work for:

- solo creator
- single actor
- simple locations
- thriller
- comedy
- crime-comedy
- suspense
- relatable situations
- Telugu/Indian audience
- high curiosity
- high CTR

============================================================
INDIA YOUTUBE DATA
============================================================

{json.dumps(
    india_videos,
    indent=2,
    ensure_ascii=False
)}

============================================================
WORLDWIDE PROXY DATA
============================================================

{json.dumps(
    worldwide_videos,
    indent=2,
    ensure_ascii=False
)}

YouTube Data API requires a region code.

The worldwide section uses the United States as a broad
global trend proxy.

Do not falsely claim it represents every worldwide trend.

============================================================
INDIA SUMMARY
============================================================

{json.dumps(
    india_summary,
    indent=2,
    ensure_ascii=False
)}

============================================================
WORLDWIDE SUMMARY
============================================================

{json.dumps(
    worldwide_summary,
    indent=2,
    ensure_ascii=False
)}

{original_section}

============================================================
EVERY IDEA
============================================================

Every video idea must contain:

TITLE
GENRE
LOGLINE
HOOK
CONTENT SUMMARY
VIDEO OUTLINE
TARGET AUDIENCE
ESTIMATED DURATION
VIRAL POTENTIAL

VIRAL POTENTIAL:

HIGH
MEDIUM
LOW

============================================================
LOGLINE
============================================================

The logline should clearly communicate:

- protagonist
- situation
- goal
- obstacle
- curiosity

Avoid vague concepts.

============================================================
OUTPUT
============================================================

Return ONLY valid JSON.

Use exactly:

{{
  "report_title":
    "YouTube Trend Intelligence Report",

  "executive_goal": {{
    "goal": "",
    "best_direction": "",
    "best_idea_title": "",
    "best_idea_logline": "",
    "reason": ""
  }},

  "india_trends": {{
    "overview": "",
    "trending_topics": [],
    "trending_formats": [],
    "trending_genres": [],
    "evidence": []
  }},

  "worldwide_trends": {{
    "overview": "",
    "trending_topics": [],
    "trending_formats": [],
    "trending_genres": [],
    "evidence": []
  }},

  "shorts_trend_ideas": [],

  "long_form_trend_ideas": [],

  "crime_comedy_shorts_trend_based": [],

  "crime_comedy_shorts_normal": [],

  "thriller_comedy_trend_based": [],

  "thriller_comedy_normal": [],

  "monetization_5_months_best_ideas": [],

  "final_best_idea": {{
    "title": "",
    "genre": "",
    "logline": "",
    "hook": "",
    "content_summary": "",
    "video_outline": [],
    "target_audience": "",
    "estimated_duration": "",
    "viral_potential": "",
    "why_best_for_monetization": ""
  }}
}}

Every idea object must contain:

{{
    "title": "",
    "genre": "",
    "logline": "",
    "hook": "",
    "content_summary": "",
    "video_outline": [],
    "target_audience": "",
    "estimated_duration": "",
    "viral_potential": ""
}}

Preserve all original report information when provided.
"""

    return prompt


# ============================================================
# GEMINI
# ============================================================

def generate_report(
    india_videos,
    worldwide_videos,
    original_report
):

    print(
        "[3/5] Generating report with Gemini..."
    )

    client = genai.Client(
        api_key=GEMINI_API_KEY
    )

    prompt = build_prompt(
        india_videos,
        worldwide_videos,
        original_report
    )

    response = client.models.generate_content(

        model="gemini-2.5-flash",

        contents=prompt,

        config=types.GenerateContentConfig(

            response_mime_type="application/json",

            temperature=0.4,
        ),
    )

    if not response.text:

        raise RuntimeError(
            "Gemini returned an empty response."
        )

    text = response.text.strip()

    if text.startswith("```"):

        text = text.replace(
            "```json",
            ""
        )

        text = text.replace(
            "```",
            ""
        )

        text = text.strip()

    try:

        return json.loads(
            text
        )

    except json.JSONDecodeError as error:

        print()
        print(
            "Gemini returned invalid JSON."
        )

        print(
            text[:5000]
        )

        raise RuntimeError(
            f"Gemini JSON parsing failed: {error}"
        )


# ============================================================
# PDF FONT
# ============================================================

def setup_font():

    candidates = [

        Path(
            "C:/Windows/Fonts/NotoSans-Regular.ttf"
        ),

        Path(
            "C:/Windows/Fonts/arial.ttf"
        ),

        Path(
            "C:/Windows/Fonts/calibri.ttf"
        ),

    ]

    for path in candidates:

        if path.exists():

            try:

                pdfmetrics.registerFont(
                    TTFont(
                        "ReportFont",
                        str(path)
                    )
                )

                return "ReportFont"

            except Exception:
                pass

    return "Helvetica"


# ============================================================
# PDF STYLES
# ============================================================

def make_styles(font):

    base = getSampleStyleSheet()

    return {

        "cover": ParagraphStyle(
            "Cover",
            parent=base["Title"],
            fontName=font,
            fontSize=27,
            leading=34,
            alignment=TA_CENTER,
            spaceAfter=15 * mm,
        ),

        "subtitle": ParagraphStyle(
            "Subtitle",
            parent=base["Normal"],
            fontName=font,
            fontSize=11,
            leading=17,
            alignment=TA_CENTER,
            textColor=colors.HexColor(
                "#555555"
            ),
        ),

        "section": ParagraphStyle(
            "Section",
            parent=base["Heading1"],
            fontName=font,
            fontSize=20,
            leading=26,
            spaceBefore=12 * mm,
            spaceAfter=8 * mm,
        ),

        "idea": ParagraphStyle(
            "Idea",
            parent=base["Heading2"],
            fontName=font,
            fontSize=16,
            leading=21,
            spaceBefore=3 * mm,
            spaceAfter=5 * mm,
        ),

        "label": ParagraphStyle(
            "Label",
            parent=base["Normal"],
            fontName=font,
            fontSize=9,
            leading=13,
            textColor=colors.HexColor(
                "#555555"
            ),
            spaceBefore=2 * mm,
            spaceAfter=1 * mm,
        ),

        "body": ParagraphStyle(
            "Body",
            parent=base["BodyText"],
            fontName=font,
            fontSize=9.5,
            leading=15,
            spaceAfter=3 * mm,
        ),

        "bullet": ParagraphStyle(
            "Bullet",
            parent=base["BodyText"],
            fontName=font,
            fontSize=9.5,
            leading=14,
            leftIndent=5 * mm,
            firstLineIndent=-3 * mm,
            spaceAfter=1.5 * mm,
        ),

    }


# ============================================================
# PDF TEXT HELPERS
# ============================================================

def safe(value):

    if value is None:
        return ""

    return (
        str(value)
        .replace(
            "&",
            "&amp;"
        )
        .replace(
            "<",
            "&lt;"
        )
        .replace(
            ">",
            "&gt;"
        )
    )


def add_field(
    story,
    styles,
    label,
    value
):

    if value is None:
        return

    if isinstance(
        value,
        list
    ):

        if not value:
            return

        story.append(
            Paragraph(
                f"<b>{label}</b>",
                styles["label"]
            )
        )

        for item in value:

            story.append(
                Paragraph(
                    f"• {safe(item)}",
                    styles["bullet"]
                )
            )

    else:

        story.append(
            Paragraph(
                f"<b>{label}</b>",
                styles["label"]
            )
        )

        story.append(
            Paragraph(
                safe(value),
                styles["body"]
            )
        )


# ============================================================
# VIRAL POTENTIAL
# ============================================================

def viral_background(
    value
):

    value = str(
        value or ""
    ).upper()

    if value == "HIGH":

        return colors.HexColor(
            "#E8F5E9"
        )

    if value == "MEDIUM":

        return colors.HexColor(
            "#FFF8E1"
        )

    return colors.HexColor(
        "#F5F5F5"
    )


# ============================================================
# IMPORTANT PDF FIX
# ============================================================

def idea_card(
    idea,
    styles
):
    """
    IMPORTANT:

    Do NOT put the entire idea inside one Table.

    Long ideas must be allowed to flow naturally across
    multiple pages.

    This fixes:

    Flowable Table too large on page
    tallest cell too large
    """

    story = []

    title = idea.get(
        "title",
        "Untitled Idea"
    )

    story.append(
        Spacer(
            1,
            5 * mm
        )
    )

    story.append(
        Paragraph(
            safe(title),
            styles["idea"]
        )
    )

    # Small editorial divider.
    story.append(
        HRFlowable(
            width="100%",
            thickness=0.6,
            color=colors.HexColor(
                "#D5D5D5"
            ),
            spaceBefore=1 * mm,
            spaceAfter=3 * mm,
        )
    )

    add_field(
        story,
        styles,
        "GENRE",
        idea.get(
            "genre"
        )
    )

    add_field(
        story,
        styles,
        "LOGLINE",
        idea.get(
            "logline"
        )
    )

    add_field(
        story,
        styles,
        "HOOK",
        idea.get(
            "hook"
        )
    )

    add_field(
        story,
        styles,
        "CONTENT SUMMARY",
        idea.get(
            "content_summary"
        )
    )

    add_field(
        story,
        styles,
        "VIDEO OUTLINE",
        idea.get(
            "video_outline"
        )
    )

    add_field(
        story,
        styles,
        "TARGET AUDIENCE",
        idea.get(
            "target_audience"
        )
    )

    add_field(
        story,
        styles,
        "ESTIMATED DURATION",
        idea.get(
            "estimated_duration"
        )
    )

    viral = idea.get(
        "viral_potential",
        ""
    )

    viral_table = Table(
        [[
            Paragraph(
                f"<b>VIRAL POTENTIAL: "
                f"{safe(viral)}</b>",
                styles["body"]
            )
        ]],
        colWidths=[
            165 * mm
        ],
        splitByRow=True,
    )

    viral_table.setStyle(
        TableStyle([

            (
                "BACKGROUND",
                (0, 0),
                (-1, -1),
                viral_background(
                    viral
                )
            ),

            (
                "BOX",
                (0, 0),
                (-1, -1),
                0.5,
                colors.HexColor(
                    "#DDDDDD"
                )
            ),

            (
                "LEFTPADDING",
                (0, 0),
                (-1, -1),
                5 * mm
            ),

            (
                "RIGHTPADDING",
                (0, 0),
                (-1, -1),
                5 * mm
            ),

            (
                "TOPPADDING",
                (0, 0),
                (-1, -1),
                2 * mm
            ),

            (
                "BOTTOMPADDING",
                (0, 0),
                (-1, -1),
                2 * mm
            ),

        ])
    )

    story.append(
        viral_table
    )

    story.append(
        Spacer(
            1,
            7 * mm
        )
    )

    return story


# ============================================================
# PDF FOOTER
# ============================================================

def footer(
    canvas,
    doc
):

    canvas.saveState()

    canvas.setFont(
        "Helvetica",
        8
    )

    canvas.setFillColor(
        colors.HexColor(
            "#777777"
        )
    )

    canvas.drawString(
        20 * mm,
        10 * mm,
        "YouTube Trend Intelligence Report"
    )

    canvas.drawRightString(
        190 * mm,
        10 * mm,
        f"Page {doc.page}"
    )

    canvas.restoreState()


# ============================================================
# CREATE PDF
# ============================================================

def create_pdf(
    report,
    output_path
):

    print()
    print(
        "[4/5] Creating professional PDF..."
    )

    font = setup_font()

    styles = make_styles(
        font
    )

    document = SimpleDocTemplate(

        str(output_path),

        pagesize=A4,

        rightMargin=20 * mm,

        leftMargin=20 * mm,

        topMargin=18 * mm,

        bottomMargin=18 * mm,

        title="YouTube Trend Intelligence Report",

        author="YouTube Trend Intelligence Generator",
    )

    story = []

    # ========================================================
    # COVER
    # ========================================================

    story.append(
        Spacer(
            1,
            30 * mm
        )
    )

    story.append(
        Paragraph(
            "YouTube Trend Intelligence Report",
            styles["cover"]
        )
    )

    story.append(
        Paragraph(
            "India + Worldwide YouTube Trends<br/>"
            "Shorts • Long Form • Crime Comedy • Thriller/Comedy",
            styles["subtitle"]
        )
    )

    story.append(
        Spacer(
            1,
            10 * mm
        )
    )

    story.append(
        Paragraph(
            datetime.now().strftime(
                "%d %B %Y"
            ),
            styles["subtitle"]
        )
    )

    story.append(
        PageBreak()
    )

    # ========================================================
    # EXECUTIVE
    # ========================================================

    story.append(
        Paragraph(
            "1. MONETIZATION GOAL & BEST DIRECTION",
            styles["section"]
        )
    )

    executive = report.get(
        "executive_goal",
        {}
    )

    add_field(
        story,
        styles,
        "GOAL",
        executive.get(
            "goal"
        )
    )

    add_field(
        story,
        styles,
        "BEST DIRECTION",
        executive.get(
            "best_direction"
        )
    )

    add_field(
        story,
        styles,
        "BEST IDEA",
        executive.get(
            "best_idea_title"
        )
    )

    add_field(
        story,
        styles,
        "LOGLINE",
        executive.get(
            "best_idea_logline"
        )
    )

    add_field(
        story,
        styles,
        "REASON",
        executive.get(
            "reason"
        )
    )

    # ========================================================
    # INDIA
    # ========================================================

    story.append(
        Paragraph(
            "2. INDIA — WHAT IS TRENDING ON YOUTUBE",
            styles["section"]
        )
    )

    india = report.get(
        "india_trends",
        {}
    )

    add_field(
        story,
        styles,
        "OVERVIEW",
        india.get(
            "overview"
        )
    )

    add_field(
        story,
        styles,
        "TRENDING TOPICS",
        india.get(
            "trending_topics"
        )
    )

    add_field(
        story,
        styles,
        "TRENDING FORMATS",
        india.get(
            "trending_formats"
        )
    )

    add_field(
        story,
        styles,
        "TRENDING GENRES",
        india.get(
            "trending_genres"
        )
    )

    add_field(
        story,
        styles,
        "EVIDENCE",
        india.get(
            "evidence"
        )
    )

    # ========================================================
    # WORLDWIDE
    # ========================================================

    story.append(
        Paragraph(
            "3. WORLDWIDE — WHAT IS TRENDING ON YOUTUBE",
            styles["section"]
        )
    )

    worldwide = report.get(
        "worldwide_trends",
        {}
    )

    add_field(
        story,
        styles,
        "OVERVIEW",
        worldwide.get(
            "overview"
        )
    )

    add_field(
        story,
        styles,
        "TRENDING TOPICS",
        worldwide.get(
            "trending_topics"
        )
    )

    add_field(
        story,
        styles,
        "TRENDING FORMATS",
        worldwide.get(
            "trending_formats"
        )
    )

    add_field(
        story,
        styles,
        "TRENDING GENRES",
        worldwide.get(
            "trending_genres"
        )
    )

    add_field(
        story,
        styles,
        "EVIDENCE",
        worldwide.get(
            "evidence"
        )
    )

    # ========================================================
    # IDEA SECTIONS
    # ========================================================

    sections = [

        (
            "4. YOUTUBE SHORTS IDEAS BASED ON CURRENT TRENDS",
            "shorts_trend_ideas"
        ),

        (
            "5. LONG-FORM VIDEO IDEAS — 8–10 MINUTES",
            "long_form_trend_ideas"
        ),

        (
            "6. CRIME-COMEDY SHORTS — TREND BASED",
            "crime_comedy_shorts_trend_based"
        ),

        (
            "7. CRIME-COMEDY SHORTS — NORMAL / ORIGINAL",
            "crime_comedy_shorts_normal"
        ),

        (
            "8. THRILLER/COMEDY — TREND BASED",
            "thriller_comedy_trend_based"
        ),

        (
            "9. THRILLER/COMEDY — NORMAL / ORIGINAL",
            "thriller_comedy_normal"
        ),

    ]

    for section_title, key in sections:

        story.append(
            Paragraph(
                section_title,
                styles["section"]
            )
        )

        ideas = report.get(
            key,
            []
        )

        for idea in ideas:

            # IMPORTANT:
            # Do not KeepTogether the entire idea.
            # It is allowed to split naturally.
            story.extend(
                idea_card(
                    idea,
                    styles
                )
            )

    # ========================================================
    # MONETIZATION
    # ========================================================

    story.append(
        Paragraph(
            "10. BEST IDEAS FOR 5-MONTH MONETIZATION",
            styles["section"]
        )
    )

    best_ideas = report.get(
        "monetization_5_months_best_ideas",
        []
    )

    for idea in best_ideas:

        story.extend(
            idea_card(
                idea,
                styles
            )
        )

    # ========================================================
    # FINAL BEST IDEA
    # ========================================================

    story.append(
        Paragraph(
            "11. FINAL BEST IDEA",
            styles["section"]
        )
    )

    final = report.get(
        "final_best_idea",
        {}
    )

    story.extend(
        idea_card(
            final,
            styles
        )
    )

    add_field(
        story,
        styles,
        "WHY BEST FOR MONETIZATION",
        final.get(
            "why_best_for_monetization"
        )
    )

    # ========================================================
    # BUILD
    # ========================================================

    document.build(

        story,

        onFirstPage=footer,

        onLaterPages=footer,
    )

    print()
    print(
        "PDF created successfully:"
    )

    print(
        output_path
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
            indent=2,
            ensure_ascii=False
        )

    print()
    print(
        "JSON saved:"
    )

    print(
        JSON_FILE
    )


# ============================================================
# RESEND EMAIL
# ============================================================

def send_email(
    pdf_path,
    report
):

    print()
    print(
        "[5/5] Sending PDF through Resend..."
    )

    with open(
        pdf_path,
        "rb"
    ) as file:

        encoded_pdf = base64.b64encode(
            file.read()
        ).decode(
            "utf-8"
        )

    final_title = report.get(
        "final_best_idea",
        {}
    ).get(
        "title",
        "YouTube Trend Intelligence Report"
    )

    payload = {

        "from":
            FROM_EMAIL,

        "to":
            [RECIPIENT_EMAIL],

        "subject":
            "YouTube Trend Intelligence Report - "
            + datetime.now().strftime(
                "%d %B %Y"
            ),

        "html":
            f"""
            <div style="
                font-family:Arial,sans-serif;
                max-width:700px;
                margin:auto;
                color:#222;
            ">

                <h1>
                    YouTube Trend Intelligence Report
                </h1>

                <p>
                    Your latest YouTube Trend Intelligence
                    Report has been generated successfully.
                </p>

                <h2>
                    Final Best Idea
                </h2>

                <p>
                    <strong>
                        {safe(final_title)}
                    </strong>
                </p>

                <p>
                    The professional PDF report is attached.
                </p>

                <ul>
                    <li>India YouTube trends</li>
                    <li>Worldwide trend proxy</li>
                    <li>Trending genres</li>
                    <li>YouTube Shorts ideas</li>
                    <li>8–10 minute long-form ideas</li>
                    <li>Crime-comedy Shorts</li>
                    <li>Thriller/Comedy ideas</li>
                    <li>Loglines</li>
                    <li>Hooks</li>
                    <li>Target audiences</li>
                    <li>Estimated durations</li>
                    <li>Viral potential</li>
                    <li>5-month monetization ideas</li>
                </ul>

            </div>
            """,

        "attachments": [

            {
                "filename":
                    Path(pdf_path).name,

                "content":
                    encoded_pdf,
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

    if response.status_code >= 400:

        print()
        print(
            "RESEND ERROR:"
        )

        print(
            response.text
        )

        raise RuntimeError(
            f"Resend failed: "
            f"{response.status_code}"
        )

    print()
    print(
        "Email sent successfully."
    )

    print(
        f"Recipient: {RECIPIENT_EMAIL}"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    validate_environment()

    # --------------------------------------------------------
    # 1
    # --------------------------------------------------------

    print(
        "[1/5] Connecting to YouTube API..."
    )

    youtube = get_youtube_client()

    print(
        "YouTube API connection successful."
    )

    # --------------------------------------------------------
    # 2
    # --------------------------------------------------------

    print()
    print(
        "[2/5] Fetching current India/World proxy "
        "YouTube data..."
    )

    print()
    print(
        "Fetching India..."
    )

    india_videos = fetch_trending_videos(
        youtube,
        "IN",
        50
    )

    print(
        f"India videos received: "
        f"{len(india_videos)}"
    )

    print()
    print(
        "Fetching worldwide proxy..."
    )

    worldwide_videos = fetch_trending_videos(
        youtube,
        "US",
        50
    )

    print(
        "Note: YouTube Data API requires a region code, "
        "so WORLD is represented by the United States "
        "as a broad global trend proxy."
    )

    print(
        f"World proxy videos received: "
        f"{len(worldwide_videos)}"
    )

    print()
    print(
        "Fetching YouTube category names..."
    )

    india_videos = enrich_videos_with_categories(
        youtube,
        india_videos
    )

    worldwide_videos = enrich_videos_with_categories(
        youtube,
        worldwide_videos
    )

    # --------------------------------------------------------
    # ORIGINAL REPORT
    # --------------------------------------------------------

    original_report = load_original_report()

    # --------------------------------------------------------
    # 3
    # --------------------------------------------------------

    report = generate_report(
        india_videos,
        worldwide_videos,
        original_report
    )

    # --------------------------------------------------------
    # JSON
    # --------------------------------------------------------

    save_json(
        report
    )

    # --------------------------------------------------------
    # 4
    # --------------------------------------------------------

    create_pdf(
        report,
        PDF_FILE
    )

    # --------------------------------------------------------
    # 5
    # --------------------------------------------------------

    send_email(
        PDF_FILE,
        report
    )

    # --------------------------------------------------------
    # DONE
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("COMPLETED SUCCESSFULLY")
    print("=" * 70)
    print()

    print(
        f"PDF: {PDF_FILE}"
    )

    print(
        f"JSON: {JSON_FILE}"
    )

    print(
        f"Email: {RECIPIENT_EMAIL}"
    )

    print()


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    try:

        main()

    except KeyboardInterrupt:

        print()
        print(
            "Process cancelled by user."
        )

    except Exception as error:

        print()
        print("=" * 70)
        print("ERROR")
        print("=" * 70)
        print()
        print(
            str(error)
        )
        print()

        sys.exit(1)
