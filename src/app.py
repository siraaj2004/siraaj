import os
import json
import re
import html
import base64
import time
from datetime import datetime
from collections import Counter

import requests
from dotenv import load_dotenv

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
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


# ============================================================
# CONFIG
# ============================================================

load_dotenv()

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

DATA_DIR = os.path.join(
    PROJECT_ROOT,
    "data"
)

REPORTS_DIR = os.path.join(
    PROJECT_ROOT,
    "reports"
)

os.makedirs(
    DATA_DIR,
    exist_ok=True
)

os.makedirs(
    REPORTS_DIR,
    exist_ok=True
)


# ============================================================
# API URLS
# ============================================================

YOUTUBE_URL = (
    "https://www.googleapis.com/youtube/v3/videos"
)

OPENROUTER_URL = (
    "https://openrouter.ai/api/v1/chat/completions"
)

RESEND_URL = (
    "https://api.resend.com/emails"
)


# ============================================================
# ENVIRONMENT VARIABLES
# ============================================================

YOUTUBE_API_KEY = os.getenv(
    "YOUTUBE_API_KEY",
    ""
).strip()

OPENROUTER_API_KEY = os.getenv(
    "OPENROUTER_API_KEY",
    ""
).strip()

RESEND_API_KEY = os.getenv(
    "RESEND_API_KEY",
    ""
).strip()

RECIPIENT_EMAIL = os.getenv(
    "RECIPIENT_EMAIL",
    ""
).strip()

RESEND_FROM = os.getenv(
    "RESEND_FROM",
    "onboarding@resend.dev"
).strip()


# ============================================================
# OPENROUTER MODEL CONFIGURATION
# ============================================================

OPENROUTER_MODEL = (
    os.getenv(
        "OPENROUTER_MODEL",
        ""
    ).strip()
    or "openrouter/free"
)


OPENROUTER_FALLBACK_MODELS = [
    "openrouter/free",
    "nvidia/nemotron-3-ultra:free",
    "google/gemma-4-31b-it:free",
]


# ============================================================
# ENVIRONMENT CHECK
# ============================================================

def check_environment():

    required = {
        "YOUTUBE_API_KEY": YOUTUBE_API_KEY,
        "OPENROUTER_API_KEY": OPENROUTER_API_KEY,
        "RESEND_API_KEY": RESEND_API_KEY,
        "RECIPIENT_EMAIL": RECIPIENT_EMAIL,
    }

    missing = [
        name
        for name, value in required.items()
        if not value
    ]

    if missing:

        print("")
        print("=" * 70)
        print("MISSING ENVIRONMENT VARIABLES")
        print("=" * 70)

        for item in missing:
            print(f"  - {item}")

        print("")
        print(
            "GitHub:"
        )
        print(
            "Settings -> Secrets and variables -> Actions"
        )

        raise RuntimeError(
            "Missing GitHub Secrets / environment variables: "
            + ", ".join(missing)
        )

    print(
        "Environment check: OK"
    )

    print(
        f"OpenRouter primary model: "
        f"{OPENROUTER_MODEL}"
    )

    print(
        "OpenRouter fallback models:"
    )

    for model in OPENROUTER_FALLBACK_MODELS:
        print(
            f"  - {model}"
        )


# ============================================================
# TEXT HELPERS
# ============================================================

def clean_text(value):

    if value is None:
        return ""

    value = str(value)

    value = value.replace(
        "\x00",
        ""
    )

    return value.strip()


def safe_html(value):

    return html.escape(
        clean_text(value)
    )


# ============================================================
# HTTP RETRY
# ============================================================

def retry_request(
    method,
    url,
    **kwargs
):

    last_error = None

    for attempt in range(3):

        try:

            response = requests.request(
                method,
                url,
                timeout=120,
                **kwargs
            )

            if response.status_code in (
                429,
                500,
                502,
                503,
                504,
            ):

                wait_time = (
                    3 * (attempt + 1)
                )

                print(
                    f"HTTP {response.status_code}. "
                    f"Retrying in {wait_time}s..."
                )

                time.sleep(
                    wait_time
                )

                continue

            return response

        except requests.RequestException as exc:

            last_error = exc

            wait_time = (
                3 * (attempt + 1)
            )

            print(
                f"Request error: {exc}"
            )

            print(
                f"Retrying in {wait_time}s..."
            )

            time.sleep(
                wait_time
            )

    if last_error:
        raise last_error

    raise RuntimeError(
        "HTTP request failed after retries."
    )


# ============================================================
# JSON PARSER
# ============================================================

def parse_json(text):

    if not text:

        raise ValueError(
            "Empty AI response."
        )

    text = text.strip()

    # Remove markdown code fences
    text = re.sub(
        r"^```(?:json)?\s*",
        "",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"\s*```$",
        "",
        text
    )

    # Find first JSON object
    start = text.find("{")

    # Find last JSON object
    end = text.rfind("}")

    if start == -1 or end == -1:

        raise ValueError(
            "AI did not return valid JSON:\n"
            + text[:3000]
        )

    json_text = text[
        start:end + 1
    ]

    try:

        return json.loads(
            json_text
        )

    except json.JSONDecodeError as exc:

        raise ValueError(
            "AI returned invalid JSON: "
            f"{exc}\n\n"
            + json_text[:5000]
        )


# ============================================================
# SAVE JSON
# ============================================================

def save_json(
    filename,
    data
):

    path = os.path.join(
        DATA_DIR,
        filename
    )

    with open(
        path,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2
        )

    return path


# ============================================================
# YOUTUBE DATA
# ============================================================

def get_youtube_trends(
    region_code
):

    print(
        f"\nCollecting YouTube mostPopular data: "
        f"{region_code}"
    )

    params = {
        "part": (
            "snippet,"
            "statistics,"
            "contentDetails"
        ),
        "chart": "mostPopular",
        "regionCode": region_code,
        "maxResults": 50,
        "key": YOUTUBE_API_KEY,
    }

    response = retry_request(
        "GET",
        YOUTUBE_URL,
        params=params
    )

    if response.status_code != 200:

        raise RuntimeError(
            "YouTube API error "
            f"{response.status_code}: "
            f"{response.text[:2000]}"
        )

    data = response.json()

    videos = []

    for item in data.get(
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

        videos.append(
            {
                "video_id": item.get(
                    "id",
                    ""
                ),

                "title": clean_text(
                    snippet.get(
                        "title",
                        ""
                    )
                ),

                "channel": clean_text(
                    snippet.get(
                        "channelTitle",
                        ""
                    )
                ),

                "category_id": clean_text(
                    snippet.get(
                        "categoryId",
                        ""
                    )
                ),

                "published_at": snippet.get(
                    "publishedAt",
                    ""
                ),

                "views": int(
                    statistics.get(
                        "viewCount",
                        0
                    ) or 0
                ),

                "likes": int(
                    statistics.get(
                        "likeCount",
                        0
                    ) or 0
                ),

                "comments": int(
                    statistics.get(
                        "commentCount",
                        0
                    ) or 0
                ),
            }
        )

    print(
        f"Collected {len(videos)} videos."
    )

    return videos


# ============================================================
# YOUTUBE CATEGORIES
# ============================================================

CATEGORY_NAMES = {

    "1": "Film & Animation",

    "2": "Autos & Vehicles",

    "10": "Music",

    "15": "Pets & Animals",

    "17": "Sports",

    "19": "Travel & Events",

    "20": "Gaming",

    "22": "People & Blogs",

    "23": "Comedy",

    "24": "Entertainment",

    "25": "News & Politics",

    "26": "Howto & Style",

    "27": "Education",

    "28": "Science & Technology",
}


# ============================================================
# TREND ANALYSIS
# ============================================================

def analyze_trends(
    videos
):

    if not videos:

        return {
            "video_count": 0,
            "total_views": 0,
            "average_views": 0,
            "top_videos": [],
            "top_channels": [],
            "top_categories": [],
            "keywords": [],
        }

    total_views = sum(
        video["views"]
        for video in videos
    )

    average_views = int(
        total_views / len(videos)
    )

    top_videos = sorted(
        videos,
        key=lambda x: x["views"],
        reverse=True
    )[:15]

    channel_counter = Counter(
        video["channel"]
        for video in videos
        if video["channel"]
    )

    category_counter = Counter(
        CATEGORY_NAMES.get(
            video["category_id"],
            f"Category {video['category_id']}"
        )
        for video in videos
    )

    stop_words = {
        "the",
        "and",
        "for",
        "with",
        "this",
        "that",
        "from",
        "you",
        "your",
        "new",
        "how",
        "what",
        "why",
        "into",
        "are",
        "was",
        "will",
        "have",
        "has",
        "not",
        "india",
        "world",
        "official",
        "video",
        "shorts",
    }

    words = []

    for video in videos:

        title = video[
            "title"
        ].lower()

        title = re.sub(
            r"[^a-zA-Z0-9\s]",
            " ",
            title
        )

        for word in title.split():

            if (
                len(word) >= 4
                and word not in stop_words
                and not word.isdigit()
            ):

                words.append(
                    word
                )

    keyword_counter = Counter(
        words
    )

    return {

        "video_count": len(videos),

        "total_views": total_views,

        "average_views": average_views,

        "top_videos": [

            {
                "title": x["title"],
                "channel": x["channel"],
                "views": x["views"],
            }

            for x in top_videos
        ],

        "top_channels": [

            {
                "channel": name,
                "count": count,
            }

            for name, count
            in channel_counter.most_common(10)
        ],

        "top_categories": [

            {
                "category": name,
                "count": count,
            }

            for name, count
            in category_counter.most_common(10)
        ],

        "keywords": [

            word

            for word, count
            in keyword_counter.most_common(25)
        ],
    }


# ============================================================
# OPENROUTER
# ============================================================

def get_openrouter_models():

    models = []

    if OPENROUTER_MODEL:
        models.append(
            OPENROUTER_MODEL
        )

    for model in OPENROUTER_FALLBACK_MODELS:

        if (
            model
            and model not in models
        ):

            models.append(
                model
            )

    if not models:

        models = [
            "openrouter/free"
        ]

    return models


def openrouter_call(
    system_prompt,
    user_prompt
):

    if not OPENROUTER_API_KEY:

        raise RuntimeError(
            "OPENROUTER_API_KEY is missing."
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

    models = get_openrouter_models()

    print("")
    print("=" * 70)
    print("OPENROUTER REQUEST")
    print("=" * 70)

    print(
        "Available models:"
    )

    for model in models:

        print(
            f"  - {model}"
        )

    last_error = None

    for model in models:

        print("")
        print(
            f"Trying OpenRouter model: "
            f"{model}"
        )

        payload = {

            "model": model,

            "messages": [

                {
                    "role": "system",
                    "content": system_prompt,
                },

                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],

            "temperature": 0.9,

            # Lower than the previous 10000
            # to work better with free models.
            "max_tokens": 6000,
        }

        try:

            response = requests.post(
                OPENROUTER_URL,
                headers=headers,
                json=payload,
                timeout=180
            )

            print(
                f"HTTP status: "
                f"{response.status_code}"
            )

            # ==================================================
            # SUCCESS
            # ==================================================

            if response.status_code == 200:

                data = response.json()

                choices = data.get(
                    "choices",
                    []
                )

                if not choices:

                    raise RuntimeError(
                        "OpenRouter returned "
                        "no choices:\n"
                        + json.dumps(
                            data,
                            indent=2
                        )[:4000]
                    )

                message = choices[0].get(
                    "message",
                    {}
                )

                content = message.get(
                    "content"
                )

                # Some providers can return
                # content in an unusual structure.
                if isinstance(
                    content,
                    list
                ):

                    content = "".join(
                        str(
                            item.get(
                                "text",
                                ""
                            )
                        )
                        if isinstance(
                            item,
                            dict
                        )
                        else str(item)

                        for item in content
                    )

                if not content:

                    raise RuntimeError(
                        "OpenRouter returned "
                        "empty content."
                    )

                print("")
                print(
                    "OpenRouter SUCCESS"
                )

                print(
                    f"Model used: {model}"
                )

                return parse_json(
                    content
                )

            # ==================================================
            # MODEL / CREDIT / RATE LIMIT
            # ==================================================

            error_text = response.text[
                :4000
            ]

            print("")
            print(
                "OpenRouter error:"
            )

            print(
                error_text
            )

            last_error = RuntimeError(
                "OpenRouter API error "
                f"{response.status_code}: "
                f"{error_text}"
            )

            # Try next model.
            if response.status_code in (
                400,
                402,
                404,
                408,
                429,
                500,
                502,
                503,
                504,
            ):

                print(
                    "Trying next fallback model..."
                )

                continue

            raise last_error

        except requests.RequestException as exc:

            last_error = exc

            print(
                f"Network error with "
                f"{model}: {exc}"
            )

            print(
                "Trying next model..."
            )

            continue

        except ValueError as exc:

            last_error = exc

            print(
                "JSON parsing error:"
            )

            print(
                str(exc)[:3000]
            )

            # A successful HTTP response with
            # invalid JSON should try another model.
            print(
                "Trying next model..."
            )

            continue

        except Exception as exc:

            last_error = exc

            print(
                f"Model error: {exc}"
            )

            print(
                "Trying next model..."
            )

            continue

    raise RuntimeError(
        "ALL OPENROUTER MODELS FAILED.\n"
        f"Last error: {last_error}"
    )


# ============================================================
# AI SYSTEM PROMPT
# ============================================================

SYSTEM_PROMPT = """
You are an ELITE YouTube creative director,
screenwriter, trend strategist and CTR specialist.

Your job is NOT to produce generic YouTube ideas.

The user wants ideas that make someone hear the idea and say:

"WAAH... WHAT AN IDEA!"

Every idea must have:

1. A powerful curiosity gap
2. A clear story problem
3. Escalating stakes
4. A strong reason to keep watching
5. A surprising reveal, reversal or payoff
6. Strong thumbnail/title potential
7. Indian/Telugu relatability where appropriate
8. Easy execution for a solo creator
9. Cinematic feeling
10. A concept that can actually be explained in one powerful sentence

VERY IMPORTANT:

DO NOT create:

- silly remote jokes
- Wi-Fi jokes
- random ghost appears
- generic prank ideas
- generic challenges
- generic motivation
- generic food challenges
- random kidnapping stories
- generic "24 hours" concepts
- copied movie plots
- copied viral videos
- weak relationship drama
- "I found a mysterious box" unless the concept is genuinely exceptional
- ideas whose only hook is "something strange happened"

Prefer:

- thriller
- mystery
- crime
- psychological thriller
- dark comedy
- crime comedy
- technology thriller
- social mystery
- high-concept stories
- reality-bending concepts
- unexpected consequences
- moral dilemmas
- secrets
- impossible situations
- clever reversals
- Indian/Telugu everyday situations turned into extraordinary stories

The creator is a solo creator.

Ideas should be shootable with:

- one actor
- simple locations
- simple props
- camera
- editing
- sound design

Roman Telugu loglines must sound natural,
cinematic and interesting.

Do not translate word-by-word.

The Roman Telugu logline should make a Telugu viewer
immediately understand why the story is exciting.

IMPORTANT:

"CURRENT TREND" ideas must be inspired by the supplied
YouTube trend data.

"GENERAL" ideas must NOT simply copy the current trend data.

They should be evergreen/high-concept ideas for
India/World audiences.

Return ONLY valid JSON.

No markdown.

No explanations outside JSON.
"""


# ============================================================
# GENERATE STRATEGY
# ============================================================

def generate_strategy(
    india_analysis,
    world_analysis
):

    prompt = f"""
Create:

1. Monetization Goal & Best Direction
2. India YouTube Trends
3. Worldwide YouTube Trends

IMPORTANT:

Worldwide data below is a US YouTube
mostPopular proxy.

Do not falsely call it a complete
worldwide measurement.

INDIA DATA:

{json.dumps(
    india_analysis,
    ensure_ascii=False
)}

WORLD DATA:

{json.dumps(
    world_analysis,
    ensure_ascii=False
)}

Return exactly:

{{
  "monetization": {{
    "primary_goal": "",
    "best_direction": "",
    "why": "",
    "content_strategy": "",
    "monetization_paths": []
  }},

  "india_trends": {{
    "summary": "",
    "patterns": [],
    "top_formats": [],
    "top_topics": [],
    "creator_opportunities": []
  }},

  "worldwide_trends": {{
    "summary": "",
    "patterns": [],
    "top_formats": [],
    "top_topics": [],
    "creator_opportunities": []
  }}
}}
"""

    return openrouter_call(
        SYSTEM_PROMPT,
        prompt
    )


# ============================================================
# GENERATE IDEAS
# ============================================================

def generate_current_ideas(
    india_analysis,
    world_analysis
):

    prompt = f"""
Create the following:

SECTION 4:

10 YouTube Shorts ideas based on CURRENT trends.

SECTION 5:

8 long-form YouTube ideas based on CURRENT trends.

Each must be suitable for 8-10 minutes.

SECTION 6:

10 GENERAL India/World Shorts ideas.

These must NOT directly depend on current YouTube trends.

SECTION 7:

8 GENERAL India/World long-form ideas.

These must NOT directly depend on current YouTube trends.

Each must be suitable for 8-10 minutes.

Also create ONE:

HIGH CTR IDEA

The High CTR Idea must be the strongest concept
from your creative thinking.

It must be much stronger than an ordinary
YouTube idea.

INDIA TREND DATA:

{json.dumps(
    india_analysis,
    ensure_ascii=False
)}

WORLD TREND DATA:

{json.dumps(
    world_analysis,
    ensure_ascii=False
)}

For every normal idea use:

{{
  "title": "",
  "genre": "",
  "english_logline": "",
  "roman_telugu_logline": "",
  "hook": "",
  "content_summary": "",
  "video_outline": [
    "",
    "",
    "",
    "",
    ""
  ],
  "target_audience": "",
  "estimated_duration": "",
  "viral_potential": "",
  "why_it_can_get_high_ctr": ""
}}

HIGH CTR IDEA must use:

{{
  "title": "",
  "genre": "",
  "english_logline": "",
  "roman_telugu_logline": "",
  "hook": "",
  "why_this_is_the_best_ctr_choice": ""
}}

Return exactly:

{{
  "high_ctr_idea": {{}},
  "current_shorts": [],
  "current_longform": [],
  "general_shorts": [],
  "general_longform": []
}}

Counts MUST be:

current_shorts = 10

current_longform = 8

general_shorts = 10

general_longform = 8

Do not give fewer ideas.

Do not give filler ideas.

Do not repeat the same concept
with different titles.

Every concept must be meaningfully different.
"""

    result = openrouter_call(
        SYSTEM_PROMPT,
        prompt
    )

    validate_idea_counts(
        result
    )

    return result


# ============================================================
# VALIDATION
# ============================================================

def validate_idea_counts(
    data
):

    required_counts = {

        "current_shorts": 10,

        "current_longform": 8,

        "general_shorts": 10,

        "general_longform": 8,
    }

    for key, expected in (
        required_counts.items()
    ):

        actual = len(
            data.get(
                key,
                []
            )
        )

        if actual != expected:

            raise RuntimeError(
                f"AI generated {actual} ideas "
                f"for {key}; "
                f"expected {expected}"
            )

    if not data.get(
        "high_ctr_idea"
    ):

        raise RuntimeError(
            "AI did not generate "
            "HIGH CTR IDEA"
        )


# ============================================================
# PDF FONT
# ============================================================

def setup_fonts():

    possible_fonts = [

        "/usr/share/fonts/"
        "truetype/dejavu/"
        "DejaVuSans.ttf",

        "/usr/share/fonts/"
        "truetype/dejavu/"
        "DejaVuSansCondensed.ttf",
    ]

    for path in possible_fonts:

        if os.path.exists(path):

            pdfmetrics.registerFont(
                TTFont(
                    "DejaVu",
                    path
                )
            )

            return "DejaVu"

    return "Helvetica"


# ============================================================
# PDF STYLES
# ============================================================

def make_styles(
    font_name
):

    styles = getSampleStyleSheet()

    return {

        "title": ParagraphStyle(
            "TitleCustom",
            parent=styles["Title"],
            fontName=font_name,
            fontSize=25,
            leading=31,
            alignment=TA_CENTER,
            spaceAfter=15,
        ),

        "subtitle": ParagraphStyle(
            "Subtitle",
            parent=styles["Normal"],
            fontName=font_name,
            fontSize=10,
            leading=15,
            alignment=TA_CENTER,
            spaceAfter=20,
        ),

        "section": ParagraphStyle(
            "Section",
            parent=styles["Heading1"],
            fontName=font_name,
            fontSize=18,
            leading=23,
            spaceBefore=10,
            spaceAfter=12,
        ),

        "idea_title": ParagraphStyle(
            "IdeaTitle",
            parent=styles["Heading2"],
            fontName=font_name,
            fontSize=14,
            leading=19,
            spaceBefore=8,
            spaceAfter=7,
        ),

        "body": ParagraphStyle(
            "BodyCustom",
            parent=styles["BodyText"],
            fontName=font_name,
            fontSize=9.5,
            leading=14,
            spaceAfter=7,
        ),

        "small": ParagraphStyle(
            "Small",
            parent=styles["BodyText"],
            fontName=font_name,
            fontSize=8,
            leading=11,
            spaceAfter=5,
        ),

        "high_ctr": ParagraphStyle(
            "HighCTR",
            parent=styles["BodyText"],
            fontName=font_name,
            fontSize=11,
            leading=17,
            spaceAfter=8,
        ),
    }


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
        7
    )

    canvas.drawCentredString(
        A4[0] / 2,
        10 * mm,
        "YouTube Trend Intelligence Report "
        f"| Page {doc.page}"
    )

    canvas.restoreState()


# ============================================================
# PDF PARAGRAPH
# ============================================================

def paragraph(
    text,
    style
):

    text = safe_html(
        text
    )

    text = text.replace(
        "\n",
        "<br/>"
    )

    return Paragraph(
        text,
        style
    )


# ============================================================
# ADD IDEA TO PDF
# ============================================================

def add_idea(
    story,
    idea,
    styles,
    number
):

    title = idea.get(
        "title",
        "Untitled Idea"
    )

    story.append(
        paragraph(
            f"{number}. {title}",
            styles["idea_title"]
        )
    )

    fields = [

        (
            "Genre",
            idea.get(
                "genre"
            )
        ),

        (
            "English Logline",
            idea.get(
                "english_logline"
            )
        ),

        (
            "Roman Telugu Logline",
            idea.get(
                "roman_telugu_logline"
            )
        ),

        (
            "Hook",
            idea.get(
                "hook"
            )
        ),

        (
            "Content Summary",
            idea.get(
                "content_summary"
            )
        ),

        (
            "Target Audience",
            idea.get(
                "target_audience"
            )
        ),

        (
            "Estimated Duration",
            idea.get(
                "estimated_duration"
            )
        ),

        (
            "Viral Potential",
            idea.get(
                "viral_potential"
            )
        ),

        (
            "Why It Can Get High CTR",
            idea.get(
                "why_it_can_get_high_ctr"
            )
        ),
    ]

    for label, value in fields:

        story.append(
            Paragraph(
                f"<b>{safe_html(label)}:</b> "
                f"{safe_html(value)}",
                styles["body"]
            )
        )

    outline = idea.get(
        "video_outline",
        []
    )

    if outline:

        story.append(
            paragraph(
                "Video Outline:",
                styles["body"]
            )
        )

        for index, item in enumerate(
            outline,
            1
        ):

            story.append(
                Paragraph(
                    f"{index}. "
                    f"{safe_html(item)}",
                    styles["small"]
                )
            )

    story.append(
        Spacer(
            1,
            5
        )
    )


# ============================================================
# BUILD PDF
# ============================================================

def build_pdf(
    strategy,
    ideas,
    india_analysis,
    world_analysis
):

    font_name = setup_fonts()

    styles = make_styles(
        font_name
    )

    filename = (
        "youtube_trend_intelligence_"
        + datetime.now().strftime(
            "%Y%m%d_%H%M%S"
        )
        + ".pdf"
    )

    pdf_path = os.path.join(
        REPORTS_DIR,
        filename
    )

    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=A4,
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=18 * mm,
        title=(
            "YouTube Trend Intelligence Report"
        ),
    )

    story = []

    # ========================================================
    # COVER
    # ========================================================

    story.append(
        Spacer(
            1,
            35 * mm
        )
    )

    story.append(
        paragraph(
            "YouTube Trend Intelligence Report",
            styles["title"]
        )
    )

    story.append(
        paragraph(
            datetime.now().strftime(
                "%d %B %Y"
            ),
            styles["subtitle"]
        )
    )

    story.append(
        paragraph(
            "AI-powered YouTube trend research, "
            "high-CTR concept generation and "
            "content strategy.",
            styles["subtitle"]
        )
    )

    story.append(
        PageBreak()
    )

    # ========================================================
    # HIGH CTR IDEA
    # ========================================================

    story.append(
        paragraph(
            "HIGH CTR IDEA",
            styles["section"]
        )
    )

    high = ideas[
        "high_ctr_idea"
    ]

    story.append(
        paragraph(
            high.get(
                "title",
                ""
            ),
            styles["idea_title"]
        )
    )

    story.append(
        paragraph(
            "<b>Genre:</b> "
            + safe_html(
                high.get(
                    "genre",
                    ""
                )
            ),
            styles["high_ctr"]
        )
    )

    story.append(
        paragraph(
            "<b>English Logline:</b> "
            + safe_html(
                high.get(
                    "english_logline",
                    ""
                )
            ),
            styles["high_ctr"]
        )
    )

    story.append(
        paragraph(
            "<b>Roman Telugu Logline:</b> "
            + safe_html(
                high.get(
                    "roman_telugu_logline",
                    ""
                )
            ),
            styles["high_ctr"]
        )
    )

    story.append(
        paragraph(
            "<b>Hook:</b> "
            + safe_html(
                high.get(
                    "hook",
                    ""
                )
            ),
            styles["high_ctr"]
        )
    )

    story.append(
        paragraph(
            "<b>Why This Is The Best CTR Choice:</b> "
            + safe_html(
                high.get(
                    "why_this_is_the_best_ctr_choice",
                    ""
                )
            ),
            styles["high_ctr"]
        )
    )

    story.append(
        PageBreak()
    )

    # ========================================================
    # 1 MONETIZATION
    # ========================================================

    story.append(
        paragraph(
            "1. MONETIZATION GOAL & BEST DIRECTION",
            styles["section"]
        )
    )

    monetization = strategy[
        "monetization"
    ]

    for label in [
        "primary_goal",
        "best_direction",
        "why",
        "content_strategy",
    ]:

        story.append(
            paragraph(
                f"<b>{label.replace('_', ' ').title()}:</b> "
                f"{safe_html(monetization.get(label))}",
                styles["body"]
            )
        )

    story.append(
        paragraph(
            "Monetization Paths:",
            styles["body"]
        )
    )

    for item in monetization.get(
        "monetization_paths",
        []
    ):

        story.append(
            paragraph(
                f"• {item}",
                styles["body"]
            )
        )

    # ========================================================
    # 2 INDIA
    # ========================================================

    story.append(
        PageBreak()
    )

    story.append(
        paragraph(
            "2. INDIA — WHAT IS TRENDING ON YOUTUBE",
            styles["section"]
        )
    )

    india = strategy[
        "india_trends"
    ]

    story.append(
        paragraph(
            india.get(
                "summary",
                ""
            ),
            styles["body"]
        )
    )

    for label in [
        "patterns",
        "top_formats",
        "top_topics",
        "creator_opportunities",
    ]:

        story.append(
            paragraph(
                f"{label.replace('_', ' ').title()}:",
                styles["body"]
            )
        )

        for item in india.get(
            label,
            []
        ):

            story.append(
                paragraph(
                    f"• {item}",
                    styles["body"]
                )
            )

    # ========================================================
    # 3 WORLD
    # ========================================================

    story.append(
        PageBreak()
    )

    story.append(
        paragraph(
            "3. WORLDWIDE — WHAT IS TRENDING ON YOUTUBE",
            styles["section"]
        )
    )

    story.append(
        paragraph(
            "Important: Worldwide trend data is "
            "represented using the US YouTube "
            "mostPopular chart as a worldwide proxy.",
            styles["body"]
        )
    )

    world = strategy[
        "worldwide_trends"
    ]

    story.append(
        paragraph(
            world.get(
                "summary",
                ""
            ),
            styles["body"]
        )
    )

    for label in [
        "patterns",
        "top_formats",
        "top_topics",
        "creator_opportunities",
    ]:

        story.append(
            paragraph(
                f"{label.replace('_', ' ').title()}:",
                styles["body"]
            )
        )

        for item in world.get(
            label,
            []
        ):

            story.append(
                paragraph(
                    f"• {item}",
                    styles["body"]
                )
            )

    # ========================================================
    # TREND SNAPSHOT
    # ========================================================

    story.append(
        PageBreak()
    )

    story.append(
        paragraph(
            "Trend Data Snapshot",
            styles["section"]
        )
    )

    for name, data in [
        (
            "India",
            india_analysis
        ),
        (
            "Worldwide Proxy",
            world_analysis
        ),
    ]:

        story.append(
            paragraph(
                name,
                styles["idea_title"]
            )
        )

        story.append(
            paragraph(
                f"Videos analyzed: "
                f"{data['video_count']}",
                styles["body"]
            )
        )

        story.append(
            paragraph(
                f"Total views: "
                f"{data['total_views']:,}",
                styles["body"]
            )
        )

        story.append(
            paragraph(
                f"Average views: "
                f"{data['average_views']:,}",
                styles["body"]
            )
        )

        story.append(
            paragraph(
                "Top videos:",
                styles["body"]
            )
        )

        for video in data[
            "top_videos"
        ][:10]:

            story.append(
                paragraph(
                    f"• {video['title']} "
                    f"— {video['views']:,} views",
                    styles["small"]
                )
            )

    # ========================================================
    # 4 CURRENT SHORTS
    # ========================================================

    story.append(
        PageBreak()
    )

    story.append(
        paragraph(
            "4. YOUTUBE SHORTS IDEAS BASED ON CURRENT TRENDS",
            styles["section"]
        )
    )

    for i, idea in enumerate(
        ideas[
            "current_shorts"
        ],
        1
    ):

        add_idea(
            story,
            idea,
            styles,
            i
        )

    # ========================================================
    # 5 CURRENT LONG FORM
    # ========================================================

    story.append(
        PageBreak()
    )

    story.append(
        paragraph(
            "5. LONG-FORM VIDEO IDEAS — 8–10 MINUTES",
            styles["section"]
        )
    )

    for i, idea in enumerate(
        ideas[
            "current_longform"
        ],
        1
    ):

        add_idea(
            story,
            idea,
            styles,
            i
        )

    # ========================================================
    # 6 GENERAL SHORTS
    # ========================================================

    story.append(
        PageBreak()
    )

    story.append(
        paragraph(
            "6. INDIA/WORLD GENERAL YOUTUBE SHORTS IDEAS",
            styles["section"]
        )
    )

    story.append(
        paragraph(
            "These ideas are evergreen and are NOT "
            "direct copies of current YouTube trends.",
            styles["body"]
        )
    )

    for i, idea in enumerate(
        ideas[
            "general_shorts"
        ],
        1
    ):

        add_idea(
            story,
            idea,
            styles,
            i
        )

    # ========================================================
    # 7 GENERAL LONG FORM
    # ========================================================

    story.append(
        PageBreak()
    )

    story.append(
        paragraph(
            "7. INDIA/WORLD GENERAL LONG-FORM IDEAS — 8–10 MINUTES",
            styles["section"]
        )
    )

    story.append(
        paragraph(
            "These ideas are evergreen and are NOT "
            "direct copies of current YouTube trends.",
            styles["body"]
        )
    )

    for i, idea in enumerate(
        ideas[
            "general_longform"
        ],
        1
    ):

        add_idea(
            story,
            idea,
            styles,
            i
        )

    # ========================================================
    # CREATE PDF
    # ========================================================

    doc.build(
        story,
        onFirstPage=footer,
        onLaterPages=footer
    )

    return pdf_path


# ============================================================
# RESEND EMAIL
# ============================================================

def send_email(
    pdf_path,
    high_ctr
):

    print(
        "\nSending email through Resend..."
    )

    with open(
        pdf_path,
        "rb"
    ) as file:

        encoded_pdf = (
            base64.b64encode(
                file.read()
            ).decode(
                "utf-8"
            )
        )

    title = safe_html(
        high_ctr.get(
            "title",
            "High CTR Idea"
        )
    )

    roman = safe_html(
        high_ctr.get(
            "roman_telugu_logline",
            ""
        )
    )

    hook = safe_html(
        high_ctr.get(
            "hook",
            ""
        )
    )

    html_body = f"""
<!DOCTYPE html>

<html>

<head>

<meta charset="UTF-8">

</head>

<body style="
font-family:Arial,sans-serif;
background:#f5f5f5;
margin:0;
padding:30px;
">

<div style="
max-width:700px;
margin:auto;
background:white;
padding:35px;
border-radius:10px;
">

<h1>
YouTube Trend Intelligence Report
</h1>

<p>
Your latest YouTube Trend Intelligence Report
has been generated successfully.
</p>

<hr>

<h2>
Final Best Idea
</h2>

<h3>
{title}
</h3>

<p>
<b>Roman Telugu Logline:</b>
<br>
{roman}
</p>

<p>
<b>Hook:</b>
<br>
{hook}
</p>

<p>
The professional PDF report is attached.
</p>

<ul>

<li>
India YouTube trends
</li>

<li>
Worldwide trend proxy
</li>

<li>
Current-trend Shorts ideas
</li>

<li>
Current-trend 8–10 minute ideas
</li>

<li>
General Shorts ideas
</li>

<li>
General 8–10 minute ideas
</li>

</ul>

<hr>

<p style="color:#777;">

Generated automatically by
YouTube High CTR Idea Generator.

</p>

</div>

</body>

</html>
"""

    payload = {

        "from": RESEND_FROM,

        "to": [
            RECIPIENT_EMAIL
        ],

        "subject":
            "YouTube Trend Intelligence Report",

        "html":
            html_body,

        "attachments": [

            {
                "filename":
                    os.path.basename(
                        pdf_path
                    ),

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

    response = retry_request(
        "POST",
        RESEND_URL,
        headers=headers,
        json=payload
    )

    if response.status_code not in (
        200,
        201
    ):

        raise RuntimeError(
            "Resend API error "
            f"{response.status_code}: "
            f"{response.text[:3000]}"
        )

    print(
        "Email sent successfully."
    )

    try:

        print(
            "Resend response:",
            response.json()
        )

    except Exception:

        pass


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)

    print(
        "STARTING YOUTUBE HIGH CTR IDEA GENERATOR"
    )

    print("=" * 70)

    # --------------------------------------------------------
    # 1. Environment
    # --------------------------------------------------------

    check_environment()

    # --------------------------------------------------------
    # 2. India trends
    # --------------------------------------------------------

    print(
        "\n1. Collecting India trends..."
    )

    india_videos = get_youtube_trends(
        "IN"
    )

    # --------------------------------------------------------
    # 3. Worldwide proxy
    # --------------------------------------------------------

    print(
        "\n2. Collecting worldwide proxy trends..."
    )

    world_videos = get_youtube_trends(
        "US"
    )

    # --------------------------------------------------------
    # 4. Analyze
    # --------------------------------------------------------

    india_analysis = analyze_trends(
        india_videos
    )

    world_analysis = analyze_trends(
        world_videos
    )

    # --------------------------------------------------------
    # 5. Save trend data
    # --------------------------------------------------------

    save_json(
        "india_trends.json",
        india_analysis
    )

    save_json(
        "world_trends.json",
        world_analysis
    )

    # --------------------------------------------------------
    # 6. Strategy
    # --------------------------------------------------------

    print(
        "\n3. Generating monetization strategy..."
    )

    strategy = generate_strategy(
        india_analysis,
        world_analysis
    )

    save_json(
        "strategy.json",
        strategy
    )

    # --------------------------------------------------------
    # 7. Ideas
    # --------------------------------------------------------

    print(
        "\n4. Generating HIGH CTR + YouTube ideas..."
    )

    ideas = generate_current_ideas(
        india_analysis,
        world_analysis
    )

    save_json(
        "ideas.json",
        ideas
    )

    # --------------------------------------------------------
    # 8. PDF
    # --------------------------------------------------------

    print(
        "\n5. Creating professional PDF..."
    )

    pdf_path = build_pdf(
        strategy,
        ideas,
        india_analysis,
        world_analysis
    )

    print(
        f"PDF created: {pdf_path}"
    )

    # --------------------------------------------------------
    # 9. Email
    # --------------------------------------------------------

    print(
        "\n6. Sending report email..."
    )

    send_email(
        pdf_path,
        ideas[
            "high_ctr_idea"
        ]
    )

    # --------------------------------------------------------
    # 10. Success
    # --------------------------------------------------------

    print("")
    print("=" * 70)
    print("SUCCESS")
    print("=" * 70)

    print(
        f"PDF: {pdf_path}"
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    main()
