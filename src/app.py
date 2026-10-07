"""
YouTube High CTR Idea Generator
--------------------------------
Generates:
1. India YouTube trends - long-form + Shorts
2. Worldwide YouTube trends - long-form + Shorts
3. YouTube genre trends - long-form + Shorts
4. Trend-based Shorts ideas - India + World + Roman Telugu logline
5. Trend-based long-form ideas - India + World + Roman Telugu logline
6. General/non-trend Shorts ideas - India + World + Roman Telugu logline
7. General/non-trend long-form ideas - India + World + Roman Telugu logline

Required environment variables:
OPENROUTER_API_KEY
YOUTUBE_API_KEY
RESEND_API_KEY
FROM_EMAIL
RECIPIENT_EMAIL

Optional:
OPENROUTER_MODEL=openrouter/auto
WORLD_COUNTRIES=US,GB,CA,AU,DE,FR,JP,KR,BR,MX
IDEAS_PER_SECTION=8
"""

import json
import os
import re
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from typing import Any, Dict, List

import requests


# ============================================================
# CONFIG
# ============================================================

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
YOUTUBE_URL = "https://www.googleapis.com/youtube/v3/videos"
RESEND_URL = "https://api.resend.com/emails"

OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openrouter/auto")
WORLD_COUNTRIES = [
    x.strip().upper()
    for x in os.getenv(
        "WORLD_COUNTRIES",
        "US,GB,CA,AU,DE,FR,JP,KR,BR,MX",
    ).split(",")
    if x.strip()
]

IDEAS_PER_SECTION = max(
    5,
    min(12, int(os.getenv("IDEAS_PER_SECTION", "8"))),
)

REQUEST_TIMEOUT = 60


# ============================================================
# ENVIRONMENT
# ============================================================

def require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def check_environment() -> Dict[str, str]:
    print("=" * 60)
    print("CHECKING ENVIRONMENT")
    print("=" * 60)

    names = [
        "OPENROUTER_API_KEY",
        "RESEND_API_KEY",
        "FROM_EMAIL",
        "RECIPIENT_EMAIL",
        "YOUTUBE_API_KEY",
    ]

    values = {}
    for name in names:
        value = os.getenv(name, "").strip()
        values[name] = value
        print(f"{name}: {'OK' if value else 'MISSING'}")

    missing = [n for n, v in values.items() if not v]
    if missing:
        raise RuntimeError(
            "Missing environment variables: " + ", ".join(missing)
        )

    print("Environment check: OK")
    return values


# ============================================================
# YOUTUBE COLLECTION
# ============================================================

def youtube_request(country_code: str) -> List[Dict[str, Any]]:
    api_key = require_env("YOUTUBE_API_KEY")

    params = {
        "part": "snippet,statistics,contentDetails",
        "chart": "mostPopular",
        "regionCode": country_code,
        "maxResults": 50,
        "key": api_key,
    }

    print(f"Collecting YouTube mostPopular data: {country_code}")

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
            detail = response.text[:500]
        raise RuntimeError(
            f"YouTube API failed for {country_code}: {detail}"
        )

    data = response.json()
    items = data.get("items", [])

    print(f"Collected {len(items)} videos.")
    return items


def collect_trends() -> Dict[str, List[Dict[str, Any]]]:
    print("1. Collecting India trends...")
    india = youtube_request("IN")

    print("2. Collecting worldwide proxy trends...")
    world: List[Dict[str, Any]] = []

    for country in WORLD_COUNTRIES:
        try:
            world.extend(youtube_request(country))
        except Exception as exc:
            print(f"WARNING: Could not collect {country}: {exc}")

    return {
        "india": india,
        "world": world,
    }


# ============================================================
# TREND ANALYSIS
# ============================================================

def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def parse_duration_seconds(duration: str) -> int:
    """
    Converts ISO-8601 YouTube duration such as PT8M31S to seconds.
    """
    if not duration:
        return 0

    match = re.fullmatch(
        r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?",
        duration,
    )

    if not match:
        return 0

    hours = safe_int(match.group(1))
    minutes = safe_int(match.group(2))
    seconds = safe_int(match.group(3))

    return hours * 3600 + minutes * 60 + seconds


def normalize_video(item: Dict[str, Any], country: str = "") -> Dict[str, Any]:
    snippet = item.get("snippet", {})
    stats = item.get("statistics", {})
    details = item.get("contentDetails", {})

    duration_seconds = parse_duration_seconds(
        details.get("duration", "")
    )

    if duration_seconds < 61:
        format_name = "Shorts/Very Short"
    elif duration_seconds <= 12 * 60:
        format_name = "Long-form"
    else:
        format_name = "Long-form"

    return {
        "title": snippet.get("title", "").strip(),
        "channel": snippet.get("channelTitle", "").strip(),
        "category_id": str(snippet.get("categoryId", "")),
        "published_at": snippet.get("publishedAt", ""),
        "views": safe_int(stats.get("viewCount")),
        "likes": safe_int(stats.get("likeCount")),
        "comments": safe_int(stats.get("commentCount")),
        "duration_seconds": duration_seconds,
        "format": format_name,
        "country": country,
    }


def normalize_collection(items: List[Dict[str, Any]], country: str = "") -> List[Dict[str, Any]]:
    return [
        normalize_video(item, country)
        for item in items
        if item.get("snippet", {}).get("title")
    ]


def category_name(category_id: str) -> str:
    # Common YouTube categories. Unknown IDs remain generic.
    mapping = {
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
    return mapping.get(str(category_id), f"Category {category_id or 'Unknown'}")


def analyze_trends(collection: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
    india = normalize_collection(collection["india"], "IN")

    # World source country is not preserved by the raw collection, so
    # we use the aggregate trend pool intentionally.
    world = normalize_collection(collection["world"], "WORLD")

    def top_videos(videos: List[Dict[str, Any]], limit: int = 40):
        return sorted(
            videos,
            key=lambda x: (
                x["views"],
                x["likes"],
                x["comments"],
            ),
            reverse=True,
        )[:limit]

    def genre_counts(videos: List[Dict[str, Any]]):
        counter = Counter(category_name(v["category_id"]) for v in videos)
        return counter.most_common()

    def format_counts(videos: List[Dict[str, Any]]):
        short_count = sum(
            1 for v in videos if v["duration_seconds"] < 61
        )
        long_count = len(videos) - short_count
        return {
            "shorts_or_very_short": short_count,
            "long_form": long_count,
        }

    return {
        "india": {
            "video_count": len(india),
            "top_videos": top_videos(india),
            "genres": genre_counts(india),
            "formats": format_counts(india),
        },
        "world": {
            "video_count": len(world),
            "top_videos": top_videos(world),
            "genres": genre_counts(world),
            "formats": format_counts(world),
        },
    }


def compact_trend_context(analysis: Dict[str, Any]) -> str:
    """
    Keep prompt size controlled. The AI does NOT need every API field.
    """
    result = {
        "india": {
            "video_count": analysis["india"]["video_count"],
            "formats": analysis["india"]["formats"],
            "genres": analysis["india"]["genres"][:12],
            "top_videos": [
                {
                    "title": x["title"],
                    "views": x["views"],
                    "likes": x["likes"],
                    "comments": x["comments"],
                    "format": x["format"],
                }
                for x in analysis["india"]["top_videos"][:35]
            ],
        },
        "world": {
            "video_count": analysis["world"]["video_count"],
            "formats": analysis["world"]["formats"],
            "genres": analysis["world"]["genres"][:15],
            "top_videos": [
                {
                    "title": x["title"],
                    "views": x["views"],
                    "likes": x["likes"],
                    "comments": x["comments"],
                    "format": x["format"],
                }
                for x in analysis["world"]["top_videos"][:50]
            ],
        },
    }

    return json.dumps(result, ensure_ascii=False)


# ============================================================
# AI PROMPT
# ============================================================

def build_system_prompt() -> str:
    return """
You are an elite YouTube creative strategist, viral-format researcher,
story developer and high-CTR title writer.

Your job is NOT to make generic YouTube ideas.

Every idea must have:
- a genuinely strong hook
- a clear curiosity gap
- emotional or intellectual stakes
- a reason to click NOW
- a simple but powerful core premise
- visual potential
- strong retention potential
- a clear target audience
- a realistic solo-creator execution path where possible

Avoid:
- silly prank ideas
- generic "24 hours challenge"
- generic "I tried..."
- generic reaction videos
- copied movie plots
- boring listicles
- ideas that need expensive celebrities
- fake facts
- impossible claims
- weak titles
- titles that explain the entire video
- repetitive ideas

The standard is:
"If a smart creator hears this idea, they should think:
WOW, THAT IS ACTUALLY A GREAT IDEA."

Use current trend data only as inspiration. Do not simply copy existing videos.

IMPORTANT:
Roman Telugu loglines must sound natural to a Telugu-speaking creator.
Use Roman Telugu written in English letters, NOT Telugu script.

Example style:
"Mana city lo andaru ignore chese oka normal place venuka unna
secret ni 24 hours lo investigate chesthe, final ga dorikedi
evaru expect cheyyani connection."

High CTR does NOT mean misleading clickbait.
The title should create curiosity while honestly matching the concept.

Return ONLY valid JSON.
No markdown.
No ``` fences.
No explanation outside JSON.
""".strip()


def build_user_prompt(trend_context: str) -> str:
    n = IDEAS_PER_SECTION

    schema = {
        "report_title": "string",
        "generated_at": "string",
        "top_high_ctr": {
            "title": "string",
            "logline_roman_telugu": "string",
            "why_people_click": "string",
        },
        "india_trends": {
            "longform_trends": [
                {
                    "trend": "string",
                    "evidence": "string",
                    "opportunity": "string",
                }
            ],
            "shorts_trends": [
                {
                    "trend": "string",
                    "evidence": "string",
                    "opportunity": "string",
                }
            ],
        },
        "world_trends": {
            "longform_trends": [
                {
                    "trend": "string",
                    "evidence": "string",
                    "opportunity": "string",
                }
            ],
            "shorts_trends": [
                {
                    "trend": "string",
                    "evidence": "string",
                    "opportunity": "string",
                }
            ],
        },
        "genre_trends": {
            "longform": [
                {
                    "genre": "string",
                    "trend": "string",
                    "why_now": "string",
                    "creator_opportunity": "string",
                }
            ],
            "shorts": [
                {
                    "genre": "string",
                    "trend": "string",
                    "why_now": "string",
                    "creator_opportunity": "string",
                }
            ],
        },
        "trend_shorts_ideas": [
            {
                "region": "India or World",
                "title": "string",
                "logline_roman_telugu": "string",
                "hook": "string",
                "why_it_can_work": "string",
                "format": "Shorts",
                "ctr_score": 1,
                "retention_score": 1,
                "originality_score": 1,
            }
        ],
        "trend_longform_ideas": [
            {
                "region": "India or World",
                "title": "string",
                "logline_roman_telugu": "string",
                "hook": "string",
                "why_it_can_work": "string",
                "format": "8-10 minute long-form",
                "ctr_score": 1,
                "retention_score": 1,
                "originality_score": 1,
            }
        ],
        "general_shorts_ideas": [
            {
                "region": "India or World",
                "title": "string",
                "logline_roman_telugu": "string",
                "hook": "string",
                "why_it_can_work": "string",
                "format": "Shorts",
                "ctr_score": 1,
                "retention_score": 1,
                "originality_score": 1,
            }
        ],
        "general_longform_ideas": [
            {
                "region": "India or World",
                "title": "string",
                "logline_roman_telugu": "string",
                "hook": "string",
                "why_it_can_work": "string",
                "format": "8-10 minute long-form",
                "ctr_score": 1,
                "retention_score": 1,
                "originality_score": 1,
            }
        ],
    }

    instructions = f"""
Create exactly {n} strong ideas in EACH of these four idea sections:
- trend_shorts_ideas
- trend_longform_ideas
- general_shorts_ideas
- general_longform_ideas

Also provide useful trend analysis for India, World and genres.

Requirements:

1. INDIA YOUTUBE TRENDS
Separate:
- long-form trends
- Shorts trends

2. WORLD YOUTUBE TRENDS
Separate:
- long-form trends
- Shorts trends

3. YOUTUBE GENRE TRENDS
Separate:
- long-form genre trends
- Shorts genre trends

4. INDIA/WORLD TREND-BASED SHORTS
Use actual observed trend patterns from the supplied data.
Make ideas extremely engaging.
Every idea needs a Roman Telugu logline.

5. INDIA/WORLD TREND-BASED LONG-FORM
Every idea must be suitable for an 8-10 minute video.
Strong opening, escalation and payoff.
Every idea needs a Roman Telugu logline.

6. INDIA/WORLD GENERAL SHORTS
These MUST NOT depend on the current trend list.
Use evergreen/high-potential concepts.
Still make them fresh and original.
Every idea needs a Roman Telugu logline.

7. INDIA/WORLD GENERAL LONG-FORM
These MUST NOT depend on current trend titles.
Create original 8-10 minute concepts.
Every idea needs a Roman Telugu logline.

TOP HIGH CTR IDEA:
Pick the single strongest concept from everything you generated.
Put it in top_high_ctr.
The title and Roman Telugu logline must be extremely compelling.

SCORING:
Use integer scores from 1 to 10.
Be selective. Do not give 9/10 or 10/10 to weak concepts.

JSON SHAPE:
{json.dumps(schema, ensure_ascii=False, indent=2)}

TREND DATA:
{trend_context}
"""

    return instructions


# ============================================================
# OPENROUTER
# ============================================================

def extract_json_object(text: str) -> Dict[str, Any]:
    """
    Robust JSON extraction.

    Handles:
    - pure JSON
    - ```json ... ```
    - explanatory text before/after JSON
    - JSON surrounded by accidental whitespace
    """

    if not text or not text.strip():
        raise RuntimeError("OpenRouter returned empty content.")

    cleaned = text.strip()

    # Remove markdown fences if present.
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.I)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    # First direct parse.
    try:
        obj = json.loads(cleaned)
        if isinstance(obj, dict):
            return obj
    except json.JSONDecodeError:
        pass

    # Locate first { and last }.
    start = cleaned.find("{")
    end = cleaned.rfind("}")

    if start == -1 or end <= start:
        raise RuntimeError(
            "AI response does not contain a JSON object."
        )

    candidate = cleaned[start:end + 1]

    try:
        obj = json.loads(candidate)
        if isinstance(obj, dict):
            return obj
    except json.JSONDecodeError as exc:
        # Try a small cleanup for common model mistakes.
        candidate2 = re.sub(
            r",\s*([}\]])",
            r"\1",
            candidate,
        )

        try:
            obj = json.loads(candidate2)
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            raise RuntimeError(
                f"AI returned malformed JSON: {exc}"
            ) from exc

    raise RuntimeError("AI result is not a JSON object.")


def validate_and_normalize_ai_result(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    This is the important fix.

    The old code apparently required:
        result["ideas"]

    This project actually needs multiple named sections, so this function
    accepts the correct seven-section structure and also tolerates common
    alternate AI key names.
    """

    aliases = {
        "trend_shorts_ideas": [
            "trend_shorts_ideas",
            "trend_based_shorts",
            "shorts_trend_ideas",
            "shorts_ideas",
        ],
        "trend_longform_ideas": [
            "trend_longform_ideas",
            "trend_based_longform",
            "longform_trend_ideas",
            "long_form_ideas",
        ],
        "general_shorts_ideas": [
            "general_shorts_ideas",
            "evergreen_shorts_ideas",
            "general_short_ideas",
        ],
        "general_longform_ideas": [
            "general_longform_ideas",
            "evergreen_longform_ideas",
            "general_long_form_ideas",
        ],
    }

    normalized = dict(data)

    # Accept an old generic "ideas" array as a fallback.
    generic = data.get("ideas")
    if isinstance(generic, list):
        normalized.setdefault("trend_shorts_ideas", generic[:IDEAS_PER_SECTION])

    for target, keys in aliases.items():
        value = None
        for key in keys:
            candidate = data.get(key)
            if isinstance(candidate, list):
                value = candidate
                break

        if value is None:
            value = []

        normalized[target] = value

    normalized.setdefault("india_trends", {
        "longform_trends": [],
        "shorts_trends": [],
    })
    normalized.setdefault("world_trends", {
        "longform_trends": [],
        "shorts_trends": [],
    })
    normalized.setdefault("genre_trends", {
        "longform": [],
        "shorts": [],
    })

    # Do not fail just because the model used a slightly different
    # structure. Fail only if the entire idea generation failed.
    total_ideas = sum(
        len(normalized[key])
        for key in aliases
    )

    if total_ideas == 0:
        raise RuntimeError(
            "AI response was valid JSON, but contained no usable idea lists."
        )

    # Guarantee top_high_ctr exists.
    if not isinstance(normalized.get("top_high_ctr"), dict):
        first = None
        for key in aliases:
            if normalized[key]:
                first = normalized[key][0]
                break

        if isinstance(first, dict):
            normalized["top_high_ctr"] = {
                "title": first.get("title", "Untitled"),
                "logline_roman_telugu": first.get(
                    "logline_roman_telugu",
                    "",
                ),
                "why_people_click": first.get(
                    "why_it_can_work",
                    first.get("hook", ""),
                ),
            }
        else:
            normalized["top_high_ctr"] = {}

    return normalized


def call_openrouter(trend_context: str) -> Dict[str, Any]:
    api_key = require_env("OPENROUTER_API_KEY")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/",
        "X-Title": "YouTube High CTR Idea Generator",
    }

    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {
                "role": "system",
                "content": build_system_prompt(),
            },
            {
                "role": "user",
                "content": build_user_prompt(trend_context),
            },
        ],
        "temperature": 0.85,
        "max_tokens": 16000,
        "response_format": {
            "type": "json_object"
        },
    }

    last_error = None

    for attempt in range(1, 4):
        print()
        print("OPENROUTER REQUEST")
        print(f"Model: {OPENROUTER_MODEL}")
        print(f"Attempt: {attempt}")

        try:
            response = requests.post(
                OPENROUTER_URL,
                headers=headers,
                json=payload,
                timeout=REQUEST_TIMEOUT,
            )

            print(f"HTTP status: {response.status_code}")

            if response.status_code != 200:
                try:
                    detail = response.json()
                except Exception:
                    detail = response.text[:1000]

                last_error = RuntimeError(
                    f"OpenRouter HTTP {response.status_code}: {detail}"
                )
                print(f"AI attempt {attempt} failed: {last_error}")
                time.sleep(2)
                continue

            body = response.json()

            choices = body.get("choices") or []
            if not choices:
                raise RuntimeError(
                    "OpenRouter response contains no choices."
                )

            message = choices[0].get("message") or {}
            content = message.get("content")

            # Some providers can return structured content.
            if isinstance(content, list):
                parts = []
                for part in content:
                    if isinstance(part, dict):
                        if part.get("type") == "text":
                            parts.append(part.get("text", ""))
                        elif "text" in part:
                            parts.append(str(part["text"]))
                content = "".join(parts)

            if not isinstance(content, str) or not content.strip():
                raise RuntimeError(
                    "OpenRouter returned empty content."
                )

            print("OpenRouter SUCCESS")
            print(
                "Model used:",
                body.get("model", OPENROUTER_MODEL),
            )
            print(
                "AI response length:",
                len(content),
                "characters",
            )

            parsed = extract_json_object(content)
            result = validate_and_normalize_ai_result(parsed)

            print("AI JSON parsed successfully.")
            print(
                "Total usable ideas:",
                sum(
                    len(result.get(k, []))
                    for k in (
                        "trend_shorts_ideas",
                        "trend_longform_ideas",
                        "general_shorts_ideas",
                        "general_longform_ideas",
                    )
                ),
            )

            return result

        except Exception as exc:
            last_error = exc
            print(f"AI attempt {attempt} failed: {type(exc).__name__}: {exc}")

            if attempt < 3:
                print("Retrying OpenRouter...")
                time.sleep(2)

    raise RuntimeError(
        f"OpenRouter failed after 3 attempts: {last_error}"
    )


# ============================================================
# MARKDOWN REPORT
# ============================================================

def score(value: Any) -> str:
    try:
        return f"{int(value)}/10"
    except Exception:
        return "N/A"


def idea_markdown(idea: Dict[str, Any], number: int) -> str:
    title = idea.get("title", "Untitled idea")
    logline = idea.get("logline_roman_telugu", "")
    hook = idea.get("hook", "")
    why = idea.get("why_it_can_work", "")
    region = idea.get("region", "")
    ctr = score(idea.get("ctr_score"))
    retention = score(idea.get("retention_score"))
    originality = score(idea.get("originality_score"))

    lines = [
        f"### {number}. {title}",
    ]

    if region:
        lines.append(f"**Region:** {region}")

    if logline:
        lines.append(
            f"**Roman Telugu Logline:** {logline}"
        )

    if hook:
        lines.append(f"**Hook:** {hook}")

    if why:
        lines.append(f"**Why it can work:** {why}")

    lines.append(
        f"**Scores:** CTR {ctr} · Retention {retention} · Originality {originality}"
    )

    return "\n".join(lines)


def trends_markdown(
    heading: str,
    trends: List[Dict[str, Any]],
) -> str:
    if not trends:
        return "_No trend analysis returned._"

    chunks = []

    for i, item in enumerate(trends, 1):
        trend = item.get("trend", "Unknown")
        evidence = item.get("evidence", "")
        opportunity = item.get("opportunity", "")
        why_now = item.get("why_now", "")
        creator = item.get("creator_opportunity", "")

        chunks.append(f"### {i}. {trend}")

        if evidence:
            chunks.append(f"**Evidence:** {evidence}")

        if why_now:
            chunks.append(f"**Why now:** {why_now}")

        if opportunity:
            chunks.append(f"**Opportunity:** {opportunity}")

        if creator:
            chunks.append(f"**Creator opportunity:** {creator}")

    return "\n\n".join(chunks)


def build_markdown(
    result: Dict[str, Any],
    analysis: Dict[str, Any],
) -> str:
    now = datetime.now(timezone.utc).strftime(
        "%Y-%m-%d %H:%M UTC"
    )

    top = result.get("top_high_ctr") or {}

    lines = [
        "# YOUTUBE HIGH CTR IDEA GENERATOR",
        "",
        f"Generated: {now}",
        "",
        "## 🔥 TOP HIGH CTR IDEA",
        "",
        f"### {top.get('title', 'No top idea returned')}",
        "",
        f"**Roman Telugu Logline:** {top.get('logline_roman_telugu', '')}",
        "",
        f"**Why people click:** {top.get('why_people_click', '')}",
        "",
        "---",
        "",
        "# 1. INDIA YOUTUBE TRENDS",
        "",
        f"Videos collected: {analysis['india']['video_count']}",
        "",
        "## India Long-form Trends",
        "",
        trends_markdown(
            "India Long-form",
            result.get("india_trends", {}).get(
                "longform_trends", []
            ),
        ),
        "",
        "## India Shorts Trends",
        "",
        trends_markdown(
            "India Shorts",
            result.get("india_trends", {}).get(
                "shorts_trends", []
            ),
        ),
        "",
        "---",
        "",
        "# 2. WORLD YOUTUBE TRENDS",
        "",
        f"Videos collected: {analysis['world']['video_count']}",
        "",
        "## World Long-form Trends",
        "",
        trends_markdown(
            "World Long-form",
            result.get("world_trends", {}).get(
                "longform_trends", []
            ),
        ),
        "",
        "## World Shorts Trends",
        "",
        trends_markdown(
            "World Shorts",
            result.get("world_trends", {}).get(
                "shorts_trends", []
            ),
        ),
        "",
        "---",
        "",
        "# 3. YOUTUBE GENRE TRENDS",
        "",
        "## Long-form Genre Trends",
        "",
        trends_markdown(
            "Genres",
            result.get("genre_trends", {}).get(
                "longform", []
            ),
        ),
        "",
        "## Shorts Genre Trends",
        "",
        trends_markdown(
            "Genres",
            result.get("genre_trends", {}).get(
                "shorts", []
            ),
        ),
        "",
        "---",
        "",
        "# 4. INDIA/WORLD TREND-BASED SHORTS IDEAS",
        "",
    ]

    ideas = result.get("trend_shorts_ideas", [])
    for i, idea in enumerate(ideas, 1):
        lines.extend([idea_markdown(idea, i), ""])

    lines.extend([
        "---",
        "",
        "# 5. INDIA/WORLD TREND-BASED LONG-FORM IDEAS",
        "",
        "**Target duration: 8-10 minutes**",
        "",
    ])

    ideas = result.get("trend_longform_ideas", [])
    for i, idea in enumerate(ideas, 1):
        lines.extend([idea_markdown(idea, i), ""])

    lines.extend([
        "---",
        "",
        "# 6. INDIA/WORLD GENERAL SHORTS IDEAS",
        "",
        "**These are NOT based directly on the current trend list.**",
        "",
    ])

    ideas = result.get("general_shorts_ideas", [])
    for i, idea in enumerate(ideas, 1):
        lines.extend([idea_markdown(idea, i), ""])

    lines.extend([
        "---",
        "",
        "# 7. INDIA/WORLD GENERAL LONG-FORM IDEAS",
        "",
        "**These are NOT based directly on the current trend list.**",
        "**Target duration: 8-10 minutes**",
        "",
    ])

    ideas = result.get("general_longform_ideas", [])
    for i, idea in enumerate(ideas, 1):
        lines.extend([idea_markdown(idea, i), ""])

    lines.extend([
        "---",
        "",
        "# CREATIVE STANDARD",
        "",
        "Ideas were requested to prioritize curiosity, emotional stakes,",
        "originality, visual potential, retention and honest high CTR",
        "rather than generic challenge/reaction concepts.",
        "",
    ])

    return "\n".join(lines)


# ============================================================
# RESEND EMAIL
# ============================================================

def markdown_to_basic_html(markdown: str) -> str:
    """
    Lightweight Markdown -> HTML for the email.
    The actual markdown file remains the primary report.
    """
    text = escape(markdown)

    text = re.sub(
        r"^### (.+)$",
        r"<h3>\1</h3>",
        text,
        flags=re.M,
    )
    text = re.sub(
        r"^## (.+)$",
        r"<h2>\1</h2>",
        text,
        flags=re.M,
    )
    text = re.sub(
        r"^# (.+)$",
        r"<h1>\1</h1>",
        text,
        flags=re.M,
    )

    text = re.sub(
        r"\*\*(.+?)\*\*",
        r"<strong>\1</strong>",
        text,
    )

    text = text.replace(
        "\n\n",
        "</p><p>",
    )

    text = "<p>" + text + "</p>"

    return f"""
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>YouTube High CTR Ideas</title>
<style>
body {{
    font-family: Arial, sans-serif;
    line-height: 1.6;
    max-width: 1000px;
    margin: 40px auto;
    padding: 0 20px;
}}
h1 {{ margin-top: 32px; }}
h2 {{ margin-top: 28px; }}
h3 {{ margin-top: 22px; }}
p {{ margin: 8px 0; }}
</style>
</head>
<body>
{text}
</body>
</html>
"""


def send_email(markdown_report: str, output_file: Path) -> None:
    api_key = require_env("RESEND_API_KEY")
    from_email = require_env("FROM_EMAIL")
    recipient = require_env("RECIPIENT_EMAIL")

    subject = (
        "🔥 YouTube High CTR Ideas | "
        + datetime.now().strftime("%d %b %Y")
    )

    # Resend API supports attachments as base64.
    import base64

    encoded = base64.b64encode(
        output_file.read_bytes()
    ).decode("utf-8")

    payload = {
        "from": from_email,
        "to": [recipient],
        "subject": subject,
        "html": markdown_to_basic_html(markdown_report),
        "attachments": [
            {
                "filename": output_file.name,
                "content": encoded,
            }
        ],
    }

    response = requests.post(
        RESEND_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=REQUEST_TIMEOUT,
    )

    print(f"Resend HTTP status: {response.status_code}")

    if response.status_code >= 300:
        try:
            detail = response.json()
        except Exception:
            detail = response.text[:1000]
        raise RuntimeError(
            f"Resend email failed: {detail}"
        )

    print("Email sent successfully.")


# ============================================================
# SAVE JSON + MARKDOWN
# ============================================================

def save_outputs(
    result: Dict[str, Any],
    analysis: Dict[str, Any],
) -> Path:
    output_dir = Path("output")
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    json_file = output_dir / f"youtube_ideas_{timestamp}.json"
    md_file = output_dir / f"youtube_high_ctr_{timestamp}.md"

    json_file.write_text(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    markdown = build_markdown(result, analysis)

    md_file.write_text(
        markdown,
        encoding="utf-8",
    )

    # Also save stable/latest files for GitHub Actions.
    Path("youtube_high_ctr_latest.md").write_text(
        markdown,
        encoding="utf-8",
    )

    Path("youtube_high_ctr_latest.json").write_text(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print()
    print("OUTPUT FILES")
    print(f"Markdown: {md_file}")
    print(f"JSON:     {json_file}")
    print("Latest:   youtube_high_ctr_latest.md")

    return md_file


# ============================================================
# MAIN
# ============================================================

def main() -> None:
    print("=" * 60)
    print("STARTING YOUTUBE HIGH CTR IDEA GENERATOR")
    print("=" * 60)
    print("Python:", sys.version.split()[0])

    check_environment()

    collection = collect_trends()

    print()
    print("3. Analysing YouTube genre trends...")
    analysis = analyze_trends(collection)

    print()
    print("4. Generating HIGH CTR + YouTube ideas...")

    trend_context = compact_trend_context(analysis)

    result = call_openrouter(trend_context)

    print()
    print("5. Formatting report...")

    output_file = save_outputs(
        result,
        analysis,
    )

    print()
    print("6. Sending report by email...")

    markdown_report = output_file.read_text(
        encoding="utf-8"
    )

    send_email(
        markdown_report,
        output_file,
    )

    print()
    print("=" * 60)
    print("YOUTUBE HIGH CTR IDEA GENERATOR COMPLETED")
    print("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped by user.")
        sys.exit(130)
    except Exception as exc:
        print()
        print("=" * 60)
        print("FATAL ERROR")
        print("=" * 60)
        print(f"{type(exc).__name__}: {exc}")
        sys.exit(1)
