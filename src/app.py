"""
src/app.py
YOUTUBE HIGH CTR IDEA GENERATOR
7-SECTION, OPENROUTER-SAFE VERSION

ROOT FIXES FOR THE PREVIOUS FAILURE:
- OpenRouter malformed JSON NEVER stops the workflow.
- OpenRouter HTTP 402 NEVER stops the workflow.
- OpenRouter is called at most ONCE.
- If OpenRouter fails, local deterministic trend analysis + idea generation runs.
- YouTube API data is still used for current trends.
- Final PDF is ALWAYS generated when ReportLab is installed.
- Final email is attempted after the PDF is created.
- The final report keeps exactly 7 numbered sections.

Required .env:
YOUTUBE_API_KEY=...
OPENROUTER_API_KEY=...
RESEND_API_KEY=...
FROM_EMAIL=...
RECIPIENT_EMAIL=...

Optional:
OPENROUTER_MODEL=z-ai/glm-5.3-flash
WORLD_COUNTRIES=US,GB,CA,AU,DE,FR,JP,KR,BR,MX
OUTPUT_DIR=output
"""

from __future__ import annotations

import html
import json
import os
import re
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# CONFIG
# ============================================================

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "").strip()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "").strip()
FROM_EMAIL = os.getenv("FROM_EMAIL", "").strip()
RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL", "").strip()

OPENROUTER_MODEL = os.getenv(
    "OPENROUTER_MODEL",
    "z-ai/glm-5.3-flash",
).strip()

WORLD_COUNTRIES = [
    x.strip().upper()
    for x in os.getenv(
        "WORLD_COUNTRIES",
        "US,GB,CA,AU,DE,FR,JP,KR,BR,MX",
    ).split(",")
    if x.strip()
]

OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "output"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

TODAY_UTC = datetime.now(timezone.utc).strftime("%Y-%m-%d")
REPORT_TIME = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

PDF_PATH = OUTPUT_DIR / f"YouTube_High_CTR_{TODAY_UTC}.pdf"
MD_PATH = OUTPUT_DIR / f"YouTube_High_CTR_{TODAY_UTC}.md"
JSON_PATH = OUTPUT_DIR / f"YouTube_High_CTR_{TODAY_UTC}.json"

YOUTUBE_URL = "https://www.googleapis.com/youtube/v3/videos"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
RESEND_URL = "https://api.resend.com/emails"

REQUEST_TIMEOUT = 45

# YouTube category IDs.
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
    "29": "Nonprofits & Activism",
}

GENRE_KEYWORDS = {
    "Gaming": [
        "minecraft", "gta", "bgmi", "pubg", "free fire", "valorant",
        "fortnite", "roblox", "geometry dash", "among us", "gaming",
        "gameplay", "esports", "game",
    ],
    "Movies & Trailers": [
        "trailer", "teaser", "movie", "film", "cinema", "jailer",
        "actor", "actress", "review", "tollywood", "bollywood",
        "kollywood", "hollywood",
    ],
    "Music": [
        "song", "music", "lyrics", "singer", "album", "remix",
        "official audio", "concert",
    ],
    "Technology & AI": [
        "ai", "chatgpt", "gemini", "openai", "technology", "tech",
        "robot", "iphone", "android", "coding", "software",
    ],
    "News & Current Affairs": [
        "news", "breaking", "politics", "election", "government",
        "update", "today", "war", "protest",
    ],
    "Entertainment": [
        "comedy", "funny", "reaction", "challenge", "prank", "viral",
        "celebrity", "entertainment",
    ],
    "Education": [
        "tutorial", "how to", "learn", "education", "explained",
        "science", "math", "study", "exam",
    ],
    "Lifestyle": [
        "vlog", "travel", "food", "fitness", "gym", "fashion",
        "lifestyle", "routine", "cooking",
    ],
    "Documentary & Story": [
        "documentary", "story", "mystery", "history", "psychology",
        "investigation", "true story", "explained",
    ],
}

STOPWORDS = {
    "the", "and", "for", "with", "this", "that", "from", "your",
    "you", "are", "was", "has", "have", "will", "what", "when",
    "where", "who", "why", "how", "into", "after", "before",
    "just", "new", "official", "video", "videos", "short", "shorts",
    "full", "part", "episode", "today", "2026", "2025", "india",
    "world",
}


# ============================================================
# SECTION A — ENVIRONMENT / BASIC HELPERS
# ============================================================

def require_env() -> None:
    print("=" * 60)
    print("CHECKING ENVIRONMENT")
    print("=" * 60)

    checks = {
        "OPENROUTER_API_KEY": OPENROUTER_API_KEY,
        "RESEND_API_KEY": RESEND_API_KEY,
        "FROM_EMAIL": FROM_EMAIL,
        "RECIPIENT_EMAIL": RECIPIENT_EMAIL,
        "YOUTUBE_API_KEY": YOUTUBE_API_KEY,
    }

    for name, value in checks.items():
        print(f"{name}: {'OK' if value else 'MISSING'}")

    if not YOUTUBE_API_KEY:
        raise RuntimeError("YOUTUBE_API_KEY is missing.")

    if not RESEND_API_KEY:
        print("WARNING: RESEND_API_KEY missing. PDF will still be created.")

    if not FROM_EMAIL or not RECIPIENT_EMAIL:
        print(
            "WARNING: FROM_EMAIL or RECIPIENT_EMAIL missing. "
            "Email will be skipped."
        )

    print("Environment check: OK")


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(str(value).replace(",", "").strip()))
    except Exception:
        return default


def clean_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def format_views(value: int) -> str:
    if value >= 1_000_000_000:
        return f"{value / 1_000_000_000:.1f}B"
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if value >= 1_000:
        return f"{value / 1_000:.1f}K"
    return str(value)


def parse_iso_duration(value: str) -> int:
    if not value:
        return 0

    match = re.fullmatch(
        r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?",
        value,
    )

    if not match:
        return 0

    hours = safe_int(match.group(1))
    minutes = safe_int(match.group(2))
    seconds = safe_int(match.group(3))

    return hours * 3600 + minutes * 60 + seconds


def classify_format(video: dict[str, Any]) -> str:
    seconds = safe_int(video.get("duration_seconds"))

    if seconds:
        return "Shorts" if seconds <= 180 else "Long-form"

    text = (
        clean_text(video.get("title"))
        + " "
        + clean_text(video.get("description"))
    ).lower()

    if "#shorts" in text or "#short" in text:
        return "Shorts"

    return "Long-form"


def detect_genre(video: dict[str, Any]) -> str:
    category = clean_text(video.get("category_name"))

    if category:
        category_lower = category.lower()

        if category_lower == "gaming":
            return "Gaming"
        if category_lower == "music":
            return "Music"
        if category_lower == "comedy":
            return "Entertainment"
        if category_lower in {
            "film & animation",
            "entertainment",
        }:
            return "Movies & Entertainment"
        if category_lower == "science & technology":
            return "Technology & AI"
        if category_lower == "education":
            return "Education"

    text = (
        clean_text(video.get("title"))
        + " "
        + clean_text(video.get("description"))
    ).lower()

    scores = {}

    for genre, keywords in GENRE_KEYWORDS.items():
        scores[genre] = sum(
            1 for keyword in keywords if keyword in text
        )

    best = max(scores, key=scores.get)

    return best if scores[best] > 0 else "Other"


# ============================================================
# SECTION B — YOUTUBE COLLECTION
# ============================================================

def collect_country(country_code: str, max_results: int = 50) -> list[dict]:
    print(
        f"Collecting YouTube mostPopular data: {country_code}"
    )

    params = {
        "part": "snippet,statistics,contentDetails",
        "chart": "mostPopular",
        "regionCode": country_code,
        "maxResults": min(max_results, 50),
        "key": YOUTUBE_API_KEY,
    }

    response = requests.get(
        YOUTUBE_URL,
        params=params,
        timeout=REQUEST_TIMEOUT,
    )

    print(f"YouTube HTTP status: {response.status_code}")

    if response.status_code != 200:
        try:
            detail = response.json()
        except Exception:
            detail = response.text[:1000]

        raise RuntimeError(
            f"YouTube API failed for {country_code}: "
            f"HTTP {response.status_code}: {detail}"
        )

    data = response.json()
    videos = []

    for item in data.get("items", []):
        snippet = item.get("snippet", {})
        stats = item.get("statistics", {})
        details = item.get("contentDetails", {})

        category_id = clean_text(
            snippet.get("categoryId")
        )

        video = {
            "video_id": clean_text(item.get("id")),
            "title": clean_text(snippet.get("title")),
            "description": clean_text(
                snippet.get("description")
            )[:1000],
            "channel": clean_text(
                snippet.get("channelTitle")
            ),
            "published_at": clean_text(
                snippet.get("publishedAt")
            ),
            "category_id": category_id,
            "category_name": CATEGORY_NAMES.get(
                category_id,
                "",
            ),
            "view_count": safe_int(
                stats.get("viewCount")
            ),
            "like_count": safe_int(
                stats.get("likeCount")
            ),
            "comment_count": safe_int(
                stats.get("commentCount")
            ),
            "duration": clean_text(
                details.get("duration")
            ),
            "duration_seconds": parse_iso_duration(
                details.get("duration", "")
            ),
            "region": country_code,
            "url": (
                "https://www.youtube.com/watch?v="
                + clean_text(item.get("id"))
            ),
        }

        video["format"] = classify_format(video)
        video["genre"] = detect_genre(video)

        if video["title"]:
            videos.append(video)

    print(f"Collected {len(videos)} videos.")
    return videos


def collect_all_trends() -> tuple[list[dict], list[dict]]:
    print("1. Collecting India trends...")
    india = collect_country("IN", 50)

    print("2. Collecting worldwide proxy trends...")
    world = []

    for country in WORLD_COUNTRIES:
        try:
            world.extend(
                collect_country(country, 50)
            )
        except Exception as exc:
            print(
                f"WARNING: {country} collection failed: {exc}"
            )

    return india, world


# ============================================================
# SECTION C — DETERMINISTIC TREND ANALYSIS
# ============================================================

def topic_rows(
    videos: list[dict],
    limit: int = 10,
) -> list[dict]:
    counts = Counter()
    total_views = defaultdict(int)
    titles = defaultdict(list)

    for video in videos:
        words = set(
            re.findall(
                r"[A-Za-z0-9']{3,}",
                video["title"].lower(),
            )
        )

        for word in words:
            if word in STOPWORDS or word.isdigit():
                continue

            counts[word] += 1
            total_views[word] += video["view_count"]
            titles[word].append(video["title"])

    rows = []

    for word, count in counts.most_common():
        # A recurring word is more useful than a one-off word.
        if count < 2 and len(videos) >= 10:
            continue

        rows.append({
            "topic": word.title(),
            "mentions": count,
            "combined_views": total_views[word],
            "avg_views": round(
                total_views[word] / max(count, 1)
            ),
            "example_title": titles[word][0],
        })

        if len(rows) >= limit:
            break

    return rows


def genre_rows(
    videos: list[dict],
    limit: int = 10,
) -> list[dict]:
    groups = defaultdict(list)

    for video in videos:
        groups[video["genre"]].append(video)

    rows = []

    for genre, items in sorted(
        groups.items(),
        key=lambda pair: sum(
            x["view_count"] for x in pair[1]
        ),
        reverse=True,
    ):
        total = sum(
            x["view_count"] for x in items
        )

        rows.append({
            "topic": genre,
            "mentions": len(items),
            "combined_views": total,
            "avg_views": round(
                total / max(len(items), 1)
            ),
        })

        if len(rows) >= limit:
            break

    return rows


def analyze_trends(
    india: list[dict],
    world: list[dict],
) -> dict[str, Any]:
    all_videos = india + world

    india_long = [
        x for x in india if x["format"] == "Long-form"
    ]
    india_shorts = [
        x for x in india if x["format"] == "Shorts"
    ]

    world_long = [
        x for x in world if x["format"] == "Long-form"
    ]
    world_shorts = [
        x for x in world if x["format"] == "Shorts"
    ]

    analysis = {
        "india_count": len(india),
        "world_count": len(world),
        "total_count": len(all_videos),

        "india_long": india_long,
        "india_shorts": india_shorts,
        "world_long": world_long,
        "world_shorts": world_shorts,

        "india_long_topics": topic_rows(
            india_long
        ),
        "india_short_topics": topic_rows(
            india_shorts
        ),
        "world_long_topics": topic_rows(
            world_long
        ),
        "world_short_topics": topic_rows(
            world_shorts
        ),

        "genre_long": genre_rows(
            [
                x for x in all_videos
                if x["format"] == "Long-form"
            ]
        ),
        "genre_shorts": genre_rows(
            [
                x for x in all_videos
                if x["format"] == "Shorts"
            ]
        ),
    }

    return analysis


# ============================================================
# SECTION D — OPENROUTER SAFE AI LAYER
# ============================================================

def extract_json(text: str) -> Any:
    """
    Handles:
    - normal JSON
    - ```json ... ```
    - extra text before/after JSON
    """
    if not text:
        raise ValueError("Empty AI response.")

    cleaned = text.strip()

    cleaned = re.sub(
        r"^```(?:json)?\s*",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"\s*```$",
        "",
        cleaned,
    ).strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    first_obj = cleaned.find("{")
    last_obj = cleaned.rfind("}")

    if first_obj >= 0 and last_obj > first_obj:
        candidate = cleaned[first_obj:last_obj + 1]

        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    first_array = cleaned.find("[")
    last_array = cleaned.rfind("]")

    if first_array >= 0 and last_array > first_array:
        candidate = cleaned[first_array:last_array + 1]

        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    raise ValueError("AI returned malformed JSON.")


def build_ai_prompt(
    analysis: dict[str, Any],
) -> str:
    def compact(rows: list[dict]) -> str:
        return json.dumps(
            rows[:10],
            ensure_ascii=False,
        )

    return f"""
You are a professional YouTube content strategist.

Use the supplied CURRENT YouTube API trend analysis.
Do not invent current view counts.

Return ONLY valid JSON.
No markdown.
No code fences.

JSON shape:
{{
  "top_idea": {{
    "title": "...",
    "logline": "...",
    "why": "..."
  }},
  "shorts": [
    {{
      "title": "...",
      "region": "India or World",
      "logline": "...",
      "hook": "...",
      "why": "...",
      "ctr": 1,
      "retention": 1,
      "originality": 1
    }}
  ],
  "longform": [
    {{
      "title": "...",
      "region": "India or World",
      "logline": "...",
      "hook": "...",
      "why": "...",
      "ctr": 1,
      "retention": 1,
      "originality": 1
    }}
  ],
  "general_shorts": [
    {{
      "title": "...",
      "region": "India or World",
      "logline": "...",
      "hook": "...",
      "ctr": "N/A",
      "retention": "N/A",
      "originality": "N/A"
    }}
  ],
  "general_longform": [
    {{
      "title": "...",
      "region": "India or World",
      "logline": "...",
      "hook": "...",
      "ctr": "N/A",
      "retention": "N/A",
      "originality": "N/A"
    }}
  ]
}}

Requirements:
- shorts: exactly 8
- longform: exactly 8
- general_shorts: exactly 8
- general_longform: exactly 8
- Roman Telugu loglines.
- Long-form ideas should target 8-10 minutes.
- Prefer solo-creator-friendly ideas.
- Avoid fabricated current trend claims.

INDIA LONG:
{compact(analysis["india_long_topics"])}

INDIA SHORTS:
{compact(analysis["india_short_topics"])}

WORLD LONG:
{compact(analysis["world_long_topics"])}

WORLD SHORTS:
{compact(analysis["world_short_topics"])}

GENRE LONG:
{compact(analysis["genre_long"])}

GENRE SHORTS:
{compact(analysis["genre_shorts"])}
""".strip()


def call_openrouter_once(
    analysis: dict[str, Any],
) -> dict[str, Any] | None:
    """
    CRITICAL:
    Only ONE OpenRouter request.
    402 / malformed JSON / timeout => local fallback.
    """
    if not OPENROUTER_API_KEY:
        print(
            "OpenRouter key missing. "
            "Using local generator."
        )
        return None

    prompt = build_ai_prompt(analysis)

    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {
                "role": "user",
                "content": prompt,
            }
        ],
        "temperature": 0.7,
        "max_tokens": 9000,
    }

    headers = {
        "Authorization": (
            f"Bearer {OPENROUTER_API_KEY}"
        ),
        "Content-Type": "application/json",
        "HTTP-Referer": (
            "https://github.com/"
        ),
        "X-Title": (
            "YouTube High CTR Idea Generator"
        ),
    }

    print("OPENROUTER REQUEST | Attempt: 1")

    try:
        response = requests.post(
            OPENROUTER_URL,
            headers=headers,
            json=payload,
            timeout=90,
        )

        print(
            f"OpenRouter HTTP status: "
            f"{response.status_code}"
        )

        if response.status_code == 402:
            print(
                "OpenRouter 402 detected. "
                "Skipping ALL further OpenRouter retries."
            )
            print(
                "Reason: in-flight budget exhausted. "
                "Using local generator."
            )
            return None

        if response.status_code != 200:
            print(
                "OpenRouter failed. "
                "Using local generator."
            )
            return None

        data = response.json()

        choices = data.get("choices") or []

        if not choices:
            print(
                "OpenRouter returned no choices. "
                "Using local generator."
            )
            return None

        message = choices[0].get("message") or {}
        content = message.get("content")

        if isinstance(content, list):
            content = "".join(
                str(x.get("text", ""))
                for x in content
                if isinstance(x, dict)
            )

        content = clean_text(content)

        print(
            f"AI response length: "
            f"{len(content)} characters"
        )

        if not content:
            print(
                "OpenRouter returned empty content. "
                "Using local generator."
            )
            return None

        try:
            result = extract_json(content)
        except Exception as exc:
            print(
                f"AI JSON parsing failed: {exc}"
            )
            print(
                "Using local generator instead."
            )
            return None

        if not isinstance(result, dict):
            print(
                "AI JSON root is not an object. "
                "Using local generator."
            )
            return None

        print("OpenRouter SUCCESS")
        print(
            "AI result accepted. "
            "Local validation will still run."
        )

        return result

    except requests.RequestException as exc:
        print(
            f"OpenRouter request error: {exc}"
        )
        print(
            "Using local generator."
        )
        return None
    except Exception as exc:
        print(
            f"OpenRouter unexpected error: {exc}"
        )
        print(
            "Using local generator."
        )
        return None


# ============================================================
# SECTION E — LOCAL FALLBACK IDEA GENERATOR
# ============================================================

def best_topic(
    rows: list[dict],
    fallback: str,
) -> str:
    if rows:
        return clean_text(
            rows[0].get("topic")
        ) or fallback

    return fallback


def score_from_rows(
    rows: list[dict],
) -> tuple[int, int, int]:
    if not rows:
        return 7, 7, 8

    views = sum(
        safe_int(x.get("combined_views"))
        for x in rows[:5]
    )

    if views >= 10_000_000:
        ctr = 9
    elif views >= 2_000_000:
        ctr = 8
    elif views >= 500_000:
        ctr = 7
    else:
        ctr = 6

    return ctr, 8, 8


def local_trend_ideas(
    analysis: dict[str, Any],
) -> tuple[list[dict], list[dict]]:
    shorts = []
    longform = []

    short_sources = [
        (
            "India",
            analysis["india_short_topics"],
        ),
        (
            "World",
            analysis["world_short_topics"],
        ),
    ]

    long_sources = [
        (
            "India",
            analysis["india_long_topics"],
        ),
        (
            "World",
            analysis["world_long_topics"],
        ),
    ]

    # -----------------------------
    # Trend Shorts
    # -----------------------------
    for region, rows in short_sources:
        for row in rows:
            topic = best_topic(
                [row],
                "YouTube Trend",
            )

            ctr, retention, originality = (
                score_from_rows([row])
            )

            shorts.append({
                "title": (
                    f"{topic}: The Secret "
                    f"Everyone Missed"
                ),
                "region": region,
                "logline": (
                    f"{region} YouTube lo "
                    f"'{topic}' trend enduku "
                    f"attention techukundo 45–60 "
                    f"seconds lo hidden reason tho "
                    f"explain cheyyadam."
                ),
                "hook": (
                    f"'{topic}' lo meeru miss ayina "
                    f"oka detail undi — 3 seconds lo "
                    f"chudandi."
                ),
                "why": (
                    f"Collected trend data lo "
                    f"'{topic}' {row['mentions']} "
                    f"sarlu kanipinchindi and "
                    f"combined views approximately "
                    f"{format_views(row['combined_views'])}."
                ),
                "ctr": ctr,
                "retention": retention,
                "originality": originality,
            })

    # -----------------------------
    # Trend Long-form
    # -----------------------------
    for region, rows in long_sources:
        for row in rows:
            topic = best_topic(
                [row],
                "YouTube Trend",
            )

            ctr, retention, originality = (
                score_from_rows([row])
            )

            longform.append({
                "title": (
                    f"Why {topic} Is Exploding "
                    f"on YouTube"
                ),
                "region": region,
                "logline": (
                    f"{region} YouTube lo "
                    f"'{topic}' enduku explode "
                    f"ayyindo 8–10 minutes "
                    f"documentary-style story lo "
                    f"audience psychology, creator "
                    f"strategy and visual examples "
                    f"tho investigate cheyyadam."
                ),
                "hook": (
                    f"Millions mandi '{topic}' "
                    f"chustunnaru. Kani actual "
                    f"reason enti?"
                ),
                "why": (
                    f"Current collected data lo "
                    f"'{topic}' repeated trend "
                    f"signal ga kanipinchindi."
                ),
                "ctr": ctr,
                "retention": 9,
                "originality": originality,
            })

    # Ensure exactly 8 if possible.
    return shorts[:8], longform[:8]


def local_general_shorts() -> list[dict]:
    ideas = [
        (
            "The Indian Village With a Rule Nobody Expects",
            "India",
        ),
        (
            "The Job That Sounds Fake But Actually Exists",
            "World",
        ),
        (
            "The Railway Station With a Strange Tradition",
            "India",
        ),
        (
            "The City That Solved One Problem Without Cars",
            "World",
        ),
        (
            "The Temple Kitchen That Feeds Thousands",
            "India",
        ),
        (
            "The Museum You Can Only Visit Once",
            "World",
        ),
        (
            "The Letter That Took Decades to Arrive",
            "India",
        ),
        (
            "The Airport With One Very Strange Rule",
            "World",
        ),
    ]

    result = []

    for title, region in ideas:
        result.append({
            "title": title,
            "region": region,
            "logline": (
                f"{title} gurinchi 45–60 seconds "
                f"curiosity-driven Roman Telugu "
                f"story tho final reveal varaku "
                f"audience ni hold cheyyadam."
            ),
            "hook": (
                f"'{title}' — idi nijam ani "
                f"first lo meeru nammaru."
            ),
            "why": (
                "Evergreen curiosity + visual "
                "storytelling angle."
            ),
            "ctr": "N/A",
            "retention": "N/A",
            "originality": "N/A",
        })

    return result


def local_general_longform() -> list[dict]:
    ideas = [
        (
            "The Hidden Story Behind India's Most Unusual Place",
            "India",
        ),
        (
            "I Investigated a Rule That Sounds Impossible",
            "World",
        ),
        (
            "Inside India's Giant Free-Meal System",
            "India",
        ),
        (
            "The Job Nobody Talks About",
            "World",
        ),
        (
            "The City That Designed Life Without Cars",
            "World",
        ),
        (
            "The Lost Letter That Took Decades to Arrive",
            "India",
        ),
        (
            "The Museum With a Lifetime Entry Rule",
            "World",
        ),
        (
            "The Strange Railway Story Nobody Tells",
            "India",
        ),
    ]

    result = []

    for title, region in ideas:
        result.append({
            "title": title,
            "region": region,
            "logline": (
                f"{title} ni 8–10 minutes "
                f"documentary/story format lo "
                f"research, visual evidence and "
                f"human angle tho explain cheyyadam."
            ),
            "hook": (
                "Ee story lo first 30 seconds "
                "lo oka question untundi; "
                "answer final varaku reveal kaadu."
            ),
            "why": (
                "Evergreen documentary + curiosity "
                "format with strong retention potential."
            ),
            "ctr": "N/A",
            "retention": "N/A",
            "originality": "N/A",
        })

    return result


def validate_ai_result(
    ai: dict[str, Any] | None,
    fallback_short: list[dict],
    fallback_long: list[dict],
) -> tuple[
    list[dict],
    list[dict],
    list[dict],
    list[dict],
]:
    """
    AI is optional.
    Every missing/invalid AI section is replaced locally.
    """
    if not isinstance(ai, dict):
        return (
            fallback_short,
            fallback_long,
            local_general_shorts(),
            local_general_longform(),
        )

    def valid_list(
        key: str,
        fallback: list[dict],
    ) -> list[dict]:
        value = ai.get(key)

        if not isinstance(value, list):
            return fallback

        clean = []

        for item in value:
            if not isinstance(item, dict):
                continue

            title = clean_text(
                item.get("title")
            )

            if not title:
                continue

            item["title"] = title
            item["region"] = (
                clean_text(item.get("region"))
                or "India/World"
            )
            item["logline"] = (
                clean_text(item.get("logline"))
                or "Curiosity-driven YouTube idea."
            )
            item["hook"] = (
                clean_text(item.get("hook"))
                or "You will not expect the final reveal."
            )
            item["why"] = (
                clean_text(item.get("why"))
                or "Strong curiosity and retention potential."
            )

            clean.append(item)

        return clean if clean else fallback

    return (
        valid_list("shorts", fallback_short),
        valid_list("longform", fallback_long),
        valid_list(
            "general_shorts",
            local_general_shorts(),
        ),
        valid_list(
            "general_longform",
            local_general_longform(),
        ),
    )


# ============================================================
# SECTION F — 7-SECTION REPORT
# ============================================================

def trend_table(
    rows: list[dict],
) -> list[str]:
    lines = [
        "| Trend | Mentions | Combined Views | Avg Views |",
        "|---|---:|---:|---:|",
    ]

    if not rows:
        lines.append(
            "| No repeated keyword signal | 0 | 0 | 0 |"
        )
        return lines

    for row in rows[:10]:
        lines.append(
            "| "
            + str(row["topic"])
            + " | "
            + str(row["mentions"])
            + " | "
            + format_views(
                safe_int(row["combined_views"])
            )
            + " | "
            + format_views(
                safe_int(row["avg_views"])
            )
            + " |"
        )

    return lines


def render_idea(
    idea: dict,
    number: int,
) -> str:
    return (
        f"### {number}. {idea['title']}\n\n"
        f"**Region:** {idea['region']}\n"
        f"**Roman Telugu Logline:** "
        f"{idea['logline']}\n\n"
        f"**Hook:** {idea['hook']}\n\n"
        f"**Why it can work:** {idea['why']}\n\n"
        f"**Scores:** CTR {idea.get('ctr', 'N/A')}/10 · "
        f"Retention {idea.get('retention', 'N/A')}/10 · "
        f"Originality {idea.get('originality', 'N/A')}/10\n"
    )


def build_report(
    analysis: dict[str, Any],
    shorts: list[dict],
    longform: list[dict],
    general_shorts: list[dict],
    general_longform: list[dict],
    top_idea: dict,
) -> str:

    parts = []

    parts.append(
        "# YOUTUBE HIGH CTR IDEA GENERATOR\n\n"
        f"Generated: {REPORT_TIME}\n\n"
        "## 🔥 TOP HIGH CTR IDEA\n\n"
        f"### {top_idea['title']}\n\n"
        f"**Roman Telugu Logline:** "
        f"{top_idea.get('logline', '')}\n\n"
        f"**Why people click:** "
        f"{top_idea.get('why', '')}\n\n"
        "---\n\n"
    )

    # ========================================================
    # 1
    # ========================================================
    parts.append(
        "# 1. INDIA YOUTUBE TRENDS\n\n"
        f"Videos collected: {analysis['india_count']}\n\n"
        "## India Long-form Trends\n\n"
    )

    parts.extend(
        x + "\n"
        for x in trend_table(
            analysis["india_long_topics"]
        )
    )

    parts.append(
        "\n## India Shorts Trends\n\n"
    )

    parts.extend(
        x + "\n"
        for x in trend_table(
            analysis["india_short_topics"]
        )
    )

    parts.append("\n")

    # ========================================================
    # 2
    # ========================================================
    parts.append(
        "# 2. WORLD YOUTUBE TRENDS\n\n"
        f"Videos collected: {analysis['world_count']}\n\n"
        "## World Long-form Trends\n\n"
    )

    parts.extend(
        x + "\n"
        for x in trend_table(
            analysis["world_long_topics"]
        )
    )

    parts.append(
        "\n## World Shorts Trends\n\n"
    )

    parts.extend(
        x + "\n"
        for x in trend_table(
            analysis["world_short_topics"]
        )
    )

    parts.append("\n")

    # ========================================================
    # 3
    # ========================================================
    parts.append(
        "# 3. YOUTUBE GENRE TRENDS\n\n"
        "## Long-form Genre Trends\n\n"
    )

    parts.extend(
        x + "\n"
        for x in trend_table(
            analysis["genre_long"]
        )
    )

    parts.append(
        "\n## Shorts Genre Trends\n\n"
    )

    parts.extend(
        x + "\n"
        for x in trend_table(
            analysis["genre_shorts"]
        )
    )

    parts.append("\n")

    # ========================================================
    # 4
    # ========================================================
    parts.append(
        "# 4. INDIA/WORLD TREND-BASED SHORTS IDEAS\n\n"
    )

    for i, idea in enumerate(shorts, 1):
        parts.append(
            render_idea(idea, i)
            + "\n"
        )

    # ========================================================
    # 5
    # ========================================================
    parts.append(
        "# 5. INDIA/WORLD TREND-BASED LONG-FORM IDEAS\n\n"
        "**Target duration: 8-10 minutes**\n\n"
    )

    for i, idea in enumerate(longform, 1):
        parts.append(
            render_idea(idea, i)
            + "\n"
        )

    # ========================================================
    # 6
    # ========================================================
    parts.append(
        "# 6. INDIA/WORLD GENERAL SHORTS IDEAS\n\n"
        "**These are NOT based directly on the current trend list.**\n\n"
    )

    for i, idea in enumerate(general_shorts, 1):
        parts.append(
            render_idea(idea, i)
            + "\n"
        )

    # ========================================================
    # 7
    # ========================================================
    parts.append(
        "# 7. INDIA/WORLD GENERAL LONG-FORM IDEAS\n\n"
        "**These are NOT based directly on the current trend list.**\n"
        "**Target duration: 8-10 minutes**\n\n"
    )

    for i, idea in enumerate(general_longform, 1):
        parts.append(
            render_idea(idea, i)
            + "\n"
        )

    parts.append(
        "---\n\n"
        "# CREATIVE STANDARD\n\n"
        "Ideas prioritize curiosity, emotional stakes, "
        "originality, visual potential, retention and "
        "honest high CTR rather than generic "
        "challenge/reaction concepts.\n"
    )

    return "".join(parts)


def choose_top_idea(
    ai: dict[str, Any] | None,
    shorts: list[dict],
    longform: list[dict],
) -> dict:
    if isinstance(ai, dict):
        top = ai.get("top_idea")
        if isinstance(top, dict) and clean_text(
            top.get("title")
        ):
            return {
                "title": clean_text(
                    top["title"]
                ),
                "logline": clean_text(
                    top.get("logline")
                ),
                "why": clean_text(
                    top.get("why")
                ),
            }

    candidates = shorts + longform

    if candidates:
        return max(
            candidates,
            key=lambda x: (
                safe_int(x.get("ctr")),
                safe_int(x.get("retention")),
                safe_int(x.get("originality")),
            ),
        )

    return {
        "title": (
            "The Trend Everyone Is Watching "
            "But Nobody Is Explaining"
        ),
        "logline": (
            "Current YouTube trends ni "
            "curiosity-driven documentary angle "
            "lo explain cheyyadam."
        ),
        "why": (
            "Current API data provides a real "
            "trend signal."
        ),
    }


# ============================================================
# SECTION G — PDF + RESEND + MAIN
# ============================================================

def write_markdown(text: str) -> None:
    MD_PATH.write_text(
        text,
        encoding="utf-8",
    )


def create_pdf(
    markdown_text: str,
) -> None:
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import (
        SimpleDocTemplate,
        Paragraph,
        Spacer,
    )
    from reportlab.lib.styles import (
        getSampleStyleSheet,
        ParagraphStyle,
    )
    from reportlab.lib.enums import TA_CENTER

    doc = SimpleDocTemplate(
        str(PDF_PATH),
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
        title="YouTube High CTR Idea Generator",
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        fontSize=18,
        leading=22,
        alignment=TA_CENTER,
        spaceAfter=16,
    )

    h1 = ParagraphStyle(
        "ReportH1",
        parent=styles["Heading1"],
        fontSize=15,
        leading=19,
        spaceBefore=14,
        spaceAfter=8,
    )

    h2 = ParagraphStyle(
        "ReportH2",
        parent=styles["Heading2"],
        fontSize=12,
        leading=15,
        spaceBefore=10,
        spaceAfter=6,
    )

    h3 = ParagraphStyle(
        "ReportH3",
        parent=styles["Heading3"],
        fontSize=10.5,
        leading=14,
        spaceBefore=8,
        spaceAfter=5,
    )

    body = ParagraphStyle(
        "ReportBody",
        parent=styles["BodyText"],
        fontSize=8.8,
        leading=12.5,
        spaceAfter=5,
    )

    story = []

    for raw in markdown_text.splitlines():
        line = raw.strip()

        if not line:
            story.append(Spacer(1, 4))
            continue

        if line == "---":
            story.append(Spacer(1, 8))
            continue

        if line.startswith("# "):
            text = line[2:]
            text = html.escape(text)
            story.append(
                Paragraph(
                    text,
                    title_style,
                )
            )
            continue

        if line.startswith("## "):
            text = html.escape(line[3:])
            story.append(
                Paragraph(
                    text,
                    h1,
                )
            )
            continue

        if line.startswith("### "):
            text = html.escape(line[4:])
            story.append(
                Paragraph(
                    text,
                    h3,
                )
            )
            continue

        if line.startswith("|---"):
            continue

        if line.startswith("|"):
            cells = [
                x.strip()
                for x in line.strip("|").split("|")
            ]

            safe = " • ".join(
                html.escape(x)
                for x in cells
            )

            story.append(
                Paragraph(
                    safe,
                    body,
                )
            )
            continue

        text = html.escape(line)

        text = re.sub(
            r"\*\*(.*?)\*\*",
            r"<b>\1</b>",
            text,
        )

        story.append(
            Paragraph(
                text,
                body,
            )
        )

    doc.build(story)

    if not PDF_PATH.exists():
        raise RuntimeError(
            "PDF file was not created."
        )

    print(
        f"PDF CREATED: {PDF_PATH}"
    )


def send_email() -> bool:
    if not RESEND_API_KEY:
        print(
            "EMAIL SKIPPED: RESEND_API_KEY missing."
        )
        return False

    if not FROM_EMAIL or not RECIPIENT_EMAIL:
        print(
            "EMAIL SKIPPED: "
            "FROM_EMAIL or RECIPIENT_EMAIL missing."
        )
        return False

    try:
        import base64

        pdf_bytes = PDF_PATH.read_bytes()

        attachment = {
            "filename": PDF_PATH.name,
            "content": base64.b64encode(
                pdf_bytes
            ).decode("ascii"),
        }

        payload = {
            "from": FROM_EMAIL,
            "to": [RECIPIENT_EMAIL],
            "subject": (
                "YOUTUBE HIGH CTR IDEA GENERATOR"
            ),
            "html": (
                "<h1>YouTube High CTR Idea Generator</h1>"
                f"<p>Generated: {REPORT_TIME}</p>"
                "<p>Your 7-section trend report is attached.</p>"
            ),
            "attachments": [attachment],
        }

        headers = {
            "Authorization": (
                f"Bearer {RESEND_API_KEY}"
            ),
            "Content-Type": "application/json",
        }

        response = requests.post(
            RESEND_URL,
            headers=headers,
            json=payload,
            timeout=60,
        )

        print(
            f"Resend HTTP status: "
            f"{response.status_code}"
        )

        if response.status_code not in {
            200,
            201,
        }:
            print(
                "WARNING: Email failed but report "
                "generation is still successful."
            )
            print(response.text[:1000])
            return False

        print(
            "EMAIL SENT: PDF delivered through Resend."
        )
        return True

    except Exception as exc:
        print(
            f"WARNING: Email failed: {exc}"
        )
        return False


def save_json(
    analysis: dict[str, Any],
    shorts: list[dict],
    longform: list[dict],
    general_shorts: list[dict],
    general_longform: list[dict],
) -> None:
    data = {
        "generated_at": REPORT_TIME,
        "analysis": {
            "india_count": analysis["india_count"],
            "world_count": analysis["world_count"],
            "total_count": analysis["total_count"],
            "india_long_topics": analysis[
                "india_long_topics"
            ],
            "india_short_topics": analysis[
                "india_short_topics"
            ],
            "world_long_topics": analysis[
                "world_long_topics"
            ],
            "world_short_topics": analysis[
                "world_short_topics"
            ],
            "genre_long": analysis["genre_long"],
            "genre_shorts": analysis["genre_shorts"],
        },
        "shorts": shorts,
        "longform": longform,
        "general_shorts": general_shorts,
        "general_longform": general_longform,
    }

    JSON_PATH.write_text(
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def main() -> None:
    print("=" * 60)
    print("STARTING YOUTUBE HIGH CTR IDEA GENERATOR")
    print("=" * 60)
    print(f"Python: {os.sys.version}")

    require_env()

    # --------------------------------------------------------
    # 1. Collect
    # --------------------------------------------------------
    india, world = collect_all_trends()

    # --------------------------------------------------------
    # 2. Analyze locally FIRST.
    #    This guarantees the report can be produced without AI.
    # --------------------------------------------------------
    print("3. Analysing YouTube genre trends...")

    analysis = analyze_trends(
        india,
        world,
    )

    print(
        f"India: {analysis['india_count']} | "
        f"World: {analysis['world_count']} | "
        f"Total: {analysis['total_count']}"
    )

    print(
        f"India long: {len(analysis['india_long'])} | "
        f"India shorts: {len(analysis['india_shorts'])}"
    )

    print(
        f"World long: {len(analysis['world_long'])} | "
        f"World shorts: {len(analysis['world_shorts'])}"
    )

    # --------------------------------------------------------
    # 3. Local ideas BEFORE AI.
    # --------------------------------------------------------
    print(
        "4. Generating HIGH CTR + YouTube ideas..."
    )

    fallback_short, fallback_long = (
        local_trend_ideas(analysis)
    )

    # If one side has fewer than 8 trend ideas,
    # fill from the other available trend topics.
    if len(fallback_short) < 8:
        fallback_short.extend(
            local_general_shorts()[
                :8 - len(fallback_short)
            ]
        )

    if len(fallback_long) < 8:
        fallback_long.extend(
            local_general_longform()[
                :8 - len(fallback_long)
            ]
        )

    fallback_short = fallback_short[:8]
    fallback_long = fallback_long[:8]

    # --------------------------------------------------------
    # 4. ONE AI request only.
    # --------------------------------------------------------
    ai_result = call_openrouter_once(
        analysis
    )

    # --------------------------------------------------------
    # 5. Validate AI or use fallback.
    # --------------------------------------------------------
    (
        shorts,
        longform,
        general_shorts,
        general_longform,
    ) = validate_ai_result(
        ai_result,
        fallback_short,
        fallback_long,
    )

    # Force exact 8 in each idea section.
    shorts = (
        shorts
        + fallback_short
        + local_general_shorts()
    )[:8]

    longform = (
        longform
        + fallback_long
        + local_general_longform()
    )[:8]

    general_shorts = (
        general_shorts
        + local_general_shorts()
    )[:8]

    general_longform = (
        general_longform
        + local_general_longform()
    )[:8]

    top_idea = choose_top_idea(
        ai_result,
        shorts,
        longform,
    )

    # --------------------------------------------------------
    # 6. Build report.
    # --------------------------------------------------------
    report = build_report(
        analysis,
        shorts,
        longform,
        general_shorts,
        general_longform,
        top_idea,
    )

    write_markdown(report)

    save_json(
        analysis,
        shorts,
        longform,
        general_shorts,
        general_longform,
    )

    # --------------------------------------------------------
    # 7. PDF.
    # --------------------------------------------------------
    create_pdf(report)

    # --------------------------------------------------------
    # 8. Email.
    # --------------------------------------------------------
    send_email()

    print("=" * 60)
    print("YOUTUBE HIGH CTR IDEA GENERATOR COMPLETE")
    print("=" * 60)
    print(f"India videos : {analysis['india_count']}")
    print(f"World videos : {analysis['world_count']}")
    print(f"Shorts ideas : {len(shorts)}")
    print(f"Long ideas   : {len(longform)}")
    print(f"PDF          : {PDF_PATH}")
    print(f"Markdown     : {MD_PATH}")
    print(f"JSON         : {JSON_PATH}")
    print("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Stopped by user.")
        raise SystemExit(130)
    except Exception as exc:
        print("=" * 60)
        print("FATAL ERROR")
        print("=" * 60)
        print(f"{type(exc).__name__}: {exc}")
        raise
