"""
YouTube High CTR Idea Generator
--------------------------------
Generates exactly the requested 8-section report.

Design:
- Trends are evidence, NOT the idea itself.
- Entertainment trends are classified into useful sub-genres:
  Thriller, Crime, Comedy, Horror, Mystery, Action, Romance, Drama,
  Sci-Fi, Fantasy, Documentary, Music, Anime, etc.
- Every idea must have a real story premise, not a generic keyword.
- Every idea includes a Roman Telugu logline.
- The report always starts with one "TOP HIGH CTR IDEA" + logline.
- LLM output is validated and repaired before rendering.

Environment:
OPENROUTER_API_KEY=...
OPENROUTER_MODEL=google/gemini-2.5-flash
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

try:
    import requests
except ImportError:
    requests = None


# ---------------------------------------------------------------------------
# PROMPT
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = r"""
You are an elite YouTube creative strategist, documentary producer and
high-CTR idea writer.

Your job is NOT to turn a trend keyword into a silly video title.

BAD:
- "Why Trailer Is Exploding"
- "The Secret Everyone Missed"
- "Why Song Is Trending"
- "Kumar: The Secret Everyone Missed"

GOOD:
- A specific story with conflict, mystery, stakes, contradiction, reveal,
  human behaviour, cultural angle, visual potential, or an unexpected
  consequence.
- The trend should be used as evidence for WHY this story is timely.
- If the source trend is entertainment, identify the actual sub-genre:
  Thriller, Crime, Mystery, Horror, Comedy, Action, Romance, Drama,
  Sci-Fi, Fantasy, Music, Anime, etc.
- Never invent a factual claim about a real person/event. If a detail is
  not supplied by the data, phrase it as an angle/question to investigate.

QUALITY BAR:
The idea must make a creator say:
"WAH. Ee idea ni video cheyyali."
The audience should immediately understand why they would click.

Avoid:
- generic "secret nobody knows" titles
- generic "why X is trending"
- random villages/jobs/museums without a concrete story
- weak listicles
- reaction/challenge concepts unless the trend data strongly supports them
- changing only one noun in the same template
- meaningless trend words such as "Oct", "Kumar", "Sur", "Day" becoming
  the whole idea
- fake statistics
- fake facts
- repetitive ideas

Use these creative engines when appropriate:
1. Mystery + reveal
2. Investigation + evidence
3. Rise/fall + consequence
4. Hidden system + human stakes
5. What changed + why now
6. One decision + unexpected chain reaction
7. Culture + psychology
8. Technology + human behaviour
9. Crime/thriller + unanswered question
10. Entertainment phenomenon + behind-the-scenes mechanism
11. Game world + real-world consequence
12. "Everyone noticed X, but nobody asked Y"

ROMAN TELUGU:
Write natural conversational Roman Telugu mixed with necessary English
YouTube vocabulary. Do not translate mechanically.
Example style:
"Ee trend venaka audience ni repeatedly click cheyinche actual trigger enti?
Mana video aa trigger ni real examples tho break down chestundi."

OUTPUT:
Return JSON only. No markdown. No commentary.
"""


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def _num(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _fmt_views(value: Any) -> str:
    n = _num(value)
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return f"{int(n):,}"


def _trend_type(title: str) -> str:
    t = title.lower()
    if any(x in t for x in ("trailer", "teaser", "movie", "film", "episode",
                             "series", "anime", "actor", "actress", "star")):
        return "Movies & Entertainment"
    if any(x in t for x in ("song", "music", "lyrics", "official video",
                             "cover", "concert", "singer")):
        return "Music"
    if any(x in t for x in ("minecraft", "roblox", "gta", "gameplay",
                             "gaming", "fortnite", "valorant")):
        return "Gaming"
    if any(x in t for x in ("ai", "iphone", "android", "tech", "robot",
                             "openai", "google")):
        return "Technology & AI"
    return "Other"


def _entertainment_subgenre(text: str) -> str:
    t = text.lower()
    mapping = [
        ("Thriller", ["thriller", "suspense", "chase", "killer", "murder"]),
        ("Crime", ["crime", "criminal", "police", "cop", "gangster", "heist"]),
        ("Mystery", ["mystery", "hidden", "secret", "unknown", "case"]),
        ("Horror", ["horror", "ghost", "haunted", "demon", "scary"]),
        ("Comedy", ["comedy", "funny", "comed", "prank"]),
        ("Action", ["action", "fight", "war", "battle", "mass"]),
        ("Romance", ["love", "romance", "couple", "relationship"]),
        ("Drama", ["drama", "family", "emotional"]),
        ("Sci-Fi", ["sci-fi", "science fiction", "future", "robot", "space"]),
        ("Fantasy", ["fantasy", "magic", "dragon", "supernatural"]),
        ("Anime", ["anime", "crunchyroll", "manga"]),
        ("Music", ["song", "music", "lyrics", "singer", "concert"]),
    ]
    for genre, words in mapping:
        if any(w in t for w in words):
            return genre
    return "Entertainment"


def normalize_trends(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Accepts flexible trend data.

    Preferred structure:
    {
      "india": {"longform": [...], "shorts": [...]},
      "world": {"longform": [...], "shorts": [...]},
      "genre": {"longform": [...], "shorts": [...]}
    }

    Each trend item can contain:
    trend, mentions, combined_views, avg_views, videos, titles, examples
    """
    out = {
        "india": {"longform": [], "shorts": []},
        "world": {"longform": [], "shorts": []},
        "genre": {"longform": [], "shorts": []},
    }

    def norm_list(items):
        result = []
        if not isinstance(items, list):
            return result
        for item in items:
            if isinstance(item, str):
                item = {"trend": item}
            x = dict(item)
            title = _clean_text(x.get("trend") or x.get("keyword") or x.get("title"))
            if not title:
                continue
            x["trend"] = title
            x["mentions"] = int(_num(x.get("mentions"), 1))
            x["combined_views"] = _num(
                x.get("combined_views", x.get("views", x.get("total_views"))))
            x["avg_views"] = _num(
                x.get("avg_views"),
                x["combined_views"] / max(x["mentions"], 1)
            )
            joined = " ".join([
                title,
                _clean_text(x.get("category")),
                _clean_text(x.get("description")),
                " ".join(map(str, x.get("titles", []) or []))
            ])
            x["category"] = x.get("category") or _trend_type(joined)
            if x["category"] in ("Movies & Entertainment", "Entertainment"):
                x["subgenre"] = x.get("subgenre") or _entertainment_subgenre(joined)
            else:
                x["subgenre"] = x.get("subgenre") or ""
            result.append(x)
        return result

    for region in ("india", "world"):
        region_data = raw.get(region, {})
        out[region]["longform"] = norm_list(
            region_data.get("longform", region_data.get("long_form", [])))
        out[region]["shorts"] = norm_list(region_data.get("shorts", []))

    genre = raw.get("genre", {})
    out["genre"]["longform"] = norm_list(
        genre.get("longform", genre.get("long_form", [])))
    out["genre"]["shorts"] = norm_list(genre.get("shorts", []))

    # If explicit genre data is absent, derive it from all video trends.
    if not out["genre"]["longform"]:
        out["genre"]["longform"] = _aggregate_genres(
            out["india"]["longform"] + out["world"]["longform"])
    if not out["genre"]["shorts"]:
        out["genre"]["shorts"] = _aggregate_genres(
            out["india"]["shorts"] + out["world"]["shorts"])

    return out


def _aggregate_genres(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    buckets: Dict[str, Dict[str, Any]] = {}
    for x in items:
        g = x.get("category") or "Other"
        b = buckets.setdefault(g, {
            "trend": g,
            "mentions": 0,
            "combined_views": 0.0,
            "examples": [],
            "subgenres": {},
        })
        b["mentions"] += int(x.get("mentions", 0))
        b["combined_views"] += _num(x.get("combined_views"))
        if x.get("trend") and len(b["examples"]) < 8:
            b["examples"].append(x["trend"])
        sg = x.get("subgenre")
        if sg:
            b["subgenres"][sg] = b["subgenres"].get(sg, 0) + int(x.get("mentions", 1))

    result = []
    for b in buckets.values():
        b["avg_views"] = b["combined_views"] / max(b["mentions"], 1)
        b["subgenre"] = max(
            b["subgenres"], key=b["subgenres"].get) if b["subgenres"] else ""
        result.append(b)
    return sorted(result, key=lambda z: z["combined_views"], reverse=True)


def _top(items: List[Dict[str, Any]], n: int = 10) -> List[Dict[str, Any]]:
    return sorted(
        items,
        key=lambda x: (
            _num(x.get("combined_views")),
            int(x.get("mentions", 0)),
            _num(x.get("avg_views")),
        ),
        reverse=True,
    )[:n]


def build_prompt(data: Dict[str, Any]) -> str:
    n = normalize_trends(data)

    compact = {
        "india": {
            "longform": _top(n["india"]["longform"]),
            "shorts": _top(n["india"]["shorts"]),
        },
        "world": {
            "longform": _top(n["world"]["longform"]),
            "shorts": _top(n["world"]["shorts"]),
        },
        "genre": {
            "longform": _top(n["genre"]["longform"]),
            "shorts": _top(n["genre"]["shorts"]),
        },
    }

    schema = {
        "top_high_ctr": {
            "title": "",
            "region": "India or World",
            "format": "Long-form 8-10 minutes or Shorts 45-60 seconds",
            "genre": "",
            "subgenre": "",
            "roman_telugu_logline": "",
            "hook": "",
            "why_people_click": "",
            "why_now": "",
            "source_trend": "",
            "ctr_score": 1,
            "retention_score": 1,
            "originality_score": 1
        },
        "india_youtube_trends": {
            "longform": [],
            "shorts": []
        },
        "world_youtube_trends": {
            "longform": [],
            "shorts": []
        },
        "youtube_genre_trends": {
            "longform": [],
            "shorts": []
        },
        "trend_based_shorts_ideas": [],
        "trend_based_longform_ideas": [],
        "general_shorts_ideas": [],
        "general_longform_ideas": [],
        "genre_combo_ideas": []
    }

    idea_schema = {
        "title": "",
        "region": "India or World",
        "genre": "",
        "subgenre": "",
        "roman_telugu_logline": "",
        "hook": "",
        "concept": "",
        "why_people_click": "",
        "why_it_can_work": "",
        "source_trends": [],
        "visual_potential": "",
        "ctr_score": 1,
        "retention_score": 1,
        "originality_score": 1
    }

    prompt = f"""
Create the final YouTube High CTR Idea Generator report.

SOURCE TREND DATA:
{json.dumps(compact, ensure_ascii=False, indent=2)}

HARD REQUIREMENTS:

1. TOP HIGH CTR IDEA
Choose ONE genuinely strong idea from the strongest combination of trend,
audience psychology and story potential. Put this FIRST.
It must include a strong Roman Telugu logline.

2. INDIA YOUTUBE TRENDS
Show BOTH:
- Long-form (8-10 minutes)
- Shorts (45-60 seconds)
For each trend explain:
- what the trend is
- mentions/views
- why it is trending based on the supplied signals
- likely audience trigger
- entertainment category when applicable
- specific subgenre when applicable (Thriller/Comedy/Crime/Mystery/Horror/
  Action/Romance/Drama/Sci-Fi/Fantasy/Music/Anime/etc.)
- example video/title if supplied by source data
Do not turn a raw keyword into a fake claim.

3. WORLD YOUTUBE TRENDS
Same requirements as India.

4. YOUTUBE GENRE TRENDS
For BOTH long-form and Shorts explain:
- genre performance
- why it is working
- audience psychology
- entertainment subgenre opportunities
- examples from supplied data where possible

5. TREND-BASED SHORTS IDEAS
Create 8 total:
- 4 India
- 4 World
45-60 seconds.
Each must be a REAL premise with a twist/reveal/conflict.
Each needs a natural Roman Telugu logline.
Use trend data as the trigger, not as the entire idea.

6. TREND-BASED LONG-FORM IDEAS
Create 8 total:
- 4 India
- 4 World
8-10 minutes.
Each must feel like a documentary, investigation, story, case, phenomenon,
or cinematic deep-dive worth watching for 8-10 minutes.
Natural Roman Telugu logline required.

7. GENERAL IDEAS NOT FROM CURRENT TRENDS
Create 8 Shorts and 8 long-form:
- India/World mixed.
- Do NOT reuse the current trend keywords as the premise.
- They must be specific and highly visual, not generic "strange place/job/rule"
  templates.
- The idea should be possible to research and turn into a real video.

8. GENRE-COMBO IDEAS
Combine the strongest genre signals, e.g.
Gaming + Mystery, Music + Psychology, Movies + Thriller, Entertainment +
Crime, Gaming + Documentary, etc.
Create 6 very strong ideas.
Every idea needs Roman Telugu logline.

QUALITY SCORING:
Scores must be honest.
Do not give 9/10 or 10/10 automatically.
A 9+ idea must have:
- strong curiosity gap
- concrete premise
- strong visual storytelling
- clear audience
- real tension/reveal
- trend or genre evidence when trend-based.

TITLE RULE:
Do not use repetitive templates such as:
"Why X Is Exploding"
"X: The Secret Everyone Missed"
"The Secret Nobody Knows"
unless the actual premise is substantially different.

ROMAN TELUGU RULE:
Loglines should sound like a Telugu creator talking naturally:
"Ee story lo..." / "Mana video..." / "Audience ki..." / "Asalu..."
Use Roman Telugu, not Telugu script.

Return JSON matching this exact top-level structure:
{json.dumps(schema, ensure_ascii=False)}
For each idea array use this exact object structure:
{json.dumps(idea_schema, ensure_ascii=False)}
Do not add extra top-level keys.
"""

    return prompt


def _extract_json(text: str) -> Dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.I)
        text = re.sub(r"\s*```$", "", text)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start:end + 1])
        raise


def _valid_idea(x: Any) -> bool:
    if not isinstance(x, dict):
        return False
    title = _clean_text(x.get("title"))
    logline = _clean_text(x.get("roman_telugu_logline"))
    return len(title) >= 12 and len(logline) >= 30


def _repair_ideas(items: Any, count: int) -> List[Dict[str, Any]]:
    if not isinstance(items, list):
        items = []
    good = [x for x in items if _valid_idea(x)]

    # Remove duplicate titles.
    seen = set()
    unique = []
    for x in good:
        key = _clean_text(x["title"]).lower()
        if key not in seen:
            seen.add(key)
            unique.append(x)

    return unique[:count]


def validate_report(report: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
    required = [
        "top_high_ctr",
        "india_youtube_trends",
        "world_youtube_trends",
        "youtube_genre_trends",
        "trend_based_shorts_ideas",
        "trend_based_longform_ideas",
        "general_shorts_ideas",
        "general_longform_ideas",
        "genre_combo_ideas",
    ]
    for key in required:
        if key not in report:
            report[key] = {} if key.endswith("trends") else []

    if not _valid_idea(report.get("top_high_ctr")):
        # Fail loudly rather than silently producing the old bad report.
        raise ValueError("LLM did not return a valid TOP HIGH CTR IDEA.")

    # Exact requested counts.
    counts = {
        "trend_based_shorts_ideas": 8,
        "trend_based_longform_ideas": 8,
        "general_shorts_ideas": 8,
        "general_longform_ideas": 8,
        "genre_combo_ideas": 6,
    }
    for key, count in counts.items():
        report[key] = _repair_ideas(report[key], count)
        if len(report[key]) < count:
            raise ValueError(
                f"LLM returned only {len(report[key])}/{count} valid ideas for {key}."
            )

    # Ensure trend tables are present even if the LLM omitted details.
    n = normalize_trends(data)
    for root, source in (
        ("india_youtube_trends", n["india"]),
        ("world_youtube_trends", n["world"]),
        ("youtube_genre_trends", n["genre"]),
    ):
        report[root].setdefault("longform", source["longform"])
        report[root].setdefault("shorts", source["shorts"])

    return report


# ---------------------------------------------------------------------------
# OPENROUTER
# ---------------------------------------------------------------------------

def generate_with_openrouter(data: Dict[str, Any]) -> Dict[str, Any]:
    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is not set.")

    if requests is None:
        raise RuntimeError("requests is not installed. Run: pip install requests")

    model = os.getenv(
        "OPENROUTER_MODEL",
        "google/gemini-2.5-flash"
    ).strip()

    payload = {
        "model": model,
        "temperature": 0.85,
        "max_tokens": 14000,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_prompt(data)},
        ],
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": os.getenv("OPENROUTER_SITE_URL", "https://github.com/"),
        "X-Title": os.getenv(
            "OPENROUTER_APP_NAME",
            "YouTube High CTR Idea Generator"
        ),
    }

    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers=headers,
        json=payload,
        timeout=180,
    )
    response.raise_for_status()

    body = response.json()
    content = body["choices"][0]["message"]["content"]
    return _extract_json(content)


# ---------------------------------------------------------------------------
# HIGH-QUALITY FALLBACK
# ---------------------------------------------------------------------------

def fallback_report(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Offline fallback. It intentionally uses strong story structures rather
    than the old generic "Why X is exploding" output.
    """
    n = normalize_trends(data)
    india = _top(n["india"]["longform"] + n["india"]["shorts"], 4)
    world = _top(n["world"]["longform"] + n["world"]["shorts"], 4)

    strongest = india[0] if india else {
        "trend": "Indian entertainment",
        "mentions": 0,
        "combined_views": 0,
        "subgenre": "Mystery",
    }
    sg = strongest.get("subgenre") or "Mystery"
    trend = strongest["trend"]

    top = {
        "title": f"The Pattern Behind India's New {sg} Obsession",
        "region": "India",
        "format": "Long-form 8-10 minutes",
        "genre": "Movies & Entertainment",
        "subgenre": sg,
        "roman_telugu_logline": (
            f"India YouTube lo '{trend}' laanti signals enduku repeated ga "
            f"audience attention ni capture chestunnayo, aa pattern venaka "
            f"unnadi {sg.lower()} storytelling aa, star power aa, leka "
            f"audience psychology aa ane question ni real examples tho "
            f"investigate cheyyadam."
        ),
        "hook": (
            f"Mana feed lo '{trend}' repeatedly kanipistundi. Kani audience "
            f"click chestunnadi trend kosama... leka trend venaka unna "
            f"oka deeper trigger kosama?"
        ),
        "why_people_click": (
            "The premise turns a visible trend into an unanswered audience-"
            "psychology question."
        ),
        "why_now": f"The supplied India trend data repeatedly signals {trend}.",
        "source_trend": trend,
        "ctr_score": 8,
        "retention_score": 9,
        "originality_score": 8,
    }

    def make_idea(region, x, longform):
        t = x.get("trend", "the current trend")
        genre = x.get("category", "Entertainment")
        sub = x.get("subgenre") or ("Mystery" if genre == "Movies & Entertainment" else "")
        if longform:
            title = f"The Hidden Engine Behind {t}: Why Audiences Can't Look Away"
            log = (
                f"{region} YouTube lo '{t}' signal ni starting point ga teesukoni, "
                f"audience enduku repeatedly return avutundo, content design, "
                f"emotion and {sub.lower() if sub else 'story'} mechanics ni "
                f"8–10 minutes lo cinematic investigation laga break down cheyyadam."
            )
        else:
            title = f"Why Everyone Suddenly Cares About {t}"
            log = (
                f"{region} YouTube lo '{t}' signal ni 45–60 seconds lo oka "
                f"sharp question ga turn chesi, audience attention venaka unna "
                f"unexpected reason ni fast reveal tho cheppadam."
            )
        return {
            "title": title,
            "region": region,
            "genre": genre,
            "subgenre": sub,
            "roman_telugu_logline": log,
            "hook": (
                f"'{t}' ni andaroo chustunnaru. Kani asalaina question "
                f"'{t}' kaadu — people enduku stop chesi chustunnaru?"
            ),
            "concept": (
                "Use the trend as evidence, then investigate the underlying "
                "story mechanism instead of making the keyword the story."
            ),
            "why_people_click": "Curiosity gap + recognizable trend + specific explanation.",
            "why_it_can_work": "It gives the audience an answer, not just a trend recap.",
            "source_trends": [t],
            "visual_potential": "Screens, title evolution, thumbnails, clips, charts and visual comparisons.",
            "ctr_score": 8,
            "retention_score": 8,
            "originality_score": 7,
        }

    trend_short = []
    trend_long = []
    for region, items in (("India", india), ("World", world)):
        for x in items[:4]:
            trend_short.append(make_idea(region, x, False))
            trend_long.append(make_idea(region, x, True))

    general_titles = [
        ("India", "The One Night That Changed an Entire Street"),
        ("India", "Why This Ordinary Place Becomes Extraordinary After Dark"),
        ("India", "The System Behind Something Millions Use Without Thinking"),
        ("India", "A Decision Made Years Ago Is Still Changing People's Lives"),
        ("World", "The Day a Normal System Suddenly Stopped Working"),
        ("World", "The Hidden Business Behind Something Everyone Takes for Granted"),
        ("World", "The Mystery That Exists in Plain Sight"),
        ("World", "The Human Story Behind a Technology Everyone Uses"),
    ]

    general_shorts, general_long = [], []
    for region, title in general_titles:
        base = {
            "title": title,
            "region": region,
            "genre": "Documentary",
            "subgenre": "Mystery",
            "roman_telugu_logline": (
                f"{region} lo ordinary ga kanipinche oka real-world phenomenon "
                f"venaka extraordinary story ni 45–60 seconds lo setup, tension, "
                f"reveal structure tho cheppadam."
            ),
            "hook": "First 3 seconds lo question. Final seconds lo reveal.",
            "concept": "Researchable real-world story with a concrete reveal.",
            "why_people_click": "Strong curiosity gap and real-world stakes.",
            "why_it_can_work": "Specific premise rather than generic trivia.",
            "source_trends": [],
            "visual_potential": "Maps, archive footage, diagrams, locations and cinematic B-roll.",
            "ctr_score": 7,
            "retention_score": 8,
            "originality_score": 8,
        }
        general_shorts.append(base.copy())
        lf = base.copy()
        lf["title"] = title + " — The Full Investigation"
        lf["roman_telugu_logline"] = (
            f"{region} lo ee phenomenon ela start ayyindi, people meeda "
            f"impact enti, and final ga audience expect cheyyani reveal enti "
            f"ane story ni 8–10 minutes documentary format lo investigate cheyyadam."
        )
        lf["visual_potential"] = "Archive + maps + interviews + cinematic reconstruction."
        general_long.append(lf)

    genre_ideas = [
        ("Gaming + Mystery", "The Game Mechanic That Quietly Changed How Millions Play"),
        ("Music + Psychology", "The 10 Seconds in a Song That Makes People Replay It"),
        ("Movies + Thriller", "Why One Trailer Can Create a Mystery Bigger Than the Movie"),
        ("Entertainment + Crime", "When a Fictional Crime Story Starts Looking Uncomfortably Real"),
        ("Gaming + Documentary", "How a Virtual World Became a Real Social Experiment"),
        ("Music + Entertainment", "The Hidden Moment That Turns a Song Into a Cultural Event"),
    ]
    combos = []
    for g, title in genre_ideas:
        combos.append({
            "title": title,
            "region": "India / World",
            "genre": g.split(" + ")[0],
            "subgenre": g.split(" + ")[1],
            "roman_telugu_logline": (
                f"{g} ni combine chesi, audience already familiar ga unna "
                f"world ni completely new question tho choodela chese "
                f"high-CTR story ni cinematic ga build cheyyadam."
            ),
            "hook": "Two familiar worlds. One unexpected question.",
            "concept": "Cross-genre premise designed for curiosity and visual storytelling.",
            "why_people_click": "Genre collision creates novelty.",
            "why_it_can_work": "The combination gives a stronger premise than either genre alone.",
            "source_trends": [],
            "visual_potential": "Fast genre transitions, examples, comparisons and cinematic B-roll.",
            "ctr_score": 8,
            "retention_score": 8,
            "originality_score": 9,
        })

    return {
        "top_high_ctr": top,
        "india_youtube_trends": {
            "longform": n["india"]["longform"],
            "shorts": n["india"]["shorts"],
        },
        "world_youtube_trends": {
            "longform": n["world"]["longform"],
            "shorts": n["world"]["shorts"],
        },
        "youtube_genre_trends": {
            "longform": n["genre"]["longform"],
            "shorts": n["genre"]["shorts"],
        },
        "trend_based_shorts_ideas": trend_short[:8],
        "trend_based_longform_ideas": trend_long[:8],
        "general_shorts_ideas": general_shorts[:8],
        "general_longform_ideas": general_long[:8],
        "genre_combo_ideas": combos[:6],
    }


# ---------------------------------------------------------------------------
# RENDERING
# ---------------------------------------------------------------------------

def render_trend_table(title: str, items: List[Dict[str, Any]]) -> List[str]:
    lines = [title, "-" * len(title)]
    if not items:
        lines.append("No trend data available.")
        return lines

    for i, x in enumerate(items, 1):
        trend = x.get("trend", "Unknown")
        mentions = int(x.get("mentions", 0))
        views = _fmt_views(x.get("combined_views", 0))
        avg = _fmt_views(x.get("avg_views", 0))
        category = x.get("category", "")
        sub = x.get("subgenre", "")
        lines.append(f"{i}. {trend}")
        lines.append(
            f"   Mentions: {mentions} | Combined views: {views} | Avg views: {avg}"
        )
        if category:
            lines.append(f"   Category: {category}")
        if sub:
            lines.append(f"   Sub-genre: {sub}")
        why = x.get("why_trending")
        if why:
            lines.append(f"   Why trending: {why}")
        examples = x.get("titles") or x.get("examples") or x.get("videos")
        if examples:
            if isinstance(examples, list):
                examples = " | ".join(map(str, examples[:3]))
            lines.append(f"   Example video/title: {examples}")
    lines.append("")
    return lines


def render_idea(i: int, x: Dict[str, Any]) -> List[str]:
    scores = (
        f"CTR {x.get('ctr_score', 'N/A')}/10 | "
        f"Retention {x.get('retention_score', 'N/A')}/10 | "
        f"Originality {x.get('originality_score', 'N/A')}/10"
    )
    return [
        f"{i}. {x.get('title', 'Untitled')}",
        f"Region: {x.get('region', 'India / World')}",
        f"Genre: {x.get('genre', 'N/A')}",
        f"Sub-genre: {x.get('subgenre', 'N/A')}",
        f"Roman Telugu Logline: {x.get('roman_telugu_logline', '')}",
        f"Hook: {x.get('hook', '')}",
        f"Concept: {x.get('concept', '')}",
        f"Why people click: {x.get('why_people_click', '')}",
        f"Why it can work: {x.get('why_it_can_work', '')}",
        f"Visual potential: {x.get('visual_potential', '')}",
        f"Source trends: {', '.join(map(str, x.get('source_trends', [])))}",
        f"Scores: {scores}",
        "",
    ]


def render_report(report: Dict[str, Any]) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    top = report["top_high_ctr"]

    lines = [
        "YOUTUBE HIGH CTR IDEA GENERATOR",
        f"Generated: {now}",
        "",
        "TOP HIGH CTR IDEA",
        "===================",
        top["title"],
        f"Region: {top.get('region', '')}",
        f"Format: {top.get('format', 'Long-form 8-10 minutes')}",
        f"Genre: {top.get('genre', '')}",
        f"Sub-genre: {top.get('subgenre', '')}",
        f"Roman Telugu Logline: {top['roman_telugu_logline']}",
        f"Hook: {top.get('hook', '')}",
        f"Why people click: {top.get('why_people_click', '')}",
        f"Why now: {top.get('why_now', '')}",
        f"Source trend: {top.get('source_trend', '')}",
        (
            f"Scores: CTR {top.get('ctr_score', 'N/A')}/10 | "
            f"Retention {top.get('retention_score', 'N/A')}/10 | "
            f"Originality {top.get('originality_score', 'N/A')}/10"
        ),
        "",
        "1. INDIA YOUTUBE TRENDS",
        "========================",
        "INDIA LONG-FORM TRENDS (8-10 minutes)",
        "",
    ]

    lines += render_trend_table("", report["india_youtube_trends"]["longform"])
    lines += [
        "INDIA SHORTS TRENDS (45-60 seconds)",
        "",
    ]
    lines += render_trend_table("", report["india_youtube_trends"]["shorts"])

    lines += [
        "2. WORLD YOUTUBE TRENDS",
        "========================",
        "WORLD LONG-FORM TRENDS (8-10 minutes)",
        "",
    ]
    lines += render_trend_table("", report["world_youtube_trends"]["longform"])
    lines += [
        "WORLD SHORTS TRENDS (45-60 seconds)",
        "",
    ]
    lines += render_trend_table("", report["world_youtube_trends"]["shorts"])

    lines += [
        "3. YOUTUBE GENRE TRENDS",
        "========================",
        "LONG-FORM GENRE TRENDS (8-10 minutes)",
        "",
    ]
    lines += render_trend_table("", report["youtube_genre_trends"]["longform"])
    lines += [
        "SHORTS GENRE TRENDS (45-60 seconds)",
        "",
    ]
    lines += render_trend_table("", report["youtube_genre_trends"]["shorts"])

    sections = [
        ("4. INDIA/WORLD TREND-BASED SHORTS IDEAS", "trend_based_shorts_ideas"),
        ("5. INDIA/WORLD TREND-BASED LONG-FORM IDEAS (8-10 minutes)", "trend_based_longform_ideas"),
        ("6. INDIA/WORLD GENERAL SHORTS IDEAS — NOT FROM CURRENT TRENDS", "general_shorts_ideas"),
        ("7. INDIA/WORLD GENERAL LONG-FORM IDEAS — NOT FROM CURRENT TRENDS", "general_longform_ideas"),
        ("8. GENRE-COMBO HIGH CTR IDEAS", "genre_combo_ideas"),
    ]

    for heading, key in sections:
        lines += [heading, "=" * len(heading), ""]
        for i, idea in enumerate(report[key], 1):
            lines += render_idea(i, idea)

    lines += [
        "CREATIVE STANDARD",
        "=================",
        "Ideas prioritize curiosity, emotional stakes, originality, visual",
        "potential, retention and honest high CTR.",
        "Trends are evidence; they are NOT automatically the video idea.",
    ]
    return "\n".join(lines)


def generate_report(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main public API.

    Uses OpenRouter when OPENROUTER_API_KEY exists.
    Falls back to a deterministic generator when it does not.
    """
    try:
        report = generate_with_openrouter(data)
        return validate_report(report, data)
    except Exception as exc:
        if os.getenv("STRICT_LLM", "0") == "1":
            raise
        print(f"[idea_generator] LLM unavailable/invalid: {exc}")
        print("[idea_generator] Using high-quality offline fallback.")
        return fallback_report(data)


def generate_text(data: Dict[str, Any]) -> str:
    return render_report(generate_report(data))
