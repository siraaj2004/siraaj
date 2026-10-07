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

GEMINI_API_KEY = os.getenv(
    "GEMINI_API_KEY",
    ""
).strip()

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
    os.getenv(
        "IDEAS_PER_SECTION",
        "8"
    )
)

REQUEST_TIMEOUT = 180


# ============================================================
# 8 SECTIONS
# ============================================================

SECTION_DEFINITIONS = [

    {
        "id": 1,
        "name": "India YouTube Trends",
        "purpose": "india_trends"
    },

    {
        "id": 2,
        "name": "World YouTube Trends",
        "purpose": "world_trends"
    },

    {
        "id": 3,
        "name": "YouTube Genre Trends",
        "purpose": "genre_trends"
    },

    {
        "id": 4,
        "name": "Trend-Based Shorts Ideas",
        "purpose": "trend_shorts"
    },

    {
        "id": 5,
        "name": "Trend-Based Longform Ideas",
        "purpose": "trend_longform"
    },

    {
        "id": 6,
        "name": "General Original Shorts Ideas",
        "purpose": "general_shorts"
    },

    {
        "id": 7,
        "name": "General Original Longform Ideas",
        "purpose": "general_longform"
    },

    {
        "id": 8,
        "name": "Genre-Fusion High CTR Ideas",
        "purpose": "genre_fusion"
    },
]


# ============================================================
# SYSTEM PROMPT
# ============================================================

SYSTEM_PROMPT = r"""
You are an elite YouTube creative director,
viral concept developer, story designer,
CTR strategist and audience-retention expert.

Your job is NOT to produce ordinary YouTube ideas.

Your job is to create concepts that make a viewer say:

"WAH... WHAT AN IDEA!"

"I HAVE TO WATCH THIS."

"WHAT HAPPENS NEXT?"

"I HAVE NEVER SEEN THIS CONCEPT BEFORE."

============================================================
ABSOLUTE QUALITY STANDARD
============================================================

NEVER generate filler.

NEVER generate silly ideas.

NEVER generate generic ideas just to complete a list.

Reject ideas such as:

- generic 24-hour challenges
- generic pranks
- generic reactions
- generic vlogs
- generic food reviews
- generic motivation
- generic interviews
- generic gaming challenges
- generic top 10 lists
- generic facts
- generic "I tried X"
- generic horror stories
- generic AI videos

The premise itself must be powerful.

============================================================
WHAT MAKES A GREAT IDEA
============================================================

Prioritize:

1. Curiosity gap
2. Mystery
3. Conflict
4. Psychological tension
5. Emotional stakes
6. Unexpected consequence
7. Discovery
8. Moral dilemma
9. Hidden truth
10. Investigation
11. Surprise reversal
12. Strong visual concept
13. Strong thumbnail
14. Strong title
15. Retention engine
16. Satisfying payoff

============================================================
TITLE
============================================================

The title should make the viewer ask:

WHY?

HOW?

WHAT?

WHO?

IS THIS POSSIBLE?

Avoid explaining the whole story.

WEAK:
"I Visited an Abandoned Building"

STRONG:
"The Camera Recorded Someone Who Wasn't There"

WEAK:
"I Used My Phone for 24 Hours"

STRONG:
"My Phone Received a Message From Tomorrow"

============================================================
ROMAN TELUGU LOGLINE
============================================================

Every idea MUST have a Roman Telugu logline.

It must sound natural,
like a Telugu YouTube storyteller speaking.

NOT literal translation.

Example:

"Night 2:13 ki tana phone ki tana own number
nunchi call vastundi. Call lift chesthe avatala
tana voice lone oka warning vinipisthundi.
Kaani aa warning lo cheppina incident next
morning jaragabothundi."

The logline must itself be engaging.

============================================================
ENTERTAINMENT GENRE
============================================================

Never simply say "Entertainment".

Identify exact genre/subgenre.

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

============================================================
SHORTS
============================================================

Shorts need an immediate curiosity loop.

The viewer should immediately think:

"WHY?"

"HOW?"

"WHAT?"

"IS THAT REALLY POSSIBLE?"

============================================================
LONGFORM
============================================================

8-10 minute videos must have:

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

============================================================
TREND ANALYSIS
============================================================

For trends explain:

- What is trending
- Why it is trending
- Audience psychology
- Emotional trigger
- Format
- Genre
- Subgenre
- Example videos
- Creator opportunity

Do not simply copy the trend.

============================================================
ORIGINAL IDEAS
============================================================

Sections 6 and 7 must NOT simply copy current trends.

Use audience psychology and original premises.

============================================================
GENRE FUSION
============================================================

Section 8 must combine genres intelligently.

Examples:

Psychological Thriller + Social Experiment

Crime Mystery + Dark Comedy

Technology + Mystery

Science + Thriller

Horror + Investigation

Documentary + Psychological Mystery

Gaming + Real World Mystery

============================================================
SCORING
============================================================

Every idea must receive:

ctr_score
retention_score
novelty_score
emotional_impact
feasibility

0-100.

Do NOT give everything 95+.

90+ should be reserved for exceptional ideas.

============================================================
IMPORTANT
============================================================

The FIRST idea in every idea-generating section
must be the strongest concept.

Quality is more important than filling space.

Do not make every idea horror.

Do not make every idea thriller.

Use genre diversity.

Return ONLY valid JSON.
"""


# ============================================================
# HELPERS
# ============================================================

def clean_text(value: Any) -> str:

    if value is None:
        return ""

    if isinstance(value, str):
        return value

    if isinstance(value, list):

        return ", ".join(
            clean_text(item)
            for item in value
        )

    if isinstance(value, dict):

        return "; ".join(
            f"{key}: {clean_text(val)}"
            for key, val in value.items()
        )

    return str(value)


def parse_json(text: str) -> Dict[str, Any]:

    if not text:
        raise ValueError(
            "Empty AI response."
        )

    text = text.strip()

    # Remove markdown fences
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
            "Could not find JSON object in AI response."
        )

    json_text = text[
        start:end + 1
    ]

    return json.loads(
        json_text
    )


# ============================================================
# NORMALIZE TREND DATA
# ============================================================

def normalize_data(
    data: Any
) -> Dict[str, Any]:

    if data is None:

        return {
            "india": [],
            "world": [],
            "genres": [],
            "all": []
        }

    if isinstance(data, str):

        try:
            data = json.loads(data)

        except Exception:

            return {
                "india": [],
                "world": [],
                "genres": [],
                "all": []
            }

    if isinstance(data, list):

        return {
            "india": data,
            "world": [],
            "genres": [],
            "all": data
        }

    if not isinstance(data, dict):

        return {
            "india": [],
            "world": [],
            "genres": [],
            "all": []
        }

    # Support many possible names used by
    # different trend collectors.

    india = (
        data.get("india")
        or data.get("india_trends")
        or data.get("IN")
        or data.get("india_youtube")
        or []
    )

    world = (
        data.get("world")
        or data.get("world_trends")
        or data.get("US")
        or data.get("global")
        or data.get("world_youtube")
        or []
    )

    genres = (
        data.get("genres")
        or data.get("genre_trends")
        or data.get("youtube_genres")
        or []
    )

    all_data = (
        data.get("all")
        or data.get("videos")
        or data.get("trends")
        or []
    )

    if not all_data:

        all_data = (
            list(india)
            + list(world)
        )

    return {
        "india": india,
        "world": world,
        "genres": genres,
        "all": all_data
    }


# ============================================================
# COMPACT DATA
# ============================================================

def compact_items(
    items: Any,
    limit: int = 35
) -> List[Dict[str, Any]]:

    if not isinstance(items, list):

        return []

    result = []

    for item in items[:limit]:

        if not isinstance(
            item,
            dict
        ):
            continue

        result.append({

            "title":
                clean_text(
                    item.get(
                        "title",
                        item.get(
                            "name",
                            ""
                        )
                    )
                ),

            "channel":
                clean_text(
                    item.get(
                        "channel",
                        item.get(
                            "channelTitle",
                            ""
                        )
                    )
                ),

            "views":
                item.get(
                    "views",
                    item.get(
                        "view_count",
                        0
                    )
                ),

            "likes":
                item.get(
                    "likes",
                    item.get(
                        "like_count",
                        0
                    )
                ),

            "comments":
                item.get(
                    "comments",
                    item.get(
                        "comment_count",
                        0
                    )
                ),

            "published_at":
                clean_text(
                    item.get(
                        "published_at",
                        item.get(
                            "publishedAt",
                            ""
                        )
                    )
                ),

            "category":
                clean_text(
                    item.get(
                        "category",
                        ""
                    )
                ),

            "genre":
                clean_text(
                    item.get(
                        "genre",
                        ""
                    )
                ),

            "url":
                clean_text(
                    item.get(
                        "url",
                        ""
                    )
                )
        })

    return result


# ============================================================
# GEMINI
# ============================================================

def call_gemini(
    prompt: str
) -> str:

    if not GEMINI_API_KEY:

        raise RuntimeError(
            "GEMINI_API_KEY is not configured."
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
                    "text":
                        SYSTEM_PROMPT
                }

            ]
        },

        "contents": [

            {

                "role":
                    "user",

                "parts": [

                    {
                        "text":
                            prompt
                    }

                ]
            }

        ],

        "generationConfig": {

            "temperature":
                0.95,

            "topP":
                0.95,

            "responseMimeType":
                "application/json"
        }
    }

    response = requests.post(
        url,
        params=params,
        json=payload,
        timeout=REQUEST_TIMEOUT
    )

    response.raise_for_status()

    result = response.json()

    candidates = result.get(
        "candidates",
        []
    )

    if not candidates:

        raise RuntimeError(
            "Gemini returned no candidates."
        )

    parts = (
        candidates[0]
        .get(
            "content",
            {}
        )
        .get(
            "parts",
            []
        )
    )

    texts = []

    for part in parts:

        if part.get("text"):

            texts.append(
                part["text"]
            )

    if not texts:

        raise RuntimeError(
            "Gemini returned empty text."
        )

    return "\n".join(
        texts
    )


# ============================================================
# OPENROUTER
# ============================================================

def call_openrouter(
    prompt: str
) -> str:

    if not OPENROUTER_API_KEY:

        raise RuntimeError(
            "OPENROUTER_API_KEY is not configured."
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

    result = response.json()

    return (
        result[
            "choices"
        ][0][
            "message"
        ][
            "content"
        ]
    )


# ============================================================
# AI ROUTER
# ============================================================

def call_ai(
    prompt: str
) -> str:

    if GEMINI_API_KEY:

        return call_gemini(
            prompt
        )

    if OPENROUTER_API_KEY:

        return call_openrouter(
            prompt
        )

    raise RuntimeError(
        "No AI API key found. "
        "Configure GEMINI_API_KEY "
        "or OPENROUTER_API_KEY."
    )


# ============================================================
# SECTION PROMPTS
# ============================================================

def get_section_instruction(
    section_id: int
) -> str:

    if section_id == 1:

        return """
SECTION 1 — INDIA YOUTUBE TRENDS

Analyze current India YouTube trends.

Separate the analysis into:

1. Longform opportunities around 8-10 minutes
2. Shorts opportunities

For every meaningful trend explain:

- What is trending
- Why it is trending
- Audience psychology
- Emotional trigger
- Format
- Genre
- Exact entertainment subgenre if applicable
- Example videos from the supplied data
- Opportunity for a creator

Do NOT invent trend statistics.
"""

    if section_id == 2:

        return """
SECTION 2 — WORLD YOUTUBE TRENDS

Analyze worldwide YouTube trends.

Separate:

1. Longform 8-10 minutes
2. Shorts

Explain:

- What is trending
- Why
- Audience psychology
- Format
- Genre
- Subgenre
- Example videos
- Creator opportunity

Do not invent statistics.
"""

    if section_id == 3:

        return """
SECTION 3 — YOUTUBE GENRE TRENDS

Analyze genre patterns across India and World data.

Identify:

- Genre
- Subgenre
- Longform potential
- Shorts potential
- Why people watch it
- Emotional trigger
- Storytelling pattern
- Example videos
- Creator opportunity

Entertainment must use specific subgenres.
"""

    if section_id == 4:

        return """
SECTION 4 — TREND BASED SHORTS IDEAS

Generate highly engaging Shorts ideas based on
India + World YouTube trends.

Do NOT simply copy existing videos.

Transform trends into fresh concepts.

Each idea requires:

- title
- roman_telugu_logline
- genre
- subgenre
- hook
- why_it_is_clickable
- twist_or_payoff
- thumbnail_concept
- ctr_score
- retention_score
- novelty_score
- emotional_impact
- feasibility
"""

    if section_id == 5:

        return """
SECTION 5 — TREND BASED LONGFORM IDEAS

Generate highly engaging 8-10 minute videos
based on India + World YouTube trends.

Every idea must have:

- title
- roman_telugu_logline
- genre
- subgenre
- opening_30_seconds
- central_question
- story_premise
- escalation
- major_reveal
- twist_or_payoff
- ending
- thumbnail_concept
- ctr_score
- retention_score
- novelty_score
- emotional_impact
- feasibility

The concept must support an actual 8-10 minute story.
"""

    if section_id == 6:

        return """
SECTION 6 — GENERAL ORIGINAL SHORTS IDEAS

Generate original Shorts concepts.

They must NOT depend on current YouTube trends.

Use:

- curiosity
- mystery
- psychology
- human behavior
- unusual situations
- emotional conflict
- unexpected consequences
- investigation
- surprising discoveries

Every idea must feel original.
"""

    if section_id == 7:

        return """
SECTION 7 — GENERAL ORIGINAL LONGFORM IDEAS

Generate original 8-10 minute concepts.

Do NOT copy current trends.

Use:

HOOK
QUESTION
ESCALATION
DISCOVERY
REVEAL
PAYOFF

The idea must feel like a premium YouTube concept.
"""

    if section_id == 8:

        return """
SECTION 8 — GENRE FUSION HIGH CTR IDEAS

Combine strong genre patterns into new concepts.

Examples:

Psychological Thriller + Social Experiment

Crime Mystery + Dark Comedy

Technology + Mystery

Science + Thriller

Horror + Investigation

Documentary + Psychological Mystery

Gaming + Real World Mystery

The combination must make sense.

Create highly clickable concepts.
"""


# ============================================================
# GENERATE ONE SECTION
# ============================================================

def generate_section(
    section_id: int,
    section_name: str,
    trend_data: Dict[str, Any]
) -> Dict[str, Any]:

    india = compact_items(
        trend_data.get(
            "india",
            []
        )
    )

    world = compact_items(
        trend_data.get(
            "world",
            []
        )
    )

    genres = compact_items(
        trend_data.get(
            "genres",
            []
        )
    )

    instruction = get_section_instruction(
        section_id
    )

    prompt = f"""
Create SECTION {section_id}:

{section_name}

============================================================
SECTION INSTRUCTIONS
============================================================

{instruction}

============================================================
INDIA TREND DATA
============================================================

{json.dumps(
    india,
    ensure_ascii=False,
    indent=2
)}

============================================================
WORLD TREND DATA
============================================================

{json.dumps(
    world,
    ensure_ascii=False,
    indent=2
)}

============================================================
GENRE DATA
============================================================

{json.dumps(
    genres,
    ensure_ascii=False,
    indent=2
)}

============================================================
QUALITY FILTER
============================================================

Generate {IDEAS_PER_SECTION} ideas where ideas are requested.

The first idea MUST be the strongest.

Reject any idea that sounds:

- generic
- childish
- obvious
- copied
- filler
- predictable
- boring

The idea should create:

"WAH... WHAT AN IDEA!"

Every idea needs a strong reason for a viewer to click.

Roman Telugu loglines must be natural and engaging.

Do not make every idea horror.

Do not make every idea thriller.

Use genre diversity.

Return ONLY this JSON:

{{
    "section_id": {section_id},
    "section_name": "{section_name}",
    "trend_analysis": [],
    "ideas": []
}}
"""

    raw = call_ai(
        prompt
    )

    return parse_json(
        raw
    )


# ============================================================
# FIXED generate_report(data)
# ============================================================

def generate_report(
    data: Any
) -> Dict[str, Any]:

    """
    IMPORTANT:
    app.py calls:

        generate_report(data)

    Therefore this function MUST accept data.
    """

    trend_data = normalize_data(
        data
    )

    report = {

        "generator":
            "YouTube High CTR Idea Generator",

        "version":
            "3.0",

        "quality_standard":
            "Very High CTR / Very High Engagement",

        "sections":
            []
    }

    total = len(
        SECTION_DEFINITIONS
    )

    for position, section in enumerate(
        SECTION_DEFINITIONS,
        start=1
    ):

        print(
            f"\n[{position}/{total}] "
            f"Generating {section['name']}..."
        )

        try:

            result = generate_section(

                section_id=
                    section["id"],

                section_name=
                    section["name"],

                trend_data=
                    trend_data
            )

            report[
                "sections"
            ].append(
                result
            )

            print(
                f"[OK] Section "
                f"{section['id']} completed."
            )

        except Exception as exc:

            print(
                f"[WARNING] Section "
                f"{section['id']} failed: "
                f"{exc}"
            )

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
# RENDER REPORT
# ============================================================

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
        "VERY HIGH ENGAGEMENT EDITION"
    )

    lines.append(
        "=" * 80
    )

    lines.append("")

    for section in report.get(
        "sections",
        []
    ):

        section_id = section.get(
            "section_id",
            ""
        )

        section_name = section.get(
            "section_name",
            ""
        )

        lines.append(
            "\n"
            + "#" * 80
        )

        lines.append(
            f"SECTION {section_id} — "
            f"{section_name}"
        )

        lines.append(
            "#" * 80
        )

        # ----------------------------------------------------
        # TREND ANALYSIS
        # ----------------------------------------------------

        trends = section.get(
            "trend_analysis",
            []
        )

        if trends:

            lines.append(
                "\nTREND ANALYSIS"
            )

            lines.append(
                "-" * 60
            )

            for trend in trends:

                if isinstance(
                    trend,
                    dict
                ):

                    lines.append(
                        f"\nTrend: "
                        f"{clean_text(
                            trend.get(
                                'trend_name'
                            )
                        )}"
                    )

                    lines.append(
                        f"Why Trending: "
                        f"{clean_text(
                            trend.get(
                                'why_trending'
                            )
                        )}"
                    )

                    lines.append(
                        f"Audience Psychology: "
                        f"{clean_text(
                            trend.get(
                                'audience_psychology'
                            )
                        )}"
                    )

                    lines.append(
                        f"Genre: "
                        f"{clean_text(
                            trend.get(
                                'genre'
                            )
                        )}"
                    )

                    lines.append(
                        f"Subgenre: "
                        f"{clean_text(
                            trend.get(
                                'subgenre'
                            )
                        )}"
                    )

                    examples = trend.get(
                        "example_videos",
                        []
                    )

                    if examples:

                        lines.append(
                            "Example Videos:"
                        )

                        for example in examples:

                            lines.append(
                                f"  - "
                                f"{clean_text(example)}"
                            )

        # ----------------------------------------------------
        # IDEAS
        # ----------------------------------------------------

        ideas = section.get(
            "ideas",
            []
        )

        for index, idea in enumerate(
            ideas,
            start=1
        ):

            if not isinstance(
                idea,
                dict
            ):

                continue

            title = clean_text(
                idea.get(
                    "title"
                )
            )

            lines.append(
                "\n"
                + "-" * 75
            )

            lines.append(
                f"#{index} — {title}"
            )

            lines.append(
                "-" * 75
            )

            # THIS IS DELIBERATELY FIRST
            # SO THE LOG-LINE APPEARS AT THE TOP.

            logline = clean_text(
                idea.get(
                    "roman_telugu_logline"
                )
            )

            if logline:

                lines.append(
                    "\n🔥 HIGH CTR IDEA LOGLINE"
                )

                lines.append(
                    logline
                )

            # Genre

            genre = clean_text(
                idea.get(
                    "genre"
                )
            )

            subgenre = clean_text(
                idea.get(
                    "subgenre"
                )
            )

            if genre:

                lines.append(
                    f"\nGenre: {genre}"
                )

            if subgenre:

                lines.append(
                    f"Subgenre: {subgenre}"
                )

            # Hook

            hook = clean_text(
                idea.get(
                    "hook"
                )
            )

            if hook:

                lines.append(
                    f"\nHOOK:\n{hook}"
                )

            # Why click

            why_click = clean_text(
                idea.get(
                    "why_it_is_clickable"
                )
            )

            if why_click:

                lines.append(
                    "\nWHY PEOPLE WILL CLICK:"
                )

                lines.append(
                    why_click
                )

            # Story

            story = clean_text(
                idea.get(
                    "story_premise"
                )
            )

            if story:

                lines.append(
                    "\nSTORY PREMISE:"
                )

                lines.append(
                    story
                )

            # Opening

            opening = clean_text(
                idea.get(
                    "opening_30_seconds"
                )
            )

            if opening:

                lines.append(
                    "\nOPENING 30 SECONDS:"
                )

                lines.append(
                    opening
                )

            # Escalation

            escalation = clean_text(
                idea.get(
                    "escalation"
                )
            )

            if escalation:

                lines.append(
                    "\nESCALATION:"
                )

                lines.append(
                    escalation
                )

            # Reveal

            reveal = clean_text(
                idea.get(
                    "major_reveal"
                )
            )

            if reveal:

                lines.append(
                    "\nMAJOR REVEAL:"
                )

                lines.append(
                    reveal
                )

            # Twist

            twist = clean_text(
                idea.get(
                    "twist_or_payoff"
                )
            )

            if twist:

                lines.append(
                    "\nTWIST / PAYOFF:"
                )

                lines.append(
                    twist
                )

            # Ending

            ending = clean_text(
                idea.get(
                    "ending"
                )
            )

            if ending:

                lines.append(
                    "\nENDING:"
                )

                lines.append(
                    ending
                )

            # Thumbnail

            thumbnail = clean_text(
                idea.get(
                    "thumbnail_concept"
                )
            )

            if thumbnail:

                lines.append(
                    "\nTHUMBNAIL CONCEPT:"
                )

                lines.append(
                    thumbnail
                )

            # Scores

            scores = [

                (
                    "CTR",
                    idea.get(
                        "ctr_score"
                    )
                ),

                (
                    "Retention",
                    idea.get(
                        "retention_score"
                    )
                ),

                (
                    "Novelty",
                    idea.get(
                        "novelty_score"
                    )
                ),

                (
                    "Emotional Impact",
                    idea.get(
                        "emotional_impact"
                    )
                ),

                (
                    "Feasibility",
                    idea.get(
                        "feasibility"
                    )
                )
            ]

            lines.append(
                "\nSCORES:"
            )

            for name, value in scores:

                if value not in (
                    None,
                    ""
                ):

                    lines.append(
                        f"{name}: "
                        f"{clean_text(value)}/100"
                    )

    return "\n".join(
        lines
    )


# ============================================================
# SAVE
# ============================================================

def save_report(
    report: Dict[str, Any]
):

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

        render_report(
            report
        ),

        encoding="utf-8"
    )

    return (
        json_path,
        txt_path
    )
