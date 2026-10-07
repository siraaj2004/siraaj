from __future__ import annotations

import base64
import json
import math
import os
import re
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import requests
from dotenv import load_dotenv


# ============================================================
# YOUTUBE HIGH CTR IDEA GENERATOR
# ============================================================
#
# 1. INDIA YOUTUBE TRENDS
#    - Shorts
#    - Long-form 8-10 minutes
#
# 2. WORLD YOUTUBE TRENDS
#    - Shorts
#    - Long-form 8-10 minutes
#
# 3. YOUTUBE GENRE TRENDS
#    - Shorts
#    - Long-form
#
# 4. TREND-BASED SHORTS IDEAS
#    - India
#    - World
#    - Roman Telugu logline
#
# 5. TREND-BASED LONG-FORM IDEAS
#    - India
#    - World
#    - 8-10 minutes
#    - Roman Telugu logline
#
# 6. GENERAL / NON-TREND SHORTS IDEAS
#    - India
#    - World
#    - Roman Telugu logline
#
# 7. GENERAL / NON-TREND LONG-FORM IDEAS
#    - India
#    - World
#    - 8-10 minutes
#    - Roman Telugu logline
#
# AI:
# OpenRouter
#
# EMAIL:
# Resend
#
# Python:
# 3.12+
#
# ============================================================


# ============================================================
# LOAD ENVIRONMENT
# ============================================================

load_dotenv()


# ============================================================
# CONFIG
# ============================================================

YOUTUBE_API_KEY = os.getenv(
    "YOUTUBE_API_KEY",
    ""
).strip()

OPENROUTER_API_KEY = os.getenv(
    "OPENROUTER_API_KEY",
    ""
).strip()

OPENROUTER_MODEL = os.getenv(
    "OPENROUTER_MODEL",
    "openrouter/auto"
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

OPENROUTER_TIMEOUT = int(
    os.getenv(
        "OPENROUTER_TIMEOUT",
        "180"
    )
)

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

YOUTUBE_API_URL = (
    "https://www.googleapis.com/youtube/v3/videos"
)

OPENROUTER_API_URL = (
    "https://openrouter.ai/api/v1/chat/completions"
)

RESEND_API_URL = (
    "https://api.resend.com/emails"
)


# ============================================================
# REGIONS
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
# YOUTUBE GENRES
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
# CONSOLE
# ============================================================

def banner(text: str) -> None:
    print()
    print("=" * 60)
    print(text)
    print("=" * 60)
    print()


# ============================================================
# GENERAL HELPERS
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
    except Exception:
        return default


def clean_text(
    value: Any
) -> str:

    if value is None:
        return ""

    text = str(value)

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
        return f"{number / 1_000_000_000:.1f}B"

    if number >= 1_000_000:
        return f"{number / 1_000_000:.1f}M"

    if number >= 1_000:
        return f"{number / 1_000:.1f}K"

    return str(number)


# ============================================================
# YOUTUBE DURATION
# ============================================================

def parse_iso_duration(
    duration: str
) -> int:

    if not duration:
        return 0

    match = re.fullmatch(
        r"PT"
        r"(?:(\d+)H)?"
        r"(?:(\d+)M)?"
        r"(?:(\d+)S)?",
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


# ============================================================
# FORMAT CLASSIFICATION
# ============================================================

def classify_format(
    seconds: int
) -> str:

    if seconds <= 180:
        return "Short"

    return "Long-form"


# ============================================================
# YOUTUBE API
# ============================================================

def youtube_request(
    region: str
) -> Dict[str, Any]:

    if not YOUTUBE_API_KEY:
        raise RuntimeError(
            "YOUTUBE_API_KEY is missing."
        )

    params = {
        "part": (
            "snippet,"
            "statistics,"
            "contentDetails"
        ),
        "chart": "mostPopular",
        "regionCode": region,
        "maxResults": min(
            TRENDING_LIMIT,
            50
        ),
        "key": YOUTUBE_API_KEY,
    }

    response = requests.get(
        YOUTUBE_API_URL,
        params=params,
        timeout=45
    )

    print(
        f"YouTube HTTP status: "
        f"{response.status_code}"
    )

    if not response.ok:

        try:
            error = response.json()
        except Exception:
            error = response.text

        raise RuntimeError(
            "YouTube API error "
            f"{response.status_code}: "
            f"{error}"
        )

    return response.json()


# ============================================================
# COLLECT YOUTUBE VIDEOS
# ============================================================

def collect_region_trends(
    region: str
) -> List[Dict[str, Any]]:

    print(
        f"Collecting YouTube "
        f"mostPopular data: {region}"
    )

    data = youtube_request(
        region
    )

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

        content_details = item.get(
            "contentDetails",
            {}
        )

        duration_seconds = parse_iso_duration(
            content_details.get(
                "duration",
                ""
            )
        )

        views = safe_int(
            statistics.get(
                "viewCount"
            )
        )

        likes = safe_int(
            statistics.get(
                "likeCount"
            )
        )

        comments = safe_int(
            statistics.get(
                "commentCount"
            )
        )

        engagement = (
            (
                likes
                + comments
            )
            / max(
                views,
                1
            )
        )

        videos.append(
            {
                "id": item.get(
                    "id",
                    ""
                ),
                "title": clean_text(
                    snippet.get(
                        "title"
                    )
                ),
                "channel": clean_text(
                    snippet.get(
                        "channelTitle"
                    )
                ),
                "category_id": str(
                    snippet.get(
                        "categoryId",
                        ""
                    )
                ),
                "genre": GENRE_CATEGORIES.get(
                    str(
                        snippet.get(
                            "categoryId",
                            ""
                        )
                    ),
                    "Other"
                ),
                "published_at": snippet.get(
                    "publishedAt"
                ),
                "duration_seconds": duration_seconds,
                "format": classify_format(
                    duration_seconds
                ),
                "views": views,
                "likes": likes,
                "comments": comments,
                "engagement_rate": round(
                    engagement * 100,
                    4
                ),
                "region": region,
            }
        )

    print(
        f"Collected "
        f"{len(videos)} videos."
    )

    return videos


# ============================================================
# INDIA
# ============================================================

def collect_india_trends() -> List[Dict[str, Any]]:

    return collect_region_trends(
        INDIA_REGION
    )


# ============================================================
# WORLD
# ============================================================

def collect_world_trends() -> List[Dict[str, Any]]:

    all_videos = []

    for region in WORLD_REGIONS:

        try:

            videos = collect_region_trends(
                region
            )

            all_videos.extend(
                videos
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
# TREND SCORE
# ============================================================

def trend_score(
    video: Dict[str, Any]
) -> float:

    views = max(
        safe_int(
            video.get(
                "views"
            )
        ),
        1
    )

    engagement = float(
        video.get(
            "engagement_rate",
            0
        )
    )

    view_score = min(
        100,
        math.log10(
            views
        ) * 10
    )

    engagement_score = min(
        100,
        engagement * 10
    )

    score = (
        view_score * 0.60
        + engagement_score * 0.40
    )

    return round(
        score,
        2
    )


# ============================================================
# ADD TREND SCORES
# ============================================================

def score_videos(
    videos: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:

    for video in videos:

        video["trend_score"] = trend_score(
            video
        )

    return videos


# ============================================================
# SORT
# ============================================================

def top_videos(
    videos: List[Dict[str, Any]],
    limit: int = 15
) -> List[Dict[str, Any]]:

    return sorted(
        videos,
        key=lambda x: x.get(
            "trend_score",
            0
        ),
        reverse=True
    )[:limit]


# ============================================================
# SIMPLE VIDEO
# ============================================================

def simplify_video(
    video: Dict[str, Any]
) -> Dict[str, Any]:

    return {
        "title": video.get(
            "title",
            ""
        ),
        "channel": video.get(
            "channel",
            ""
        ),
        "genre": video.get(
            "genre",
            "Other"
        ),
        "format": video.get(
            "format",
            ""
        ),
        "duration_seconds": video.get(
            "duration_seconds",
            0
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
        "engagement_rate": video.get(
            "engagement_rate",
            0
        ),
        "trend_score": video.get(
            "trend_score",
            0
        ),
        "region": video.get(
            "region",
            ""
        ),
    }


# ============================================================
# TITLE PATTERNS
# ============================================================

def detect_title_patterns(
    videos: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:

    patterns = {
        "question": [
            "why",
            "what",
            "how",
            "who",
            "when",
        ],
        "curiosity": [
            "secret",
            "truth",
            "real",
            "hidden",
            "inside",
            "revealed",
            "unknown",
        ],
        "urgency": [
            "today",
            "now",
            "warning",
            "before",
            "last",
        ],
        "discovery": [
            "found",
            "discovered",
            "caught",
            "missing",
            "lost",
        ],
    }

    results = []

    titles = [
        clean_text(
            video.get(
                "title"
            )
        ).lower()
        for video in videos
    ]

    for pattern, words in patterns.items():

        count = 0

        for title in titles:

            if any(
                word in title
                for word in words
            ):
                count += 1

        results.append(
            {
                "pattern": pattern,
                "count": count,
            }
        )

    return sorted(
        results,
        key=lambda x: x[
            "count"
        ],
        reverse=True
    )


# ============================================================
# GENRE ANALYSIS
# ============================================================

def genre_analysis(
    videos: List[Dict[str, Any]]
) -> Dict[str, Any]:

    if not videos:

        return {
            "total": 0,
            "all_formats": [],
            "shorts": [],
            "long_form": [],
        }

    def analyze(
        data: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:

        counter = Counter(
            video.get(
                "genre",
                "Other"
            )
            for video in data
        )

        total = max(
            len(data),
            1
        )

        output = []

        for genre, count in counter.most_common():

            output.append(
                {
                    "genre": genre,
                    "video_count": count,
                    "percentage": round(
                        (
                            count
                            / total
                        ) * 100,
                        2
                    ),
                    "average_views": round(
                        sum(
                            safe_int(
                                v.get(
                                    "views"
                                )
                            )
                            for v in data
                            if v.get(
                                "genre"
                            ) == genre
                        )
                        / max(
                            count,
                            1
                        )
                    ),
                }
            )

        return output

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

    return {
        "total": len(
            videos
        ),
        "all_formats": analyze(
            videos
        ),
        "shorts": analyze(
            shorts
        ),
        "long_form": analyze(
            long_form
        ),
    }


# ============================================================
# FORMAT ANALYSIS
# ============================================================

def format_analysis(
    videos: List[Dict[str, Any]]
) -> Dict[str, Any]:

    shorts = [
        v
        for v in videos
        if v.get(
            "format"
        ) == "Short"
    ]

    long_form = [
        v
        for v in videos
        if v.get(
            "format"
        ) == "Long-form"
    ]

    long_8_10 = [
        v
        for v in long_form
        if 480
        <= safe_int(
            v.get(
                "duration_seconds"
            )
        )
        <= 600
    ]

    return {
        "total_videos": len(
            videos
        ),
        "shorts_count": len(
            shorts
        ),
        "long_form_count": len(
            long_form
        ),
        "eight_to_ten_minute_count": len(
            long_8_10
        ),
        "top_shorts": [
            simplify_video(
                v
            )
            for v in top_videos(
                shorts,
                15
            )
        ],
        "top_long_form_8_10_minutes": [
            simplify_video(
                v
            )
            for v in top_videos(
                long_8_10,
                15
            )
        ],
        "top_long_form": [
            simplify_video(
                v
            )
            for v in top_videos(
                long_form,
                15
            )
        ],
    }


# ============================================================
# COMPLETE TREND REPORT
# ============================================================

def build_trend_report(
    videos: List[Dict[str, Any]]
) -> Dict[str, Any]:

    videos = score_videos(
        videos
    )

    return {
        "total_videos": len(
            videos
        ),
        "format_analysis": format_analysis(
            videos
        ),
        "genre_trends": genre_analysis(
            videos
        ),
        "title_patterns": detect_title_patterns(
            videos
        ),
        "top_videos": [
            simplify_video(
                v
            )
            for v in top_videos(
                videos,
                20
            )
        ],
    }


# ============================================================
# OPENROUTER
# ============================================================

def call_openrouter(
    prompt: str,
    attempt: int = 1
) -> str:

    if not OPENROUTER_API_KEY:

        raise RuntimeError(
            "OPENROUTER_API_KEY is missing."
        )

    print()
    print(
        "OPENROUTER REQUEST"
    )

    print(
        f"Model: "
        f"{OPENROUTER_MODEL}"
    )

    print(
        f"Attempt: "
        f"{attempt}"
    )

    headers = {
        "Authorization": (
            f"Bearer "
            f"{OPENROUTER_API_KEY}"
        ),
        "Content-Type": (
            "application/json"
        ),
        "HTTP-Referer": (
            "https://github.com/"
        ),
        "X-Title": (
            "YouTube High CTR "
            "Idea Generator"
        ),
    }

    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are an elite YouTube "
                    "creative director and "
                    "story strategist."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        "temperature": 0.85,
        "max_tokens": 14000,
    }

    response = requests.post(
        OPENROUTER_API_URL,
        headers=headers,
        json=payload,
        timeout=OPENROUTER_TIMEOUT,
    )

    print(
        f"HTTP status: "
        f"{response.status_code}"
    )

    if not response.ok:

        try:
            error = response.json()
        except Exception:
            error = response.text

        raise RuntimeError(
            "OpenRouter HTTP error "
            f"{response.status_code}: "
            f"{error}"
        )

    data = response.json()

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

        pieces = []

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
                    pieces.append(
                        str(text)
                    )

        content = "".join(
            pieces
        )

    content = clean_text(
        content
    )

    if not content:

        raise RuntimeError(
            "OpenRouter returned "
            "empty content."
        )

    actual_model = data.get(
        "model",
        OPENROUTER_MODEL
    )

    print(
        "OpenRouter SUCCESS"
    )

    print(
        f"Model used: "
        f"{actual_model}"
    )

    print(
        f"AI response length: "
        f"{len(content)} characters"
    )

    return content


# ============================================================
# ROBUST JSON EXTRACTION
# ============================================================

def strip_code_fences(
    text: str
) -> str:

    text = text.strip()

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

    return text.strip()


def extract_json_value(
    text: str
) -> Any:

    text = strip_code_fences(
        text
    )

    # ----------------------------------------
    # First try complete response.
    # ----------------------------------------

    try:

        return json.loads(
            text
        )

    except Exception:
        pass

    # ----------------------------------------
    # Find JSON object / array.
    # ----------------------------------------

    candidates = []

    for index, char in enumerate(
        text
    ):

        if char in "[{":

            candidates.append(
                index
            )

    # ----------------------------------------
    # Balanced JSON scanner.
    # ----------------------------------------

    for start in candidates:

        stack = []

        in_string = False
        escaped = False

        for index in range(
            start,
            len(text)
        ):

            char = text[index]

            if in_string:

                if escaped:

                    escaped = False

                elif char == "\\":
                    escaped = True

                elif char == '"':
                    in_string = False

                continue

            if char == '"':
                in_string = True
                continue

            if char in "[{":
                stack.append(
                    char
                )

            elif char in "]}":

                if not stack:
                    break

                opening = stack.pop()

                if (
                    opening == "["
                    and char != "]"
                ):
                    break

                if (
                    opening == "{"
                    and char != "}"
                ):
                    break

                if not stack:

                    candidate = text[
                        start:index + 1
                    ].strip()

                    try:

                        return json.loads(
                            candidate
                        )

                    except Exception:
                        break

    raise RuntimeError(
        "AI response does not contain "
        "valid JSON."
    )


# ============================================================
# NORMALIZE AI RESPONSE
# ============================================================

def normalize_ideas(
    result: Any
) -> List[Dict[str, Any]]:

    # ----------------------------------------
    # CASE 1:
    # {
    #   "ideas": [...]
    # }
    # ----------------------------------------

    if isinstance(
        result,
        dict
    ):

        for key in [
            "ideas",
            "idea_list",
            "results",
            "items",
            "concepts",
        ]:

            value = result.get(
                key
            )

            if isinstance(
                value,
                list
            ):

                result = value
                break

        else:

            # --------------------------------
            # Model may return:
            # {
            #   "india": {
            #       "ideas": [...]
            #   },
            #   "world": {
            #       "ideas": [...]
            #   }
            # }
            # --------------------------------

            combined = []

            for value in result.values():

                if isinstance(
                    value,
                    list
                ):

                    combined.extend(
                        value
                    )

                elif isinstance(
                    value,
                    dict
                ):

                    nested = normalize_ideas(
                        value
                    )

                    combined.extend(
                        nested
                    )

            if combined:
                result = combined

    # ----------------------------------------
    # CASE 2:
    # [...]
    # ----------------------------------------

    if not isinstance(
        result,
        list
    ):

        raise RuntimeError(
            "AI result does not contain "
            "an ideas list."
        )

    normalized = []

    for index, idea in enumerate(
        result,
        start=1
    ):

        if isinstance(
            idea,
            str
        ):

            idea = {
                "high_ctr_title": idea
            }

        if not isinstance(
            idea,
            dict
        ):
            continue

        title = clean_text(
            idea.get(
                "high_ctr_title"
            )
            or idea.get(
                "title"
            )
            or idea.get(
                "youtube_title"
            )
        )

        logline = clean_text(
            idea.get(
                "logline_roman_telugu"
            )
            or idea.get(
                "roman_telugu_logline"
            )
            or idea.get(
                "logline"
            )
        )

        if not title:
            continue

        normalized.append(
            {
                "rank": index,
                "high_ctr_title": title,
                "logline_roman_telugu": logline,
                "format": clean_text(
                    idea.get(
                        "format"
                    )
                ),
                "duration": clean_text(
                    idea.get(
                        "duration"
                    )
                ),
                "genre": clean_text(
                    idea.get(
                        "genre"
                    )
                ),
                "hook": clean_text(
                    idea.get(
                        "hook"
                    )
                ),
                "core_concept": clean_text(
                    idea.get(
                        "core_concept"
                    )
                    or idea.get(
                        "concept"
                    )
                ),
                "story_engine": clean_text(
                    idea.get(
                        "story_engine"
                    )
                ),
                "escalation": clean_text(
                    idea.get(
                        "escalation"
                    )
                ),
                "twist_or_payoff": clean_text(
                    idea.get(
                        "twist_or_payoff"
                    )
                    or idea.get(
                        "twist"
                    )
                    or idea.get(
                        "payoff"
                    )
                ),
                "thumbnail_concept": clean_text(
                    idea.get(
                        "thumbnail_concept"
                    )
                    or idea.get(
                        "thumbnail"
                    )
                ),
                "why_people_click": clean_text(
                    idea.get(
                        "why_people_click"
                    )
                ),
                "why_people_watch_till_end": clean_text(
                    idea.get(
                        "why_people_watch_till_end"
                    )
                    or idea.get(
                        "retention_reason"
                    )
                ),
                "shareability": clean_text(
                    idea.get(
                        "shareability"
                    )
                ),
                "production_difficulty": clean_text(
                    idea.get(
                        "production_difficulty"
                    )
                ),
                "ctr_score": safe_int(
                    idea.get(
                        "ctr_score"
                    )
                ),
                "originality_score": safe_int(
                    idea.get(
                        "originality_score"
                    )
                ),
                "retention_score": safe_int(
                    idea.get(
                        "retention_score"
                    )
                ),
                "overall_score": safe_int(
                    idea.get(
                        "overall_score"
                    )
                ),
            }
        )

    if not normalized:

        raise RuntimeError(
            "AI result contains no usable ideas."
        )

    return normalized


# ============================================================
# IDEA QUALITY RULES
# ============================================================

QUALITY_RULES = """

NON-NEGOTIABLE QUALITY RULES:

DO NOT CREATE SILLY IDEAS.

DO NOT create:
- generic 24-hour challenges
- generic prank videos
- generic reaction videos
- generic motivation
- generic haunted-house stories
- generic ghost stories
- random "what if" concepts
- copied movies
- copied viral videos
- fake-news style concepts
- meaningless shock bait
- childish concepts
- ideas that sound mysterious but have no story
- ideas that require impossible logic without explanation

EVERY IDEA MUST HAVE:

1. A familiar situation.
2. A surprising central concept.
3. A powerful curiosity gap.
4. A clear story engine.
5. Escalation.
6. A reveal, reversal, discovery or emotional payoff.
7. A strong visual moment.
8. A reason to watch until the end.
9. A reason to tell another person about the idea.

THE TARGET REACTION IS:

"WAH... WHAT AN IDEA!"

The viewer should immediately understand why
the concept is interesting.

The idea must be memorable.

Prefer:
- Indian everyday life
- Telugu culture
- technology
- money
- jobs
- family
- relationships
- cities
- transport
- social behavior
- hidden systems
- psychology
- real-world mysteries
- crime
- investigation
- unusual human stories
- emotional reversals
- clever experiments
- unexpected discoveries

Do not make every idea horror.

Use different genres.

Do not repeat the same story mechanism.

Do not simply change names and locations.

Every idea must feel independently valuable.
"""


# ============================================================
# AI PROMPT
# ============================================================

def build_ideas_prompt(
    section_name: str,
    trend_data: Dict[str, Any],
    trend_based: bool,
    format_type: str
) -> str:

    if trend_based:

        source_instruction = """
USE THE SUPPLIED CURRENT YOUTUBE TREND DATA.

Do NOT copy any title.

Do NOT copy any existing video's plot.

Instead identify:
- audience interest
- genre movement
- curiosity patterns
- title structures
- subjects
- emotional triggers
- formats
- storytelling mechanisms

Then transform those signals into ORIGINAL concepts.
"""

    else:

        source_instruction = """
THIS IS A GENERAL / NON-TREND SECTION.

Do NOT depend on current trending video titles.

Use general YouTube audience psychology,
storytelling principles, cultural observations,
human behavior and strong narrative mechanics.

The result must feel fresh and original.
"""

    if format_type == "Short":

        format_rules = """
FORMAT:

YouTube Shorts.

Target approximately:
30-180 seconds.

The first 1-2 seconds must immediately
create curiosity.

There must be:
HOOK -> ESCALATION -> REVEAL/PAYOFF.

The concept must be visually understandable.
"""

    else:

        format_rules = """
FORMAT:

YouTube long-form.

TARGET:
8-10 MINUTES.

The concept must support an actual story.

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

There must be a reason to keep watching
through every stage.
"""

    prompt = f"""
You are an elite YouTube creative director,
story producer, screenwriter and high-CTR strategist.

You understand Indian YouTube,
Telugu audiences,
global YouTube,
viewer psychology,
CTR,
retention,
shareability,
story structure
and thumbnail psychology.

SECTION:
{section_name}

FORMAT:
{format_type}

{source_instruction}

{format_rules}

{QUALITY_RULES}

REGIONAL REQUIREMENT:

Create ideas for BOTH:

INDIA:
Especially suitable for Indian/Telugu audiences
when appropriate.

WORLD:
Globally understandable and interesting.

Do not make the World ideas simply Indian ideas
translated into English.

Create genuinely different concepts.

IMPORTANT:

The first field shown for every idea must be:

HIGH CTR TITLE

The second field must be:

ROMAN TELUGU LOGLINE

The Roman Telugu logline must sound like natural
spoken Telugu typed in English letters.

Do NOT translate word-by-word.

Example style:

"Okka normal delivery order venaka unna secret ni
follow chesthu vellinappudu, hero tana life gurinchi
thanake teliyani oka nijam discover chestadu."

BAD:
"Man takes challenge and finds mystery."

GOOD:
"Prathi roju same route lo vellina oka cab driver
oka particular road ni enduku avoid chestunnado
telusukovadaniki follow ayithe, aa road gurinchi
telisina nijam tana life ni complete ga marchestundi."

VERY IMPORTANT:

The title must create a strong curiosity gap.

Do not reveal the entire story in the title.

The idea should make people say:

"WAH... IDI CHALA KOTTHAGA UNDI."

Generate exactly:
{IDEAS_PER_SECTION}

Return ONLY valid JSON.

Use this exact top-level structure:

{{
  "ideas": [
    {{
      "rank": 1,
      "region": "India",
      "high_ctr_title": "...",
      "logline_roman_telugu": "...",
      "format": "Short",
      "duration": "60 seconds",
      "genre": "...",
      "hook": "...",
      "core_concept": "...",
      "story_engine": "...",
      "escalation": "...",
      "twist_or_payoff": "...",
      "thumbnail_concept": "...",
      "why_people_click": "...",
      "why_people_watch_till_end": "...",
      "shareability": "...",
      "production_difficulty": "Easy",
      "ctr_score": 95,
      "originality_score": 95,
      "retention_score": 94,
      "overall_score": 95
    }}
  ]
}}

SCORING:

ctr_score:
How irresistible the title/concept is.

originality_score:
How fresh and non-generic the concept is.

retention_score:
How strongly the story makes viewers stay.

overall_score:
Overall YouTube potential.

Do NOT give fake 100 scores to everything.

Only use 90+ when the idea genuinely deserves it.

TREND DATA:

{json.dumps(
    trend_data,
    ensure_ascii=False,
    indent=2
)}
"""

    return prompt


# ============================================================
# GENERATE ONE IDEA SECTION
# ============================================================

def generate_idea_section(
    section_name: str,
    trend_data: Dict[str, Any],
    trend_based: bool,
    format_type: str
) -> List[Dict[str, Any]]:

    prompt = build_ideas_prompt(
        section_name=section_name,
        trend_data=trend_data,
        trend_based=trend_based,
        format_type=format_type
    )

    last_error = None

    for attempt in range(
        1,
        4
    ):

        try:

            raw = call_openrouter(
                prompt,
                attempt
            )

            parsed = extract_json_value(
                raw
            )

            ideas = normalize_ideas(
                parsed
            )

            # --------------------------------
            # Sort by overall score.
            # --------------------------------

            ideas = sorted(
                ideas,
                key=lambda x: (
                    safe_int(
                        x.get(
                            "overall_score"
                        )
                    ),
                    safe_int(
                        x.get(
                            "ctr_score"
                        )
                    ),
                    safe_int(
                        x.get(
                            "retention_score"
                        )
                    )
                ),
                reverse=True
            )

            for index, idea in enumerate(
                ideas,
                start=1
            ):

                idea["rank"] = index

            return ideas[
                :IDEAS_PER_SECTION
            ]

        except Exception as exc:

            last_error = exc

            print(
                f"AI attempt "
                f"{attempt} failed: "
                f"{type(exc).__name__}: "
                f"{exc}"
            )

            if attempt < 3:

                print(
                    "Retrying OpenRouter..."
                )

                time.sleep(
                    2 * attempt
                )

    raise RuntimeError(
        "OpenRouter failed after "
        "3 attempts: "
        f"{last_error}"
    )


# ============================================================
# RENDER IDEA
# ============================================================

def render_idea(
    idea: Dict[str, Any]
) -> str:

    lines = []

    lines.append(
        "HIGH CTR TITLE"
    )

    lines.append(
        idea.get(
            "high_ctr_title",
            ""
        )
    )

    lines.append("")

    lines.append(
        "LOG-LINE — ROMAN TELUGU"
    )

    lines.append(
        idea.get(
            "logline_roman_telugu",
            ""
        )
    )

    lines.append("")

    lines.append(
        f"Format: "
        f"{idea.get('format', '')}"
    )

    lines.append(
        f"Duration: "
        f"{idea.get('duration', '')}"
    )

    lines.append(
        f"Genre: "
        f"{idea.get('genre', '')}"
    )

    lines.append("")

    lines.append(
        "HOOK"
    )

    lines.append(
        idea.get(
            "hook",
            ""
        )
    )

    lines.append("")

    lines.append(
        "CORE CONCEPT"
    )

    lines.append(
        idea.get(
            "core_concept",
            ""
        )
    )

    lines.append("")

    lines.append(
        "STORY ENGINE"
    )

    lines.append(
        idea.get(
            "story_engine",
            ""
        )
    )

    lines.append("")

    lines.append(
        "ESCALATION"
    )

    lines.append(
        idea.get(
            "escalation",
            ""
        )
    )

    lines.append("")

    lines.append(
        "TWIST / PAYOFF"
    )

    lines.append(
        idea.get(
            "twist_or_payoff",
            ""
        )
    )

    lines.append("")

    lines.append(
        "THUMBNAIL CONCEPT"
    )

    lines.append(
        idea.get(
            "thumbnail_concept",
            ""
        )
    )

    lines.append("")

    lines.append(
        "WHY PEOPLE CLICK"
    )

    lines.append(
        idea.get(
            "why_people_click",
            ""
        )
    )

    lines.append("")

    lines.append(
        "WHY PEOPLE WATCH TILL END"
    )

    lines.append(
        idea.get(
            "why_people_watch_till_end",
            ""
        )
    )

    lines.append("")

    lines.append(
        "SHAREABILITY"
    )

    lines.append(
        idea.get(
            "shareability",
            ""
        )
    )

    lines.append("")

    lines.append(
        f"Production Difficulty: "
        f"{idea.get('production_difficulty', '')}"
    )

    lines.append(
        f"CTR Score: "
        f"{idea.get('ctr_score', 0)}/100"
    )

    lines.append(
        f"Originality Score: "
        f"{idea.get('originality_score', 0)}/100"
    )

    lines.append(
        f"Retention Score: "
        f"{idea.get('retention_score', 0)}/100"
    )

    lines.append(
        f"Overall Score: "
        f"{idea.get('overall_score', 0)}/100"
    )

    return "\n".join(
        lines
    )


# ============================================================
# MARKDOWN REPORT
# ============================================================

def build_markdown(
    india_report: Dict[str, Any],
    world_report: Dict[str, Any],
    genre_report: Dict[str, Any],
    idea_sections: Dict[str, List[Dict[str, Any]]]
) -> str:

    lines = []

    lines.append(
        "# YOUTUBE HIGH CTR IDEA GENERATOR"
    )

    lines.append("")

    lines.append(
        f"Generated: {now_iso()}"
    )

    lines.append("")

    lines.append(
        "=========================================="
    )

    lines.append(
        "1. INDIA YOUTUBE TRENDS"
    )

    lines.append(
        "=========================================="
    )

    india_format = india_report[
        "format_analysis"
    ]

    lines.append("")

    lines.append(
        f"Total videos: "
        f"{india_report['total_videos']}"
    )

    lines.append(
        f"Shorts detected: "
        f"{india_format['shorts_count']}"
    )

    lines.append(
        f"Long-form detected: "
        f"{india_format['long_form_count']}"
    )

    lines.append(
        f"8-10 minute videos detected: "
        f"{india_format['eight_to_ten_minute_count']}"
    )

    lines.append("")

    lines.append(
        "TOP INDIA SHORTS"
    )

    for index, video in enumerate(
        india_format[
            "top_shorts"
        ],
        start=1
    ):

        lines.append(
            f"{index}. "
            f"{video['title']} | "
            f"{video['genre']} | "
            f"{format_number(video['views'])} views"
        )

    lines.append("")

    lines.append(
        "TOP INDIA LONG-FORM 8-10 MIN"
    )

    for index, video in enumerate(
        india_format[
            "top_long_form_8_10_minutes"
        ],
        start=1
    ):

        lines.append(
            f"{index}. "
            f"{video['title']} | "
            f"{video['genre']} | "
            f"{video['duration_seconds']} sec | "
            f"{format_number(video['views'])} views"
        )

    lines.append("")

    lines.append(
        "=========================================="
    )

    lines.append(
        "2. WORLD YOUTUBE TRENDS"
    )

    lines.append(
        "=========================================="
    )

    world_format = world_report[
        "format_analysis"
    ]

    lines.append("")

    lines.append(
        f"Total videos: "
        f"{world_report['total_videos']}"
    )

    lines.append(
        f"Shorts detected: "
        f"{world_format['shorts_count']}"
    )

    lines.append(
        f"Long-form detected: "
        f"{world_format['long_form_count']}"
    )

    lines.append(
        f"8-10 minute videos detected: "
        f"{world_format['eight_to_ten_minute_count']}"
    )

    lines.append("")

    lines.append(
        "TOP WORLD SHORTS"
    )

    for index, video in enumerate(
        world_format[
            "top_shorts"
        ],
        start=1
    ):

        lines.append(
            f"{index}. "
            f"{video['title']} | "
            f"{video['genre']} | "
            f"{video['region']} | "
            f"{format_number(video['views'])} views"
        )

    lines.append("")

    lines.append(
        "TOP WORLD LONG-FORM 8-10 MIN"
    )

    for index, video in enumerate(
        world_format[
            "top_long_form_8_10_minutes"
        ],
        start=1
    ):

        lines.append(
            f"{index}. "
            f"{video['title']} | "
            f"{video['genre']} | "
            f"{video['region']} | "
            f"{video['duration_seconds']} sec"
        )

    lines.append("")

    lines.append(
        "=========================================="
    )

    lines.append(
        "3. YOUTUBE GENRE TRENDS"
    )

    lines.append(
        "=========================================="
    )

    lines.append("")

    lines.append(
        "SHORTS GENRE TRENDS"
    )

    for item in genre_report[
        "shorts"
    ][:15]:

        lines.append(
            f"- {item['genre']}: "
            f"{item['video_count']} videos "
            f"({item['percentage']}%)"
        )

    lines.append("")

    lines.append(
        "LONG-FORM GENRE TRENDS"
    )

    for item in genre_report[
        "long_form"
    ][:15]:

        lines.append(
            f"- {item['genre']}: "
            f"{item['video_count']} videos "
            f"({item['percentage']}%)"
        )

    # --------------------------------------------------------
    # IDEA SECTIONS
    # --------------------------------------------------------

    section_titles = [
        (
            "4. TREND-BASED SHORTS IDEAS",
            "trend_shorts"
        ),
        (
            "5. TREND-BASED LONG-FORM 8-10 MIN IDEAS",
            "trend_longform"
        ),
        (
            "6. GENERAL / NON-TREND SHORTS IDEAS",
            "general_shorts"
        ),
        (
            "7. GENERAL / NON-TREND LONG-FORM 8-10 MIN IDEAS",
            "general_longform"
        ),
    ]

    for title, key in section_titles:

        lines.append("")

        lines.append(
            "=========================================="
        )

        lines.append(
            title
        )

        lines.append(
            "=========================================="
        )

        lines.append("")

        for index, idea in enumerate(
            idea_sections.get(
                key,
                []
            ),
            start=1
        ):

            lines.append(
                f"## IDEA {index}"
            )

            lines.append("")

            lines.append(
                render_idea(
                    idea
                )
            )

            lines.append("")

            lines.append(
                "---"
            )

            lines.append("")

    return "\n".join(
        lines
    )


# ============================================================
# JSON SERIALIZATION
# ============================================================

def save_json(
    filename: str,
    data: Any
) -> Path:

    path = (
        OUTPUT_DIR
        / filename
    )

    path.write_text(
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    return path


def save_text(
    filename: str,
    content: str
) -> Path:

    path = (
        OUTPUT_DIR
        / filename
    )

    path.write_text(
        content,
        encoding="utf-8"
    )

    return path


# ============================================================
# RESEND EMAIL
# ============================================================

def send_email(
    markdown_path: Path,
    json_path: Path
) -> None:

    if not RESEND_API_KEY:
        print(
            "RESEND_API_KEY missing. "
            "Email skipped."
        )
        return

    if not FROM_EMAIL:
        print(
            "FROM_EMAIL missing. "
            "Email skipped."
        )
        return

    if not RECIPIENT_EMAIL:
        print(
            "RECIPIENT_EMAIL missing. "
            "Email skipped."
        )
        return

    markdown_data = base64.b64encode(
        markdown_path.read_bytes()
    ).decode(
        "utf-8"
    )

    json_data = base64.b64encode(
        json_path.read_bytes()
    ).decode(
        "utf-8"
    )

    today = datetime.now().strftime(
        "%Y-%m-%d"
    )

    payload = {
        "from": FROM_EMAIL,
        "to": [
            RECIPIENT_EMAIL
        ],
        "subject": (
            "YouTube High CTR Ideas - "
            f"{today}"
        ),
        "html": """
        <h2>YouTube High CTR Idea Generator</h2>

        <p>
        Your India + World YouTube trend analysis
        and high-CTR idea report is attached.
        </p>

        <p>
        The report contains:
        </p>

        <ul>
        <li>India YouTube trends</li>
        <li>World YouTube trends</li>
        <li>Genre trends</li>
        <li>Trend-based Shorts ideas</li>
        <li>Trend-based 8-10 minute ideas</li>
        <li>General/non-trend Shorts ideas</li>
        <li>General/non-trend 8-10 minute ideas</li>
        <li>Roman Telugu loglines</li>
        <li>High CTR scores</li>
        </ul>
        """,
        "attachments": [
            {
                "filename": (
                    markdown_path.name
                ),
                "content": markdown_data,
            },
            {
                "filename": (
                    json_path.name
                ),
                "content": json_data,
            },
        ],
    }

    headers = {
        "Authorization": (
            f"Bearer "
            f"{RESEND_API_KEY}"
        ),
        "Content-Type": (
            "application/json"
        ),
    }

    response = requests.post(
        RESEND_API_URL,
        headers=headers,
        json=payload,
        timeout=60,
    )

    if not response.ok:

        try:
            error = response.json()
        except Exception:
            error = response.text

        raise RuntimeError(
            "Resend email error "
            f"{response.status_code}: "
            f"{error}"
        )

    print(
        "Email sent successfully."
    )


# ============================================================
# ENVIRONMENT CHECK
# ============================================================

def check_environment() -> None:

    banner(
        "CHECKING ENVIRONMENT"
    )

    checks = {
        "OPENROUTER_API_KEY":
            OPENROUTER_API_KEY,

        "RESEND_API_KEY":
            RESEND_API_KEY,

        "FROM_EMAIL":
            FROM_EMAIL,

        "RECIPIENT_EMAIL":
            RECIPIENT_EMAIL,

        "YOUTUBE_API_KEY":
            YOUTUBE_API_KEY,
    }

    for name, value in checks.items():

        print(
            f"{name}: "
            f"{'OK' if value else 'MISSING'}"
        )

    required = [
        (
            "OPENROUTER_API_KEY",
            OPENROUTER_API_KEY
        ),
        (
            "YOUTUBE_API_KEY",
            YOUTUBE_API_KEY
        ),
    ]

    missing = [
        name
        for name, value
        in required
        if not value
    ]

    if missing:

        raise RuntimeError(
            "Missing required environment "
            "variables: "
            + ", ".join(
                missing
            )
        )

    print(
        "Environment check: OK"
    )


# ============================================================
# MAIN
# ============================================================

def main() -> None:

    banner(
        "STARTING YOUTUBE HIGH CTR IDEA GENERATOR"
    )

    check_environment()

    # --------------------------------------------------------
    # 1. INDIA
    # --------------------------------------------------------

    print(
        "1. Collecting India trends..."
    )

    india_videos = collect_india_trends()

    india_videos = score_videos(
        india_videos
    )

    india_report = build_trend_report(
        india_videos
    )

    # --------------------------------------------------------
    # 2. WORLD
    # --------------------------------------------------------

    print(
        "2. Collecting worldwide proxy trends..."
    )

    world_videos = collect_world_trends()

    world_videos = score_videos(
        world_videos
    )

    world_report = build_trend_report(
        world_videos
    )

    # --------------------------------------------------------
    # 3. GENRE
    # --------------------------------------------------------

    print(
        "3. Analysing YouTube genre trends..."
    )

    combined_videos = (
        india_videos
        + world_videos
    )

    genre_report = genre_analysis(
        combined_videos
    )

    # --------------------------------------------------------
    # SAVE RAW TREND DATA
    # --------------------------------------------------------

    trend_data = {
        "generated_at": now_iso(),
        "india": india_report,
        "world": world_report,
        "genre_trends": genre_report,
    }

    trend_json_path = save_json(
        "youtube_trend_analysis.json",
        trend_data
    )

    # --------------------------------------------------------
    # AI TREND DATA
    # --------------------------------------------------------

    ai_trend_data = {
        "india": {
            "shorts": india_report[
                "format_analysis"
            ][
                "top_shorts"
            ],
            "long_form_8_10_minutes":
                india_report[
                    "format_analysis"
                ][
                    "top_long_form_8_10_minutes"
                ],
            "genres":
                india_report[
                    "genre_trends"
                ],
            "title_patterns":
                india_report[
                    "title_patterns"
                ],
        },

        "world": {
            "shorts": world_report[
                "format_analysis"
            ][
                "top_shorts"
            ],
            "long_form_8_10_minutes":
                world_report[
                    "format_analysis"
                ][
                    "top_long_form_8_10_minutes"
                ],
            "genres":
                world_report[
                    "genre_trends"
                ],
            "title_patterns":
                world_report[
                    "title_patterns"
                ],
        },

        "combined_genre_trends":
            genre_report,
    }

    # --------------------------------------------------------
    # 4-7. AI IDEAS
    # --------------------------------------------------------

    print()
    print(
        "Generating HIGH CTR + YouTube ideas..."
    )

    idea_sections = {}

    # --------------------------------------------------------
    # 4. TREND SHORTS
    # --------------------------------------------------------

    print(
        "4. Generating trend-based Shorts..."
    )

    idea_sections[
        "trend_shorts"
    ] = generate_idea_section(
        section_name=(
            "Trend-Based Shorts - "
            "India + World"
        ),
        trend_data=ai_trend_data,
        trend_based=True,
        format_type="Short"
    )

    # --------------------------------------------------------
    # 5. TREND LONG FORM
    # --------------------------------------------------------

    print(
        "5. Generating trend-based "
        "8-10 minute long-form..."
    )

    idea_sections[
        "trend_longform"
    ] = generate_idea_section(
        section_name=(
            "Trend-Based Long-form 8-10 Minutes "
            "- India + World"
        ),
        trend_data=ai_trend_data,
        trend_based=True,
        format_type="Long-form"
    )

    # --------------------------------------------------------
    # 6. GENERAL SHORTS
    # --------------------------------------------------------

    print(
        "6. Generating general/non-trend Shorts..."
    )

    idea_sections[
        "general_shorts"
    ] = generate_idea_section(
        section_name=(
            "General YouTube Ideas "
            "Not Based On Current Trends "
            "- India + World"
        ),
        trend_data={
            "instruction": (
                "Do not use current trends."
            ),
            "audience_regions": [
                "India",
                "World"
            ],
        },
        trend_based=False,
        format_type="Short"
    )

    # --------------------------------------------------------
    # 7. GENERAL LONG FORM
    # --------------------------------------------------------

    print(
        "7. Generating general/non-trend "
        "8-10 minute long-form..."
    )

    idea_sections[
        "general_longform"
    ] = generate_idea_section(
        section_name=(
            "General YouTube Ideas "
            "Not Based On Current Trends "
            "- India + World "
            "- 8-10 Minutes"
        ),
        trend_data={
            "instruction": (
                "Do not use current trends."
            ),
            "audience_regions": [
                "India",
                "World"
            ],
        },
        trend_based=False,
        format_type="Long-form"
    )

    # --------------------------------------------------------
    # ALL IDEAS
    # --------------------------------------------------------

    ideas_output = {
        "generated_at": now_iso(),

        "requirements": [
            "India YouTube Trends",
            "World YouTube Trends",
            "YouTube Genre Trends",
            "Trend-Based Shorts",
            "Trend-Based Long-form 8-10 Minutes",
            "General Non-Trend Shorts",
            "General Non-Trend Long-form 8-10 Minutes",
        ],

        "quality_target": (
            "Very engaging, high CTR, "
            "original, memorable, "
            "WAH WHAT AN IDEA reaction"
        ),

        "roman_telugu": True,

        "sections": idea_sections,
    }

    ideas_json_path = save_json(
        "youtube_high_ctr_ideas.json",
        ideas_output
    )

    # --------------------------------------------------------
    # MARKDOWN
    # --------------------------------------------------------

    markdown = build_markdown(
        india_report=india_report,
        world_report=world_report,
        genre_report=genre_report,
        idea_sections=idea_sections,
    )

    markdown_path = save_text(
        "youtube_high_ctr_ideas.md",
        markdown
    )

    # --------------------------------------------------------
    # EMAIL
    # --------------------------------------------------------

    try:

        send_email(
            markdown_path,
            ideas_json_path
        )

    except Exception as exc:

        print(
            f"EMAIL WARNING: "
            f"{type(exc).__name__}: "
            f"{exc}"
        )

    # --------------------------------------------------------
    # FINISH
    # --------------------------------------------------------

    banner(
        "YOUTUBE HIGH CTR IDEA GENERATOR COMPLETED"
    )

    print(
        f"Trend JSON: "
        f"{trend_json_path}"
    )

    print(
        f"Ideas JSON: "
        f"{ideas_json_path}"
    )

    print(
        f"Markdown report: "
        f"{markdown_path}"
    )

    print()
    print(
        "SUCCESS"
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()
