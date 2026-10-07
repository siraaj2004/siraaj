# src/idea_generator.py

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List

import requests
from dotenv import load_dotenv


# ============================================================
# PATHS / ENVIRONMENT
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

load_dotenv(BASE_DIR / ".env")


def env_int(name: str, default: int) -> int:
    """Safely read an integer environment variable."""
    try:
        return int(os.getenv(name, str(default)).strip())
    except (TypeError, ValueError):
        return default


GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-2.5-flash",
).strip()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()
OPENROUTER_MODEL = os.getenv(
    "OPENROUTER_MODEL",
    "google/gemini-2.5-flash",
).strip()

IDEAS_PER_SECTION = env_int("IDEAS_PER_SECTION", 8)
REQUEST_TIMEOUT = env_int("REQUEST_TIMEOUT", 180)


# ============================================================
# SECTION DEFINITIONS
# ============================================================

SECTION_DEFINITIONS = [
    {
        "id": 1,
        "name": "India YouTube Trends",
    },
    {
        "id": 2,
        "name": "World YouTube Trends",
    },
    {
        "id": 3,
        "name": "YouTube Genre Trends",
    },
    {
        "id": 4,
        "name": "Trend-Based Shorts Ideas",
    },
    {
        "id": 5,
        "name": "Trend-Based Longform Ideas",
    },
    {
        "id": 6,
        "name": "General India and World Shorts Ideas",
    },
    {
        "id": 7,
        "name": "General India and World Longform Ideas",
    },
    {
        "id": 8,
        "name": "Genre-Fusion High-CTR Ideas",
    },
]


# ============================================================
# SYSTEM PROMPT
# ============================================================

SYSTEM_PROMPT = """
You are an elite YouTube content strategist, story developer,
trend analyst and high-CTR idea generator.

Your job is to create ORIGINAL YouTube concepts that make a creator
think:

"WAHH, WHAT A IDEA!"

The concepts must NOT feel generic, copied, predictable or like
basic AI-generated YouTube ideas.

IMPORTANT RULES:

1. Prioritize curiosity.
2. Prioritize strong unanswered questions.
3. Prioritize unusual premises.
4. Prioritize visual storytelling.
5. Prioritize emotional stakes.
6. Prioritize retention.
7. Prioritize thumbnail potential.
8. Prioritize title curiosity.
9. Use trends as inspiration, not as copies.
10. Do not invent fake statistics.
11. Do not claim a video is trending unless supported by the supplied data.
12. If entertainment is involved, ALWAYS specify the exact subgenre.

Entertainment subgenres may include:

- Thriller
- Psychological Thriller
- Mystery Thriller
- Crime Thriller
- Survival Thriller
- Dark Comedy
- Situational Comedy
- Horror Comedy
- Psychological Horror
- Crime Investigation
- Emotional Drama
- Sci-Fi Mystery
- Social Experiment
- Documentary
- Adventure
- Action
- Fantasy
- Mystery
- Satire
- Dystopian Thriller

AVOID generic concepts such as:

- 24-hour challenges
- random pranks
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
- generic celebrity gossip
- generic "things you didn't know"

Every idea must contain a strong reason why someone would click.

For longform videos, think structurally:

HOOK
→ QUESTION
→ ESCALATION
→ DISCOVERY
→ COMPLICATION
→ REVEAL
→ PAYOFF

For Shorts, create immediate curiosity using:

WHY?
HOW?
WHAT?
IS THIS REALLY POSSIBLE?
WHAT HAPPENS NEXT?

Roman Telugu loglines must sound natural and cinematic,
not like literal machine translation.

Example style:

"Ratri 2 gantala ki oka unknown number nunchi call vastundi.
Call lo matladedi tana voice laane untundi... kani aa voice
repu jaragaboye incident gurinchi cheptundi."

Do NOT use hashtags in the output.
"""


# ============================================================
# DATA HELPERS
# ============================================================

def clean_text(value: Any) -> str:
    """
    Convert any value into safe plain text.

    IMPORTANT:
    Removes '#' characters so TXT reports never contain
    Markdown heading/hash separators.
    """
    if value is None:
        return ""

    text = str(value)

    text = text.replace("#", "")
    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")

    return text.strip()


def normalize_data(data: Any) -> Dict[str, List[Dict[str, Any]]]:
    """
    Normalize different possible trend JSON structures.
    """

    if data is None:
        data = {}

    if isinstance(data, list):
        data = {"all": data}

    if not isinstance(data, dict):
        data = {}

    def get_list(*keys: str) -> List[Dict[str, Any]]:
        for key in keys:
            value = data.get(key)

            if isinstance(value, list):
                return [
                    item
                    for item in value
                    if isinstance(item, dict)
                ]

            if isinstance(value, dict):
                for nested_key in (
                    "videos",
                    "items",
                    "results",
                    "data",
                    "trends",
                ):
                    nested = value.get(nested_key)

                    if isinstance(nested, list):
                        return [
                            item
                            for item in nested
                            if isinstance(item, dict)
                        ]

        return []

    india = get_list(
        "india",
        "india_trends",
        "india_youtube",
        "IN",
        "in",
    )

    world = get_list(
        "world",
        "world_trends",
        "world_youtube",
        "global",
        "US",
        "us",
    )

    genres = get_list(
        "genres",
        "genre_trends",
        "youtube_genres",
        "categories",
    )

    all_data = get_list(
        "all",
        "videos",
        "trends",
        "data",
        "results",
    )

    if not india:
        india = list(all_data)

    if not world:
        world = list(all_data)

    if not genres:
        genres = list(all_data)

    def deduplicate(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        result = []
        seen = set()

        for item in items:
            title = clean_text(
                item.get("title")
                or item.get("name")
                or item.get("video_title")
            )

            key = title.lower()

            if not key:
                key = json.dumps(
                    item,
                    sort_keys=True,
                    default=str,
                )

            if key in seen:
                continue

            seen.add(key)
            result.append(item)

        return result

    return {
        "india": deduplicate(india),
        "world": deduplicate(world),
        "genres": deduplicate(genres),
        "all": deduplicate(all_data),
    }


def compact_items(
    items: List[Dict[str, Any]],
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """
    Reduce trend data before sending it to the LLM.
    """

    compact = []

    for item in items[:limit]:
        compact.append(
            {
                "title": clean_text(
                    item.get("title")
                    or item.get("name")
                    or item.get("video_title")
                ),
                "channel": clean_text(
                    item.get("channel")
                    or item.get("channel_name")
                    or item.get("creator")
                ),
                "views": item.get("views"),
                "likes": item.get("likes"),
                "comments": item.get("comments"),
                "published_at": clean_text(
                    item.get("published_at")
                    or item.get("published")
                    or item.get("date")
                ),
                "category": clean_text(
                    item.get("category")
                    or item.get("category_name")
                ),
                "genre": clean_text(
                    item.get("genre")
                    or item.get("subgenre")
                ),
                "url": clean_text(
                    item.get("url")
                    or item.get("video_url")
                    or item.get("link")
                ),
            }
        )

    return compact


# ============================================================
# AI API - GEMINI
# ============================================================

def call_gemini(prompt: str) -> str:
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not configured.")

    url = (
        "https://generativelanguage.googleapis.com/"
        f"v1beta/models/{GEMINI_MODEL}:generateContent"
    )

    payload = {
        "systemInstruction": {
            "parts": [
                {
                    "text": SYSTEM_PROMPT,
                }
            ]
        },
        "contents": [
            {
                "role": "user",
                "parts": [
                    {
                        "text": prompt,
                    }
                ],
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
        params={"key": GEMINI_API_KEY},
        json=payload,
        timeout=REQUEST_TIMEOUT,
    )

    response.raise_for_status()

    result = response.json()

    try:
        return result["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(
            "Gemini returned an unexpected response."
        ) from exc


# ============================================================
# AI API - OPENROUTER
# ============================================================

def call_openrouter(prompt: str) -> str:
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

    result = response.json()

    try:
        return result["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(
            "OpenRouter returned an unexpected response."
        ) from exc


# ============================================================
# JSON PARSER
# ============================================================

def parse_json_response(text: str) -> Any:
    """
    Parse JSON even when the model accidentally surrounds it
    with Markdown code fences or extra text.
    """

    if not text:
        raise ValueError("AI returned an empty response.")

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
        flags=re.IGNORECASE,
    )

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    object_match = re.search(
        r"\{.*\}",
        cleaned,
        flags=re.DOTALL,
    )

    if object_match:
        candidate = object_match.group(0)

        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    array_match = re.search(
        r"\[.*\]",
        cleaned,
        flags=re.DOTALL,
    )

    if array_match:
        candidate = array_match.group(0)

        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    raise ValueError(
        "Could not parse AI response as JSON."
    )


# ============================================================
# AI SELECTOR
# ============================================================

def call_ai(prompt: str) -> str:
    """
    Prefer Gemini.
    Fall back to OpenRouter if Gemini is unavailable.
    """

    errors = []

    if GEMINI_API_KEY:
        try:
            return call_gemini(prompt)
        except Exception as exc:
            errors.append(f"Gemini: {exc}")

    if OPENROUTER_API_KEY:
        try:
            return call_openrouter(prompt)
        except Exception as exc:
            errors.append(f"OpenRouter: {exc}")

    if not errors:
        raise RuntimeError(
            "No AI API key configured. Set GEMINI_API_KEY "
            "or OPENROUTER_API_KEY."
        )

    raise RuntimeError(
        "All AI providers failed: "
        + " | ".join(errors)
    )


# ============================================================
# SECTION INSTRUCTIONS
# ============================================================

def get_section_instruction(section_id: int) -> str:

    instructions = {
        1: """
Create India YouTube trend analysis.

Cover both:

A. Longform videos around 8–10 minutes
B. Shorts

For every important trend explain:

- What is happening
- Why it is trending
- Audience psychology
- Format
- Genre
- Entertainment subgenre when applicable
- Creator opportunity

Then create highly original ideas based on those trends.
Do not copy existing videos.
""",

        2: """
Create World YouTube trend analysis.

Cover both:

A. Longform videos around 8–10 minutes
B. Shorts

Explain:

- What is happening
- Why it is trending
- Audience psychology
- Format
- Genre
- Entertainment subgenre
- Creator opportunity

Then create original ideas inspired by these trends.
""",

        3: """
Analyze YouTube genre trends.

Cover:

- Longform
- Shorts
- Entertainment genres
- Entertainment subgenres
- Documentary
- Mystery
- Thriller
- Comedy
- Drama
- Science
- Technology
- Lifestyle where relevant
- Other strong categories

Explain why each genre/subgenre is attractive right now.

Then create original high-CTR concepts.
""",

        4: """
Create extremely engaging YouTube Shorts concepts
based on the strongest supplied trends.

Each concept must have:

- High CTR idea
- Roman Telugu logline
- Strong first-second hook
- Curiosity gap
- Escalation
- Payoff

The Shorts should feel visually executable and highly shareable.
""",

        5: """
Create highly original 8–10 minute YouTube longform concepts
based on the strongest trends.

Every idea must follow:

HOOK
QUESTION
ESCALATION
DISCOVERY
COMPLICATION
REVEAL
PAYOFF

Include a cinematic Roman Telugu logline.

The premise should feel big enough to sustain 8–10 minutes.
""",

        6: """
Create non-trend-dependent Shorts ideas for India and worldwide
audiences.

These must NOT simply copy current trends.

Focus on unusual premises, curiosity, human behavior,
mystery, clever experiments, unexpected discoveries,
social situations and strong visual storytelling.

Include Roman Telugu loglines.
""",

        7: """
Create non-trend-dependent 8–10 minute longform ideas.

The concepts should work even when trends change.

Use strong narrative structures and unusual premises.

Include:

- High CTR idea
- Roman Telugu logline
- Hook
- Question
- Escalation
- Discovery
- Complication
- Reveal
- Payoff
""",

        8: """
Create genre-fusion concepts.

Combine genres in unexpected but logical ways.

Examples:

Mystery + Comedy
Crime + Dark Comedy
Psychological Thriller + Social Experiment
Sci-Fi + Mystery
Horror + Comedy
Documentary + Thriller
Adventure + Mystery
Emotional Drama + Mystery

Do NOT make random combinations.

The genre fusion must create a genuinely interesting story engine.

Include Roman Telugu loglines.
""",
    }

    return instructions.get(
        section_id,
        "Create original high-CTR YouTube ideas.",
    )


# ============================================================
# PROMPT BUILDER
# ============================================================

def build_section_prompt(
    section: Dict[str, Any],
    data: Dict[str, List[Dict[str, Any]]],
) -> str:

    section_id = int(section["id"])
    section_name = clean_text(section["name"])

    india = compact_items(
        data.get("india", []),
        limit=50,
    )

    world = compact_items(
        data.get("world", []),
        limit=50,
    )

    genres = compact_items(
        data.get("genres", []),
        limit=50,
    )

    all_data = compact_items(
        data.get("all", []),
        limit=50,
    )

    instruction = get_section_instruction(section_id)

    schema = {
        "section_id": section_id,
        "section_name": section_name,
        "trend_analysis": [
            {
                "trend": "string",
                "what_is_happening": "string",
                "why_trending": "string",
                "audience_psychology": "string",
                "format": "string",
                "genre": "string",
                "subgenre": "string",
                "creator_opportunity": "string",
            }
        ],
        "ideas": [
            {
                "rank": 1,
                "title": "string",
                "high_ctr_idea": "string",
                "roman_telugu_logline": "string",
                "genre": "string",
                "subgenre": "string",
                "hook": "string",
                "why_people_click": "string",
                "story_premise": "string",
                "opening_30_seconds": "string",
                "main_question": "string",
                "escalation": "string",
                "discovery": "string",
                "complication": "string",
                "major_reveal": "string",
                "twist_payoff": "string",
                "ending": "string",
                "thumbnail_concept": "string",
                "ctr_score": 0,
                "retention_score": 0,
                "novelty_score": 0,
                "feasibility_score": 0,
                "emotional_impact_score": 0,
            }
        ],
    }

    prompt = f"""
SECTION {section_id}: {section_name}

TASK:

{instruction}

Generate exactly {IDEAS_PER_SECTION} strong ideas.

IMPORTANT:

- Do not use hashtags.
- Do not use Markdown headings.
- Do not put # characters in titles.
- Do not repeat the same concept.
- Do not copy supplied video titles.
- Use supplied trends as evidence/inspiration.
- If the data is weak, do not invent statistics.
- Clearly distinguish trend analysis from creative ideas.
- Every entertainment idea must have a specific subgenre.
- Every idea must have a Roman Telugu logline.
- Scores must be realistic from 0 to 100.
- Do not make every score 95+.

SUPPLIED INDIA TREND DATA:

{json.dumps(india, ensure_ascii=False, indent=2)}

SUPPLIED WORLD TREND DATA:

{json.dumps(world, ensure_ascii=False, indent=2)}

SUPPLIED GENRE DATA:

{json.dumps(genres, ensure_ascii=False, indent=2)}

SUPPLIED GENERAL DATA:

{json.dumps(all_data, ensure_ascii=False, indent=2)}

RETURN ONLY VALID JSON.

JSON STRUCTURE:

{json.dumps(schema, ensure_ascii=False, indent=2)}
"""

    return prompt


# ============================================================
# GENERATE ONE SECTION
# ============================================================

def generate_section(
    section: Dict[str, Any],
    data: Dict[str, List[Dict[str, Any]]],
) -> Dict[str, Any]:

    section_id = int(section["id"])
    section_name = clean_text(section["name"])

    prompt = build_section_prompt(
        section,
        data,
    )

    raw = call_ai(prompt)

    parsed = parse_json_response(raw)

    if not isinstance(parsed, dict):
        raise ValueError(
            f"Section {section_id} returned invalid JSON object."
        )

    parsed["section_id"] = section_id
    parsed["section_name"] = section_name

    if not isinstance(
        parsed.get("trend_analysis"),
        list,
    ):
        parsed["trend_analysis"] = []

    if not isinstance(
        parsed.get("ideas"),
        list,
    ):
        parsed["ideas"] = []

    return parsed


# ============================================================
# GENERATE COMPLETE REPORT
# ============================================================

def generate_report(
    data: Dict[str, Any],
) -> Dict[str, Any]:
    """
    IMPORTANT:
    app.py calls generate_report(data).

    Therefore this function MUST accept data.
    """

    normalized = normalize_data(data)

    report: Dict[str, Any] = {
        "project": "YouTube High CTR Idea Generator",
        "ideas_per_section": IDEAS_PER_SECTION,
        "sections": [],
    }

    for section in SECTION_DEFINITIONS:

        section_id = int(section["id"])
        section_name = clean_text(section["name"])

        print(
            f"Generating section {section_id}/"
            f"{len(SECTION_DEFINITIONS)}: "
            f"{section_name}"
        )

        try:
            generated = generate_section(
                section,
                normalized,
            )

            report["sections"].append(generated)

            print(
                f"Section {section_id} completed."
            )

        except Exception as exc:
            print(
                f"WARNING: Section {section_id} failed: {exc}"
            )

            report["sections"].append(
                {
                    "section_id": section_id,
                    "section_name": section_name,
                    "trend_analysis": [],
                    "ideas": [],
                    "error": clean_text(exc),
                }
            )

    return report


# ============================================================
# REPORT RENDERING
# ============================================================

def render_report(
    report: Dict[str, Any],
) -> str:
    """
    Convert report JSON into clean plain TXT.

    IMPORTANT:
    There is ONLY ONE render_report function.

    No Markdown '#' headings are used.
    All '#' characters are removed at the end.
    """

    lines: List[str] = []

    def add(text: Any = "") -> None:
        lines.append(clean_text(text))

    # --------------------------------------------------------
    # HEADER
    # --------------------------------------------------------

    add("=" * 90)
    add("YOUTUBE HIGH CTR IDEA GENERATOR")
    add("=" * 90)
    add("")

    add(
        f"Ideas per section: "
        f"{report.get('ideas_per_section', IDEAS_PER_SECTION)}"
    )

    add("")

    # --------------------------------------------------------
    # SECTIONS
    # --------------------------------------------------------

    sections = report.get("sections", [])

    if not isinstance(sections, list):
        sections = []

    for section_index, section in enumerate(
        sections,
        start=1,
    ):

        if not isinstance(section, dict):
            continue

        section_id = section.get(
            "section_id",
            section_index,
        )

        section_name = clean_text(
            section.get(
                "section_name",
                f"Section {section_id}",
            )
        )

        add("")
        add("=" * 90)
        add(
            f"SECTION {section_id}: {section_name}"
        )
        add("=" * 90)
        add("")

        # ----------------------------------------------------
        # TREND ANALYSIS
        # ----------------------------------------------------

        trend_analysis = section.get(
            "trend_analysis",
            [],
        )

        if isinstance(trend_analysis, list) and trend_analysis:

            add("TREND ANALYSIS")
            add("-" * 90)

            for index, trend in enumerate(
                trend_analysis,
                start=1,
            ):

                if not isinstance(trend, dict):
                    continue

                add(
                    f"Trend {index}: "
                    f"{clean_text(trend.get('trend'))}"
                )

                add(
                    "What is happening: "
                    + clean_text(
                        trend.get(
                            "what_is_happening"
                        )
                    )
                )

                add(
                    "Why trending: "
                    + clean_text(
                        trend.get(
                            "why_trending"
                        )
                    )
                )

                add(
                    "Audience psychology: "
                    + clean_text(
                        trend.get(
                            "audience_psychology"
                        )
                    )
                )

                add(
                    "Format: "
                    + clean_text(
                        trend.get("format")
                    )
                )

                add(
                    "Genre: "
                    + clean_text(
                        trend.get("genre")
                    )
                )

                add(
                    "Subgenre: "
                    + clean_text(
                        trend.get("subgenre")
                    )
                )

                add(
                    "Creator opportunity: "
                    + clean_text(
                        trend.get(
                            "creator_opportunity"
                        )
                    )
                )

                add("")

        # ----------------------------------------------------
        # IDEAS
        # ----------------------------------------------------

        ideas = section.get(
            "ideas",
            [],
        )

        if not isinstance(ideas, list):
            ideas = []

        add("HIGH-CTR IDEAS")
        add("-" * 90)

        if not ideas:
            add("No ideas were generated for this section.")

        for idea_index, idea in enumerate(
            ideas,
            start=1,
        ):

            if not isinstance(idea, dict):
                continue

            rank = idea.get(
                "rank",
                idea_index,
            )

            title = clean_text(
                idea.get("title")
                or idea.get("high_ctr_idea")
                or f"Idea {rank}"
            )

            add("")
            add(
                f"IDEA {rank}: {title}"
            )
            add("-" * 90)

            add(
                "High CTR Idea: "
                + clean_text(
                    idea.get(
                        "high_ctr_idea"
                    )
                )
            )

            add(
                "Roman Telugu Logline: "
                + clean_text(
                    idea.get(
                        "roman_telugu_logline"
                    )
                )
            )

            add(
                "Genre: "
                + clean_text(
                    idea.get("genre")
                )
            )

            add(
                "Subgenre: "
                + clean_text(
                    idea.get("subgenre")
                )
            )

            add(
                "Hook: "
                + clean_text(
                    idea.get("hook")
                )
            )

            add(
                "Why People Click: "
                + clean_text(
                    idea.get(
                        "why_people_click"
                    )
                )
            )

            add(
                "Story Premise: "
                + clean_text(
                    idea.get(
                        "story_premise"
                    )
                )
            )

            add(
                "Opening 30 Seconds: "
                + clean_text(
                    idea.get(
                        "opening_30_seconds"
                    )
                )
            )

            add(
                "Main Question: "
                + clean_text(
                    idea.get(
                        "main_question"
                    )
                )
            )

            add(
                "Escalation: "
                + clean_text(
                    idea.get(
                        "escalation"
                    )
                )
            )

            add(
                "Discovery: "
                + clean_text(
                    idea.get(
                        "discovery"
                    )
                )
            )

            add(
                "Complication: "
                + clean_text(
                    idea.get(
                        "complication"
                    )
                )
            )

            add(
                "Major Reveal: "
                + clean_text(
                    idea.get(
                        "major_reveal"
                    )
                )
            )

            add(
                "Twist / Payoff: "
                + clean_text(
                    idea.get(
                        "twist_payoff"
                    )
                )
            )

            add(
                "Ending: "
                + clean_text(
                    idea.get(
                        "ending"
                    )
                )
            )

            add(
                "Thumbnail Concept: "
                + clean_text(
                    idea.get(
                        "thumbnail_concept"
                    )
                )
            )

            add("")
            add("SCORES")

            add(
                "CTR Score: "
                + clean_text(
                    idea.get(
                        "ctr_score",
                        0,
                    )
                )
            )

            add(
                "Retention Score: "
                + clean_text(
                    idea.get(
                        "retention_score",
                        0,
                    )
                )
            )

            add(
                "Novelty Score: "
                + clean_text(
                    idea.get(
                        "novelty_score",
                        0,
                    )
                )
            )

            add(
                "Feasibility Score: "
                + clean_text(
                    idea.get(
                        "feasibility_score",
                        0,
                    )
                )
            )

            add(
                "Emotional Impact Score: "
                + clean_text(
                    idea.get(
                        "emotional_impact_score",
                        0,
                    )
                )
            )

            add("")

    # --------------------------------------------------------
    # FOOTER
    # --------------------------------------------------------

    add("=" * 90)
    add("END OF YOUTUBE HIGH CTR IDEA REPORT")
    add("=" * 90)

    # --------------------------------------------------------
    # FINAL SAFETY CLEAN
    # --------------------------------------------------------

    text = "\n".join(lines)

    # Absolute guarantee:
    # no # characters in TXT output.
    text = text.replace("#", "")

    # Remove accidental excessive blank lines.
    text = re.sub(
        r"\n{4,}",
        "\n\n\n",
        text,
    )

    return text.strip() + "\n"


# ============================================================
# SAVE REPORT
# ============================================================

def save_report(
    report: Dict[str, Any],
) -> Dict[str, Path]:
    """
    Save JSON and TXT versions of the report.
    """

    json_path = (
        OUTPUT_DIR
        / "youtube_high_ctr_report.json"
    )

    txt_path = (
        OUTPUT_DIR
        / "youtube_high_ctr_report.txt"
    )

    # JSON
    with json_path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            report,
            file,
            ensure_ascii=False,
            indent=2,
        )

    # TXT
    rendered = render_report(report)

    with txt_path.open(
        "w",
        encoding="utf-8",
        newline="\n",
    ) as file:
        file.write(rendered)

    print("")
    print("=" * 60)
    print("REPORT FILES CREATED")
    print("=" * 60)
    print(f"JSON: {json_path}")
    print(f"TXT : {txt_path}")
    print("=" * 60)

    # Safety check
    if "#" in rendered:
        raise RuntimeError(
            "TXT report still contains '#' characters."
        )

    return {
        "json": json_path,
        "txt": txt_path,
    }


# ============================================================
# MAIN TEST
# ============================================================

if __name__ == "__main__":

    print("=" * 60)
    print("TESTING IDEA GENERATOR")
    print("=" * 60)

    sample_data = {
        "india": [],
        "world": [],
        "genres": [],
        "all": [],
    }

    try:
        generated_report = generate_report(
            sample_data
        )

        save_report(
            generated_report
        )

        print("")
        print("Idea generator test completed successfully.")

    except Exception as exc:

        print("")
        print("ERROR:")
        print(clean_text(exc))

        raise
