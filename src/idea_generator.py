import json
import re
import requests
from typing import Dict, List

from config import (
    GEMINI_API_KEY,
    GEMINI_MODEL,
    OPENROUTER_API_KEY,
    OPENROUTER_MODEL,
    IDEAS_PER_SECTION,
)


SYSTEM_PROMPT = """
You are an elite YouTube creative strategist, viral story developer,
CTR specialist, and entertainment concept designer.

Your job is NOT to generate ordinary YouTube ideas.

You must generate concepts that make a viewer think:

"WAH... WHAT AN IDEA!"
"I HAVE TO CLICK THIS."
"I NEED TO KNOW WHAT HAPPENS."
"HOW DID THEY EVEN THINK OF THIS?"

Avoid:
- generic challenges
- generic vlogs
- generic reaction videos
- generic interviews
- generic "I tried X for 24 hours"
- generic motivational videos
- generic food videos
- generic prank ideas
- copied movie plots
- copied viral videos
- boring educational titles
- meaningless shock value
- fake claims
- impossible production requirements

Every idea needs a strong central premise.

Prioritize:
1. Curiosity gap
2. Strong conflict
3. Unexpected situation
4. Mystery
5. Emotional stakes
6. Human psychology
7. Surprise/reversal
8. Strong thumbnail potential
9. Strong title potential
10. Retention potential
11. Clear payoff
12. Practical production feasibility

For entertainment concepts, ALWAYS identify the subgenre.

Examples:
- Thriller
- Psychological Thriller
- Mystery Thriller
- Crime Thriller
- Survival Thriller
- Dark Comedy
- Situational Comedy
- Horror Comedy
- Social Experiment
- Emotional Drama
- Sci-Fi
- Mystery
- Documentary
- Investigative
- Action
- Adventure

Roman Telugu must sound natural like actual Telugu YouTube storytelling,
NOT literal word-by-word translation.

Examples of good Roman Telugu style:

"Night 2:13 ki tana phone ki tana own number nunchi call vastundi.
Call lift chesthe... avatala tana voice lone oka warning vinipisthundi."

"Veedu oka abandoned room lo camera petti vellipothadu.
Kaani morning footage chusthe room lo jarigindhi vaadiki kuda explain cheyyaleni vishayam."

Do NOT make every idea horror.

Use different psychological mechanisms:
- curiosity
- fear
- wonder
- emotional tension
- moral dilemma
- social pressure
- mystery
- competition
- discovery
- irony
- impossible-looking situation
- hidden truth
- unexpected consequence

IMPORTANT:
The first idea must be the strongest idea.

The response must contain EXACTLY 8 sections.

Return valid JSON only.
No markdown.
"""


SECTION_DEFINITIONS = {

    "section_1": {
        "name": "INDIA YOUTUBE TRENDS",
        "description": """
Analyze current India YouTube trends for:
A) Longform videos around 8-10 minutes
B) Shorts

Identify what is actually trending and explain WHY.

For entertainment trends identify the specific genre/subgenre.
Mention concrete example videos from the supplied trend data.

Then generate strong opportunities based on those trends.
"""
    },

    "section_2": {
        "name": "WORLD YOUTUBE TRENDS",
        "description": """
Analyze worldwide YouTube trends for:
A) Longform videos around 8-10 minutes
B) Shorts

Explain why each trend is gaining attention.

For entertainment, identify the specific genre/subgenre.

Use concrete example videos from supplied trend data.
"""
    },

    "section_3": {
        "name": "YOUTUBE GENRE TRENDS",
        "description": """
Identify which YouTube genres and entertainment subgenres are currently
showing strong momentum.

Examples:
Thriller
Comedy
Mystery
Crime
Horror
Psychological
Documentary
Science
Technology
Gaming
Storytelling
Social Experiment
Challenge
Adventure
etc.

Explain WHY each genre has potential.
Separate longform and Shorts opportunities.
"""
    },

    "section_4": {
        "name": "TREND BASED SHORTS IDEAS",
        "description": """
Generate extremely engaging Shorts concepts based on India + World
YouTube trends.

Each idea must contain:
- High CTR title
- Roman Telugu logline
- Core hook
- Why people will stop scrolling
- Twist/payoff
- Genre
- Thumbnail concept
- CTR score
- Retention score

Do NOT generate silly or childish concepts.
"""
    },

    "section_5": {
        "name": "TREND BASED LONGFORM IDEAS",
        "description": """
Generate extremely engaging 8-10 minute YouTube longform concepts based
on India + World trends.

Each idea must have:
- High CTR title
- Roman Telugu logline
- Story premise
- Opening hook
- Escalation
- Major reveal/twist
- Ending/payoff
- Genre
- Thumbnail concept
- CTR score
- Retention score
- Production difficulty

Ideas must feel like actual videos people would click.
"""
    },

    "section_6": {
        "name": "GENERAL YOUTUBE SHORTS IDEAS",
        "description": """
Generate original Shorts ideas based on India + World audience psychology,
NOT directly copied from current trends.

Use strong concepts involving:
mystery, psychology, human behavior, surprising facts, emotional situations,
social experiments, unusual stories, suspense, irony, discoveries, etc.

Every concept must have a strong reason to click.
"""
    },

    "section_7": {
        "name": "GENERAL YOUTUBE LONGFORM IDEAS",
        "description": """
Generate original 8-10 minute longform concepts based on broad India + World
audience interests, NOT directly copied from current trends.

Ideas should feel like premium YouTube concepts.

Strong narrative structure:
HOOK -> QUESTION -> ESCALATION -> DISCOVERY -> TWIST -> PAYOFF

Avoid generic ideas.
"""
    },

    "section_8": {
        "name": "GENRE FUSION HIGH CTR IDEAS",
        "description": """
Combine the strongest genre trends into unusual but commercially attractive
concepts.

Examples:
Psychological Thriller + Social Experiment
Crime Mystery + Comedy
Horror + Investigation
Technology + Mystery
Science + Thriller
Documentary + Psychological Mystery
Gaming + Real World Mystery

The genre combination must make sense.

Generate ideas that sound fresh, cinematic and highly clickable.
"""
    }
}


def extract_json(text: str) -> Dict:

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
        raise ValueError("No JSON object found in LLM response.")

    json_text = text[start:end + 1]

    return json.loads(json_text)


def call_gemini(prompt: str) -> str:

    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is missing.")

    url = (
        "https://generativelanguage.googleapis.com/v1beta/"
        f"models/{GEMINI_MODEL}:generateContent"
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
            "temperature": 0.9,
            "topP": 0.95,
            "responseMimeType": "application/json"
        }
    }

    response = requests.post(
        url,
        params=params,
        json=payload,
        timeout=180
    )

    response.raise_for_status()

    data = response.json()

    candidates = data.get("candidates", [])

    if not candidates:
        raise RuntimeError("Gemini returned no candidates.")

    parts = (
        candidates[0]
        .get("content", {})
        .get("parts", [])
    )

    text_parts = [
        part.get("text", "")
        for part in parts
        if part.get("text")
    ]

    if not text_parts:
        raise RuntimeError("Gemini returned empty text.")

    return "\n".join(text_parts)


def call_openrouter(prompt: str) -> str:

    if not OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY is missing.")

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
                "content": SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.9,
        "top_p": 0.95,
    }

    response = requests.post(
        url,
        headers=headers,
        json=payload,
        timeout=180
    )

    response.raise_for_status()

    data = response.json()

    return (
        data["choices"][0]["message"]["content"]
    )


def call_llm(prompt: str) -> str:

    if GEMINI_API_KEY:
        return call_gemini(prompt)

    if OPENROUTER_API_KEY:
        return call_openrouter(prompt)

    raise RuntimeError(
        "No AI API key found. Add GEMINI_API_KEY or "
        "OPENROUTER_API_KEY to .env."
    )


def build_trend_context(
    india_trends: List[Dict],
    world_trends: List[Dict],
    genre_data: List[Dict]
) -> str:

    return json.dumps(
        {
            "india_trends": india_trends,
            "world_trends": world_trends,
            "genre_data": genre_data,
        },
        ensure_ascii=False,
        indent=2
    )


def build_prompt(
    section_key: str,
    trend_context: str
) -> str:

    section = SECTION_DEFINITIONS[section_key]

    return f"""
You are creating SECTION:

{section["name"]}

SECTION REQUIREMENTS:
{section["description"]}

CURRENT YOUTUBE DATA:
{trend_context}

Generate {IDEAS_PER_SECTION} strong opportunities.

VERY IMPORTANT QUALITY RULE:

Do not fill the list with weak ideas just to reach the requested number.

If an idea sounds like something thousands of small YouTubers could generate
in 10 seconds, reject it.

Before including an idea mentally ask:

"Would a viewer immediately want to know what happens?"

"Can the title create a curiosity gap?"

"Can the thumbnail communicate the premise in one second?"

"Does the idea contain conflict or tension?"

"Is there a satisfying reveal/payoff?"

"Does this feel fresh?"

For every idea provide:

- rank
- title
- roman_telugu_logline
- genre
- subgenre
- hook
- why_it_is_clickable
- story_or_content_engine
- twist_or_payoff
- thumbnail_concept
- ctr_score
- retention_score
- novelty_score
- feasibility_score

For longform also provide:

- opening_30_seconds
- escalation
- ending

For trend sections provide:

- trend_name
- why_trending
- audience_psychology
- example_videos

The FIRST idea must be the strongest concept.

Do not use fake statistics.

Return JSON in this exact structure:

{{
  "section": "{section_key}",
  "section_name": "{section["name"]}",
  "ideas": []
}}
"""


def generate_section(
    section_key: str,
    trend_context: str
) -> Dict:

    prompt = build_prompt(
        section_key,
        trend_context
    )

    raw = call_llm(prompt)

    data = extract_json(raw)

    return data


def generate_all_sections(
    india_trends: List[Dict],
    world_trends: List[Dict],
    genre_data: List[Dict]
) -> Dict:

    context = build_trend_context(
        india_trends,
        world_trends,
        genre_data
    )

    report = {
        "title": "YouTube High CTR Idea Generator",
        "sections": []
    }

    for section_key in SECTION_DEFINITIONS:

        print(
            f"Generating {section_key}..."
        )

        section = generate_section(
            section_key,
            context
        )

        report["sections"].append(section)

    return report
