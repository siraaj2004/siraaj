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
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

load_dotenv(BASE_DIR / ".env")


# ============================================================
# ENVIRONMENT
# ============================================================

def env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)).strip())
    except (TypeError, ValueError):
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

IDEAS_PER_SECTION = env_int(
    "IDEAS_PER_SECTION",
    8,
)

REQUEST_TIMEOUT = env_int(
    "REQUEST_TIMEOUT",
    180,
)

MAX_RETRIES = env_int(
    "AI_MAX_RETRIES",
    3,
)


# ============================================================
# SYSTEM PROMPT
# ============================================================

SYSTEM_PROMPT = (
    "You are an expert YouTube strategist, storyteller and "
    "viral-content idea generator. "
    "Create original cinematic high-CTR YouTube ideas. "
    "Ideas must feel surprising and highly clickable. "
    "Avoid generic 24 hour challenges, generic pranks, "
    "generic reactions, generic vlogs, generic food videos, "
    "generic motivation, generic interviews, generic gaming "
    "challenges, generic top 10 videos, generic facts, "
    "generic I tried X videos, generic AI videos, generic "
    "horror stories and generic celebrity gossip. "
    "Prefer curiosity, mystery, unusual situations, "
    "psychological tension, unexpected discoveries, emotional "
    "stakes, visual storytelling, strong reveals and strong "
    "thumbnail moments. "
    "Entertainment ideas must always specify a subgenre. "
    "Possible subgenres include Thriller, Psychological "
    "Thriller, Mystery Thriller, Crime Thriller, Survival "
    "Thriller, Dark Comedy, Situational Comedy, Horror Comedy, "
    "Psychological Horror, Crime Investigation, Emotional "
    "Drama, Sci-Fi Mystery, Social Experiment, Documentary, "
    "Adventure, Action, Fantasy and Dystopian Thriller. "
    "Longform should follow HOOK, QUESTION, ESCALATION, "
    "DISCOVERY, COMPLICATION, REVEAL and PAYOFF. "
    "Shorts should use immediate hook, curiosity, escalation, "
    "surprise and payoff. "
    "Roman Telugu loglines must sound natural and cinematic. "
    "Return ONLY valid JSON. "
    "Do not return Markdown. "
    "Do not return code fences. "
    "Do not use hashtag characters."
)


# ============================================================
# SECTIONS
# ============================================================

SECTION_DEFINITIONS = [
    {
        "id": 1,
        "name": "India YouTube Trends",
        "instruction": (
            "Analyze India YouTube trends for longform 8-10 "
            "minute videos and Shorts. Explain what is trending, "
            "why it is trending, audience psychology, format, "
            "genre, subgenre and creator opportunity."
        ),
    },
    {
        "id": 2,
        "name": "World YouTube Trends",
        "instruction": (
            "Analyze World YouTube trends for longform 8-10 "
            "minute videos and Shorts. Explain what is trending, "
            "why it is trending, audience psychology, format, "
            "genre, subgenre and creator opportunity."
        ),
    },
    {
        "id": 3,
        "name": "YouTube Genre Trends",
        "instruction": (
            "Analyze YouTube genre trends for longform and "
            "Shorts. Cover entertainment and relevant genres. "
            "Always specify entertainment subgenres."
        ),
    },
    {
        "id": 4,
        "name": "Trend-Based Shorts Ideas",
        "instruction": (
            "Create highly engaging Shorts ideas based on the "
            "strongest supplied trends. Every idea needs an "
            "immediate hook, curiosity, escalation, surprise, "
            "payoff and Roman Telugu logline."
        ),
    },
    {
        "id": 5,
        "name": "Trend-Based Longform Ideas",
        "instruction": (
            "Create original 8-10 minute longform ideas based "
            "on the strongest trends. Use Hook, Question, "
            "Escalation, Discovery, Complication, Reveal and "
            "Payoff. Include Roman Telugu logline."
        ),
    },
    {
        "id": 6,
        "name": "General India and World Shorts Ideas",
        "instruction": (
            "Create original non-trend-dependent Shorts ideas "
            "for India and worldwide audiences. Use unusual "
            "situations, mystery, psychology, human behavior, "
            "discoveries and visual storytelling."
        ),
    },
    {
        "id": 7,
        "name": "General India and World Longform Ideas",
        "instruction": (
            "Create original non-trend-dependent 8-10 minute "
            "longform ideas that remain useful even when trends "
            "change. Use strong story structure and unusual "
            "premises."
        ),
    },
    {
        "id": 8,
        "name": "Genre-Fusion High-CTR Ideas",
        "instruction": (
            "Create original genre-fusion concepts such as "
            "Mystery plus Comedy, Crime plus Dark Comedy, "
            "Psychological Thriller plus Social Experiment, "
            "Sci-Fi plus Mystery, Horror plus Comedy and "
            "Documentary plus Thriller."
        ),
    },
]


# ============================================================
# CLEAN TEXT
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
# NORMALIZE INPUT DATA
# ============================================================

def normalize_data(
    data: Any,
) -> Dict[str, List[Dict[str, Any]]]:

    if data is None:
        data = {}

    if isinstance(data, list):
        data = {"all": data}

    if not isinstance(data, dict):
        data = {}

    def extract(
        keys: List[str],
    ) -> List[Dict[str, Any]]:

        for key in keys:

            value = data.get(key)

            if isinstance(value, list):
                return [
                    item
                    for item in value
                    if isinstance(item, dict)
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
                            item
                            for item in nested
                            if isinstance(item, dict)
                        ]

        return []

    india = extract(
        [
            "india",
            "india_trends",
            "india_youtube",
            "IN",
            "in",
        ]
    )

    world = extract(
        [
            "world",
            "world_trends",
            "world_youtube",
            "global",
            "US",
            "us",
        ]
    )

    genres = extract(
        [
            "genres",
            "genre_trends",
            "youtube_genres",
            "categories",
        ]
    )

    all_data = extract(
        [
            "all",
            "videos",
            "trends",
            "data",
            "results",
        ]
    )

    if not all_data:
        all_data = india + world + genres

    if not india:
        india = list(all_data)

    if not world:
        world = list(all_data)

    if not genres:
        genres = list(all_data)

    def dedupe(
        items: List[Dict[str, Any]],
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

    result = []

    for item in items[:limit]:

        result.append(
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

    return result


# ============================================================
# GEMINI
# ============================================================

def call_gemini(
    prompt: str,
) -> str:

    if not GEMINI_API_KEY:
        raise RuntimeError(
            "GEMINI_API_KEY is not configured."
        )

    url = (
        "https://generativelanguage.googleapis.com/"
        "v1beta/models/"
        + GEMINI_MODEL
        + ":generateContent"
    )

    payload = {
        "systemInstruction": {
            "parts": [
                {
                    "text": SYSTEM_PROMPT,
                }
            ],
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
            "temperature": 0.9,
            "topP": 0.95,
            "maxOutputTokens": 30000,
            "responseMimeType": "application/json",
        },
    }

    response = requests.post(
        url,
        params={
            "key": GEMINI_API_KEY,
        },
        json=payload,
        timeout=REQUEST_TIMEOUT,
    )

    if response.status_code != 200:
        raise RuntimeError(
            "Gemini HTTP "
            + str(response.status_code)
            + ": "
            + response.text[:1500]
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
    ) as exc:

        raise RuntimeError(
            "Gemini response did not contain text: "
            + json.dumps(
                result,
                ensure_ascii=False,
            )[:2000]
        ) from exc


# ============================================================
# OPENROUTER
# ============================================================

def call_openrouter(
    prompt: str,
) -> str:

    if not OPENROUTER_API_KEY:
        raise RuntimeError(
            "OPENROUTER_API_KEY is not configured."
        )

    url = (
        "https://openrouter.ai/api/v1/"
        "chat/completions"
    )

    headers = {
        "Authorization": (
            "Bearer "
            + OPENROUTER_API_KEY
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
            + str(response.status_code)
            + ": "
            + response.text[:1500]
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
    ) as exc:

        raise RuntimeError(
            "OpenRouter response did not contain "
            "assistant text: "
            + json.dumps(
                result,
                ensure_ascii=False,
            )[:2000]
        ) from exc


# ============================================================
# AI CALL
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
            "AI attempt "
            + str(attempt)
            + "/"
            + str(MAX_RETRIES)
        )

        if GEMINI_API_KEY:

            try:
                return call_gemini(
                    prompt
                )
            except Exception as exc:

                message = (
                    "Gemini: "
                    + str(exc)
                )

                errors.append(message)

                print(
                    "WARNING: "
                    + message
                )

        if OPENROUTER_API_KEY:

            try:
                return call_openrouter(
                    prompt
                )
            except Exception as exc:

                message = (
                    "OpenRouter: "
                    + str(exc)
                )

                errors.append(message)

                print(
                    "WARNING: "
                    + message
                )

        if attempt < MAX_RETRIES:
            time.sleep(2)

    raise RuntimeError(
        "All AI providers failed:\n"
        + "\n".join(errors)
    )


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

    try:
        parsed = json.loads(text)

        if isinstance(parsed, dict):
            return parsed

        if isinstance(parsed, list):
            return {
                "ideas": parsed
            }

    except json.JSONDecodeError:
        pass

    first_object = text.find("{")
    last_object = text.rfind("}")

    if (
        first_object >= 0
        and last_object > first_object
    ):

        candidate = text[
            first_object:last_object + 1
        ]

        try:
            parsed = json.loads(
                candidate
            )

            if isinstance(
                parsed,
                dict,
            ):
                return parsed

        except json.JSONDecodeError:
            pass

    first_array = text.find("[")
    last_array = text.rfind("]")

    if (
        first_array >= 0
        and last_array > first_array
    ):

        candidate = text[
            first_array:last_array + 1
        ]

        try:
            parsed = json.loads(
                candidate
            )

            if isinstance(
                parsed,
                list,
            ):
                return {
                    "ideas": parsed
                }

        except json.JSONDecodeError:
            pass

    raise ValueError(
        "AI response is not valid JSON. "
        "Response preview: "
        + text[:1000]
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

    instruction = clean_text(
        section["instruction"]
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

    schema = {
        "section_id": section_id,
        "section_name": section_name,
        "trend_analysis": [
            {
                "trend": "",
                "what_is_happening": "",
                "why_trending": "",
                "audience_psychology": "",
                "format": "",
                "genre": "",
                "subgenre": "",
                "creator_opportunity": "",
            }
        ],
        "ideas": [
            {
                "rank": 1,
                "title": "",
                "high_ctr_idea": "",
                "roman_telugu_logline": "",
                "genre": "",
                "subgenre": "",
                "hook": "",
                "why_people_click": "",
                "story_premise": "",
                "opening_30_seconds": "",
                "main_question": "",
                "escalation": "",
                "discovery": "",
                "complication": "",
                "major_reveal": "",
                "twist_payoff": "",
                "ending": "",
                "thumbnail_concept": "",
                "ctr_score": 0,
                "retention_score": 0,
                "novelty_score": 0,
                "feasibility_score": 0,
                "emotional_impact_score": 0,
            }
        ],
    }

    prompt_parts = []

    prompt_parts.append(
        "SECTION ID: "
        + str(section_id)
    )

    prompt_parts.append(
        "SECTION NAME: "
        + section_name
    )

    prompt_parts.append(
        "TASK:\n"
        + instruction
    )

    prompt_parts.append(
        "Generate exactly "
        + str(IDEAS_PER_SECTION)
        + " ideas."
    )

    prompt_parts.append(
        "Every idea must contain all required fields."
    )

    prompt_parts.append(
        "Do not use hashtag characters."
    )

    prompt_parts.append(
        "Return ONLY valid JSON."
    )

    prompt_parts.append(
        "JSON STRUCTURE:"
    )

    prompt_parts.append(
        json.dumps(
            schema,
            ensure_ascii=False,
            indent=2,
        )
    )

    prompt_parts.append(
        "INDIA TREND DATA:"
    )

    prompt_parts.append(
        json.dumps(
            india,
            ensure_ascii=False,
        )
    )

    prompt_parts.append(
        "WORLD TREND DATA:"
    )

    prompt_parts.append(
        json.dumps(
            world,
            ensure_ascii=False,
        )
    )

    prompt_parts.append(
        "GENRE DATA:"
    )

    prompt_parts.append(
        json.dumps(
            genres,
            ensure_ascii=False,
        )
    )

    prompt_parts.append(
        "ALL TREND DATA:"
    )

    prompt_parts.append(
        json.dumps(
            all_data,
            ensure_ascii=False,
        )
    )

    return "\n\n".join(
        prompt_parts
    )


# ============================================================
# NORMALIZE IDEA
# ============================================================

def normalize_idea(
    idea: Dict[str, Any],
    rank: int,
) -> Dict[str, Any]:

    return {
        "rank": rank,
        "title": clean_text(
            idea.get("title")
        ),
        "high_ctr_idea": clean_text(
            idea.get("high_ctr_idea")
            or idea.get("title")
        ),
        "roman_telugu_logline": clean_text(
            idea.get(
                "roman_telugu_logline"
            )
        ),
        "genre": clean_text(
            idea.get("genre")
        ),
        "subgenre": clean_text(
            idea.get("subgenre")
        ),
        "hook": clean_text(
            idea.get("hook")
        ),
        "why_people_click": clean_text(
            idea.get(
                "why_people_click"
            )
        ),
        "story_premise": clean_text(
            idea.get(
                "story_premise"
            )
        ),
        "opening_30_seconds": clean_text(
            idea.get(
                "opening_30_seconds"
            )
        ),
        "main_question": clean_text(
            idea.get(
                "main_question"
            )
        ),
        "escalation": clean_text(
            idea.get("escalation")
        ),
        "discovery": clean_text(
            idea.get("discovery")
        ),
        "complication": clean_text(
            idea.get(
                "complication"
            )
        ),
        "major_reveal": clean_text(
            idea.get(
                "major_reveal"
            )
        ),
        "twist_payoff": clean_text(
            idea.get(
                "twist_payoff"
            )
        ),
        "ending": clean_text(
            idea.get("ending")
        ),
        "thumbnail_concept": clean_text(
            idea.get(
                "thumbnail_concept"
            )
        ),
        "ctr_score": idea.get(
            "ctr_score",
            0,
        ),
        "retention_score": idea.get(
            "retention_score",
            0,
        ),
        "novelty_score": idea.get(
            "novelty_score",
            0,
        ),
        "feasibility_score": idea.get(
            "feasibility_score",
            0,
        ),
        "emotional_impact_score": idea.get(
            "emotional_impact_score",
            0,
        ),
    }


# ============================================================
# GENERATE SECTION
# ============================================================

def generate_section(
    section: Dict[str, Any],
    data: Dict[str, List[Dict[str, Any]]],
) -> Dict[str, Any]:

    prompt = build_section_prompt(
        section,
        data,
    )

    raw = call_ai(
        prompt
    )

    parsed = parse_json_response(
        raw
    )

    ideas = parsed.get(
        "ideas",
        [],
    )

    if not isinstance(
        ideas,
        list,
    ):
        ideas = []

    normalized_ideas = []

    for index, idea in enumerate(
        ideas,
        start=1,
    ):

        if not isinstance(
            idea,
            dict,
        ):
            continue

        normalized_ideas.append(
            normalize_idea(
                idea,
                index,
            )
        )

    if not normalized_ideas:
        raise ValueError(
            "AI returned zero ideas for this section."
        )

    trends = parsed.get(
        "trend_analysis",
        [],
    )

    if not isinstance(
        trends,
        list,
    ):
        trends = []

    return {
        "section_id": section["id"],
        "section_name": section["name"],
        "trend_analysis": trends,
        "ideas": normalized_ideas,
    }


# ============================================================
# GENERATE REPORT
# ============================================================

def generate_report(
    data: Dict[str, Any],
) -> Dict[str, Any]:

    normalized = normalize_data(
        data
    )

    report = {
        "project": (
            "YouTube High CTR Idea Generator"
        ),
        "ideas_per_section": IDEAS_PER_SECTION,
        "sections": [],
    }

    total_sections = len(
        SECTION_DEFINITIONS
    )

    for position, section in enumerate(
        SECTION_DEFINITIONS,
        start=1,
    ):

        print("")
        print(
            "["
            + str(position)
            + "/"
            + str(total_sections)
            + "] "
            + section["name"]
        )

        last_error = ""

        for attempt in range(
            1,
            MAX_RETRIES + 1,
        ):

            try:

                print(
                    "Generating ideas - attempt "
                    + str(attempt)
                    + "/"
                    + str(MAX_RETRIES)
                )

                generated = generate_section(
                    section,
                    normalized,
                )

                count = len(
                    generated["ideas"]
                )

                print(
                    "SUCCESS: "
                    + str(count)
                    + " ideas generated."
                )

                report["sections"].append(
                    generated
                )

                last_error = ""
                break

            except Exception as exc:

                last_error = str(
                    exc
                )

                print(
                    "ERROR: "
                    + last_error
                )

                if attempt < MAX_RETRIES:
                    time.sleep(2)

        if last_error:

            print(
                "SECTION FAILED: "
                + section["name"]
            )

            report["sections"].append(
                {
                    "section_id": section["id"],
                    "section_name": section["name"],
                    "trend_analysis": [],
                    "ideas": [],
                    "error": clean_text(
                        last_error
                    ),
                }
            )

    return report


# ============================================================
# RENDER REPORT
# ============================================================

def render_report(
    report: Dict[str, Any],
) -> str:

    lines = []

    def add(value: Any = ""):
        lines.append(
            clean_text(value)
        )

    add("=" * 90)
    add(
        "YOUTUBE HIGH CTR IDEA GENERATOR"
    )
    add("=" * 90)

    add(
        "Ideas per section: "
        + str(
            report.get(
                "ideas_per_section",
                IDEAS_PER_SECTION,
            )
        )
    )

    add("")

    sections = report.get(
        "sections",
        [],
    )

    for section in sections:

        section_id = section.get(
            "section_id",
            "",
        )

        section_name = clean_text(
            section.get(
                "section_name",
                "",
            )
        )

        add("=" * 90)

        add(
            "SECTION "
            + str(section_id)
            + ": "
            + section_name
        )

        add("=" * 90)
        add("")

        if section.get("error"):

            add("GENERATION ERROR")
            add("-" * 90)
            add(
                section.get(
                    "error"
                )
            )
            add("")

        trends = section.get(
            "trend_analysis",
            [],
        )

        if trends:

            add("TREND ANALYSIS")
            add("-" * 90)

            for index, trend in enumerate(
                trends,
                start=1,
            ):

                if not isinstance(
                    trend,
                    dict,
                ):
                    continue

                add(
                    "Trend "
                    + str(index)
                    + ": "
                    + clean_text(
                        trend.get(
                            "trend"
                        )
                    )
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
                        trend.get(
                            "format"
                        )
                    )
                )

                add(
                    "Genre: "
                    + clean_text(
                        trend.get(
                            "genre"
                        )
                    )
                )

                add(
                    "Subgenre: "
                    + clean_text(
                        trend.get(
                            "subgenre"
                        )
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

        add("HIGH-CTR IDEAS")
        add("-" * 90)

        ideas = section.get(
            "ideas",
            [],
        )

        if not ideas:
            add(
                "NO IDEAS GENERATED."
            )

        for idea in ideas:

            add("")

            add(
                "IDEA "
                + str(
                    idea.get(
                        "rank",
                        "",
                    )
                )
                + ": "
                + clean_text(
                    idea.get(
                        "title"
                    )
                )
            )

            add("-" * 90)

            fields = [
                (
                    "High CTR Idea",
                    "high_ctr_idea",
                ),
                (
                    "Roman Telugu Logline",
                    "roman_telugu_logline",
                ),
                (
                    "Genre",
                    "genre",
                ),
                (
                    "Subgenre",
                    "subgenre",
                ),
                (
                    "Hook",
                    "hook",
                ),
                (
                    "Why People Click",
                    "why_people_click",
                ),
                (
                    "Story Premise",
                    "story_premise",
                ),
                (
                    "Opening 30 Seconds",
                    "opening_30_seconds",
                ),
                (
                    "Main Question",
                    "main_question",
                ),
                (
                    "Escalation",
                    "escalation",
                ),
                (
                    "Discovery",
                    "discovery",
                ),
                (
                    "Complication",
                    "complication",
                ),
                (
                    "Major Reveal",
                    "major_reveal",
                ),
                (
                    "Twist / Payoff",
                    "twist_payoff",
                ),
                (
                    "Ending",
                    "ending",
                ),
                (
                    "Thumbnail Concept",
                    "thumbnail_concept",
                ),
            ]

            for label, key in fields:

                add(
                    label
                    + ": "
                    + clean_text(
                        idea.get(key)
                    )
                )

            add("")
            add("SCORES")

            score_fields = [
                (
                    "CTR Score",
                    "ctr_score",
                ),
                (
                    "Retention Score",
                    "retention_score",
                ),
                (
                    "Novelty Score",
                    "novelty_score",
                ),
                (
                    "Feasibility Score",
                    "feasibility_score",
                ),
                (
                    "Emotional Impact Score",
                    "emotional_impact_score",
                ),
            ]

            for label, key in score_fields:

                add(
                    label
                    + ": "
                    + clean_text(
                        idea.get(
                            key,
                            0,
                        )
                    )
                )

            add("")

    add("=" * 90)
    add(
        "END OF YOUTUBE HIGH CTR IDEA REPORT"
    )
    add("=" * 90)

    text = "\n".join(
        lines
    )

    text = text.replace(
        "#",
        "",
    )

    return text.strip() + "\n"


# ============================================================
# SAVE REPORT
# ============================================================

def save_report(
    report: Dict[str, Any],
) -> Dict[str, Path]:

    json_path = (
        OUTPUT_DIR
        / "youtube_high_ctr_report.json"
    )

    txt_path = (
        OUTPUT_DIR
        / "youtube_high_ctr_report.txt"
    )

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

    rendered = render_report(
        report
    )

    with txt_path.open(
        "w",
        encoding="utf-8",
        newline="\n",
    ) as file:

        file.write(
            rendered
        )

    total_ideas = 0

    for section in report.get(
        "sections",
        [],
    ):

        total_ideas += len(
            section.get(
                "ideas",
                [],
            )
        )

    print("")
    print("=" * 60)
    print("REPORT CREATED")
    print("=" * 60)
    print(
        "JSON: "
        + str(json_path)
    )
    print(
        "TXT:  "
        + str(txt_path)
    )
    print(
        "TOTAL IDEAS: "
        + str(total_ideas)
    )
    print("=" * 60)

    if "#" in rendered:
        raise RuntimeError(
            "TXT contains # characters."
        )

    return {
        "json": json_path,
        "txt": txt_path,
    }


# ============================================================
# LOCAL TEST
# ============================================================

if __name__ == "__main__":

    print("=" * 60)
    print(
        "TESTING idea_generator.py"
    )
    print("=" * 60)

    test_data = {
        "india": [],
        "world": [],
        "genres": [],
        "all": [],
    }

    result = generate_report(
        test_data
    )

    save_report(
        result
    )

    print(
        "idea_generator.py completed successfully."
    )
