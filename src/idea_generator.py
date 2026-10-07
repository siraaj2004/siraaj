from __future__ import annotations

import json
import math
import os
import re
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import requests
from dotenv import load_dotenv


# ============================================================
# YOUTUBE HIGH CTR IDEA GENERATOR
# ============================================================
#
# Generates:
#
# 1. India YouTube Trends
#    - Shorts
#    - Long-form 8-10 min
#
# 2. Worldwide YouTube Trends
#    - Shorts
#    - Long-form 8-10 min
#
# 3. YouTube Genre Trends
#
# 4. Trend-based Shorts Ideas
# 5. Trend-based Long-form Ideas
# 6. General/Non-trend Shorts Ideas
# 7. General/Non-trend Long-form Ideas
#
# Features:
# - YouTube Data API
# - Gemini API
# - India + Worldwide trend analysis
# - Genre analysis
# - Shorts / Long-form separation
# - High CTR scoring
# - Roman Telugu loglines
# - Hook
# - Twist
# - Thumbnail concept
# - Audience reason
# - Production difficulty
# - JSON + Markdown output
#
# Python 3.10+
# ============================================================


# ============================================================
# LOAD ENVIRONMENT
# ============================================================

load_dotenv()


# ============================================================
# API CONFIG
# ============================================================

YOUTUBE_API_KEY = os.getenv(
    "YOUTUBE_API_KEY",
    ""
).strip()

GEMINI_API_KEY = os.getenv(
    "GEMINI_API_KEY",
    ""
).strip()

GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-2.5-flash"
).strip()


# ============================================================
# OUTPUT CONFIG
# ============================================================

OUTPUT_DIR = Path(
    os.getenv(
        "OUTPUT_DIR",
        "output"
    )
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# API URLS
# ============================================================

YOUTUBE_API_BASE = (
    "https://www.googleapis.com/youtube/v3"
)

GEMINI_API_BASE = (
    "https://generativelanguage.googleapis.com/v1beta/models"
)


# ============================================================
# SETTINGS
# ============================================================

INDIA_REGION = "IN"

WORLD_REGIONS = [
    "US",
    "GB",
    "CA",
    "AU",
    "DE",
    "FR",
    "JP",
    "KR",
    "BR",
    "MX",
]


# ============================================================
# YOUTUBE CATEGORY / GENRE MAP
# ============================================================

GENRE_CATEGORIES = {
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
    "29": "Nonprofits & Activism",
}


# ============================================================
# GENERATOR SETTINGS
# ============================================================

TRENDING_LIMIT = int(
    os.getenv(
        "TRENDING_LIMIT",
        "50"
    )
)

IDEAS_PER_SECTION = int(
    os.getenv(
        "IDEAS_PER_SECTION",
        "6"
    )
)

GEMINI_TIMEOUT = int(
    os.getenv(
        "GEMINI_TIMEOUT",
        "120"
    )
)


# ============================================================
# BASIC HELPERS
# ============================================================

def now_iso() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


def safe_int(
    value: Any,
    default: int = 0
) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def clean_text(
    text: Any
) -> str:

    if text is None:
        return ""

    text = str(text)

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


def format_number(
    number: Any
) -> str:

    number = safe_int(number)

    if number >= 1_000_000_000:
        return (
            f"{number / 1_000_000_000:.1f}B"
        )

    if number >= 1_000_000:
        return (
            f"{number / 1_000_000:.1f}M"
        )

    if number >= 1_000:
        return (
            f"{number / 1_000:.1f}K"
        )

    return str(number)


# ============================================================
# YOUTUBE DURATION
# ============================================================

def parse_iso_duration(
    duration: str
) -> int:

    if not duration:
        return 0

    pattern = re.compile(
        r"PT"
        r"(?:(\d+)H)?"
        r"(?:(\d+)M)?"
        r"(?:(\d+)S)?"
    )

    match = pattern.fullmatch(
        duration
    )

    if not match:
        return 0

    hours = safe_int(
        match.group(1)
    )

    minutes = safe_int(
        match.group(2)
    )

    seconds = safe_int(
        match.group(3)
    )

    return (
        hours * 3600
        + minutes * 60
        + seconds
    )


def classify_format(
    seconds: int
) -> str:

    if seconds <= 180:
        return "Short"

    return "Long-form"


# ============================================================
# YOUTUBE API REQUEST
# ============================================================

def youtube_get(
    endpoint: str,
    params: Dict[str, Any]
) -> Dict[str, Any]:

    if not YOUTUBE_API_KEY:

        raise RuntimeError(
            "YOUTUBE_API_KEY is missing. "
            "Add YOUTUBE_API_KEY to your .env file."
        )

    request_params = dict(
        params
    )

    request_params[
        "key"
    ] = YOUTUBE_API_KEY

    url = (
        f"{YOUTUBE_API_BASE}/"
        f"{endpoint}"
    )

    response = requests.get(
        url,
        params=request_params,
        timeout=30
    )

    if not response.ok:

        try:
            error_data = response.json()
        except ValueError:
            error_data = response.text

        raise RuntimeError(
            "YouTube API error "
            f"{response.status_code}: "
            f"{error_data}"
        )

    return response.json()


# ============================================================
# GET TRENDING VIDEOS
# ============================================================

def get_trending_videos(
    region_code: str,
    limit: int = 50
) -> List[Dict[str, Any]]:

    data = youtube_get(
        "videos",
        {
            "part": (
                "snippet,"
                "statistics,"
                "contentDetails"
            ),
            "chart": "mostPopular",
            "regionCode": region_code,
            "maxResults": min(
                max(limit, 1),
                50
            ),
        }
    )

    videos: List[
        Dict[str, Any]
    ] = []

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

        content = item.get(
            "contentDetails",
            {}
        )

        duration_seconds = (
            parse_iso_duration(
                content.get(
                    "duration",
                    ""
                )
            )
        )

        category_id = str(
            snippet.get(
                "categoryId",
                ""
            )
        )

        video = {
            "id": item.get(
                "id"
            ),

            "title": clean_text(
                snippet.get(
                    "title"
                )
            ),

            "description": clean_text(
                snippet.get(
                    "description"
                )
            ),

            "channel": clean_text(
                snippet.get(
                    "channelTitle"
                )
            ),

            "category_id": category_id,

            "category": GENRE_CATEGORIES.get(
                category_id,
                "Other"
            ),

            "published_at": snippet.get(
                "publishedAt"
            ),

            "duration_seconds": (
                duration_seconds
            ),

            "format": classify_format(
                duration_seconds
            ),

            "views": safe_int(
                statistics.get(
                    "viewCount"
                )
            ),

            "likes": safe_int(
                statistics.get(
                    "likeCount"
                )
            ),

            "comments": safe_int(
                statistics.get(
                    "commentCount"
                )
            ),

            "region": region_code,
        }

        videos.append(
            video
        )

    return videos


# ============================================================
# INDIA TRENDS
# ============================================================

def get_india_trends() -> List[
    Dict[str, Any]
]:

    return get_trending_videos(
        INDIA_REGION,
        TRENDING_LIMIT
    )


# ============================================================
# WORLD TRENDS
# ============================================================

def get_world_trends() -> List[
    Dict[str, Any]
]:

    all_videos: List[
        Dict[str, Any]
    ] = []

    for region in WORLD_REGIONS:

        try:

            videos = get_trending_videos(
                region,
                TRENDING_LIMIT
            )

            all_videos.extend(
                videos
            )

            print(
                f"[WORLD] {region}: "
                f"{len(videos)} videos"
            )

            time.sleep(
                0.15
            )

        except Exception as exc:

            print(
                f"[WORLD WARNING] "
                f"{region}: {exc}"
            )

    return all_videos


# ============================================================
# ENGAGEMENT
# ============================================================

def calculate_engagement(
    video: Dict[str, Any]
) -> float:

    views = max(
        safe_int(
            video.get("views")
        ),
        1
    )

    likes = safe_int(
        video.get("likes")
    )

    comments = safe_int(
        video.get("comments")
    )

    return (
        likes + comments
    ) / views


# ============================================================
# TREND SCORE
# ============================================================

def calculate_trend_score(
    video: Dict[str, Any]
) -> float:

    views = safe_int(
        video.get("views")
    )

    engagement = calculate_engagement(
        video
    )

    view_score = min(
        100.0,
        math.log10(
            max(
                views,
                1
            )
        ) * 10
    )

    engagement_score = min(
        100.0,
        engagement * 10000
    )

    score = (
        view_score * 0.55
        + engagement_score * 0.45
    )

    return round(
        score,
        2
    )


# ============================================================
# SIMPLIFY VIDEO
# ============================================================

def simplify_video(
    video: Dict[str, Any]
) -> Dict[str, Any]:

    return {
        "title": video.get(
            "title"
        ),

        "channel": video.get(
            "channel"
        ),

        "category": video.get(
            "category"
        ),

        "format": video.get(
            "format"
        ),

        "duration_seconds": video.get(
            "duration_seconds"
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

        "trend_score": video.get(
            "trend_score",
            0
        ),

        "region": video.get(
            "region"
        ),
    }


# ============================================================
# TITLE PATTERN ANALYSIS
# ============================================================

def extract_title_patterns(
    videos: List[
        Dict[str, Any]
    ]
) -> List[str]:

    patterns: List[str] = []

    titles = [
        clean_text(
            video.get(
                "title"
            )
        )
        for video in videos
        if video.get(
            "title"
        )
    ]

    if not titles:
        return patterns

    pattern_words = {
        "question": [
            "why",
            "what",
            "how",
            "who",
            "when",
        ],

        "fear": [
            "danger",
            "scary",
            "secret",
            "never",
            "warning",
            "dead",
            "missing",
            "caught",
        ],

        "curiosity": [
            "truth",
            "real",
            "finally",
            "hidden",
            "unknown",
            "inside",
            "revealed",
        ],

        "challenge": [
            "24",
            "challenge",
            "tried",
            "survive",
        ],
    }

    lowered_titles = [
        title.lower()
        for title in titles
    ]

    for pattern, words in (
        pattern_words.items()
    ):

        count = 0

        for title in lowered_titles:

            if any(
                word in title
                for word in words
            ):
                count += 1

        if count > 0:

            patterns.append(
                f"{pattern}: "
                f"{count} trending titles"
            )

    return patterns


# ============================================================
# TREND ANALYSIS
# ============================================================

def analyze_trends(
    videos: List[
        Dict[str, Any]
    ]
) -> Dict[str, Any]:

    if not videos:

        return {
            "total_videos": 0,
            "shorts": [],
            "long_form": [],
            "genres": [],
            "top_videos": [],
            "patterns": [],
        }

    for video in videos:

        video[
            "trend_score"
        ] = calculate_trend_score(
            video
        )

    shorts = [
        video
        for video in videos
        if video.get(
            "format"
        ) == "Short"
    ]

    long_form = [
        video
        for video in videos
        if video.get(
            "format"
        ) == "Long-form"
    ]

    genre_counter = Counter(
        video.get(
            "category",
            "Other"
        )
        for video in videos
    )

    top_genres = [
        {
            "genre": genre,
            "count": count,
        }
        for genre, count
        in genre_counter.most_common(
            12
        )
    ]

    top_videos = sorted(
        videos,
        key=lambda item: item.get(
            "trend_score",
            0
        ),
        reverse=True
    )

    return {
        "total_videos": len(
            videos
        ),

        "shorts": [
            simplify_video(
                video
            )
            for video in sorted(
                shorts,
                key=lambda item: item.get(
                    "trend_score",
                    0
                ),
                reverse=True
            )[:15]
        ],

        "long_form": [
            simplify_video(
                video
            )
            for video in sorted(
                long_form,
                key=lambda item: item.get(
                    "trend_score",
                    0
                ),
                reverse=True
            )[:15]
        ],

        "genres": top_genres,

        "top_videos": [
            simplify_video(
                video
            )
            for video in top_videos[:20]
        ],

        "patterns": (
            extract_title_patterns(
                videos
            )
        ),
    }


# ============================================================
# GEMINI API
# ============================================================

def gemini_generate(
    prompt: str,
    temperature: float = 0.95
) -> str:

    if not GEMINI_API_KEY:

        raise RuntimeError(
            "GEMINI_API_KEY is missing. "
            "Add GEMINI_API_KEY to your .env file."
        )

    url = (
        f"{GEMINI_API_BASE}/"
        f"{GEMINI_MODEL}:generateContent"
        f"?key={GEMINI_API_KEY}"
    )

    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {
                        "text": prompt
                    }
                ],
            }
        ],

        "generationConfig": {
            "temperature": temperature,
            "responseMimeType": (
                "application/json"
            ),
        },
    }

    response = requests.post(
        url,
        json=payload,
        timeout=GEMINI_TIMEOUT
    )

    if not response.ok:

        try:
            error_data = response.json()
        except ValueError:
            error_data = response.text

        raise RuntimeError(
            "Gemini API error "
            f"{response.status_code}: "
            f"{error_data}"
        )

    data = response.json()

    candidates = data.get(
        "candidates",
        []
    )

    if not candidates:

        raise RuntimeError(
            "Gemini returned no candidates."
        )

    parts = (
        candidates[0]
        .get(
            "content",
            {}
        )
        .get(
            "parts",
            []
        )
    )

    text_parts: List[str] = []

    for part in parts:

        if "text" in part:

            text_parts.append(
                str(
                    part["text"]
                )
            )

    result = "".join(
        text_parts
    ).strip()

    if not result:

        raise RuntimeError(
            "Gemini returned empty text."
        )

    return result


# ============================================================
# JSON EXTRACTION
# ============================================================

def extract_json(
    text: str
) -> Any:

    if not text:

        raise ValueError(
            "Empty Gemini response."
        )

    cleaned = text.strip()

    cleaned = re.sub(
        r"^```json\s*",
        "",
        cleaned,
        flags=re.IGNORECASE
    )

    cleaned = re.sub(
        r"^```\s*",
        "",
        cleaned
    )

    cleaned = re.sub(
        r"\s*```$",
        "",
        cleaned
    )

    try:

        return json.loads(
            cleaned
        )

    except json.JSONDecodeError:

        starts = [
            position
            for position in (
                cleaned.find("["),
                cleaned.find("{")
            )
            if position >= 0
        ]

        if not starts:

            raise ValueError(
                "Gemini response does not contain "
                "valid JSON."
            )

        start = min(
            starts
        )

        for end in range(
            len(cleaned),
            start,
            -1
        ):

            candidate = cleaned[
                start:end
            ].strip()

            try:

                return json.loads(
                    candidate
                )

            except json.JSONDecodeError:

                continue

        raise ValueError(
            "Could not extract valid JSON "
            "from Gemini response."
        )


# ============================================================
# HIGH CTR QUALITY RULES
# ============================================================

QUALITY_RULES = """
NON-NEGOTIABLE HIGH CTR IDEA RULES:

Do NOT generate silly or generic ideas.

Do NOT generate:
- generic 24-hour challenges
- random haunted house concepts
- random ghost stories
- generic prank videos
- generic motivation
- generic reaction videos
- generic food challenges
- generic "I tried X" concepts
- copied movie plots
- copied viral videos
- meaningless shock bait
- childish concepts
- fake mystery without a real story engine
- titles that sound good but have no actual story

Every idea MUST have:

1. A familiar situation.
2. An unusual problem, discovery, rule, or question.
3. A powerful curiosity gap.
4. Escalation.
5. A reveal, twist, emotional payoff, or surprising conclusion.
6. A strong visual moment.
7. A reason to watch until the end.
8. A reason to tell the idea to another person.

The concept should create this reaction:

"WAH... WHAT AN IDEA!"

Do not use supernatural elements just to make an idea
look interesting.

Use strong concepts involving:
- Indian everyday life
- Telugu culture
- technology
- money
- jobs
- family
- relationships
- transport
- cities
- social behavior
- hidden systems
- crime
- psychology
- investigation
- unusual human stories
- emotional reversals
- experiments
- real-world mysteries

For India:
Make the idea culturally authentic.

For World:
Make the idea globally understandable.

Do not make every idea thriller/horror.
Mix genres intelligently.

Originality is more important than quantity.
"""


# ============================================================
# IDEA PROMPT
# ============================================================

def build_idea_prompt(
    section_name: str,
    region: str,
    trend_data: Dict[str, Any],
    trend_based: bool,
    count: int
) -> str:

    if trend_based:

        source_instruction = """
Use the supplied YouTube trend data as inspiration.

DO NOT copy an existing video.

Do not rewrite an existing title.

Instead identify:
- audience behavior
- curiosity pattern
- genre
- format
- emotional trigger
- storytelling mechanism
- title structure

Then create a completely NEW concept.
"""

    else:

        source_instruction = """
This section is NOT based directly on current
YouTube trend titles.

Create ORIGINAL ideas using:
- audience psychology
- storytelling
- curiosity
- emotion
- social behavior
- cultural observations
- strong narrative mechanisms

The ideas must feel fresh.
"""

    if "Shorts" in section_name:

        format_instruction = """
FORMAT:
YouTube Shorts.

Target:
30-180 seconds.

The first 1-2 seconds must have a powerful hook.

The story must escalate quickly.

The ending must provide:
- reveal
OR
- twist
OR
- emotional reversal
OR
- shocking realization
OR
- strong payoff.
"""

    else:

        format_instruction = """
FORMAT:
YouTube long-form.

Target:
8-10 minutes.

The idea must support a complete story.

Suggested structure:

0:00-0:20
POWER HOOK

0:20-1:30
SETUP

1:30-4:00
INVESTIGATION / ESCALATION

4:00-7:00
COMPLICATION

7:00-8:30
REVEAL

8:30-10:00
PAYOFF / AFTERMATH

Do NOT make it a simple list of facts.

It must feel like a story viewers need to finish.
"""

    region_instruction = f"""
TARGET REGION:
{region}

If India:
Make it feel natural for Indian audiences,
and use Telugu/Indian cultural elements when
they genuinely improve the concept.

If World:
Make it understandable to a broad global audience.
"""

    trend_json = json.dumps(
        trend_data,
        ensure_ascii=False,
        indent=2
    )

    prompt = f"""
You are a world-class YouTube creative director,
viral storyteller, documentary producer,
and high-CTR concept strategist.

Your goal is NOT to generate hundreds of mediocre ideas.

Your goal is to find a small number of
exceptionally strong ideas.

SECTION:
{section_name}

{region_instruction}

{format_instruction}

{source_instruction}

{QUALITY_RULES}

CURRENT TREND SIGNALS:

{trend_json}

Generate EXACTLY {count} ideas.

For every idea return this structure:

{{
    "rank": 1,
    "high_ctr_title": "Title",
    "logline_roman_telugu": "Natural Roman Telugu logline",
    "format": "Short or Long-form",
    "duration": "60 seconds or 8-10 minutes",
    "genre": "Genre",
    "hook": "Opening hook",
    "core_concept": "Main concept",
    "story_engine": "Why the story keeps moving",
    "escalation": "How tension increases",
    "twist_or_payoff": "Final reveal/payoff",
    "thumbnail_concept": "Thumbnail visual",
    "why_people_click": "Why people click",
    "why_people_watch_till_end": "Why they stay",
    "shareability": "Why viewers share/tell others",
    "production_difficulty": "Easy, Medium, or Hard",
    "ctr_score": 1,
    "originality_score": 1,
    "retention_score": 1,
    "overall_score": 1
}}

SCORING:

CTR score:
How irresistible is the title/hook?

Originality score:
How fresh is the core concept?

Retention score:
How strongly does the concept make people
want to know what happens next?

Overall score:
Overall quality as a YouTube concept.

Scores must be between 1 and 100.

ROMAN TELUGU LOGLINE:

The Roman Telugu must sound like natural
spoken Telugu.

Do NOT translate English word-by-word.

Example style:

"Okka normal delivery order venaka unna secret ni
hero follow chesthu vellinappudu, tana gurinchi
thanake teliyani oka nijam bayata padutundi."

The logline should make a Telugu creator
immediately understand the story.

HIGH CTR TITLE:

The viewer should immediately think:

"WHAT?"

"WHY?"

"HOW?"

"WHO?"

"WHAT HAPPENS NEXT?"

Do not use fake clickbait.

MOST IMPORTANT:

Before returning an idea, mentally ask:

"Would a creator genuinely say
'WAH... idi chaala interesting idea'?"

If NO:
REJECT THE IDEA and create a better one.

Return JSON ONLY.
"""

    return prompt


# ============================================================
# GENERATE SECTION
# ============================================================

def generate_section(
    section_name: str,
    region: str,
    trend_data: Dict[str, Any],
    trend_based: bool
) -> List[
    Dict[str, Any]
]:

    print(
        f"\nGenerating: {section_name}"
    )

    prompt = build_idea_prompt(
        section_name=section_name,
        region=region,
        trend_data=trend_data,
        trend_based=trend_based,
        count=IDEAS_PER_SECTION
    )

    raw_response = gemini_generate(
        prompt,
        temperature=0.95
    )

    result = extract_json(
        raw_response
    )

    if isinstance(
        result,
        dict
    ):

        if isinstance(
            result.get("ideas"),
            list
        ):

            result = result[
                "ideas"
            ]

        else:

            result = [
                result
            ]

    if not isinstance(
        result,
        list
    ):

        raise RuntimeError(
            f"Gemini returned invalid "
            f"idea format for: "
            f"{section_name}"
        )

    ideas: List[
        Dict[str, Any]
    ] = []

    for index, idea in enumerate(
        result,
        start=1
    ):

        if not isinstance(
            idea,
            dict
        ):
            continue

        idea["rank"] = index

        ideas.append(
            idea
        )

    return ideas[
        :IDEAS_PER_SECTION
    ]


# ============================================================
# SCORE IDEA
# ============================================================

def score_idea(
    idea: Dict[str, Any]
) -> float:

    overall = safe_int(
        idea.get(
            "overall_score"
        )
    )

    ctr = safe_int(
        idea.get(
            "ctr_score"
        )
    )

    originality = safe_int(
        idea.get(
            "originality_score"
        )
    )

    retention = safe_int(
        idea.get(
            "retention_score"
        )
    )

    return (
        overall * 0.40
        + ctr * 0.30
        + originality * 0.15
        + retention * 0.15
    )


# ============================================================
# SELECT TOP IDEAS
# ============================================================

def select_high_ctr_ideas(
    all_sections: Dict[
        str,
        List[Dict[str, Any]]
    ]
) -> List[
    Dict[str, Any]
]:

    candidates: List[
        Dict[str, Any]
    ] = []

    for section, ideas in (
        all_sections.items()
    ):

        for idea in ideas:

            candidate = dict(
                idea
            )

            candidate[
                "source_section"
            ] = section

            candidate[
                "_selection_score"
            ] = score_idea(
                candidate
            )

            candidates.append(
                candidate
            )

    candidates.sort(
        key=lambda item: item[
            "_selection_score"
        ],
        reverse=True
    )

    selected: List[
        Dict[str, Any]
    ] = []

    section_count = defaultdict(
        int
    )

    for candidate in candidates:

        section = candidate[
            "source_section"
        ]

        if section_count[
            section
        ] >= 2:

            continue

        candidate.pop(
            "_selection_score",
            None
        )

        selected.append(
            candidate
        )

        section_count[
            section
        ] += 1

        if len(selected) >= 10:
            break

    return selected


# ============================================================
# RENDER IDEA
# ============================================================

def render_idea(
    idea: Dict[str, Any],
    index: int
) -> str:

    return f"""
### {index}. {clean_text(idea.get("high_ctr_title"))}

**🔥 HIGH CTR SCORE:** {idea.get("ctr_score", "-")}/100

**⭐ OVERALL SCORE:** {idea.get("overall_score", "-")}/100

**🎬 FORMAT:** {clean_text(idea.get("format"))}

**⏱ DURATION:** {clean_text(idea.get("duration"))}

**🎭 GENRE:** {clean_text(idea.get("genre"))}

**🇮🇳 ROMAN TELUGU LOGLINE**

> {clean_text(idea.get("logline_roman_telugu"))}

**🔥 HOOK**

{clean_text(idea.get("hook"))}

**💡 CORE CONCEPT**

{clean_text(idea.get("core_concept"))}

**⚙️ STORY ENGINE**

{clean_text(idea.get("story_engine"))}

**📈 ESCALATION**

{clean_text(idea.get("escalation"))}

**🎯 TWIST / PAYOFF**

{clean_text(idea.get("twist_or_payoff"))}

**🖼️ THUMBNAIL CONCEPT**

{clean_text(idea.get("thumbnail_concept"))}

**👆 WHY PEOPLE CLICK**

{clean_text(idea.get("why_people_click"))}

**⏳ WHY PEOPLE WATCH TILL END**

{clean_text(idea.get("why_people_watch_till_end"))}

**📤 SHAREABILITY**

{clean_text(idea.get("shareability"))}

**🎥 PRODUCTION DIFFICULTY**

{clean_text(idea.get("production_difficulty"))}

---
"""


# ============================================================
# TREND REPORT
# ============================================================

def render_trend_report(
    title: str,
    data: Dict[str, Any]
) -> str:

    lines: List[str] = []

    lines.append(
        f"## {title}"
    )

    lines.append("")

    lines.append(
        f"Total sampled videos: "
        f"{data.get('total_videos', 0)}"
    )

    lines.append("")

    lines.append(
        "### Top Genres"
    )

    for genre in data.get(
        "genres",
        []
    ):

        lines.append(
            f"- **{genre.get('genre')}**: "
            f"{genre.get('count')}"
        )

    lines.append("")

    lines.append(
        "### Trending Title Patterns"
    )

    patterns = data.get(
        "patterns",
        []
    )

    if patterns:

        for pattern in patterns:

            lines.append(
                f"- {pattern}"
            )

    else:

        lines.append(
            "- No strong title pattern detected."
        )

    lines.append("")

    lines.append(
        "### Strongest Trending Videos"
    )

    for video in data.get(
        "top_videos",
        []
    )[:10]:

        title_text = clean_text(
            video.get(
                "title"
            )
        )

        category = clean_text(
            video.get(
                "category"
            )
        )

        views = format_number(
            video.get(
                "views"
            )
        )

        lines.append(
            f"- **{title_text}** "
            f"— {category} "
            f"— {views} views"
        )

    lines.append("")

    return "\n".join(
        lines
    )


# ============================================================
# BUILD MARKDOWN REPORT
# ============================================================

def build_markdown_report(
    india_analysis: Dict[str, Any],
    world_analysis: Dict[str, Any],
    sections: Dict[
        str,
        List[Dict[str, Any]]
    ],
    top_ideas: List[
        Dict[str, Any]
    ]
) -> str:

    lines: List[str] = []

    lines.append(
        "# 🔥 YOUTUBE HIGH CTR IDEA GENERATOR"
    )

    lines.append("")

    lines.append(
        f"Generated: `{now_iso()}`"
    )

    lines.append("")

    lines.append(
        "India + Worldwide YouTube Trend Analysis"
    )

    lines.append("")

    # ========================================================
    # TOP IDEAS
    # ========================================================

    lines.append(
        "# 🚨 TOP HIGH CTR IDEAS"
    )

    lines.append("")

    lines.append(
        "The strongest concepts selected "
        "from all generated sections."
    )

    lines.append("")

    for index, idea in enumerate(
        top_ideas,
        start=1
    ):

        lines.append(
            render_idea(
                idea,
                index
            )
        )

    # ========================================================
    # INDIA
    # ========================================================

    lines.append(
        "# 🇮🇳 1. INDIA YOUTUBE TRENDS"
    )

    lines.append("")

    lines.append(
        render_trend_report(
            "India Trend Analysis",
            india_analysis
        )
    )

    # ========================================================
    # WORLD
    # ========================================================

    lines.append(
        "# 🌍 2. WORLD YOUTUBE TRENDS"
    )

    lines.append("")

    lines.append(
        render_trend_report(
            "Worldwide Trend Analysis",
            world_analysis
        )
    )

    # ========================================================
    # GENRE TRENDS
    # ========================================================

    lines.append(
        "# 🎬 3. YOUTUBE GENRE TRENDS"
    )

    lines.append("")

    combined_genres = Counter()

    for analysis in (
        india_analysis,
        world_analysis
    ):

        for genre in analysis.get(
            "genres",
            []
        ):

            combined_genres[
                genre.get(
                    "genre",
                    "Other"
                )
            ] += safe_int(
                genre.get(
                    "count"
                )
            )

    for genre, count in (
        combined_genres.most_common()
    ):

        lines.append(
            f"- **{genre}** — "
            f"{count} appearances"
        )

    lines.append("")

    # ========================================================
    # SECTION ORDER
    # ========================================================

    section_order = [
        (
            "# 🔥 4A. TREND-BASED SHORTS — INDIA",
            "Trend-Based Shorts — India"
        ),

        (
            "# 🌍 4B. TREND-BASED SHORTS — WORLD",
            "Trend-Based Shorts — World"
        ),

        (
            "# 🔥 5A. TREND-BASED LONG-FORM — INDIA",
            "Trend-Based Long-form — India"
        ),

        (
            "# 🌍 5B. TREND-BASED LONG-FORM — WORLD",
            "Trend-Based Long-form — World"
        ),

        (
            "# 🧠 6A. ORIGINAL GENERAL SHORTS — INDIA",
            "General Original Shorts — India"
        ),

        (
            "# 🌍 6B. ORIGINAL GENERAL SHORTS — WORLD",
            "General Original Shorts — World"
        ),

        (
            "# 🎥 7A. ORIGINAL GENERAL LONG-FORM — INDIA",
            "General Original Long-form — India"
        ),

        (
            "# 🌍 7B. ORIGINAL GENERAL LONG-FORM — WORLD",
            "General Original Long-form — World"
        ),
    ]

    # ========================================================
    # RENDER ALL IDEA SECTIONS
    # ========================================================

    for heading, section_key in (
        section_order
    ):

        lines.append(
            heading
        )

        lines.append("")

        ideas = sections.get(
            section_key,
            []
        )

        if not ideas:

            lines.append(
                "No ideas generated."
            )

            lines.append("")

            continue

        for index, idea in enumerate(
            ideas,
            start=1
        ):

            lines.append(
                render_idea(
                    idea,
                    index
                )
            )

    return "\n".join(
        lines
    )


# ============================================================
# SAVE JSON
# ============================================================

def save_json(
    data: Any,
    filename: str
) -> Path:

    path = (
        OUTPUT_DIR
        / filename
    )

    with path.open(
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
# SAVE TEXT
# ============================================================

def save_text(
    text: str,
    filename: str
) -> Path:

    path = (
        OUTPUT_DIR
        / filename
    )

    with path.open(
        "w",
        encoding="utf-8"
    ) as file:

        file.write(
            text
        )

    return path


# ============================================================
# MAIN
# ============================================================

def main() -> None:

    print("=" * 70)

    print(
        "🔥 STARTING YOUTUBE HIGH CTR IDEA GENERATOR"
    )

    print("=" * 70)

    print(
        f"Gemini Model: {GEMINI_MODEL}"
    )

    print(
        f"Ideas Per Section: "
        f"{IDEAS_PER_SECTION}"
    )

    # ========================================================
    # API CHECK
    # ========================================================

    if not YOUTUBE_API_KEY:

        raise RuntimeError(
            "YOUTUBE_API_KEY is missing.\n"
            "Create .env and add:\n"
            "YOUTUBE_API_KEY=YOUR_KEY"
        )

    if not GEMINI_API_KEY:

        raise RuntimeError(
            "GEMINI_API_KEY is missing.\n"
            "Create .env and add:\n"
            "GEMINI_API_KEY=YOUR_KEY"
        )

    # ========================================================
    # INDIA TRENDS
    # ========================================================

    print(
        "\n[1/8] Collecting India YouTube trends..."
    )

    india_videos = get_india_trends()

    print(
        f"India videos collected: "
        f"{len(india_videos)}"
    )

    india_analysis = analyze_trends(
        india_videos
    )

    # ========================================================
    # WORLD TRENDS
    # ========================================================

    print(
        "\n[2/8] Collecting worldwide YouTube trends..."
    )

    world_videos = get_world_trends()

    print(
        f"World videos collected: "
        f"{len(world_videos)}"
    )

    world_analysis = analyze_trends(
        world_videos
    )

    # ========================================================
    # SAVE TREND DATA
    # ========================================================

    print(
        "\n[3/8] Saving trend analysis..."
    )

    save_json(
        {
            "generated_at": now_iso(),
            "india": india_analysis,
            "world": world_analysis,
        },
        "youtube_trend_analysis.json"
    )

    # ========================================================
    # IDEA SECTIONS
    # ========================================================

    print(
        "\n[4/8] Generating trend-based Shorts..."
    )

    sections: Dict[
        str,
        List[Dict[str, Any]]
    ] = {}

    sections[
        "Trend-Based Shorts — India"
    ] = generate_section(
        "Trend-Based Shorts — India",
        "India",
        india_analysis,
        True
    )

    sections[
        "Trend-Based Shorts — World"
    ] = generate_section(
        "Trend-Based Shorts — World",
        "World",
        world_analysis,
        True
    )

    print(
        "\n[5/8] Generating trend-based Long-form..."
    )

    sections[
        "Trend-Based Long-form — India"
    ] = generate_section(
        "Trend-Based Long-form — India",
        "India",
        india_analysis,
        True
    )

    sections[
        "Trend-Based Long-form — World"
    ] = generate_section(
        "Trend-Based Long-form — World",
        "World",
        world_analysis,
        True
    )

    print(
        "\n[6/8] Generating original Shorts..."
    )

    sections[
        "General Original Shorts — India"
    ] = generate_section(
        "Original General Shorts — India",
        "India",
        {
            "instruction": (
                "Create completely original "
                "YouTube Shorts ideas. "
                "Do not copy current trend videos."
            )
        },
        False
    )

    sections[
        "General Original Shorts — World"
    ] = generate_section(
        "Original General Shorts — World",
        "World",
        {
            "instruction": (
                "Create completely original "
                "YouTube Shorts ideas. "
                "Do not copy current trend videos."
            )
        },
        False
    )

    print(
        "\n[7/8] Generating original Long-form..."
    )

    sections[
        "General Original Long-form — India"
    ] = generate_section(
        "Original General Long-form — India",
        "India",
        {
            "instruction": (
                "Create completely original "
                "8-10 minute YouTube ideas. "
                "Do not copy current trend videos."
            )
        },
        False
    )

    sections[
        "General Original Long-form — World"
    ] = generate_section(
        "Original General Long-form — World",
        "World",
        {
            "instruction": (
                "Create completely original "
                "8-10 minute YouTube ideas. "
                "Do not copy current trend videos."
            )
        },
        False
    )

    # ========================================================
    # TOP IDEAS
    # ========================================================

    print(
        "\nSelecting strongest high CTR ideas..."
    )

    top_ideas = select_high_ctr_ideas(
        sections
    )

    # ========================================================
    # FINAL JSON
    # ========================================================

    final_json = {
        "generated_at": now_iso(),

        "top_high_ctr_ideas": top_ideas,

        "india_trends": india_analysis,

        "world_trends": world_analysis,

        "sections": sections,
    }

    json_path = save_json(
        final_json,
        "youtube_high_ctr_ideas.json"
    )

    # ========================================================
    # FINAL MARKDOWN
    # ========================================================

    markdown_report = build_markdown_report(
        india_analysis,
        world_analysis,
        sections,
        top_ideas
    )

    markdown_path = save_text(
        markdown_report,
        "youtube_high_ctr_ideas.md"
    )

    # ========================================================
    # FINAL SUMMARY
    # ========================================================

    total_ideas = sum(
        len(ideas)
        for ideas in sections.values()
    )

    print("\n")
    print("=" * 70)
    print("✅ YOUTUBE HIGH CTR IDEA GENERATOR COMPLETE")
    print("=" * 70)

    print(
        f"Total ideas generated: "
        f"{total_ideas}"
    )

    print(
        f"Top High CTR ideas: "
        f"{len(top_ideas)}"
    )

    print(
        f"JSON output: "
        f"{json_path}"
    )

    print(
        f"Markdown output: "
        f"{markdown_path}"
    )

    print("=" * 70)


# ============================================================
# PROGRAM ENTRY
# ============================================================

if __name__ == "__main__":
    main()
