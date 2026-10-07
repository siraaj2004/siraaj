"""
idea_generator.py
=================

YouTube High CTR Idea Generator

Output:
1. India YouTube Trends - Long-form + Shorts
2. World YouTube Trends - Long-form + Shorts
3. YouTube Genre Trends - Long-form + Shorts
4. Trend-based India/World Shorts Ideas
5. Trend-based India/World Long-form Ideas
6. General India/World Shorts Ideas
7. General India/World Long-form Ideas
8. Genre-combination High CTR Ideas

The generator is designed to:
- Avoid silly/generic ideas
- Avoid using meaningless trend keywords as video topics
- Detect entertainment sub-genres such as:
  Thriller, Comedy, Horror, Action, Mystery, Crime, Romance, Drama,
  Sci-Fi, Fantasy, Documentary, etc.
- Explain WHY a trend is working
- Generate strong hooks
- Generate Roman Telugu loglines
- Rank ideas using CTR/Retention/Originality/Visual Potential
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

# ============================================================
# OPTIONAL LLM SUPPORT
# ============================================================

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


# ============================================================
# CONFIG
# ============================================================

OUTPUT_DIR = os.getenv("OUTPUT_DIR", "output")
OUTPUT_FILE = os.getenv(
    "IDEA_OUTPUT_FILE",
    os.path.join(OUTPUT_DIR, "youtube_high_ctr_ideas.json"),
)

REPORT_FILE = os.getenv(
    "IDEA_REPORT_FILE",
    os.path.join(OUTPUT_DIR, "youtube_high_ctr_ideas.txt"),
)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()

# You can change this in GitHub Actions:
# LLM_MODEL=gpt-4o-mini
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")

# Number of ideas per section.
SHORT_IDEAS = int(os.getenv("SHORT_IDEAS", "8"))
LONG_IDEAS = int(os.getenv("LONG_IDEAS", "8"))
GENERAL_IDEAS = int(os.getenv("GENERAL_IDEAS", "8"))
GENRE_IDEAS = int(os.getenv("GENRE_IDEAS", "8"))

# ============================================================
# TREND DATA
# ============================================================
#
# The script first tries to read:
#
# output/trend_data.json
#
# OR:
#
# trend_data.json
#
# If your scraper uses another file, set:
#
# TREND_DATA_FILE=your_file.json
#
# The parser accepts many common structures.
# ============================================================

TREND_DATA_FILE = os.getenv("TREND_DATA_FILE", "").strip()


# ============================================================
# DATA CLASSES
# ============================================================

@dataclass
class Trend:
    name: str
    mentions: int = 0
    combined_views: float = 0.0
    avg_views: float = 0.0
    region: str = ""
    format: str = ""
    category: str = ""
    source_titles: List[str] = None

    def __post_init__(self):
        if self.source_titles is None:
            self.source_titles = []


@dataclass
class Idea:
    title: str
    region: str
    format: str
    genre: str
    logline_roman_telugu: str
    hook: str
    why_trending: str
    why_people_click: str
    visual_angle: str
    story_angle: str
    ctr_score: int
    retention_score: int
    originality_score: int
    visual_score: int
    overall_score: int
    trend_basis: str = ""


# ============================================================
# BASIC HELPERS
# ============================================================

def safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default

        if isinstance(value, bool):
            return int(value)

        if isinstance(value, (int, float)):
            return int(value)

        value = str(value).strip().replace(",", "")

        if not value:
            return default

        return int(float(value))

    except Exception:
        return default


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default

        if isinstance(value, bool):
            return float(value)

        if isinstance(value, (int, float)):
            return float(value)

        text = str(value).strip().lower()
        text = text.replace(",", "")

        multiplier = 1

        if text.endswith("k"):
            multiplier = 1_000
            text = text[:-1]

        elif text.endswith("m"):
            multiplier = 1_000_000
            text = text[:-1]

        elif text.endswith("b"):
            multiplier = 1_000_000_000
            text = text[:-1]

        return float(text) * multiplier

    except Exception:
        return default


def clean_text(value: Any) -> str:
    if value is None:
        return ""

    text = str(value).strip()

    text = re.sub(r"\s+", " ", text)

    return text


def slugify(text: str) -> str:
    text = text.lower().strip()

    text = re.sub(r"[^a-z0-9]+", "_", text)

    return text.strip("_")


def ensure_output_dir() -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)


# ============================================================
# TREND KEYWORD FILTERING
# ============================================================

# These are usually not good standalone story subjects.
GENERIC_WORDS = {
    "live",
    "day",
    "days",
    "today",
    "tomorrow",
    "new",
    "news",
    "official",
    "video",
    "videos",
    "watch",
    "full",
    "short",
    "shorts",
    "episode",
    "season",
    "part",
    "part 1",
    "part 2",
    "trailer",
    "teaser",
    "launch",
    "oct",
    "jan",
    "feb",
    "mar",
    "apr",
    "may",
    "jun",
    "jul",
    "aug",
    "sep",
    "nov",
    "dec",
    "sur",
    "letra",
    "lyrics",
    "song",
    "songs",
    "music",
    "hd",
    "4k",
    "reaction",
    "viral",
    "trend",
    "trending",
    "channel",
    "youtube",
    "instagram",
    "facebook",
    "twitter",
    "tiktok",
    "don't",
    "dont",
    "the",
    "and",
    "of",
    "for",
    "with",
    "this",
    "that",
}


def normalize_keyword(text: str) -> str:
    text = clean_text(text)

    text = re.sub(
        r"\b(official|full video|hd|4k|lyrics|lyric video)\b",
        "",
        text,
        flags=re.I,
    )

    text = re.sub(r"\s+", " ", text)

    return text.strip(" -_:|")


def is_meaningful_trend(name: str) -> bool:
    normalized = normalize_keyword(name)

    if not normalized:
        return False

    low = normalized.lower()

    if low in GENERIC_WORDS:
        return False

    if len(low) <= 2:
        return False

    # Dates / numbers alone are weak.
    if re.fullmatch(r"[\d\W]+", low):
        return False

    return True


# ============================================================
# ENTERTAINMENT GENRE DETECTION
# ============================================================

GENRE_KEYWORDS: Dict[str, List[str]] = {
    "Thriller": [
        "thriller",
        "suspense",
        "secret",
        "mystery",
        "hidden",
        "investigation",
        "investigate",
        "twist",
        "unknown",
    ],
    "Crime": [
        "crime",
        "criminal",
        "murder",
        "killer",
        "police",
        "gang",
        "robbery",
        "scam",
        "fraud",
        "case",
        "detective",
    ],
    "Horror": [
        "horror",
        "ghost",
        "haunted",
        "demon",
        "scary",
        "fear",
        "evil",
        "paranormal",
        "possessed",
    ],
    "Comedy": [
        "comedy",
        "funny",
        "comedy",
        "humor",
        "humour",
        "meme",
        "prank",
        "funny",
    ],
    "Action": [
        "action",
        "fight",
        "war",
        "battle",
        "army",
        "soldier",
        "combat",
        "chase",
    ],
    "Romance": [
        "love",
        "romance",
        "romantic",
        "couple",
        "relationship",
        "girlfriend",
        "boyfriend",
        "wedding",
    ],
    "Drama": [
        "drama",
        "family",
        "emotional",
        "mother",
        "father",
        "life",
        "story",
    ],
    "Gaming": [
        "minecraft",
        "roblox",
        "gta",
        "gaming",
        "gameplay",
        "fortnite",
        "pubg",
        "free fire",
        "valorant",
        "playstation",
        "xbox",
    ],
    "Music": [
        "music",
        "song",
        "songs",
        "singer",
        "album",
        "concert",
        "lyrics",
        "anirudh",
        "arijit",
    ],
    "Movies & Entertainment": [
        "movie",
        "film",
        "cinema",
        "trailer",
        "teaser",
        "actor",
        "actress",
        "jailer",
        "superstar",
        "bollywood",
        "tollywood",
        "kollywood",
    ],
    "Anime": [
        "anime",
        "manga",
        "crunchyroll",
        "one piece",
        "naruto",
        "dragon ball",
        "jujutsu",
        "demon slayer",
    ],
    "Sci-Fi": [
        "sci-fi",
        "science fiction",
        "space",
        "alien",
        "robot",
        "future",
        "ai",
        "artificial intelligence",
    ],
    "Technology": [
        "technology",
        "tech",
        "ai",
        "artificial intelligence",
        "iphone",
        "android",
        "robot",
        "software",
    ],
    "Education": [
        "education",
        "tutorial",
        "learn",
        "study",
        "exam",
        "course",
        "science",
    ],
}


def detect_genre(text: str) -> str:
    low = clean_text(text).lower()

    scores: Dict[str, int] = {}

    for genre, keywords in GENRE_KEYWORDS.items():
        score = 0

        for keyword in keywords:
            if keyword in low:
                score += 1

        if score:
            scores[genre] = score

    if not scores:
        return "Documentary / Curiosity"

    return max(scores, key=scores.get)


def detect_subgenre(text: str) -> str:
    genre = detect_genre(text)

    if genre == "Movies & Entertainment":
        low = text.lower()

        if any(x in low for x in [
            "murder",
            "killer",
            "police",
            "crime",
            "gang",
            "case",
        ]):
            return "Crime Thriller"

        if any(x in low for x in [
            "ghost",
            "horror",
            "haunted",
            "demon",
        ]):
            return "Horror"

        if any(x in low for x in [
            "funny",
            "comedy",
            "prank",
            "meme",
        ]):
            return "Comedy"

        if any(x in low for x in [
            "fight",
            "battle",
            "war",
            "action",
        ]):
            return "Action"

        if any(x in low for x in [
            "love",
            "romance",
            "couple",
        ]):
            return "Romance"

        return "Movie / Entertainment"

    return genre


# ============================================================
# TREND ANALYSIS
# ============================================================

def trend_strength(trend: Trend) -> float:
    """
    Combines:
    - mentions
    - combined views
    - average views

    Avoids relying on only one metric.
    """

    mentions_score = min(trend.mentions / 10, 10)

    views_score = min(
        trend.combined_views / 5_000_000,
        10,
    )

    avg_score = min(
        trend.avg_views / 1_000_000,
        10,
    )

    return (
        mentions_score * 0.35
        + views_score * 0.35
        + avg_score * 0.30
    )


def why_trending(trend: Trend) -> str:
    reasons = []

    if trend.mentions >= 5:
        reasons.append(
            f"repeated strongly across the collected videos ({trend.mentions} mentions)"
        )
    elif trend.mentions >= 2:
        reasons.append(
            f"appears repeatedly in the collected videos ({trend.mentions} mentions)"
        )

    if trend.combined_views >= 10_000_000:
        reasons.append(
            f"the related videos accumulated about {trend.combined_views / 1_000_000:.1f}M views"
        )
    elif trend.combined_views >= 1_000_000:
        reasons.append(
            f"the related videos accumulated about {trend.combined_views / 1_000_000:.1f}M views"
        )

    if trend.avg_views >= 1_000_000:
        reasons.append(
            f"average views are around {trend.avg_views / 1_000_000:.1f}M"
        )

    if not reasons:
        reasons.append(
            "it has a measurable presence in the collected YouTube dataset"
        )

    return "; ".join(reasons) + "."


# ============================================================
# TREND DATA PARSER
# ============================================================

def find_possible_list(data: Any) -> List[Any]:
    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        candidates = [
            data.get("trends"),
            data.get("videos"),
            data.get("items"),
            data.get("results"),
            data.get("data"),
        ]

        for candidate in candidates:
            if isinstance(candidate, list):
                return candidate

        # Search recursively.
        for value in data.values():
            result = find_possible_list(value)

            if result:
                return result

    return []


def parse_trend_item(
    item: Any,
    region: str,
    format_name: str,
) -> Trend | None:

    if isinstance(item, str):
        name = normalize_keyword(item)

        if not is_meaningful_trend(name):
            return None

        return Trend(
            name=name,
            region=region,
            format=format_name,
        )

    if not isinstance(item, dict):
        return None

    name = (
        item.get("trend")
        or item.get("keyword")
        or item.get("name")
        or item.get("title")
        or item.get("query")
        or ""
    )

    name = normalize_keyword(name)

    if not is_meaningful_trend(name):
        return None

    mentions = (
        item.get("mentions")
        or item.get("count")
        or item.get("frequency")
        or item.get("occurrences")
        or 0
    )

    combined_views = (
        item.get("combined_views")
        or item.get("views")
        or item.get("total_views")
        or 0
    )

    avg_views = (
        item.get("avg_views")
        or item.get("average_views")
        or item.get("mean_views")
        or 0
    )

    source_titles = (
        item.get("source_titles")
        or item.get("titles")
        or []
    )

    if isinstance(source_titles, str):
        source_titles = [source_titles]

    return Trend(
        name=name,
        mentions=safe_int(mentions),
        combined_views=safe_float(combined_views),
        avg_views=safe_float(avg_views),
        region=region,
        format=format_name,
        category=clean_text
