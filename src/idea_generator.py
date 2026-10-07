import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List

import requests
from dotenv import load_dotenv


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

load_dotenv(BASE_DIR / ".env")


# ============================================================
# CONFIG
# ============================================================

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "").strip()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-2.5-flash"
).strip()

OPENROUTER_API_KEY = os.getenv(
    "OPENROUTER_API_KEY",
    ""
).strip()

OPENROUTER_MODEL = os.getenv(
    "OPENROUTER_MODEL",
    "google/gemini-2.5-flash"
).strip()

IDEAS_PER_SECTION = int(
    os.getenv("IDEAS_PER_SECTION", "8")
)

REQUEST_TIMEOUT = 180


# ============================================================
# SECTION DEFINITIONS
# ============================================================

SECTIONS = [

    {
        "id": 1,
        "name": "India YouTube Trends",
        "type": "trend_analysis"
    },

    {
        "id": 2,
        "name": "World YouTube Trends",
        "type": "trend_analysis"
    },

    {
        "id": 3,
        "name": "YouTube Genre Trends",
        "type": "genre_analysis"
    },

    {
        "id": 4,
        "name": "Trend-Based Shorts Ideas",
        "type": "trend_shorts"
    },

    {
        "id": 5,
        "name": "Trend-Based Longform Ideas",
        "type": "trend_longform"
    },

    {
        "id": 6,
        "name": "General Original Shorts Ideas",
        "type": "general_shorts"
    },

    {
        "id": 7,
        "name": "General Original Longform Ideas",
        "type": "general_longform"
    },

    {
        "id": 8,
        "name": "Genre-Fusion High CTR Ideas",
        "type": "genre_fusion"
    },
]


# ============================================================
# HIGH CTR SYSTEM PROMPT
# ============================================================

SYSTEM_PROMPT = r"""
You are an elite YouTube creative director, viral concept developer,
story designer, CTR strategist and audience-retention expert.

Your job is NOT to produce ordinary YouTube ideas.

The ideas must create this reaction:

"WAH... WHAT AN IDEA!"

"I HAVE TO WATCH THIS."

"WHAT HAPPENS NEXT?"

"I HAVE NEVER SEEN THIS CONCEPT BEFORE."

============================================================
ABSOLUTE QUALITY RULE
============================================================

NEVER generate filler ideas.

NEVER generate silly ideas simply to complete a list.

NEVER generate generic:

- "I tried this for 24 hours"
- random challenges
- generic prank
- generic reaction
- generic vlog
- generic food review
- generic motivation
- generic interview
- generic gaming challenge
- generic "top 10"
- generic facts
- generic AI video
- generic horror story

The central concept itself must be interesting.

Every concept should contain at least one powerful engine:

1. Curiosity
2. Mystery
3. Conflict
4. Psychological tension
5. Emotional stakes
6. Unexpected consequence
7. Discovery
8. Moral dilemma
9. Transformation
10. Hidden truth
11. Competition with meaningful stakes
12. Impossible-looking situation
13. Investigation
14. Social pressure
15. Surprise reversal

============================================================
TITLE
============================================================

Titles must create a strong curiosity gap.

Avoid explaining the entire story in the title.

Bad:
"I Tried Living Without My Phone For 24 Hours"

Better:
"My Phone Received a Message From Tomorrow"

Bad:
"I Visited an Abandoned Building"

Better:
"The Camera Recorded Someone Who Wasn't There"

============================================================
LOGLINE
============================================================

Roman Telugu logline must sound natural.

It must feel like something a Telugu storyteller would actually say.

Example:

"Night 2:13 ki tana phone ki tana own number nunchi call vastundi.
Call lift chesthe avatala tana voice lone oka warning vinipisthundi.
Kaani aa warning lo cheppina incident next morning jaragabothundi."

Do NOT produce literal machine translation.

============================================================
ENTERTAINMENT GENRES
============================================================

When entertainment is involved, ALWAYS identify the specific genre.

Examples:

Thriller
Psychological Thriller
Mystery Thriller
Crime Thriller
Survival Thriller
Dark Comedy
Situational Comedy
Horror Comedy
Psychological Horror
Mystery
Crime
Investigation
Documentary
Social Experiment
Emotional Drama
Sci-Fi
Adventure
Action
Fantasy
Gaming Story
Technology Mystery

Do NOT simply write "Entertainment".

============================================================
LONGFORM
============================================================

For 8-10 minute ideas use:

HOOK
↓
QUESTION
↓
ESCALATION
↓
DISCOVERY
↓
COMPLICATION
↓
REVEAL
↓
PAYOFF

The concept must have enough story material for 8-10 minutes.

============================================================
SHORTS
============================================================

Shorts must create an immediate curiosity loop.

The first few seconds must make the viewer ask:

"WHY?"

or

"HOW?"

or

"WHAT?"

or

"IS THAT REALLY POSSIBLE?"

============================================================
HIGH CTR SCORING
============================================================

Score every idea from 0-100:

CTR
RETENTION
NOVELTY
EMOTIONAL_IMPACT
FEASIBILITY

Do not give every idea 95+.

A score above 90 should be reserved for genuinely exceptional ideas.

============================================================
TREND ANALYSIS
============================================================

When trend data is supplied:

DO NOT simply repeat the video title.

Identify:

- what is happening
- why people care
- audience psychology
- emotional trigger
- format
- storytelling pattern
- genre
- subgenre
- opportunity for a creator

If entertainment appears, identify the exact subgenre.

============================================================
ORIGINAL IDEAS
============================================================

For sections 6 and 7:

DO NOT copy current trends.

Use broad audience psychology and original premises.

============================================================
GENRE FUSION
============================================================

For section 8 combine genres intelligently.

Examples:

Psychological Thriller + Social Experiment

Crime Mystery + Dark Comedy

Technology + Mystery

Science + Thriller

Horror + Investigation

Documentary + Psychological Mystery

Gaming + Real World Mystery

The combination must make creative sense.

============================================================
IMPORTANT
============================================================

The FIRST idea in each idea section must be the strongest.

Do not sacrifice quality for quantity.

Return ONLY valid JSON.
"""


# ============================================================
# YOUTUBE API
# ============================================================

def get_youtube_trending(
    region_code: str,
    max_results: int = 50
) -> List[Dict[str, Any]]:

    if not YOUTUBE_API_KEY:
        print(
            "WARNING: YOUTUBE_API_KEY is missing."
        )

        return []

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

    try:

        response = requests.get(
            url,
            params=params,
            timeout=30
        )

        response.raise_for_status()

        data = response.json()

    except Exception as exc:

        print(
            f"YouTube API warning ({region_code}): {exc}"
        )

        return []

    videos = []

    for item in data.get("items", []):

        snippet = item.get(
            "snippet",
            {}
        )

        stats = item.get(
            "statistics",
            {}
        )

        content = item.get(
            "contentDetails",
            {}
        )

        video_id = item.get("id")

        videos.append({

            "video_id": video_id,

            "title": snippet.get(
                "title",
                ""
            ),

            "channel": snippet.get(
                "channelTitle",
                ""
            ),

            "description": snippet.get(
                "description",
                ""
            ),

            "published_at": snippet.get(
                "publishedAt",
                ""
            ),

            "category_id": snippet.get(
                "categoryId",
                ""
            ),

            "views": int(
                stats.get(
                    "viewCount",
                    0
                )
            ),

            "likes": int(
                stats.get(
                    "likeCount",
                    0
                )
            ),

            "comments": int(
                stats.get(
                    "commentCount",
                    0
                )
            ),

            "duration": content.get(
                "duration",
                ""
            ),

            "url": (
                f"https://www.youtube.com/watch?v={video_id}"
            )
        })

    return videos


# ============================================================
# LLM
# ============================================================

def call_gemini(prompt: str) -> str:

    if not GEMINI_API_KEY:
        raise RuntimeError(
            "GEMINI_API_KEY is missing."
        )

    url = (
        "https://generativelanguage.googleapis.com/"
        f"v1beta/models/{GEMINI_MODEL}:generateContent"
    )

    params = {
        "key": GEMINI_API_KEY
    }

    payload = {

        "systemInstruction": {

            "parts": [

                {
                    "text": SYSTEM_PROMPT
                }

            ]
        },

        "contents": [

            {

                "role": "user",

                "parts": [

                    {
                        "text": prompt
                    }

                ]
            }

        ],

        "generationConfig": {

            "temperature": 0.95,

            "topP": 0.95,

            "responseMimeType": "application/json"

        }
    }

    response = requests.post(
        url,
        params=params,
        json=payload,
        timeout=REQUEST_TIMEOUT
    )

    response.raise_for_status()

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
        .get("content", {})
        .get("parts", [])
    )

    text_parts = []

    for part in parts:

        text = part.get(
            "text",
            ""
        )

        if text:
            text_parts.append(text)

    if not text_parts:
        raise RuntimeError(
            "Gemini returned empty response."
        )

    return "\n".join(text_parts)


def call_openrouter(prompt: str) -> str:

    if not OPENROUTER_API_KEY:
        raise RuntimeError(
            "OPENROUTER_API_KEY is missing."
        )

    url = (
        "https://openrouter.ai/api/v1/chat/completions"
    )

    headers = {

        "Authorization":
            f"Bearer {OPENROUTER_API_KEY}",

        "Content-Type":
            "application/json",

        "HTTP-Referer":
            "https://github.com/",

        "X-Title":
            "YouTube High CTR Idea Generator"
    }

    payload = {

        "model":
            OPENROUTER_MODEL,

        "messages": [

            {
                "role":
                    "system",

                "content":
                    SYSTEM_PROMPT
            },

            {
                "role":
                    "user",

                "content":
                    prompt
            }

        ],

        "temperature":
            0.95,

        "top_p":
            0.95
    }

    response = requests.post(
        url,
        headers=headers,
        json=payload,
        timeout=REQUEST_TIMEOUT
    )

    response.raise_for_status()

    data = response.json()

    return (
        data["choices"][0]
        ["message"]
        ["content"]
    )


def call_llm(prompt: str) -> str:

    if GEMINI_API_KEY:

        return call_gemini(prompt)

    if OPENROUTER_API_KEY:

        return call_openrouter(prompt)

    raise RuntimeError(
        "No AI API configured. "
        "Set GEMINI_API_KEY or OPENROUTER_API_KEY."
    )


# ============================================================
# JSON CLEANER
# ============================================================

def parse_json(text: str) -> Dict[str, Any]:

    text = text.strip()

    text = re.sub(
        r"^```json\s*",
        "",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"^```\s*",
        "",
        text
    )

    text = re.sub(
        r"\s*```$",
        "",
        text
    )

    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1:

        raise ValueError(
            "LLM did not return JSON."
        )

    json_text = text[
        start:end + 1
    ]

    return json.loads(
        json_text
    )


# ============================================================
# DATA COMPACTION
# ============================================================

def compact_videos(
    videos: List[Dict[str, Any]],
    limit: int = 30
) -> List[Dict[str, Any]]:

    sorted_videos = sorted(
        videos,
        key=lambda x: x.get(
            "views",
            0
        ),
        reverse=True
    )

    result = []

    for video in sorted_videos[:limit]:

        result.append({

            "title":
                video.get(
                    "title",
                    ""
                ),

            "channel":
                video.get(
                    "channel",
                    ""
                ),

            "views":
                video.get(
                    "views",
                    0
                ),

            "likes":
                video.get(
                    "likes",
                    0
                ),

            "comments":
                video.get(
                    "comments",
                    0
                ),

            "published_at":
                video.get(
                    "published_at",
                    ""
                ),

            "url":
                video.get(
                    "url",
                    ""
                )
        })

    return result


# ============================================================
# PROMPT
# ============================================================

def section_instruction(
    section: Dict[str, Any]
) -> str:

    section_id = section["id"]

    if section_id == 1:

        return """
SECTION 1 — INDIA YOUTUBE TRENDS

Analyze India YouTube trends.

Separate:

A. Longform opportunities around 8-10 minutes
B. Shorts opportunities

For each important trend explain:

- What is trending
- Why it is trending
- Audience psychology
- Content format
- Genre
- Entertainment subgenre if applicable
- Example videos from supplied data
- Opportunity for a creator

Then identify the strongest content opportunities.
"""

    if section_id == 2:

        return """
SECTION 2 — WORLD YOUTUBE TRENDS

Analyze worldwide YouTube trends using the supplied world data.

Separate:

A. Longform 8-10 minute opportunities
B. Shorts opportunities

Explain why each trend matters.

For entertainment identify exact genre/subgenre.

Use actual supplied videos as examples.
"""

    if section_id == 3:

        return """
SECTION 3 — YOUTUBE GENRE TRENDS

Identify the strongest genre patterns.

Include:

- Genre
- Subgenre
- Longform potential
- Shorts potential
- Why audiences watch
- Emotional trigger
- Storytelling pattern
- Example videos
- Opportunity

Entertainment must be specific:

Thriller is not enough.

Use:

Psychological Thriller
Crime Thriller
Mystery Thriller
Dark Comedy
Horror Comedy
etc.
"""

    if section_id == 4:

        return """
SECTION 4 — TREND BASED SHORTS IDEAS

Create extremely engaging Shorts ideas based on India + World trends.

Each idea must contain:

title
roman_telugu_logline
genre
subgenre
hook
why_it_is_clickable
twist_or_payoff
thumbnail_concept
ctr_score
retention_score
novelty_score
emotional_impact
feasibility
"""

    if section_id == 5:

        return """
SECTION 5 — TREND BASED LONGFORM IDEAS

Create premium 8-10 minute ideas based on India + World trends.

Each idea must contain:

title
roman_telugu_logline
genre
subgenre
opening_30_seconds
central_question
story_premise
escalation
major_reveal
twist_or_payoff
ending
thumbnail_concept
ctr_score
retention_score
novelty_score
emotional_impact
feasibility
"""

    if section_id == 6:

        return """
SECTION 6 — GENERAL ORIGINAL SHORTS

Create original Shorts ideas.

DO NOT simply copy current trends.

Use universal audience psychology.

Ideas must be highly clickable and surprising.

Include:

title
roman_telugu_logline
genre
hook
why_it_is_clickable
twist_or_payoff
thumbnail_concept
ctr_score
retention_score
novelty_score
emotional_impact
feasibility
"""

    if section_id == 7:

        return """
SECTION 7 — GENERAL ORIGINAL LONGFORM

Create original 8-10 minute concepts.

DO NOT copy current trends.

Every idea must support:

HOOK
QUESTION
ESCALATION
DISCOVERY
REVEAL
PAYOFF

Include:

title
roman_telugu_logline
genre
subgenre
opening_30_seconds
story_premise
escalation
major_reveal
ending
thumbnail_concept
ctr_score
retention_score
novelty_score
emotional_impact
feasibility
"""

    return """
SECTION 8 — GENRE FUSION

Combine genre trends to create premium high-CTR concepts.

Use combinations such as:

Psychological Thriller + Social Experiment
Crime Mystery + Dark Comedy
Technology + Mystery
Science + Thriller
Horror + Investigation
Documentary + Psychological Mystery
Gaming + Real World Mystery

Generate concepts that feel fresh.

Include:

title
roman_telugu_logline
primary_genre
secondary_genre
hook
story_premise
why_genres_work_together
twist_or_payoff
thumbnail_concept
ctr_score
retention_score
novelty_score
emotional_impact
feasibility
"""


# ============================================================
# GENERATE SECTION
# ============================================================

def generate_section(
    section: Dict[str, Any],
    india_data: List[Dict[str, Any]],
    world_data: List[Dict[str, Any]]
) -> Dict[str, Any]:

    instruction = section_instruction(
        section
    )

    prompt = f"""
You are generating:

SECTION {section["id"]}:
{section["name"]}

{instruction}

============================================================
CURRENT INDIA DATA
============================================================

{json.dumps(
    compact_videos(india_data),
    ensure_ascii=False,
    indent=2
)}

============================================================
CURRENT WORLD DATA
============================================================

{json.dumps(
    compact_videos(world_data),
    ensure_ascii=False,
    indent=2
)}

============================================================
QUALITY CONTROL
============================================================

Generate {IDEAS_PER_SECTION} concepts.

However:

QUALITY > QUANTITY.

If a concept feels generic, replace it.

The first concept must be the strongest.

At least several concepts should have:

- a strong mystery
- an unexpected reversal
- a powerful emotional question
- a visually obvious thumbnail
- a curiosity gap

Do not make every idea horror.

Do not make every idea thriller.

Use genre diversity.

Roman Telugu must sound natural.

Return:

{{
    "section_id": {section["id"]},
    "section_name": "{section["name"]}",
    "trend_analysis": [],
    "ideas": []
}}

ONLY JSON.
"""

    raw = call_llm(prompt)

    return parse_json(
        raw
    )


# ============================================================
# MAIN REPORT FUNCTION
# ============================================================

def generate_report() -> Dict[str, Any]:

    print(
        "Fetching India YouTube trends..."
    )

    india_data = get_youtube_trending(
        "IN"
    )

    print(
        f"India videos: {len(india_data)}"
    )

    print(
        "Fetching World YouTube trends..."
    )

    world_data = get_youtube_trending(
        "US"
    )

    print(
        f"World videos: {len(world_data)}"
    )

    report = {

        "generator":
            "YouTube High CTR Idea Generator",

        "version":
            "2.0",

        "sections":
            []
    }

    for section in SECTIONS:

        print(
            "\n"
            + "=" * 60
        )

        print(
            f"GENERATING SECTION {section['id']}: "
            f"{section['name']}"
        )

        print(
            "=" * 60
        )

        try:

            result = generate_section(
                section,
                india_data,
                world_data
            )

            report[
                "sections"
            ].append(
                result
            )

            print(
                f"Section {section['id']} completed."
            )

        except Exception as exc:

            print(
                f"Section {section['id']} failed: {exc}"
            )

            # Do not kill the entire workflow.
            report[
                "sections"
            ].append({

                "section_id":
                    section["id"],

                "section_name":
                    section["name"],

                "trend_analysis":
                    [],

                "ideas":
                    [],

                "error":
                    str(exc)
            })

    return report


# ============================================================
# TEXT RENDERER
# ============================================================

def clean_text(value: Any) -> str:

    if value is None:
        return ""

    if isinstance(value, list):

        return ", ".join(
            clean_text(x)
            for x in value
        )

    if isinstance(value, dict):

        return "; ".join(
            f"{k}: {clean_text(v)}"
            for k, v in value.items()
        )

    return str(value)


def render_report(
    report: Dict[str, Any]
) -> str:

    lines = []

    lines.append(
        "=" * 80
    )

    lines.append(
        "YOUTUBE HIGH CTR IDEA GENERATOR"
    )

    lines.append(
        "INDIA + WORLD + GENRE + ORIGINAL IDEAS"
    )

    lines.append(
        "=" * 80
    )

    lines.append("")

    for section in report.get(
        "sections",
        []
    ):

        lines.append(
            "\n"
            + "#" * 80
        )

        lines.append(
            f"SECTION "
            f"{section.get('section_id', '')}: "
            f"{section.get('section_name', '')}"
        )

        lines.append(
            "#" * 80
        )

        trend_analysis = section.get(
            "trend_analysis",
            []
        )

        if trend_analysis:

            lines.append(
                "\nTREND ANALYSIS\n"
            )

            for trend in trend_analysis:

                lines.append(
                    f"Trend: "
                    f"{clean_text(trend.get('trend_name'))}"
                )

                lines.append(
                    f"Why Trending: "
                    f"{clean_text(trend.get('why_trending'))}"
                )

                lines.append(
                    f"Genre: "
                    f"{clean_text(trend.get('genre'))}"
                )

                lines.append(
                    f"Subgenre: "
                    f"{clean_text(trend.get('subgenre'))}"
                )

                lines.append("")

        ideas = section.get(
            "ideas",
            []
        )

        for index, idea in enumerate(
            ideas,
            start=1
        ):

            lines.append(
                "\n"
                + "-" * 70
            )

            lines.append(
                f"#{index} "
                f"{clean_text(idea.get('title'))}"
            )

            lines.append(
                "-" * 70
            )

            # IMPORTANT:
            # LOGLINE IS SHOWN IMMEDIATELY UNDER TITLE.

            lines.append(
                "\n🔥 HIGH CTR IDEA + LOGLINE"
            )

            lines.append(
                clean_text(
                    idea.get(
                        "roman_telugu_logline"
                    )
                )
            )

            lines.append(
                f"\nGenre: "
                f"{clean_text(idea.get('genre'))}"
            )

            lines.append(
                f"Subgenre: "
                f"{clean_text(idea.get('subgenre'))}"
            )

            lines.append(
                f"\nHook:\n"
                f"{clean_text(idea.get('hook'))}"
            )

            lines.append(
                f"\nWhy People Will Click:\n"
                f"{clean_text(idea.get('why_it_is_clickable'))}"
            )

            lines.append(
                f"\nStory Premise:\n"
                f"{clean_text(idea.get('story_premise'))}"
            )

            lines.append(
                f"\nTwist / Payoff:\n"
                f"{clean_text(idea.get('twist_or_payoff'))}"
            )

            lines.append(
                f"\nThumbnail Concept:\n"
                f"{clean_text(idea.get('thumbnail_concept'))}"
            )

            lines.append(
                "\nSCORES:"
            )

            lines.append(
                f"CTR: "
                f"{clean_text(idea.get('ctr_score'))}/100"
            )

            lines.append(
                f"Retention: "
                f"{clean_text(idea.get('retention_score'))}/100"
            )

            lines.append(
                f"Novelty: "
                f"{clean_text(idea.get('novelty_score'))}/100"
            )

            lines.append(
                f"Emotional Impact: "
                f"{clean_text(idea.get('emotional_impact'))}/100"
            )

            lines.append(
                f"Feasibility: "
                f"{clean_text(idea.get('feasibility'))}/100"
            )

            if idea.get(
                "opening_30_seconds"
            ):

                lines.append(
                    "\nOpening 30 Seconds:\n"
                    + clean_text(
                        idea.get(
                            "opening_30_seconds"
                        )
                    )
                )

            if idea.get(
                "escalation"
            ):

                lines.append(
                    "\nEscalation:\n"
                    + clean_text(
                        idea.get(
                            "escalation"
                        )
                    )
                )

            if idea.get(
                "major_reveal"
            ):

                lines.append(
                    "\nMajor Reveal:\n"
                    + clean_text(
                        idea.get(
                            "major_reveal"
                        )
                    )
                )

            if idea.get(
                "ending"
            ):

                lines.append(
                    "\nEnding:\n"
                    + clean_text(
                        idea.get(
                            "ending"
                        )
                    )
                )

    return "\n".join(
        lines
    )


# ============================================================
# EXPORT
# ============================================================

def save_report(
    report: Dict[str, Any]
) -> Dict[str, Path]:

    json_path = (
        OUTPUT_DIR /
        "youtube_high_ctr_report.json"
    )

    txt_path = (
        OUTPUT_DIR /
        "youtube_high_ctr_report.txt"
    )

    json_path.write_text(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    txt_path.write_text(
        render_report(report),
        encoding="utf-8"
    )

    return {
        "json": json_path,
        "txt": txt_path
    }


# ============================================================
# COMPATIBILITY
# ============================================================

if __name__ == "__main__":

    report = generate_report()

    paths = save_report(
        report
    )

    print(
        "\nJSON:",
        paths["json"]
    )

    print(
        "TXT:",
        paths["txt"]
    )
