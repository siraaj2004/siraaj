# src/idea_generator.py

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
# ENVIRONMENT
# ============================================================

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-2.5-flash"
).strip()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()
OPENROUTER_MODEL = os.getenv(
    "OPENROUTER_MODEL",
    "google/gemini-2.5-flash"
).strip()

IDEAS_PER_SECTION = int(
    os.getenv("IDEAS_PER_SECTION", "8")
)

REQUEST_TIMEOUT = int(
    os.getenv("REQUEST_TIMEOUT", "180")
)


# ============================================================
# SECTION DEFINITIONS
# ============================================================

SECTION_DEFINITIONS = [
    {
        "id": 1,
        "name": "India YouTube Trends",
        "purpose": "India longform and Shorts trends",
    },
    {
        "id": 2,
        "name": "World YouTube Trends",
        "purpose": "World longform and Shorts trends",
    },
    {
        "id": 3,
        "name": "YouTube Genre Trends",
        "purpose": "Genre and entertainment subgenre trends",
    },
    {
        "id": 4,
        "name": "Trend-Based Shorts Ideas",
        "purpose": "High-CTR Shorts based on India and World trends",
    },
    {
        "id": 5,
        "name": "Trend-Based Longform Ideas",
        "purpose": "High-CTR 8-10 minute videos based on trends",
    },
    {
        "id": 6,
        "name": "General Original Shorts Ideas",
        "purpose": "Original non-trend-dependent Shorts",
    },
    {
        "id": 7,
        "name": "General Original Longform Ideas",
        "purpose": "Original non-trend-dependent 8-10 minute videos",
    },
    {
        "id": 8,
        "name": "Genre-Fusion High CTR Ideas",
        "purpose": "Creative genre combinations",
    },
]


# ============================================================
# SYSTEM PROMPT
# ============================================================

SYSTEM_PROMPT = """
You are an elite YouTube creative strategist, viral-content researcher,
screenwriter and high-CTR idea generator.

Your job is NOT to generate generic YouTube ideas.

Every idea must create the reaction:

"WAH! WHAT AN IDEA!"

The concepts must contain at least one strong curiosity mechanism:

- mystery
- unanswered question
- unexpected discovery
- contradiction
- hidden truth
- psychological conflict
- emotional stakes
- danger
- investigation
- reversal
- unusual human behavior
- impossible-looking situation
- countdown
- secret
- identity reveal
- cause-and-effect mystery

STRICTLY AVOID:

- generic 24-hour challenges
- generic pranks
- generic reactions
- generic vlogs
- generic food videos
- generic motivation
- generic interviews
- generic gaming challenges
- generic top-10 lists
- generic facts
- generic "I tried X"
- generic AI videos
- generic horror stories
- generic "scary things"
- copied movie plots
- boring trend summaries
- filler concepts

Entertainment ideas MUST identify the specific subgenre.

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
Crime Investigation
Emotional Drama
Sci-Fi Mystery
Social Experiment
Documentary
Adventure
Action
Fantasy

For Shorts:

The first sentence must immediately create a curiosity loop.

For longform:

Use:

HOOK
QUESTION
ESCALATION
DISCOVERY
COMPLICATION
REVEAL
PAYOFF

Roman Telugu must sound natural and cinematic.

Do not translate English word-by-word.

Example style:

"Night 2:13 ki tana phone ki tana own number nunchi call vastundi.
Call lift chesthe avatala tana voice lone oka warning vinipisthundi.
Kaani aa warning lo cheppina incident next morning jaragabothundi."

Each idea must include:

- high CTR title
- Roman Telugu logline
- genre
- subgenre
- hook
- why viewers click
- core concept
- story progression
- thumbnail concept
- novelty
- retention potential
- feasibility
- emotional impact
- CTR score

Do not give every idea a 95+ score.

Reserve 90+ for genuinely exceptional ideas.
"""


# ============================================================
# DATA NORMALIZATION
# ============================================================

def normalize_data(data: Any) -> Dict[str, List[Dict[str, Any]]]:
    """
    Converts whatever the trend collector returns into:

    {
        "india": [...],
        "world": [...],
        "genres": [...],
        "all": [...]
    }
    """

    result = {
        "india": [],
        "world": [],
        "genres": [],
        "all": [],
    }

    if data is None:
        return result

    if isinstance(data, list):
        result["all"] = data
        return result

    if not isinstance(data, dict):
        return result

    # --------------------------------------------------------
    # INDIA
    # --------------------------------------------------------

    india_keys = [
        "india",
        "india_trends",
        "india_youtube",
        "IN",
        "in",
    ]

    for key in india_keys:
        value = data.get(key)

        if isinstance(value, list):
            result["india"].extend(value)

        elif isinstance(value, dict):
            result["india"].extend(
                value.get("videos", [])
                if isinstance(value.get("videos"), list)
                else []
            )

    # --------------------------------------------------------
    # WORLD
    # --------------------------------------------------------

    world_keys = [
        "world",
        "world_trends",
        "world_youtube",
        "global",
        "US",
        "us",
    ]

    for key in world_keys:
        value = data.get(key)

        if isinstance(value, list):
            result["world"].extend(value)

        elif isinstance(value, dict):
            result["world"].extend(
                value.get("videos", [])
                if isinstance(value.get("videos"), list)
                else []
            )

    # --------------------------------------------------------
    # GENRES
    # --------------------------------------------------------

    genre_keys = [
        "genres",
        "genre_trends",
        "youtube_genres",
        "categories",
    ]

    for key in genre_keys:
        value = data.get(key)

        if isinstance(value, list):
            result["genres"].extend(value)

        elif isinstance(value, dict):
            for genre_name, genre_data in value.items():

                if isinstance(genre_data, list):
                    for item in genre_data:
                        if isinstance(item, dict):
                            item = dict(item)
                            item.setdefault("genre", genre_name)
                            result["genres"].append(item)

                elif isinstance(genre_data, dict):
                    item = dict(genre_data)
                    item.setdefault("genre", genre_name)
                    result["genres"].append(item)

    # --------------------------------------------------------
    # GENERAL VIDEOS / TRENDS
    # --------------------------------------------------------

    for key in [
        "all",
        "videos",
        "trends",
        "data",
        "results",
    ]:
        value = data.get(key)

        if isinstance(value, list):
            result["all"].extend(value)

    # --------------------------------------------------------
    # IF INDIA/WORLD WERE NOT FOUND, USE ALL DATA
    # --------------------------------------------------------

    if not result["india"] and result["all"]:
        result["india"] = result["all"][:35]

    if not result["world"] and result["all"]:
        result["world"] = result["all"][:35]

    # --------------------------------------------------------
    # DEDUPLICATE
    # --------------------------------------------------------

    for key in result:
        seen = set()
        clean = []

        for item in result[key]:

            if isinstance(item, str):
                item = {"title": item}

            if not isinstance(item, dict):
                continue

            title = str(
                item.get("title")
                or item.get("name")
                or ""
            ).strip()

            marker = title.lower()

            if marker and marker in seen:
                continue

            if marker:
                seen.add(marker)

            clean.append(item)

        result[key] = clean

    return result


# ============================================================
# COMPACT TREND DATA
# ============================================================

def compact_items(
    items: List[Dict[str, Any]],
    limit: int = 35
) -> List[Dict[str, Any]]:

    output = []

    for item in items[:limit]:

        if not isinstance(item, dict):
            continue

        cleaned = {
            "title": item.get("title")
            or item.get("name")
            or "",
            "channel": item.get("channel")
            or item.get("channel_title")
            or "",
            "views": item.get("views")
            or item.get("view_count")
            or 0,
            "likes": item.get("likes")
            or item.get("like_count")
            or 0,
            "comments": item.get("comments")
            or item.get("comment_count")
            or 0,
            "published_at": item.get("published_at")
            or item.get("published")
            or "",
            "category": item.get("category")
            or item.get("category_name")
            or "",
            "genre": item.get("genre")
            or item.get("subgenre")
            or "",
            "url": item.get("url")
            or item.get("video_url")
            or "",
        }

        output.append(cleaned)

    return output


# ============================================================
# AI CALL — GEMINI
# ============================================================

def call_gemini(prompt: str) -> Dict[str, Any]:

    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not configured.")

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
            "maxOutputTokens": 30000,
            "responseMimeType": "application/json",
        },
    }

    response = requests.post(
        url,
        params=params,
        json=payload,
        timeout=REQUEST_TIMEOUT,
    )

    response.raise_for_status()

    body = response.json()

    try:
        text = body["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(
            f"Unexpected Gemini response: {json.dumps(body)[:2000]}"
        ) from exc

    return parse_json_response(text)


# ============================================================
# AI CALL — OPENROUTER
# ============================================================

def call_openrouter(prompt: str) -> Dict[str, Any]:

    if not OPENROUTER_API_KEY:
        raise RuntimeError(
            "OPENROUTER_API_KEY is not configured."
        )

    url = "https://openrouter.ai/api/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/",
        "X-Title": "YouTube High CTR Idea Generator",
    }

    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        "temperature": 0.95,
        "top_p": 0.95,
        "max_tokens": 30000,
    }

    response = requests.post(
        url,
        headers=headers,
        json=payload,
        timeout=REQUEST_TIMEOUT,
    )

    response.raise_for_status()

    body = response.json()

    try:
        text = body["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(
            f"Unexpected OpenRouter response: {json.dumps(body)[:2000]}"
        ) from exc

    return parse_json_response(text)


# ============================================================
# JSON PARSER
# ============================================================

def parse_json_response(text: str) -> Dict[str, Any]:

    if not text:
        raise ValueError("AI returned empty response.")

    text = text.strip()

    # Remove markdown fences
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

    try:
        parsed = json.loads(text)

        if isinstance(parsed, dict):
            return parsed

        return {
            "ideas": parsed
            if isinstance(parsed, list)
            else []
        }

    except json.JSONDecodeError:

        # Try extracting first JSON object
        start = text.find("{")
        end = text.rfind("}")

        if start != -1 and end != -1 and end > start:

            candidate = text[start:end + 1]

            try:
                parsed = json.loads(candidate)

                if isinstance(parsed, dict):
                    return parsed

            except json.JSONDecodeError:
                pass

        # Try extracting JSON array
        start = text.find("[")
        end = text.rfind("]")

        if start != -1 and end != -1 and end > start:

            candidate = text[start:end + 1]

            try:
                parsed = json.loads(candidate)

                if isinstance(parsed, list):
                    return {
                        "ideas": parsed
                    }

            except json.JSONDecodeError:
                pass

    raise ValueError(
        "Could not parse AI response as JSON.\n"
        + text[:3000]
    )


# ============================================================
# AI ROUTER
# ============================================================

def call_ai(prompt: str) -> Dict[str, Any]:

    if GEMINI_API_KEY:
        return call_gemini(prompt)

    if OPENROUTER_API_KEY:
        return call_openrouter(prompt)

    raise RuntimeError(
        "No AI API key configured. "
        "Set GEMINI_API_KEY or OPENROUTER_API_KEY in GitHub Secrets/.env."
    )


# ============================================================
# SECTION INSTRUCTIONS
# ============================================================

def get_section_instruction(section_id: int) -> str:

    if section_id == 1:

        return """
SECTION 1 — INDIA YOUTUBE TRENDS

Analyze India YouTube trends.

Separate:

A. Longform 8–10 minute trends
B. Shorts trends

For every trend provide:

- trend
- example videos/titles from supplied data
- why it is trending
- audience psychology
- format
- entertainment genre/subgenre when applicable
- opportunity for creators

Do NOT invent trend statistics that are not present in the supplied data.
"""

    if section_id == 2:

        return """
SECTION 2 — WORLD YOUTUBE TRENDS

Analyze World YouTube trends.

Separate:

A. Longform 8–10 minute trends
B. Shorts trends

For every trend provide:

- trend
- example videos/titles from supplied data
- why it is trending
- audience psychology
- format
- entertainment genre/subgenre when applicable
- opportunity for creators

Do NOT invent statistics.
"""

    if section_id == 3:

        return """
SECTION 3 — YOUTUBE GENRE TRENDS

Identify strong genres and entertainment subgenres.

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
Crime
Investigation
Documentary
Social Experiment
Emotional Drama
Sci-Fi
Adventure
Action
Fantasy

Explain:

- why the genre works
- what viewer emotion it triggers
- longform opportunity
- Shorts opportunity
- typical hooks
- what makes the genre clickable
"""

    if section_id == 4:

        return """
SECTION 4 — TREND-BASED SHORTS IDEAS

Generate highly original Shorts concepts based on India and World trends.

IMPORTANT:

The idea itself comes FIRST.

Each idea must contain:

1. High CTR title
2. Roman Telugu logline
3. Genre
4. Subgenre
5. Immediate hook
6. Curiosity question
7. Concept
8. Escalation
9. Reveal/payoff
10. Thumbnail
11. Why people click
12. CTR score
13. Retention score
14. Novelty score
15. Feasibility score
16. Emotional impact score

Avoid generic Shorts.
"""

    if section_id == 5:

        return """
SECTION 5 — TREND-BASED LONGFORM IDEAS

Generate original 8–10 minute concepts using India and World trends.

Use:

HOOK
QUESTION
ESCALATION
DISCOVERY
COMPLICATION
REVEAL
PAYOFF

Each idea must contain:

1. High CTR title
2. Roman Telugu logline
3. Genre
4. Subgenre
5. Hook
6. Main question
7. Story premise
8. Opening 30 seconds
9. Escalation
10. Discovery
11. Complication
12. Major reveal
13. Twist/payoff
14. Ending
15. Thumbnail
16. CTR score
17. Retention score
18. Novelty score
19. Feasibility score
20. Emotional impact score

Do NOT produce generic challenge/vlog/reaction concepts.
"""

    if section_id == 6:

        return """
SECTION 6 — GENERAL ORIGINAL SHORTS IDEAS

Generate original Shorts ideas that do NOT depend on current trends.

They should still feel highly clickable.

Use:

WHY
HOW
WHAT
IS THAT REALLY POSSIBLE?

Each idea needs a strong curiosity gap.

Avoid generic facts, motivation, pranks, reactions and challenges.

Include natural Roman Telugu logline.
"""

    if section_id == 7:

        return """
SECTION 7 — GENERAL ORIGINAL LONGFORM IDEAS

Generate original 8–10 minute concepts that can work even without a current trend.

Every concept needs:

HOOK
QUESTION
ESCALATION
DISCOVERY
COMPLICATION
REVEAL
PAYOFF

Prioritize:

- mystery
- investigation
- psychological conflict
- unusual human behavior
- hidden truth
- emotional stakes
- unexpected reversal
- cinematic storytelling

Include natural Roman Telugu logline.
"""

    if section_id == 8:

        return """
SECTION 8 — GENRE-FUSION HIGH CTR IDEAS

Combine two or more genres to create concepts that feel fresh.

Examples:

Mystery + Comedy
Crime + Psychological Thriller
Social Experiment + Thriller
Sci-Fi + Mystery
Emotional Drama + Mystery
Horror + Dark Comedy
Investigation + Survival

Do not simply put two genre names together.

The combination must create a new story mechanism.

Explain:

- primary genre
- secondary genre
- why the combination works
- high CTR title
- Roman Telugu logline
- hook
- story
- twist
- thumbnail
- scores
"""


# ============================================================
# PROMPT BUILDER
# ============================================================

def build_section_prompt(
    section_id: int,
    section_name: str,
    trend_data: Dict[str, List[Dict[str, Any]]],
) -> str:

    india = compact_items(
        trend_data.get("india", []),
        35,
    )

    world = compact_items(
        trend_data.get("world", []),
        35,
    )

    genres = compact_items(
        trend_data.get("genres", []),
        35,
    )

    all_data = compact_items(
        trend_data.get("all", []),
        35,
    )

    instruction = get_section_instruction(section_id)

    prompt = f"""
Generate SECTION {section_id} — {section_name}.

{instruction}

NUMBER OF IDEAS:
{IDEAS_PER_SECTION}

SUPPLIED INDIA TREND DATA:
{json.dumps(india, ensure_ascii=False, indent=2)}

SUPPLIED WORLD TREND DATA:
{json.dumps(world, ensure_ascii=False, indent=2)}

SUPPLIED GENRE DATA:
{json.dumps(genres, ensure_ascii=False, indent=2)}

SUPPLIED GENERAL DATA:
{json.dumps(all_data, ensure_ascii=False, indent=2)}

IMPORTANT:

Use the supplied data as evidence.

If the data does not support a specific factual claim,
do not invent it.

However, creative ideas can be original.

Return ONLY valid JSON.

Use exactly this structure:

{{
  "section_id": {section_id},
  "section_name": "{section_name}",
  "trend_analysis": [
    {{
      "trend": "...",
      "what_is_happening": "...",
      "why_trending": "...",
      "audience_psychology": "...",
      "format": "...",
      "genre": "...",
      "subgenre": "...",
      "creator_opportunity": "..."
    }}
  ],
  "ideas": [
    {{
      "rank": 1,
      "title": "...",
      "high_ctr_idea": "...",
      "roman_telugu_logline": "...",
      "genre": "...",
      "subgenre": "...",
      "hook": "...",
      "why_people_click": "...",
      "story_premise": "...",
      "opening_30_seconds": "...",
      "main_question": "...",
      "escalation": "...",
      "discovery": "...",
      "complication": "...",
      "major_reveal": "...",
      "twist_payoff": "...",
      "ending": "...",
      "thumbnail_concept": "...",
      "ctr_score": 0,
      "retention_score": 0,
      "novelty_score": 0,
      "feasibility_score": 0,
      "emotional_impact_score": 0
    }}
  ]
}}

The "high_ctr_idea" must describe the actual compelling concept,
not merely repeat the title.

The Roman Telugu logline must be natural and cinematic.

Return no markdown.
Return no explanation outside JSON.
"""

    return prompt


# ============================================================
# GENERATE ONE SECTION
# ============================================================

def generate_section(
    section_id: int,
    section_name: str,
    trend_data: Dict[str, List[Dict[str, Any]]],
) -> Dict[str, Any]:

    prompt = build_section_prompt(
        section_id,
        section_name,
        trend_data,
    )

    result = call_ai(prompt)

    result.setdefault(
        "section_id",
        section_id,
    )

    result.setdefault(
        "section_name",
        section_name,
    )

    if not isinstance(result.get("trend_analysis"), list):
        result["trend_analysis"] = []

    if not isinstance(result.get("ideas"), list):
        result["ideas"] = []

    return result


# ============================================================
# MAIN FUNCTION
# ============================================================

def generate_report(data: Any) -> Dict[str, Any]:
    """
    IMPORTANT:
    app.py calls:

        report = generate_report(data)

    Therefore this function MUST accept data.
    """

    trend_data = normalize_data(data)

    report = {
        "generator": "YouTube High CTR Idea Generator",
        "version": "4.0",
        "quality_standard": "Very High Engagement",
        "sections": [],
    }

    for section in SECTION_DEFINITIONS:

        section_id = section["id"]
        section_name = section["name"]

        print(
            f"[AI] Generating section "
            f"{section_id}/8: {section_name}"
        )

        try:

            result = generate_section(
                section_id,
                section_name,
                trend_data,
            )

            report["sections"].append(result)

            idea_count = len(
                result.get("ideas", [])
            )

            print(
                f"[AI] Section {section_id} complete "
                f"({idea_count} ideas)"
            )

        except Exception as exc:

            print(
                f"[ERROR] Section {section_id} failed: "
                f"{exc}"
            )

            # Do NOT kill the entire GitHub Action.
            report["sections"].append(
                {
                    "section_id": section_id,
                    "section_name": section_name,
                    "trend_analysis": [],
                    "ideas": [],
                    "error": str(exc),
                }
            )

    return report


# ============================================================
# TEXT RENDERER
# ============================================================

def render_report(report: Dict[str, Any]) -> str:

    lines = []

    lines.append("=" * 90)
    lines.append("YOUTUBE HIGH CTR IDEA GENERATOR")
    lines.append("VERY HIGH ENGAGEMENT EDITION")
    lines.append("=" * 90)
    lines.append("")

    for section in report.get("sections", []):

        section_id = section.get(
            "section_id",
            ""
        )

        section_name = section.get(
            "section_name",
            ""
        )

        lines.append("#" * 90)
        lines.append(
            f"SECTION {section_id} — {section_name}"
        )
        lines.append("#" * 90)
        lines.append("")

        # ----------------------------------------------------
        # TREND ANALYSIS
        # ----------------------------------------------------

        trend_analysis = section.get(
            "trend_analysis",
            []
        )

        if trend_analysis:

            lines.append(
                "TREND ANALYSIS"
            )
            lines.append("-" * 90)

            for index, trend in enumerate(
                trend_analysis,
                start=1,
            ):

                lines.append(
                    f"{index}. {trend.get('trend', '')}"
                )

                lines.append(
                    f"   What is happening: "
                    f"{trend.get('what_is_happening', '')}"
                )

                lines.append(
                    f"   Why trending: "
                    f"{trend.get('why_trending', '')}"
                )

                lines.append(
                    f"   Audience psychology: "
                    f"{trend.get('audience_psychology', '')}"
                )

                lines.append(
                    f"   Format: "
                    f"{trend.get('format', '')}"
                )

                lines.append(
                    f"   Genre: "
                    f"{trend.get('genre', '')}"
                )

                lines.append(
                    f"   Subgenre: "
                    f"{trend.get('subgenre', '')}"
                )

                lines.append(
                    f"   Creator opportunity: "
                    f"{trend.get('creator_opportunity', '')}"
                )

                lines.append("")

        # ----------------------------------------------------
        # IDEAS
        # ----------------------------------------------------

        ideas = section.get(
            "ideas",
            []
        )

        if ideas:

            lines.append(
                "HIGH CTR IDEAS"
            )
            lines.append("-" * 90)
            lines.append("")

        for index, idea in enumerate(
            ideas,
            start=1,
        ):

            title = (
                idea.get("title")
                or idea.get("high_ctr_idea")
                or f"Idea {index}"
            )

            lines.append(
                f"{index}. {title}"
            )

            lines.append("")

            # MOST IMPORTANT:
            # Logline immediately after title.

            lines.append(
                "🔥 HIGH CTR IDEA LOGLINE"
            )

            lines.append(
                idea.get(
                    "roman_telugu_logline",
                    ""
                )
            )

            lines.append("")

            lines.append(
                f"Genre: {idea.get('genre', '')}"
            )

            lines.append(
                f"Subgenre: {idea.get('subgenre', '')}"
            )

            lines.append("")

            lines.append(
                f"🔥 High CTR Concept: "
                f"{idea.get('high_ctr_idea', '')}"
            )

            lines.append(
                f"Hook: {idea.get('hook', '')}"
            )

            lines.append(
                f"Why people click: "
                f"{idea.get('why_people_click', '')}"
            )

            lines.append(
                f"Main question: "
                f"{idea.get('main_question', '')}"
            )

            lines.append("")

            lines.append(
                f"Story premise: "
                f"{idea.get('story_premise', '')}"
            )

            lines.append(
                f"Opening 30 seconds: "
                f"{idea.get('opening_30_seconds', '')}"
            )

            lines.append(
                f"Escalation: "
                f"{idea.get('escalation', '')}"
            )

            lines.append(
                f"Discovery: "
                f"{idea.get('discovery', '')}"
            )

            lines.append(
                f"Complication: "
                f"{idea.get('complication', '')}"
            )

            lines.append(
                f"Major reveal: "
                f"{idea.get('major_reveal', '')}"
            )

            lines.append(
                f"Twist / Payoff: "
                f"{idea.get('twist_payoff', '')}"
            )

            lines.append(
                f"Ending: "
                f"{idea.get('ending', '')}"
            )

            lines.append("")

            lines.append(
                f"Thumbnail: "
                f"{idea.get('thumbnail_concept', '')}"
            )

            lines.append("")

            lines.append(
                "SCORES"
            )

            lines.append(
                f"CTR: "
                f"{idea.get('ctr_score', 0)}/100"
            )

            lines.append(
                f"Retention: "
                f"{idea.get('retention_score', 0)}/100"
            )

            lines.append(
                f"Novelty: "
                f"{idea.get('novelty_score', 0)}/100"
            )

            lines.append(
                f"Feasibility: "
                f"{idea.get('feasibility_score', 0)}/100"
            )

            lines.append(
                f"Emotional Impact: "
                f"{idea.get('emotional_impact_score', 0)}/100"
            )

            lines.append("")
            lines.append("-" * 90)
            lines.append("")

        if section.get("error"):

            lines.append(
                f"SECTION ERROR: "
                f"{section.get('error')}"
            )

            lines.append("")

    return "\n".join(lines)


# ============================================================
# SAVE REPORT
# ============================================================

def save_report(report: Dict[str, Any]) -> Dict[str, str]:

    json_path = OUTPUT_DIR / "youtube_high_ctr_report.json"
    txt_path = OUTPUT_DIR / "youtube_high_ctr_report.txt"

    json_path.write_text(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    text = render_report(report)

    txt_path.write_text(
        text,
        encoding="utf-8",
    )

    print(
        f"[output] JSON -> {json_path}"
    )

    print(
        f"[output] TXT  -> {txt_path}"
    )

    return {
        "json": str(json_path),
        "txt": str(txt_path),
    }


# ============================================================
# DIRECT TEST
# ============================================================

if __name__ == "__main__":

    print(
        "Testing YouTube High CTR Idea Generator..."
    )

    sample_data = {
        "india": [],
        "world": [],
        "genres": [],
        "all": [],
    }

    report = generate_report(
        sample_data
    )

    paths = save_report(
        report
    )

    print("")
    print("Generation completed.")
    print(paths)
