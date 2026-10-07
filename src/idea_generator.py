# src/idea_generator.py

import json
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List

import requests
from dotenv import load_dotenv


# ============================================================
# CONFIG
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

load_dotenv(BASE_DIR / ".env")


def get_int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)).strip())
    except Exception:
        return default


GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-2.5-flash",
).strip()

OPENROUTER_API_KEY = os.getenv(
    "OPENROUTER_API_KEY",
    "",
).strip()

OPENROUTER_MODEL = os.getenv(
    "OPENROUTER_MODEL",
    "google/gemini-2.5-flash",
).strip()

IDEAS_PER_SECTION = get_int_env(
    "IDEAS_PER_SECTION",
    8,
)

REQUEST_TIMEOUT = get_int_env(
    "REQUEST_TIMEOUT",
    180,
)

MAX_RETRIES = get_int_env(
    "AI_MAX_RETRIES",
    3,
)


# ============================================================
# SECTIONS
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
You are an expert YouTube strategist, storyteller and viral-content
idea generator.

Create original, cinematic, high-CTR YouTube ideas.

The ideas must make the creator think:

"WAHH, WHAT A IDEA!"

Do NOT create generic ideas.

Avoid:

- 24 hour challenges
- generic pranks
- generic reactions
- generic vlogs
- generic food videos
- generic motivation
- generic interviews
- generic gaming challenges
- generic top 10 videos
- generic facts
- generic "I tried X"
- generic AI videos
- generic horror stories
- generic celebrity gossip

Prefer:

- curiosity
- mystery
- unusual situations
- psychological tension
- unexpected discoveries
- emotional stakes
- visual storytelling
- strong reveals
- unusual human behavior
- strong thumbnail moments
- strong title curiosity

Entertainment must ALWAYS have a specific subgenre.

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
Dystopian Thriller

LONGFORM STRUCTURE:

HOOK
QUESTION
ESCALATION
DISCOVERY
COMPLICATION
REVEAL
PAYOFF

SHORTS STRUCTURE:

IMMEDIATE HOOK
CURIOSITY
ESCALATION
SURPRISE
PAYOFF

Roman Telugu loglines must sound natural and cinematic.

IMPORTANT:

Return ONLY valid JSON.

Do not return Markdown.
Do not return ```json.
Do not return explanations outside JSON.
Do not use # characters.
"""


# ============================================================
# TEXT CLEANING
# ============================================================

def clean_text(value: Any) -> str:
    if value is None:
        return ""

    text = str(value)

    text = text.replace("#", "")
    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")

    return text.strip()


# ============================================================
# DATA NORMALIZATION
# ============================================================

def normalize_data(
    data: Any,
) -> Dict[str, List[Dict[str, Any]]]:

    if data is None:
        data = {}

    if isinstance(data, list):
        data = {
            "all": data,
        }

    if not isinstance(data, dict):
        data = {}

    def extract(*keys: str) -> List[Dict[str, Any]]:

        for key in keys:

            value = data.get(key)

            if isinstance(value, list):
                return [
                    x
                    for x in value
                    if isinstance(x, dict)
                ]

            if isinstance(value, dict):

                for nested_key in [
                    "videos",
                    "items",
                    "results",
                    "data",
                    "trends",
                ]:

                    nested = value.get(
                        nested_key
                    )

                    if isinstance(
                        nested,
                        list,
                    ):
                        return [
                            x
                            for x in nested
                            if isinstance(x, dict)
                        ]

        return []

    india = extract(
        "india",
        "india_trends",
        "india_youtube",
        "IN",
        "in",
    )

    world = extract(
        "world",
        "world_trends",
        "world_youtube",
        "global",
        "US",
        "us",
    )

    genres = extract(
        "genres",
        "genre_trends",
        "youtube_genres",
        "categories",
    )

    all_data = extract(
        "all",
        "videos",
        "trends",
        "data",
        "results",
    )

    if not all_data:
        all_data = (
            india
            + world
            + genres
        )

    if not india:
        india = list(all_data)

    if not world:
        world = list(all_data)

    if not genres:
        genres = list(all_data)

    def dedupe(
        items: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:

        result = []
        seen = set()

        for item in items:

            title = clean_text(
                item.get("title")
                or item.get("name")
                or item.get("video_title")
            )

            if title:
                key = title.lower()
            else:
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
        "india": dedupe(india),
        "world": dedupe(world),
        "genres": dedupe(genres),
        "all": dedupe(all_data),
    }


# ============================================================
# COMPACT DATA
# ============================================================

def compact_items(
    items: List[Dict[str, Any]],
    limit: int = 40,
) -> List[Dict[str, Any]]:

    output = []

    for item in items[:limit]:

        output.append(
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

    return output


# ============================================================
# JSON PARSER
# ============================================================

def parse_json_response(
    raw_text: str,
) -> Dict[str, Any]:

    if not raw_text:
        raise ValueError(
            "AI returned an empty response."
        )

    text = raw_text.strip()

    # Remove code fences
    text = re.sub(
        r"^```json\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"^```\s*",
        "",
        text,
    )

    text = re.sub(
        r"\s*```$",
        "",
        text,
    )

    text = text.strip()

    # Direct JSON
    try:
        result = json.loads(text)

        if isinstance(result, dict):
            return result

    except json.JSONDecodeError:
        pass

    # Find first JSON object
    start = text.find("{")
    end = text.rfind("}")

    if start >= 0 and end > start:

        candidate = text[
            start:end + 1
        ]

        try:
            result = json.loads(candidate)

            if isinstance(result, dict):
                return result

        except json.JSONDecodeError:
            pass

    # Sometimes model returns an array
    start = text.find("[")
    end = text.rfind("]")

    if start >= 0 and end > start:

        candidate = text[
            start:end + 1
        ]

        try:
            result = json.loads(candidate)

            if isinstance(result, list):
                return {
                    "ideas": result
                }

        except json.JSONDecodeError:
            pass

    preview = text[:1000]

    raise ValueError(
        "Could not parse AI response as JSON.\n"
        f"Response preview:\n{preview}"
    )


# ============================================================
# GEMINI
# ============================================================

def call_gemini(
    prompt: str,
) -> str:

    if not GEMINI_API_KEY:
        raise RuntimeError(
            "GEMINI_API_KEY is missing."
        )

    url = (
        "https://generativelanguage.googleapis.com/"
        f"v1beta/models/{GEMINI_MODEL}:generateContent"
    )

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
                ],
            }
        ],
        "generationConfig": {
            "temperature": 0.9,
            "topP": 0.95,
            "maxOutputTokens": 30000,
            "responseMimeType": "application/json",
        },
    }

    response = requests.post(
        url,
        params={
            "key": GEMINI_API_KEY
        },
        json=payload,
        timeout=REQUEST_TIMEOUT,
    )

    if response.status_code != 200:

        raise RuntimeError(
            "Gemini HTTP "
            f"{response.status_code}: "
            f"{response.text[:1000]}"
        )

    result = response.json()

    try:
        return (
            result["candidates"][0]
            ["content"]["parts"][0]
            ["text"]
        )

    except (
        KeyError,
        IndexError,
        TypeError,
    ):

        raise RuntimeError(
            "Gemini response did not contain text.\n"
            + json.dumps(
                result,
                ensure_ascii=False,
            )[:2000]
        )


# ============================================================
# OPENROUTER
# ============================================================

def call_openrouter(
    prompt: str,
) -> str:

    if not OPENROUTER_API_KEY:
        raise RuntimeError(
            "OPENROUTER_API_KEY is missing."
        )

    url = (
        "https://openrouter.ai/api/v1/"
        "chat/completions"
    )

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
        "temperature": 0.9,
        "top_p": 0.95,
        "max_tokens": 30000,
    }

    response = requests.post(
        url,
        headers=headers,
        json=payload,
        timeout=REQUEST_TIMEOUT,
    )

    if response.status_code != 200:

        raise RuntimeError(
            "OpenRouter HTTP "
            f"{response.status_code}: "
            f"{response.text[:1000]}"
        )

    result = response.json()

    try:

        return (
            result["choices"][0]
            ["message"]["content"]
        )

    except (
        KeyError,
        IndexError,
        TypeError,
    ):

        raise RuntimeError(
            "OpenRouter response did not contain "
            "assistant text.\n"
            + json.dumps(
                result,
                ensure_ascii=False,
            )[:2000]
        )


# ============================================================
# AI CALL WITH RETRY + FALLBACK
# ============================================================

def call_ai(
    prompt: str,
) -> str:

    errors = []

    for attempt in range(
        1,
        MAX_RETRIES + 1,
    ):

        print(
            f"AI generation attempt "
            f"{attempt}/{MAX_RETRIES}"
        )

        # Gemini
        if GEMINI_API_KEY:

            try:

                return call_gemini(
                    prompt
                )

            except Exception as exc:

                message = (
                    f"Gemini attempt "
                    f"{attempt}: {exc}"
                )

                errors.append(message)

                print(
                    "WARNING:",
                    message,
                )

        # OpenRouter
        if OPENROUTER_API_KEY:

            try:

                return call_openrouter(
                    prompt
                )

            except Exception as exc:

                message = (
                    f"OpenRouter attempt "
                    f"{attempt}: {exc}"
                )

                errors.append(message)

                print(
                    "WARNING:",
                    message,
                )

        if attempt < MAX_RETRIES:
            time.sleep(2)

    raise RuntimeError(
        "All AI attempts failed:\n"
        + "\n".join(errors)
    )


# ============================================================
# SECTION INSTRUCTIONS
# ============================================================

def get_section_instruction(
    section_id: int,
) -> str:

    instructions = {

        1: """
Analyze current India YouTube trends.

Cover:

1. Longform 8–10 minute videos
2. YouTube Shorts

For each trend explain:

- what is happening
- why it is trending
- audience psychology
- format
- genre
- subgenre
- creator opportunity

Then create original ideas inspired by these trends.
""",

        2: """
Analyze current World YouTube trends.

Cover:

1. Longform 8–10 minute videos
2. YouTube Shorts

Explain:

- what is happening
- why it is trending
- audience psychology
- format
- genre
- subgenre
- creator opportunity

Then create original ideas.
""",

        3: """
Analyze YouTube genre trends.

Cover:

- longform
- Shorts
- entertainment
- thriller
- mystery
- comedy
- horror
- crime
- drama
- documentary
- science
- technology
- adventure
- other relevant genres

Entertainment must specify a subgenre.

Then generate strong original concepts.
""",

        4: """
Create highly engaging Shorts ideas based on
the supplied trends.

Every idea needs:

- high CTR concept
- Roman Telugu logline
- immediate hook
- curiosity
- escalation
- surprise
- payoff
""",

        5: """
Create highly engaging 8–10 minute longform ideas.

Use:

HOOK
QUESTION
ESCALATION
DISCOVERY
COMPLICATION
REVEAL
PAYOFF

Every idea needs a cinematic Roman Telugu logline.
""",

        6: """
Create original non-trend-dependent Shorts ideas
for India and worldwide audiences.

Do not simply copy trends.

Use unusual situations, mystery, psychology,
human behavior, discoveries and visual storytelling.
""",

        7: """
Create original non-trend-dependent 8–10 minute
longform ideas.

They should work even when current trends disappear.

Use strong story structure and unusual premises.
""",

        8: """
Create genre-fusion concepts.

Examples:

Mystery + Comedy
Crime + Dark Comedy
Psychological Thriller + Social Experiment
Sci-Fi + Mystery
Horror + Comedy
Documentary + Thriller
Adventure + Mystery
Drama + Mystery

The combination must create a real story engine.
""",
    }

    return instructions.get(
        section_id,
        "Create original YouTube ideas.",
    )


# ============================================================
# BUILD PROMPT
# ============================================================

def build_section_prompt(
    section: Dict[str, Any],
    data: Dict[str, List[Dict[str, Any]]],
) -> str:

    section_id = int(
        section["id"]
    )

    section_name = clean_text(
        section["name"]
    )

    india = compact_items(
        data.get("india", [])
    )

    world = compact_items(
        data.get("world", [])
    )

    genres = compact_items(
        data.get("genres", [])
    )

    all_data = compact_items(
        data.get("all", [])
    )

    instruction = get_section_instruction(
        section_id
    )

    return f"""
SECTION ID: {section_id}
SECTION NAME: {section_name}

TASK:

{instruction}

Generate exactly {IDEAS_PER_SECTION} ideas.

Each idea MUST contain:

rank
title
high_ctr_idea
roman_telugu_logline
genre
subgenre
hook
why_people_click
story_premise
opening_30_seconds
main_question
escalation
discovery
complication
major_reveal
twist_payoff
ending
thumbnail_concept
ctr_score
retention_score
novelty_score
feasibility_score
emotional_impact_score

Scores must be integers
