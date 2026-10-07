"""
idea_generator.py
YOUTUBE HIGH CTR IDEA GENERATOR
7-SECTION VERSION

Fixes:
1. Never prints "No trend analysis returned" when usable video data exists.
2. Safely separates INDIA / WORLD and LONG-FORM / SHORTS.
3. Generates genre trends from video titles/descriptions.
4. Generates trend-based Shorts and Long-form ideas.
5. Keeps the exact 7-section report structure.
6. Handles empty/malformed YouTube API records safely.
7. Generates a PDF-ready report through generate_report_pdf().
"""

from __future__ import annotations

import os
import re
import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

# Optional PDF dependency
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, PageBreak
    )
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib import colors
    REPORTLAB_AVAILABLE = True
except Exception:
    REPORTLAB_AVAILABLE = False


# ============================================================
# CONFIG
# ============================================================

OUTPUT_DIR = os.getenv("OUTPUT_DIR", "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

REPORT_MD = os.path.join(OUTPUT_DIR, "youtube_high_ctr_report.md")
REPORT_JSON = os.path.join(OUTPUT_DIR, "youtube_high_ctr_report.json")
REPORT_PDF = os.path.join(OUTPUT_DIR, "youtube_high_ctr_report.pdf")

LONG_FORM_MINUTES = 6
SHORTS_MAX_SECONDS = 180

# Broad genre dictionary. A video can match more than one keyword,
# but the strongest matching genre is used for reporting.
GENRES = {
    "Gaming": [
        "gaming", "gameplay", "minecraft", "gta", "bgmi", "pubg",
        "free fire", "valorant", "fortnite", "roblox", "geometry dash",
        "among us", "esports", "game"
    ],
    "Movies & Trailers": [
        "trailer", "movie", "film", "cinema", "actor", "actress",
        "jailer", "teaser", "review", "tollywood", "bollywood",
        "kollywood", "hollywood"
    ],
    "Music": [
        "song", "music", "album", "singer", "lyrics", "dj", "remix",
        "concert", "official audio"
    ],
    "Technology & AI": [
        "ai", "artificial intelligence", "chatgpt", "openai", "gemini",
        "technology", "tech", "robot", "iphone", "android", "coding"
    ],
    "News & Current Affairs": [
        "news", "breaking", "update", "politics", "election", "government",
        "war", "protest", "today"
    ],
    "Entertainment": [
        "viral", "funny", "comedy", "challenge", "reaction", "celebrity",
        "prank", "entertainment", "fun"
    ],
    "Education": [
        "tutorial", "how to", "learn", "course", "education", "explained",
        "science", "math", "study", "exam"
    ],
    "Lifestyle": [
        "vlog", "travel", "food", "fitness", "gym", "fashion", "lifestyle",
        "routine", "cooking", "restaurant"
    ],
    "Documentary & Story": [
        "story", "documentary", "investigation", "mystery", "history",
        "psychology", "true story", "explained"
    ],
}


# ============================================================
# 1. NORMALIZE / CLASSIFY VIDEO DATA
# ============================================================

def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(float(str(value).replace(",", "").strip()))
    except Exception:
        return default


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def normalize_video(item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Accepts many common YouTube API/result formats.
    """
    if not isinstance(item, dict):
        return {
            "title": "",
            "description": "",
            "views": 0,
            "likes": 0,
            "comments": 0,
            "duration_seconds": 0,
            "duration_minutes": 0,
            "region": "",
            "url": "",
            "published_at": "",
        }

    snippet = item.get("snippet") or {}
    statistics = item.get("statistics") or {}
    content = item.get("contentDetails") or {}

    title = (
        item.get("title")
        or snippet.get("title")
        or item.get("video_title")
        or ""
    )

    description = (
        item.get("description")
        or snippet.get("description")
        or ""
    )

    views = _safe_int(
        item.get("views", statistics.get("viewCount", 0))
    )
    likes = _safe_int(
        item.get("likes", statistics.get("likeCount", 0))
    )
    comments = _safe_int(
        item.get("comments", statistics.get("commentCount", 0))
    )

    duration_seconds = _safe_int(
        item.get("duration_seconds", item.get("duration", 0))
    )

    # Some collectors provide minutes instead of seconds.
    if duration_seconds <= 0 and item.get("duration_minutes"):
        duration_seconds = int(
            _safe_float(item.get("duration_minutes")) * 60
        )

    region = clean_text(
        item.get("region")
        or item.get("country")
        or item.get("market")
        or ""
    ).upper()

    url = (
        item.get("url")
        or item.get("video_url")
        or item.get("link")
        or ""
    )

    published_at = (
        item.get("published_at")
        or snippet.get("publishedAt")
        or ""
    )

    result = {
        "title": clean_text(title),
        "description": clean_text(description),
        "views": views,
        "likes": likes,
        "comments": comments,
        "duration_seconds": duration_seconds,
        "duration_minutes": round(duration_seconds / 60, 2)
        if duration_seconds else 0,
        "region": region,
        "url": clean_text(url),
        "published_at": clean_text(published_at),
    }

    result["format"] = classify_format(result)
    result["genre"] = detect_genre(result)

    return result


def classify_format(video: Dict[str, Any]) -> str:
    """
    Shorts:
      <= 180 sec when duration is known.
    Long-form:
      > 180 sec.
    Unknown duration:
      infer from title/description.
    """
    seconds = _safe_int(video.get("duration_seconds", 0))

    if seconds > 0:
        return "Shorts" if seconds <= SHORTS_MAX_SECONDS else "Long-form"

    text = (
        clean_text(video.get("title"))
        + " "
        + clean_text(video.get("description"))
    ).lower()

    short_markers = [
        "#shorts", "#short", "youtube shorts", "short video"
    ]

    if any(x in text for x in short_markers):
        return "Shorts"

    # If duration is unknown and no Shorts marker exists,
    # treat it as long-form instead of dropping the record.
    return "Long-form"


def detect_genre(video: Dict[str, Any]) -> str:
    text = (
        clean_text(video.get("title"))
        + " "
        + clean_text(video.get("description"))
    ).lower()

    scores = {}

    for genre, keywords in GENRES.items():
        score = 0
        for keyword in keywords:
            if keyword.lower() in text:
                score += 1
        scores[genre] = score

    best_genre, best_score = max(
        scores.items(),
        key=lambda x: x[1]
    )

    return best_genre if best_score > 0 else "Other"


def normalize_videos(videos: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    output = []

    for item in videos or []:
        video = normalize_video(item)

        if video["title"]:
            output.append(video)

    return output


# ============================================================
# 2. TREND ANALYSIS ENGINE
# ============================================================

def format_views(number: int) -> str:
    if number >= 1_000_000_000:
        return f"{number / 1_000_000_000:.1f}B"
    if number >= 1_000_000:
        return f"{number / 1_000_000:.1f}M"
    if number >= 1_000:
        return f"{number / 1_000:.1f}K"
    return str(number)


def extract_topics(videos: List[Dict[str, Any]], limit: int = 12) -> List[Dict[str, Any]]:
    """
    Extract recurring title phrases/keywords.
    This is deliberately local and deterministic so the report does not
    depend on an LLM returning a particular JSON structure.
    """
    stopwords = {
        "the", "and", "for", "with", "this", "that", "from", "your",
        "you", "are", "was", "has", "have", "will", "how", "why",
        "what", "when", "where", "who", "into", "after", "before",
        "just", "new", "official", "video", "short", "shorts", "full",
        "part", "episode", "today", "2026", "2025", "india", "world"
    }

    counts = Counter()
    views_by_word = defaultdict(int)

    for video in videos:
        title = video["title"].lower()
        words = re.findall(r"[a-zA-Z0-9']{3,}", title)

        unique_words = set(
            word for word in words
            if word not in stopwords and not word.isdigit()
        )

        for word in unique_words:
            counts[word] += 1
            views_by_word[word] += video["views"]

    rows = []

    for word, count in counts.most_common():
        if count < 2 and len(videos) > 10:
            continue

        rows.append({
            "topic": word.title(),
            "mentions": count,
            "total_views": views_by_word[word],
            "avg_views": round(
                views_by_word[word] / max(count, 1)
            ),
        })

        if len(rows) >= limit:
            break

    return rows


def analyze_trends(videos: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Core fix:
    Always returns a valid analysis dictionary.
    Never returns None just because one category is empty.
    """
    videos = normalize_videos(videos)

    by_region = defaultdict(list)
    by_format = defaultdict(list)
    by_genre = defaultdict(list)

    for video in videos:
        region = video["region"] or "UNKNOWN"
        by_region[region].append(video)
        by_format[video["format"]].append(video)
        by_genre[video["genre"]].append(video)

    def trend_rows(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        topics = extract_topics(items)

        # Genre fallback if titles have weak keyword overlap.
        if not topics and items:
            genre_counts = Counter(x["genre"] for x in items)
            topics = [
                {
                    "topic": genre,
                    "mentions": count,
                    "total_views": sum(
                        x["views"] for x in items if x["genre"] == genre
                    ),
                    "avg_views": round(
                        sum(
                            x["views"] for x in items
                            if x["genre"] == genre
                        ) / max(count, 1)
                    )
                }
                for genre, count in genre_counts.most_common(10)
            ]

        return topics

    india = [
        x for x in videos
        if x["region"] in {"IN", "INDIA", "IN-INDIA"}
    ]

    world = [
        x for x in videos
        if x["region"] not in {"IN", "INDIA", "IN-INDIA"}
    ]

    # If the collector didn't provide region metadata, split based on
    # explicit India/world markers rather than returning empty analysis.
    if not india and not world and videos:
        india_markers = [
            "india", "indian", "telugu", "hindi", "tamil",
            "kannada", "malayalam", "bollywood", "tollywood",
            "kollywood", "bgmi"
        ]

        for video in videos:
            text = (
                video["title"] + " " + video["description"]
            ).lower()

            if any(marker in text for marker in india_markers):
                india.append(video)
            else:
                world.append(video)

    result = {
        "total_videos": len(videos),
        "india_count": len(india),
        "world_count": len(world),

        "india_long": [
            x for x in india if x["format"] == "Long-form"
        ],
        "india_shorts": [
            x for x in india if x["format"] == "Shorts"
        ],

        "world_long": [
            x for x in world if x["format"] == "Long-form"
        ],
        "world_shorts": [
            x for x in world if x["format"] == "Shorts"
        ],

        "genre_long": [
            x for x in videos if x["format"] == "Long-form"
        ],
        "genre_shorts": [
            x for x in videos if x["format"] == "Shorts"
        ],

        "india_long_topics": trend_rows([
            x for x in india if x["format"] == "Long-form"
        ]),
        "india_short_topics": trend_rows([
            x for x in india if x["format"] == "Shorts"
        ]),
        "world_long_topics": trend_rows([
            x for x in world if x["format"] == "Long-form"
        ]),
        "world_short_topics": trend_rows([
            x for x in world if x["format"] == "Shorts"
        ]),
        "genre_long_topics": trend_rows([
            x for x in videos if x["format"] == "Long-form"
        ]),
        "genre_short_topics": trend_rows([
            x for x in videos if x["format"] == "Shorts"
        ]),
    }

    return result


# ============================================================
# 3. IDEA GENERATION
# ============================================================

def top_video(items: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not items:
        return None

    return max(
        items,
        key=lambda x: (
            x.get("views", 0),
            x.get("likes", 0),
            x.get("comments", 0)
        )
    )


def make_hook(topic: str, fmt: str) -> str:
    if fmt == "Shorts":
        return f"Ee trend lo chala mandi miss ayina secret idhe — {topic}."
    return f"Millions mandi {topic} chustunnaru. Kani actual reason enti?"


def make_roman_logline(topic: str, region: str, fmt: str) -> str:
    if fmt == "Shorts":
        return (
            f"{region} YouTube lo '{topic}' trend ni 45–60 seconds lo "
            f"breakdown chesi, audience ki immediate ga interesting ayye "
            f"hidden reason ni reveal cheyyadam."
        )

    return (
        f"{region} YouTube lo '{topic}' trend enduku explode ayyindo "
        f"8–10 minutes documentary/story format lo investigate chesi, "
        f"trend venuka unna pattern, audience psychology and creator "
        f"opportunity ni reveal cheyyadam."
    )


def score_idea(topic: str, videos: List[Dict[str, Any]]) -> Tuple[int, int, int]:
    if not videos:
        return 6, 6, 6

    total_views = sum(x["views"] for x in videos)
    avg_views = total_views / max(len(videos), 1)

    if avg_views >= 1_000_000:
        ctr = 9
    elif avg_views >= 250_000:
        ctr = 8
    elif avg_views >= 50_000:
        ctr = 7
    else:
        ctr = 6

    retention = 9 if len(videos) >= 5 else 8
    originality = 8 if len(videos) <= 20 else 7

    return ctr, retention, originality


def build_ideas(
    topics: List[Dict[str, Any]],
    source_videos: List[Dict[str, Any]],
    region: str,
    fmt: str,
    limit: int
) -> List[Dict[str, Any]]:
    ideas = []

    if not topics:
        # IMPORTANT: no empty analysis message.
        # Generate a useful fallback from available videos.
        candidates = sorted(
            source_videos,
            key=lambda x: x["views"],
            reverse=True
        )[:limit]

        for video in candidates:
            topic = video["title"][:80]
            ctr, retention, originality = score_idea(
                topic, [video]
            )

            ideas.append({
                "title": f"Why {topic} Is Trending Right Now",
                "region": region,
                "format": fmt,
                "logline": make_roman_logline(
                    topic, region, fmt
                ),
                "hook": make_hook(topic, fmt),
                "why": (
                    f"Existing video already has "
                    f"{format_views(video['views'])} views. "
                    f"This idea changes the angle from simple "
                    f"consumption to analysis/storytelling."
                ),
                "ctr": ctr,
                "retention": retention,
                "originality": originality,
            })

        return ideas

    for row in topics[:limit]:
        topic = row["topic"]
        ctr, retention, originality = score_idea(
            topic, source_videos
        )

        title = (
            f"{topic}: The Hidden Reason Everyone Is Watching"
            if fmt == "Long-form"
            else f"{topic}: The 1 Secret You Missed"
        )

        ideas.append({
            "title": title,
            "region": region,
            "format": fmt,
            "logline": make_roman_logline(
                topic, region, fmt
            ),
            "hook": make_hook(topic, fmt),
            "why": (
                f"'{topic}' appeared {row['mentions']} times in the "
                f"collected trend set with approximately "
                f"{format_views(row['total_views'])} combined views."
            ),
            "ctr": ctr,
            "retention": retention,
            "originality": originality,
        })

    return ideas


def generate_short_ideas(analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
    source = (
        analysis["india_shorts"]
        + analysis["world_shorts"]
    )

    ideas = []

    ideas.extend(build_ideas(
        analysis["india_short_topics"],
        analysis["india_shorts"],
        "India",
        "Shorts",
        4
    ))

    ideas.extend(build_ideas(
        analysis["world_short_topics"],
        analysis["world_shorts"],
        "World",
        "Shorts",
        4
    ))

    # General fallback if there are not enough regional Shorts.
    if len(ideas) < 8:
        ideas.extend(build_ideas(
            analysis["genre_short_topics"],
            source,
            "India/World",
            "Shorts",
            8 - len(ideas)
        ))

    return ideas[:8]


def generate_long_ideas(analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
    source = (
        analysis["india_long"]
        + analysis["world_long"]
    )

    ideas = []

    ideas.extend(build_ideas(
        analysis["india_long_topics"],
        analysis["india_long"],
        "India",
        "Long-form",
        4
    ))

    ideas.extend(build_ideas(
        analysis["world_long_topics"],
        analysis["world_long"],
        "World",
        "Long-form",
        4
    ))

    if len(ideas) < 8:
        ideas.extend(build_ideas(
            analysis["genre_long_topics"],
            source,
            "India/World",
            "Long-form",
            8 - len(ideas)
        ))

    return ideas[:8]


# ============================================================
# 4. GENERAL CREATIVE IDEAS
# ============================================================

GENERAL_SHORTS = [
    (
        "The Indian Village With a Strange Rule Nobody Questions",
        "India"
    ),
    (
        "The Airport Where One Normal Rule Is Completely Different",
        "World"
    ),
    (
        "The Railway Station With a Story Nobody Expects",
        "India"
    ),
    (
        "The Job That Sounds Fake But Actually Exists",
        "World"
    ),
    (
        "The Temple Kitchen That Feeds Thousands Every Day",
        "India"
    ),
    (
        "The City That Solved One Problem Without Cars",
        "World"
    ),
    (
        "The Letter That Took Decades to Reach Its Destination",
        "India"
    ),
    (
        "The Museum With a Rule You Would Never Expect",
        "World"
    ),
]

GENERAL_LONG = [
    (
        "The Hidden Story Behind One of India's Most Unusual Places",
        "India"
    ),
    (
        "Why This Strange Place Became an Internet Mystery",
        "World"
    ),
    (
        "I Investigated a Rule That Sounds Completely Impossible",
        "India"
    ),
    (
        "The Job Nobody Talks About But Someone Has to Do",
        "World"
    ),
    (
        "Inside India's Giant Free-Meal System",
        "India"
    ),
    (
        "The City That Designed Life Without Depending on Cars",
        "World"
    ),
    (
        "The Lost Letter That Took Decades to Arrive",
        "India"
    ),
    (
        "The Museum You Can Only Experience Once",
        "World"
    ),
]


def general_short_ideas() -> List[Dict[str, Any]]:
    result = []

    for title, region in GENERAL_SHORTS:
        result.append({
            "title": title,
            "region": region,
            "logline": (
                f"{title} gurinchi 45–60 seconds lo curiosity-driven "
                f"story cheppi, final reveal tho video ni close cheyyadam."
            ),
            "hook": f"First 2 seconds: '{title} — idi nijam ani nammutara?'",
            "ctr": "N/A",
            "retention": "N/A",
            "originality": "N/A",
        })

    return result


def general_long_ideas() -> List[Dict[str, Any]]:
    result = []

    for title, region in GENERAL_LONG:
        result.append({
            "title": title,
            "region": region,
            "logline": (
                f"{title} ni 8–10 minutes documentary/story format lo "
                f"research, visual evidence and human angle tho explain cheyyadam."
            ),
            "hook": (
                f"Millions of people may know the place, "
                f"but very few know the real story behind it."
            ),
            "ctr": "N/A",
            "retention": "N/A",
            "originality": "N/A",
        })

    return result


# ============================================================
# 5. MARKDOWN REPORT — EXACT 7 SECTIONS
# ============================================================

def md_escape(text: Any) -> str:
    return clean_text(text).replace("\n", " ")


def render_trend_table(rows: List[Dict[str, Any]]) -> str:
    if not rows:
        return (
            "_Not enough structured trend data for this category. "
            "The generator continued using available videos and fallback analysis._"
        )

    lines = [
        "| Trend | Mentions | Combined Views | Avg Views |",
        "|---|---:|---:|---:|",
    ]

    for row in rows[:10]:
        lines.append(
            f"| {md_escape(row['topic'])} | "
            f"{row['mentions']} | "
            f"{format_views(row['total_views'])} | "
            f"{format_views(row['avg_views'])} |"
        )

    return "\n".join(lines)


def render_idea(idea: Dict[str, Any], number: int) -> str:
    return (
        f"### {number}. {md_escape(idea['title'])}\n\n"
        f"**Region:** {md_escape(idea['region'])}\n"
        f"**Roman Telugu Logline:** {md_escape(idea['logline'])}\n"
        f"**Hook:** {md_escape(idea['hook'])}\n"
        f"**Why it can work:** {md_escape(idea.get('why', 'Trend-based opportunity.'))}\n"
        f"**Scores:** CTR {idea['ctr']}/10 · "
        f"Retention {idea['retention']}/10 · "
        f"Originality {idea['originality']}/10\n"
    )


def build_markdown_report(
    analysis: Dict[str, Any],
    short_ideas: List[Dict[str, Any]],
    long_ideas: List[Dict[str, Any]],
) -> str:

    now = datetime.now(timezone.utc).strftime(
        "%Y-%m-%d %H:%M UTC"
    )

    top_source = top_video(
        analysis["india_long"]
        + analysis["world_long"]
        + analysis["india_shorts"]
        + analysis["world_shorts"]
    )

    if top_source:
        top_title = top_source["title"]
        top_views = format_views(top_source["views"])
    else:
        top_title = "Trend data is still limited"
        top_views = "N/A"

    # Choose a top idea from generated ideas.
    all_trend_ideas = short_ideas + long_ideas

    if all_trend_ideas:
        top_idea = max(
            all_trend_ideas,
            key=lambda x: (
                _safe_int(x["ctr"]),
                _safe_int(x["retention"]),
                _safe_int(x["originality"])
            )
        )
    else:
        top_idea = {
            "title": top_title,
            "logline": "Available trend data is limited."
        }

    parts = []

    # --------------------------------------------------------
    # 0 Header / Top CTR
    # --------------------------------------------------------

    parts.append(
        "# YOUTUBE HIGH CTR IDEA GENERATOR\n\n"
        f"Generated: {now}\n\n"
        "## 🔥 TOP HIGH CTR IDEA\n\n"
        f"### {md_escape(top_idea['title'])}\n\n"
        f"**Roman Telugu Logline:** "
        f"{md_escape(top_idea.get('logline', ''))}\n\n"
        f"**Current source signal:** {md_escape(top_title)} "
        f"({top_views} views in collected data)\n\n"
        "---\n"
    )

    # --------------------------------------------------------
    # 1 India trends
    # --------------------------------------------------------

    parts.append(
        "# 1. INDIA YOUTUBE TRENDS\n\n"
        f"Videos collected: {analysis['india_count']}\n\n"
        "## India Long-form Trends\n\n"
        + render_trend_table(analysis["india_long_topics"])
        + "\n\n"
        "## India Shorts Trends\n\n"
        + render_trend_table(analysis["india_short_topics"])
        + "\n\n"
    )

    # --------------------------------------------------------
    # 2 World trends
    # --------------------------------------------------------

    parts.append(
        "# 2. WORLD YOUTUBE TRENDS\n\n"
        f"Videos collected: {analysis['world_count']}\n\n"
        "## World Long-form Trends\n\n"
        + render_trend_table(analysis["world_long_topics"])
        + "\n\n"
        "## World Shorts Trends\n\n"
        + render_trend_table(analysis["world_short_topics"])
        + "\n\n"
    )

    # --------------------------------------------------------
    # 3 Genre trends
    # --------------------------------------------------------

    parts.append(
        "# 3. YOUTUBE GENRE TRENDS\n\n"
        "## Long-form Genre Trends\n\n"
        + render_trend_table(analysis["genre_long_topics"])
        + "\n\n"
        "## Shorts Genre Trends\n\n"
        + render_trend_table(analysis["genre_short_topics"])
        + "\n\n"
    )

    # --------------------------------------------------------
    # 4 Trend-based Shorts
    # --------------------------------------------------------

    parts.append(
        "# 4. INDIA/WORLD TREND-BASED SHORTS IDEAS\n\n"
    )

    if short_ideas:
        for i, idea in enumerate(short_ideas, 1):
            parts.append(render_idea(idea, i))
    else:
        parts.append(
            "_No usable trend records were collected. "
            "General creative ideas are provided in Section 6._\n"
        )

    # --------------------------------------------------------
    # 5 Trend-based Long-form
    # --------------------------------------------------------

    parts.append(
        "# 5. INDIA/WORLD TREND-BASED LONG-FORM IDEAS\n\n"
        "**Target duration: 8-10 minutes**\n\n"
    )

    if long_ideas:
        for i, idea in enumerate(long_ideas, 1):
            parts.append(render_idea(idea, i))
    else:
        parts.append(
            "_No usable trend records were collected. "
            "General creative ideas are provided in Section 7._\n"
        )

    # --------------------------------------------------------
    # 6 General Shorts
    # --------------------------------------------------------

    parts.append(
        "# 6. INDIA/WORLD GENERAL SHORTS IDEAS\n\n"
        "**These are NOT based directly on the current trend list.**\n\n"
    )

    for i, idea in enumerate(general_short_ideas(), 1):
        parts.append(render_idea(idea, i))

    # --------------------------------------------------------
    # 7 General Long-form
    # --------------------------------------------------------

    parts.append(
        "# 7. INDIA/WORLD GENERAL LONG-FORM IDEAS\n\n"
        "**These are NOT based directly on the current trend list.**\n"
        "**Target duration: 8-10 minutes**\n\n"
    )

    for i, idea in enumerate(general_long_ideas(), 1):
        parts.append(render_idea(idea, i))

    parts.append(
        "---\n\n"
        "# CREATIVE STANDARD\n\n"
        "Ideas prioritize curiosity, emotional stakes, originality, "
        "visual potential, retention and honest high CTR rather than "
        "generic challenge/reaction concepts.\n"
    )

    return "\n".join(parts)


# ============================================================
# 6. PDF GENERATOR
# ============================================================

def markdown_to_pdf(markdown_text: str, output_path: str) -> None:
    if not REPORTLAB_AVAILABLE:
        raise RuntimeError(
            "ReportLab is required. Install it with: pip install reportlab"
        )

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
        title="YouTube High CTR Idea Generator",
        author="YouTube High CTR Idea Generator",
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Title"],
        fontSize=20,
        leading=24,
        alignment=TA_CENTER,
        spaceAfter=18,
    )

    h1 = ParagraphStyle(
        "H1",
        parent=styles["Heading1"],
        fontSize=15,
        leading=19,
        spaceBefore=14,
        spaceAfter=8,
    )

    h2 = ParagraphStyle(
        "H2",
        parent=styles["Heading2"],
        fontSize=12,
        leading=15,
        spaceBefore=10,
        spaceAfter=6,
    )

    body = ParagraphStyle(
        "Body",
        parent=styles["BodyText"],
        fontSize=9.2,
        leading=13,
        spaceAfter=6,
    )

    story = []

    # Simple Markdown-ish parser.
    for raw_line in markdown_text.splitlines():
        line = raw_line.strip()

        if not line:
            story.append(Spacer(1, 5))
            continue

        # Remove markdown separators.
        if line in {"---", "\\---"}:
            story.append(Spacer(1, 8))
            continue

        if line.startswith("# "):
            text = line[2:].replace("&", "&amp;")
            story.append(Paragraph(text, title_style))
            continue

        if line.startswith("## "):
            text = line[3:].replace("&", "&amp;")
            story.append(Paragraph(text, h1))
            continue

        if line.startswith("### "):
            text = line[4:].replace("&", "&amp;")
            story.append(Paragraph(text, h2))
            continue

        # Ignore markdown table separator rows.
        if re.fullmatch(r"\|?[\s:\-|]+\|?", line):
            continue

        # Basic table rows become readable text in PDF.
        if line.startswith("|"):
            cells = [
                x.strip()
                for x in line.strip("|").split("|")
            ]
            table_text = "  •  ".join(cells)
            table_text = (
                table_text
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
            )
            story.append(Paragraph(table_text, body))
            continue

        # Basic bold conversion.
        text = (
            line.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        text = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", text)

        story.append(Paragraph(text, body))

    doc.build(story)


# ============================================================
# 7. PUBLIC ENTRY POINT
# ============================================================

def generate_report(
    videos: List[Dict[str, Any]],
    create_pdf: bool = True
) -> Dict[str, str]:

    normalized = normalize_videos(videos)

    analysis = analyze_trends(normalized)

    short_ideas = generate_short_ideas(analysis)
    long_ideas = generate_long_ideas(analysis)

    markdown = build_markdown_report(
        analysis,
        short_ideas,
        long_ideas
    )

    with open(
        REPORT_MD,
        "w",
        encoding="utf-8"
    ) as file:
        file.write(markdown)

    with open(
        REPORT_JSON,
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            {
                "generated_at": datetime.now(
                    timezone.utc
                ).isoformat(),
                "analysis": analysis,
                "short_ideas": short_ideas,
                "long_ideas": long_ideas,
            },
            file,
            ensure_ascii=False,
            indent=2,
            default=str,
        )

    if create_pdf:
        markdown_to_pdf(
            markdown,
            REPORT_PDF
        )

    print("=" * 60)
    print("YOUTUBE HIGH CTR IDEA GENERATOR")
    print("=" * 60)
    print(f"Videos processed : {len(normalized)}")
    print(f"India videos     : {analysis['india_count']}")
    print(f"World videos     : {analysis['world_count']}")
    print(f"Shorts ideas     : {len(short_ideas)}")
    print(f"Long-form ideas  : {len(long_ideas)}")
    print(f"Markdown         : {REPORT_MD}")
    print(f"JSON             : {REPORT_JSON}")

    if create_pdf:
        print(f"PDF              : {REPORT_PDF}")

    print("=" * 60)

    return {
        "markdown": REPORT_MD,
        "json": REPORT_JSON,
        "pdf": REPORT_PDF if create_pdf else "",
    }


# ============================================================
# COMPATIBILITY HELPERS
# ============================================================

def run(videos: List[Dict[str, Any]]) -> Dict[str, str]:
    """
    Compatibility wrapper for existing app.py files.
    """
    return generate_report(videos, create_pdf=True)


def main(videos: Optional[List[Dict[str, Any]]] = None) -> Dict[str, str]:
    """
    If another collector imports this file, call main(videos).

    If this file is executed directly, it also looks for:
      output/videos.json
      videos.json
    """
    if videos is None:
        candidates = [
            os.path.join(OUTPUT_DIR, "videos.json"),
            "videos.json",
        ]

        loaded = []

        for path in candidates:
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as file:
                        data = json.load(file)

                    if isinstance(data, dict):
                        loaded = (
                            data.get("videos")
                            or data.get("items")
                            or data.get("results")
                            or []
                        )
                    elif isinstance(data, list):
                        loaded = data

                    break
                except Exception as exc:
                    print(f"WARNING: Could not read {path}: {exc}")

        videos = loaded

    return generate_report(
        videos or [],
        create_pdf=True
    )


if __name__ == "__main__":
    main()
