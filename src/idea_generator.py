import os
import sys
import json
import re
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
# PROJECT PATHS
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

YOUTUBE_URL = (
    "https://www.googleapis.com/youtube/v3/videos"
)

OPENROUTER_URL = (
    "https://openrouter.ai/api/v1/chat/completions"
)

OPENROUTER_MODEL = "openrouter/free"

AI_ATTEMPTS = 3


# ============================================================
# OUTPUT SETTINGS
# ============================================================

TREND_COUNT = 50

TREND_BASED_SHORTS_COUNT = 10
TREND_BASED_LONGFORM_COUNT = 10

GENERAL_SHORTS_COUNT = 10
GENERAL_LONGFORM_COUNT = 10


# ============================================================
# PRINT
# ============================================================

def line():
    print("=" * 70)


def section(title):
    line()
    print(title)
    line()


# ============================================================
# ENVIRONMENT CHECK
# ============================================================

def check_environment():

    section("CHECKING ENVIRONMENT")

    required = {
        "YOUTUBE_API_KEY": YOUTUBE_API_KEY,
        "OPENROUTER_API_KEY": OPENROUTER_API_KEY,
        "RESEND_API_KEY": RESEND_API_KEY,
        "FROM_EMAIL": FROM_EMAIL,
        "RECIPIENT_EMAIL": RECIPIENT_EMAIL,
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
            "Missing GitHub Secrets: "
            + ", ".join(missing)
        )

    print("Environment check: OK")


# ============================================================
# YOUTUBE TREND COLLECTION
# ============================================================

def collect_youtube_trends(
    region_code,
    max_results=50,
):

    print(
        f"Collecting YouTube mostPopular: "
        f"{region_code}"
    )

    params = {
        "part": "snippet,statistics",
        "chart": "mostPopular",
        "regionCode": region_code,
        "maxResults": max_results,
        "key": YOUTUBE_API_KEY,
    }

    response = requests.get(
        YOUTUBE_URL,
        params=params,
        timeout=40,
    )

    print(
        f"YouTube HTTP status: "
        f"{response.status_code}"
    )

    response.raise_for_status()

    data = response.json()

    videos = []

    for item in data.get("items", []):

        snippet = item.get(
            "snippet",
            {},
        )

        statistics = item.get(
            "statistics",
            {},
        )

        video_id = item.get(
            "id",
            "",
        )

        videos.append({
            "video_id": video_id,

            "title": snippet.get(
                "title",
                "",
            ),

            "channel": snippet.get(
                "channelTitle",
                "",
            ),

            "description": snippet.get(
                "description",
                "",
            ),

            "published_at": snippet.get(
                "publishedAt",
                "",
            ),

            "category_id": snippet.get(
                "categoryId",
                "",
            ),

            "views": int(
                statistics.get(
                    "viewCount",
                    0,
                )
            ),

            "likes": int(
                statistics.get(
                    "likeCount",
                    0,
                )
            ),

            "comments": int(
                statistics.get(
                    "commentCount",
                    0,
                )
            ),

            "region": region_code,

            "url": (
                f"https://www.youtube.com/watch?v="
                f"{video_id}"
            ),
        })

    print(
        f"Collected {len(videos)} videos "
        f"for {region_code}."
    )

    return videos


# ============================================================
# FORMAT TREND DATA
# ============================================================

def prepare_trend_data(
    india,
    world,
):

    all_videos = []

    for video in india:
        item = dict(video)
        item["market"] = "India"
        all_videos.append(item)

    for video in world:
        item = dict(video)
        item["market"] = "Worldwide"
        all_videos.append(item)

    compact = []

    for video in all_videos:

        compact.append({
            "market": video.get(
                "market"
            ),

            "title": video.get(
                "title"
            ),

            "channel": video.get(
                "channel"
            ),

            "views": video.get(
                "views"
            ),

            "likes": video.get(
                "likes"
            ),

            "comments": video.get(
                "comments"
            ),

            "published_at": video.get(
                "published_at"
            ),

            "category_id": video.get(
                "category_id"
            ),
        })

    return compact


# ============================================================
# AI PROMPT
# ============================================================

def build_prompt(
    india,
    world,
):

    current_time = (
        datetime.now(
            timezone.utc
        ).isoformat()
    )

    trend_data = prepare_trend_data(
        india,
        world,
    )

    trend_json = json.dumps(
        trend_data,
        ensure_ascii=False,
    )

    return f"""
You are an elite YouTube content strategist,
viral-content researcher and entertainment
story concept developer.

Your job is NOT to produce generic content ideas.

Your job is to find concepts where a creator hears
the idea and thinks:

"WAAH... WHAT AN IDEA!"

The idea should create immediate curiosity.

The audience should feel:

"Wait... what happens next?"

"Why is that happening?"

"I need to watch this."

"Bro, this is actually interesting."

============================================================
CURRENT TIME
============================================================

{current_time}

============================================================
IMPORTANT CREATIVE STANDARD
============================================================

DO NOT give:

- silly ideas
- childish ideas
- random challenges
- generic vlogs
- generic prank ideas
- generic reaction videos
- boring experiments
- "24 hours doing X" unless there is a genuinely
  strong story mechanism
- simple "I tried X" concepts
- copied viral videos
- ideas requiring expensive production
- ideas that sound interesting only because of
  exaggerated wording
- concepts with no actual story
- concepts with no uncertainty
- concepts where the twist is obvious immediately

Every idea must have a REAL central question.

Examples of strong mechanisms:

- an unexplained pattern
- a contradiction
- a strange rule
- a hidden consequence
- an everyday object behaving unexpectedly
- a social situation with uncertainty
- a mystery created by a normal mistake
- a decision where the audience wants to know the result
- an ordinary situation that slowly becomes suspicious
- a simple setup with an unexpected payoff

The idea should be understandable to a normal viewer.

============================================================
LANGUAGE
============================================================

Titles:

Use natural English / English + Telugu-style
YouTube titles when appropriate.

Logline:

MUST be written in ROMAN TELUGU.

Example style:

"Nenu roju chuse oka normal place lo oka chinna
difference notice chestha. Adi coincidence anukoni
ignore chestha, kani same pattern malli malli repeat
avvadam start ayyaka asalu akkada em jarugutundo
telusukovalani try chestha."

Do NOT use Telugu script.

Use Roman Telugu.

============================================================
CONTENT CREATOR
============================================================

Assume the creator wants:

- Indian audience
- Telugu-relatable audience
- YouTube
- strong storytelling
- mystery
- suspense
- thriller
- comedy when natural
- entertainment
- curiosity
- simple-to-medium production
- concepts that can actually be made

For long-form:

Target duration:
8-10 minutes.

For Shorts:

Target duration:
20-60 seconds.

============================================================
RESEARCH TASK
============================================================

Analyze the provided India and Worldwide
YouTube trend data.

Do NOT simply copy the videos.

Instead identify:

- recurring topics
- audience emotions
- curiosity patterns
- title patterns
- formats
- categories
- story mechanisms
- entertainment patterns
- visual hooks
- conflict patterns
- mystery mechanisms
- social situations
- surprising concepts

Then transform those patterns into ORIGINAL ideas.

============================================================
YOU MUST PRODUCE 7 SECTIONS
============================================================

SECTION 1
INDIA YOUTUBE TRENDS

Analyze India trends separately for:

A. Shorts
B. Long-form 8-10 minutes

Give:

- dominant trend
- why it is working
- audience psychology
- recurring format
- opportunity for a creator

Do not just list video titles.

============================================================

SECTION 2
WORLDWIDE YOUTUBE TRENDS

Analyze Worldwide trends separately for:

A. Shorts
B. Long-form 8-10 minutes

Give:

- dominant trend
- why it is working
- audience psychology
- recurring format
- opportunity for a creator

============================================================

SECTION 3
YOUTUBE GENRE TRENDS

Identify the strongest genres currently visible
in the data.

Separate:

A. Shorts genres
B. Long-form genres

For every genre explain:

- why viewers click
- emotional trigger
- common hook
- storytelling mechanism
- opportunity

============================================================

SECTION 4
TREND-BASED SHORTS IDEAS

Generate EXACTLY {TREND_BASED_SHORTS_COUNT}
ideas.

These ideas MUST be inspired by India/Worldwide
trend patterns.

But they MUST be ORIGINAL.

Every idea MUST contain:

- rank
- high_ctr_title
- logline_roman_telugu
- trend_source
- core_hook
- concept
- why_viewers_click
- twist_or_payoff
- production_difficulty
- estimated_duration

The HIGH CTR TITLE must be strong enough that
someone wants to click.

The Roman Telugu LOGLINE must make the story
understandable immediately.

============================================================
SECTION 5
TREND-BASED LONGFORM IDEAS
============================================================

Generate EXACTLY {TREND_BASED_LONGFORM_COUNT}
ideas.

Format:

8-10 minute YouTube video.

Inspired by India/Worldwide trend patterns.

Every idea MUST contain:

- rank
- high_ctr_title
- logline_roman_telugu
- trend_source
- core_hook
- concept
- story_progression
- why_viewers_click
- twist_or_payoff
- thumbnail_concept
- production_difficulty
- estimated_duration

These must feel like actual videos with a beginning,
middle and payoff.

============================================================
SECTION 6
GENERAL / NON-TREND SHORTS
============================================================

Generate EXACTLY {GENERAL_SHORTS_COUNT}
ORIGINAL ideas.

These must NOT depend on current YouTube trends.

Use timeless human curiosity.

Examples of mechanisms:

- everyday mysteries
- social awkwardness
- small mistakes
- misunderstandings
- hidden consequences
- psychological curiosity
- unexpected discoveries
- relatable Telugu/Indian situations

Every idea:

- rank
- high_ctr_title
- logline_roman_telugu
- core_hook
- concept
- why_viewers_click
- twist_or_payoff
- thumbnail_concept
- production_difficulty
- estimated_duration

============================================================
SECTION 7
GENERAL / NON-TREND LONGFORM
============================================================

Generate EXACTLY {GENERAL_LONGFORM_COUNT}
ORIGINAL ideas.

8-10 minute format.

These must NOT depend on current YouTube trends.

They should be evergreen.

Every idea:

- rank
- high_ctr_title
- logline_roman_telugu
- core_hook
- concept
- story_progression
- why_viewers_click
- twist_or_payoff
- thumbnail_concept
- production_difficulty
- estimated_duration

============================================================
HIGH CTR REQUIREMENT
============================================================

For every idea, think about the title BEFORE
writing the concept.

The title should create:

Curiosity
+
Uncertainty
+
A specific situation
+
A reason to click

Avoid:

"Best 5..."
"Top 10..."
"I Tried..."
"My Daily Routine..."
"Fun Challenge..."
"Crazy Challenge..."
"Funny Video..."
"Day in my life..."

unless the concept has an unusually strong
story mechanism.

============================================================
QUALITY FILTER
============================================================

Before returning an idea, mentally ask:

1. Would a normal person understand it?
2. Is there a clear curiosity gap?
3. Does the audience want to know the outcome?
4. Is the idea actually shootable?
5. Is there a story?
6. Is there uncertainty?
7. Does the title make me curious?
8. Does the Roman Telugu logline sound natural?
9. Is this different from generic YouTube ideas?
10. Would someone say:

"WAAH... WHAT AN IDEA!"

If the answer is NO, reject the idea and create
a better one.

============================================================
OUTPUT
============================================================

Return ONLY valid JSON.

NO Markdown.

NO ```json.

NO explanation.

NO reasoning.

NO commentary.

NO text before JSON.

NO text after JSON.

Use exactly this structure:

{{
  "generated_at": "{current_time}",

  "india_trends": {{
    "shorts": [],
    "longform_8_10_min": []
  }},

  "world_trends": {{
    "shorts": [],
    "longform_8_10_min": []
  }},

  "genre_trends": {{
    "shorts": [],
    "longform_8_10_min": []
  }},

  "trend_based_shorts": [],

  "trend_based_longform": [],

  "general_shorts": [],

  "general_longform": []
}}

IMPORTANT:

Do not return placeholder values.

Do not return "...".

Do not return example ideas.

Generate actual ideas.

============================================================
YOUTUBE TREND DATA
============================================================

{trend_json}
"""


# ============================================================
# CLEAN RESPONSE
# ============================================================

def clean_response(text):

    if not text:
        raise RuntimeError(
            "OpenRouter returned empty response."
        )

    text = text.strip()

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

    return text.strip()


# ============================================================
# EXTRACT JSON
# ============================================================

def extract_json(text):

    text = clean_response(text)

    # First try complete response.
    try:

        data = json.loads(text)

        if isinstance(data, dict):
            return data

    except json.JSONDecodeError:
        pass

    # Find JSON object even if model added text.
    decoder = json.JSONDecoder()

    positions = [
        match.start()
        for match in re.finditer(
            r"\{",
            text,
        )
    ]

    candidates = []

    for position in positions:

        try:

            obj, end = decoder.raw_decode(
                text[position:]
            )

            if isinstance(obj, dict):

                candidates.append(obj)

        except json.JSONDecodeError:
            continue

    for candidate in candidates:

        if (
            "india_trends" in candidate
            and "world_trends" in candidate
            and "genre_trends" in candidate
        ):
            return candidate

    if candidates:
        return candidates[0]

    raise RuntimeError(
        "Could not extract valid JSON from "
        "OpenRouter response.\n\n"
        + text[:6000]
    )


# ============================================================
# QUALITY CHECK
# ============================================================

def validate_string(value):

    if not isinstance(
        value,
        str,
    ):
        return False

    value = value.strip()

    if not value:
        return False

    bad_values = [
        "...",
        "real title",
        "real hook",
        "placeholder",
        "example title",
        "example idea",
        "current utc time",
    ]

    lower = value.lower()

    for bad in bad_values:

        if bad in lower:
            return False

    return True


def validate_idea(
    idea,
    longform=False,
):

    if not isinstance(
        idea,
        dict,
    ):
        return False

    required = [
        "rank",
        "high_ctr_title",
        "logline_roman_telugu",
        "core_hook",
        "concept",
        "why_viewers_click",
        "twist_or_payoff",
    ]

    if longform:
        required.append(
            "story_progression"
        )

    for field in required:

        if not validate_string(
            idea.get(field)
        ):
            return False

    # Roman Telugu logline should not be
    # Telugu Unicode.
    logline = idea[
        "logline_roman_telugu"
    ]

    for char in logline:

        if (
            "\u0C00"
            <= char
            <= "\u0C7F"
        ):
            return False

    return True


# ============================================================
# VALIDATE COMPLETE RESULT
# ============================================================

def validate_result(data):

    if not isinstance(
        data,
        dict,
    ):
        raise RuntimeError(
            "AI result is not an object."
        )

    required_sections = [
        "india_trends",
        "world_trends",
        "genre_trends",
        "trend_based_shorts",
        "trend_based_longform",
        "general_shorts",
        "general_longform",
    ]

    for section_name in required_sections:

        if section_name not in data:

            raise RuntimeError(
                f"Missing section: "
                f"{section_name}"
            )

    # --------------------------------------------------------
    # Trend analysis sections
    # --------------------------------------------------------

    for name in [
        "india_trends",
        "world_trends",
        "genre_trends",
    ]:

        section_data = data[name]

        if not isinstance(
            section_data,
            dict,
        ):
            raise RuntimeError(
                f"{name} must be an object."
            )

        if not isinstance(
            section_data.get(
                "shorts"
            ),
            list,
        ):
            raise RuntimeError(
                f"{name}.shorts must be a list."
            )

        if not isinstance(
            section_data.get(
                "longform_8_10_min"
            ),
            list,
        ):
            raise RuntimeError(
                f"{name}.longform_8_10_min "
                f"must be a list."
            )

    # --------------------------------------------------------
    # Idea sections
    # --------------------------------------------------------

    idea_sections = [
        (
            "trend_based_shorts",
            TREND_BASED_SHORTS_COUNT,
            False,
        ),
        (
            "trend_based_longform",
            TREND_BASED_LONGFORM_COUNT,
            True,
        ),
        (
            "general_shorts",
            GENERAL_SHORTS_COUNT,
            False,
        ),
        (
            "general_longform",
            GENERAL_LONGFORM_COUNT,
            True,
        ),
    ]

    for (
        name,
        expected,
        longform,
    ) in idea_sections:

        ideas = data.get(name)

        if not isinstance(
            ideas,
            list,
        ):
            raise RuntimeError(
                f"{name} is not a list."
            )

        valid = []

        for idea in ideas:

            if validate_idea(
                idea,
                longform,
            ):
                valid.append(idea)

        if len(valid) < expected:

            raise RuntimeError(
                f"{name}: received "
                f"{len(valid)} valid ideas, "
                f"expected {expected}."
            )

        data[name] = valid[:expected]

    data["generated_at"] = (
        datetime.now(
            timezone.utc
        ).isoformat()
    )

    return data


# ============================================================
# OPENROUTER
# ============================================================

def generate_ideas(
    india,
    world,
):

    print(
        "Generating high-engagement "
        "YouTube research + ideas..."
    )

    prompt = build_prompt(
        india,
        world,
    )

    headers = {
        "Authorization":
            f"Bearer {OPENROUTER_API_KEY}",

        "Content-Type":
            "application/json",

        "HTTP-Referer":
            "https://github.com/",

        "X-Title":
            "YouTube High Engagement "
            "Idea Generator",
    }

    for attempt in range(
        1,
        AI_ATTEMPTS + 1,
    ):

        print()
        print(
            "OPENROUTER REQUEST"
        )
        print(
            f"Model: "
            f"{OPENROUTER_MODEL}"
        )
        print(
            f"Attempt: {attempt}"
        )

        payload = {
            "model":
                OPENROUTER_MODEL,

            "messages": [
                {
                    "role":
                        "system",

                    "content":
                        (
                            "You are an elite "
                            "YouTube strategist. "
                            "Return ONLY valid JSON. "
                            "Never output reasoning "
                            "or Markdown."
                        ),
                },

                {
                    "role":
                        "user",

                    "content":
                        prompt,
                },
            ],

            "response_format": {
                "type": "json_object"
            },

            "temperature":
                0.85,

            "max_tokens":
                18000,
        }

        try:

            response = requests.post(
                OPENROUTER_URL,
                headers=headers,
                json=payload,
                timeout=240,
            )

            print(
                f"HTTP status: "
                f"{response.status_code}"
            )

            if response.status_code != 200:

                print(
                    response.text[:4000]
                )

                if (
                    attempt
                    == AI_ATTEMPTS
                ):
                    response.raise_for_status()

                continue

            result = response.json()

            print(
                "OpenRouter SUCCESS"
            )

            print(
                "Model used: "
                + str(
                    result.get(
                        "model",
                        OPENROUTER_MODEL,
                    )
                )
            )

            choices = result.get(
                "choices",
                [],
            )

            if not choices:
                raise RuntimeError(
                    "No choices returned."
                )

            message = choices[0].get(
                "message",
                {},
            )

            content = message.get(
                "content",
                "",
            )

            # Some models/providers may return
            # content as a list.
            if isinstance(
                content,
                list,
            ):

                content = "".join(
                    str(
                        part.get(
                            "text",
                            "",
                        )
                    )
                    if isinstance(
                        part,
                        dict,
                    )
                    else str(part)
                    for part in content
                )

            print(
                "AI response characters: "
                + str(len(content))
            )

            data = extract_json(
                content
            )

            data = validate_result(
                data
            )

            print(
                "HIGH-QUALITY RESULT "
                "VALIDATED"
            )

            print(
                "Trend-based Shorts: "
                + str(
                    len(
                        data[
                            "trend_based_shorts"
                        ]
                    )
                )
            )

            print(
                "Trend-based Longform: "
                + str(
                    len(
                        data[
                            "trend_based_longform"
                        ]
                    )
                )
            )

            print(
                "General Shorts: "
                + str(
                    len(
                        data[
                            "general_shorts"
                        ]
                    )
                )
            )

            print(
                "General Longform: "
                + str(
                    len(
                        data[
                            "general_longform"
                        ]
                    )
                )
            )

            return data

        except Exception as exc:

            print(
                f"Attempt {attempt} failed:"
            )

            print(
                f"{type(exc).__name__}: "
                f"{exc}"
            )

            if (
                attempt
                == AI_ATTEMPTS
            ):

                raise RuntimeError(
                    "OpenRouter generation "
                    "failed after "
                    f"{AI_ATTEMPTS} attempts."
                ) from exc

            print(
                "Retrying..."
            )

    raise RuntimeError(
        "Unable to generate ideas."
    )


# ============================================================
# SAVE JSON
# ============================================================

def save_json(data):

    json_file = (
        DATA_DIR /
        "youtube_idea_generator.json"
    )

    with json_file.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2,
        )

    print()
    print(
        "JSON SAVED:"
    )
    print(json_file)

    return json_file


# ============================================================
# PDF STYLES
# ============================================================

def create_styles():

    styles = getSampleStyleSheet()

    styles.add(
        ParagraphStyle(
            name="MainTitle",
            parent=styles["Title"],
            fontSize=20,
            leading=24,
            alignment=TA_CENTER,
            spaceAfter=12,
        )
    )

    styles.add(
        ParagraphStyle(
            name="SectionTitle",
            parent=styles["Heading1"],
            fontSize=16,
            leading=20,
            spaceAfter=10,
        )
    )

    styles.add(
        ParagraphStyle(
            name="IdeaTitle",
            parent=styles["Heading2"],
            fontSize=13,
            leading=17,
            spaceAfter=7,
        )
    )

    styles.add(
        ParagraphStyle(
            name="BodyCustom",
            parent=styles["BodyText"],
            fontSize=9,
            leading=13,
            spaceAfter=5,
        )
    )

    return styles


# ============================================================
# PDF SAFE TEXT
# ============================================================

def pdf_text(value):

    if value is None:
        return ""

    if isinstance(
        value,
        (list, dict),
    ):

        value = json.dumps(
            value,
            ensure_ascii=False,
        )

    value = str(value)

    return (
        value
        .replace(
            "&",
            "&amp;",
        )
        .replace(
            "<",
            "&lt;",
        )
        .replace(
            ">",
            "&gt;",
        )
    )


def field(
    label,
    value,
    styles,
):

    return Paragraph(
        f"<b>{label}:</b> "
        f"{pdf_text(value)}",
        styles["BodyCustom"],
    )


# ============================================================
# PDF
# ============================================================

def create_pdf(data):

    section(
        "CREATING PDF"
    )

    pdf_file = (
        OUTPUT_DIR /
        "youtube_idea_generator.pdf"
    )

    styles = create_styles()

    document = SimpleDocTemplate(
        str(pdf_file),
        pagesize=A4,
        rightMargin=14 * mm,
        leftMargin=14 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
        title=(
            "YouTube High Engagement "
            "Idea Generator"
        ),
    )

    story = []

    # --------------------------------------------------------
    # TITLE
    # --------------------------------------------------------

    story.append(
        Paragraph(
            "YOUTUBE HIGH-ENGAGEMENT "
            "IDEA GENERATOR",
            styles["MainTitle"],
        )
    )

    story.append(
        Paragraph(
            "India + Worldwide + Genre + "
            "Trend-Based + Evergreen Ideas",
            styles["BodyCustom"],
        )
    )

    story.append(
        Paragraph(
            "<b>Generated:</b> "
            + pdf_text(
                data.get(
                    "generated_at"
                )
            ),
            styles["BodyCustom"],
        )
    )

    story.append(
        Spacer(1, 10)
    )

    # --------------------------------------------------------
    # TREND ANALYSIS
    # --------------------------------------------------------

    trend_sections = [
        (
            "1. INDIA YOUTUBE TRENDS",
            data["india_trends"],
        ),

        (
            "2. WORLDWIDE YOUTUBE TRENDS",
            data["world_trends"],
        ),

        (
            "3. YOUTUBE GENRE TRENDS",
            data["genre_trends"],
        ),
    ]

    for title, trend_section in trend_sections:

        story.append(
            Paragraph(
                title,
                styles["SectionTitle"],
            )
        )

        for format_name, items in [
            (
                "SHORTS",
                trend_section[
                    "shorts"
                ],
            ),

            (
                "LONGFORM 8-10 MINUTES",
                trend_section[
                    "longform_8_10_min"
                ],
            ),
        ]:

            story.append(
                Paragraph(
                    format_name,
                    styles["IdeaTitle"],
                )
            )

            for item in items:

                if isinstance(
                    item,
                    dict,
                ):

                    for key, value in item.items():

                        story.append(
                            field(
                                key.replace(
                                    "_",
                                    " "
                                ).title(),
                                value,
                                styles,
                            )
                        )

                else:

                    story.append(
                        Paragraph(
                            pdf_text(item),
                            styles[
                                "BodyCustom"
                            ],
                        )
                    )

                story.append(
                    Spacer(1, 5)
                )

        story.append(
            PageBreak()
        )

    # --------------------------------------------------------
    # IDEA SECTIONS
    # --------------------------------------------------------

    idea_sections = [
        (
            "4. TREND-BASED SHORTS",
            "trend_based_shorts",
        ),

        (
            "5. TREND-BASED LONGFORM 8-10 MIN",
            "trend_based_longform",
        ),

        (
            "6. GENERAL / NON-TREND SHORTS",
            "general_shorts",
        ),

        (
            "7. GENERAL / NON-TREND LONGFORM 8-10 MIN",
            "general_longform",
        ),
    ]

    for title, key in idea_sections:

        story.append(
            Paragraph(
                title,
                styles["SectionTitle"],
            )
        )

        ideas = data.get(
            key,
            [],
        )

        for index, idea in enumerate(
            ideas,
            start=1,
        ):

            story.append(
                Paragraph(
                    f"{index}. "
                    f"{pdf_text(idea.get('high_ctr_title'))}",
                    styles["IdeaTitle"],
                )
            )

            story.append(
                field(
                    "Roman Telugu Logline",
                    idea.get(
                        "logline_roman_telugu"
                    ),
                    styles,
                )
            )

            # Show all fields.
            skip = {
                "rank",
                "high_ctr_title",
                "logline_roman_telugu",
            }

            for key_name, value in idea.items():

                if key_name in skip:
                    continue

                story.append(
                    field(
                        key_name.replace(
                            "_",
                            " "
                        ).title(),
                        value,
                        styles,
                    )
                )

            story.append(
                Spacer(1, 8)
            )

            if index < len(ideas):
                story.append(
                    PageBreak()
                )

        if key != "general_longform":
            story.append(
                PageBreak()
            )

    document.build(story)

    print(
        "PDF CREATED:"
    )
    print(pdf_file)

    return pdf_file


# ============================================================
# RESEND EMAIL
# ============================================================

def send_email(
    pdf_file,
    json_file,
):

    section(
        "SENDING EMAIL"
    )

    resend_url = (
        "https://api.resend.com/emails"
    )

    timestamp = (
        datetime.now(
            timezone.utc
        ).strftime(
            "%Y-%m-%d %H:%M UTC"
        )
    )

    subject = (
        "YouTube High-Engagement Ideas - "
        + timestamp
    )

    body = """
Hello,

Your latest YouTube High-Engagement
Idea Generator report is ready.

The report contains:

1. India YouTube trends
2. Worldwide YouTube trends
3. YouTube genre trends
4. Trend-based Shorts ideas
5. Trend-based 8-10 minute ideas
6. General/non-trend Shorts ideas
7. General/non-trend 8-10 minute ideas

The report includes high-CTR titles
and Roman Telugu loglines.

Regards,
YouTube High-Engagement Idea Generator
"""

    with open(
        pdf_file,
        "rb",
    ) as file:

        pdf_base64 = (
            base64.b64encode(
                file.read()
            ).decode("utf-8")
        )

    with open(
        json_file,
        "rb",
    ) as file:

        json_base64 = (
            base64.b64encode(
                file.read()
            ).decode("utf-8")
        )

    payload = {
        "from":
            FROM_EMAIL,

        "to":
            [RECIPIENT_EMAIL],

        "subject":
            subject,

        "text":
            body,

        "attachments": [
            {
                "filename":
                    "youtube_idea_generator.pdf",

                "content":
                    pdf_base64,
            },

            {
                "filename":
                    "youtube_idea_generator.json",

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

    section(
        "STARTING YOUTUBE "
        "HIGH-ENGAGEMENT IDEA GENERATOR"
    )

    check_environment()

    # --------------------------------------------------------
    # INDIA
    # --------------------------------------------------------

    print(
        "1. Collecting INDIA YouTube trends..."
    )

    india = collect_youtube_trends(
        "IN",
        TREND_COUNT,
    )

    # --------------------------------------------------------
    # WORLD
    # --------------------------------------------------------

    print(
        "2. Collecting WORLD YouTube trends..."
    )

    # US is used as a practical worldwide
    # entertainment proxy through mostPopular.
    world = collect_youtube_trends(
        "US",
        TREND_COUNT,
    )

    # --------------------------------------------------------
    # AI
    # --------------------------------------------------------

    print()
    print(
        "3. Generating research + "
        "HIGH-CTR ideas..."
    )

    data = generate_ideas(
        india,
        world,
    )

    # --------------------------------------------------------
    # JSON
    # --------------------------------------------------------

    json_file = save_json(
        data
    )

    # --------------------------------------------------------
    # PDF
    # --------------------------------------------------------

    pdf_file = create_pdf(
        data
    )

    # --------------------------------------------------------
    # EMAIL
    # --------------------------------------------------------

    send_email(
        pdf_file,
        json_file,
    )

    # --------------------------------------------------------
    # COMPLETE
    # --------------------------------------------------------

    section(
        "GENERATOR COMPLETED SUCCESSFULLY"
    )


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

        section(
            "FATAL ERROR"
        )

        print(
            f"{type(exc).__name__}: "
            f"{exc}"
        )

        sys.exit(1)
