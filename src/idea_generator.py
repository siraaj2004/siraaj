"""
Robust YouTube High-CTR Idea Generator
- Fixes OpenRouter 402 caused by requesting 30,000 max_tokens.
- Uses a small OpenRouter request only when useful.
- Falls back to deterministic local ideas when AI credits are unavailable.
- Keeps generate_report() and render_report() compatible with a typical app.py import.
- Does not require an LLM for the report to be generated.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests


# -----------------------------
# Configuration
# -----------------------------

IDEAS_PER_SECTION = int(os.getenv("IDEAS_PER_SECTION", "8"))
OPENROUTER_MODEL = os.getenv(
    "OPENROUTER_MODEL",
    "openai/gpt-oss-20b:free",
)
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# IMPORTANT:
# The old program requested 30000 tokens and OpenRouter rejected it.
# Keep this small. If your remaining balance is very low, the local
# fallback below will still produce a complete report.
OPENROUTER_MAX_TOKENS = int(os.getenv("OPENROUTER_MAX_TOKENS", "700"))
OPENROUTER_TIMEOUT = int(os.getenv("OPENROUTER_TIMEOUT", "45"))

OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "output"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


SECTIONS = [
    ("India YouTube Trends", "india_trends"),
    ("World YouTube Trends", "world_trends"),
    ("YouTube Genre Trends", "genre_trends"),
    ("Trend-Based Shorts Ideas", "trend_shorts"),
    ("Trend-Based Longform Ideas", "trend_longform"),
    ("General India and World Shorts Ideas", "general_shorts"),
    ("General India and World Longform Ideas", "general_longform"),
    ("Genre-Fusion High-CTR Ideas", "genre_fusion"),
]


# -----------------------------
# Small helpers
# -----------------------------

def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def _video_title(video: Any) -> str:
    if isinstance(video, dict):
        for key in ("title", "video_title", "name"):
            if video.get(key):
                return _clean_text(video[key])
    return _clean_text(video)


def _video_url(video: Any) -> str:
    if not isinstance(video, dict):
        return ""

    for key in ("url", "video_url", "watch_url", "link"):
        value = video.get(key)
        if value:
            return _clean_text(value)

    video_id = video.get("videoId") or video.get("video_id") or video.get("id")
    if isinstance(video_id, str) and video_id:
        return f"https://www.youtube.com/watch?v={video_id}"

    return ""


def _compact_videos(videos: Any, limit: int = 25) -> list[dict[str, str]]:
    """Turn many possible YouTube API structures into a small prompt dataset."""
    if videos is None:
        return []

    if isinstance(videos, dict):
        for key in ("videos", "items", "data", "results"):
            if isinstance(videos.get(key), list):
                videos = videos[key]
                break
        else:
            videos = [videos]

    if not isinstance(videos, (list, tuple)):
        return []

    result = []
    seen = set()

    for item in videos:
        title = _video_title(item)
        if not title or title.lower() in seen:
            continue

        seen.add(title.lower())
        result.append(
            {
                "title": title[:180],
                "url": _video_url(item),
            }
        )

        if len(result) >= limit:
            break

    return result


def _extract_json(text: str) -> Any:
    """Accept clean JSON, fenced JSON, or JSON embedded in prose."""
    if not text:
        return None

    text = text.strip()

    # Remove markdown fences.
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.I)
    text = re.sub(r"\s*```$", "", text)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Find the first JSON object/array.
    candidates = []
    first_obj = text.find("{")
    first_arr = text.find("[")
    if first_obj >= 0:
        candidates.append(first_obj)
    if first_arr >= 0:
        candidates.append(first_arr)

    if not candidates:
        return None

    start = min(candidates)

    # Try progressively shorter endings.
    for end in range(len(text), start + 1, -1):
        candidate = text[start:end].strip()
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue

    return None


# -----------------------------
# OpenRouter
# -----------------------------

def _openrouter_key() -> str:
    return (
        os.getenv("OPENROUTER_API_KEY")
        or os.getenv("OPENROUTER_KEY")
        or ""
    ).strip()


def _openrouter_generate(prompt: str) -> Any:
    """
    One deliberately small request.

    The old code requested 30000 output tokens. This implementation never
    does that. A 402/401/429/5xx error is treated as an unavailable AI
    provider and the local generator takes over.
    """
    api_key = _openrouter_key()
    if not api_key:
        return None

    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a concise YouTube trend analyst. "
                    "Return valid JSON only. Never use markdown fences."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.85,
        "max_tokens": max(250, min(OPENROUTER_MAX_TOKENS, 700)),
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/",
        "X-Title": "YouTube High CTR Idea Generator",
    }

    try:
        response = requests.post(
            OPENROUTER_URL,
            headers=headers,
            json=payload,
            timeout=OPENROUTER_TIMEOUT,
        )

        if response.status_code != 200:
            # Do not crash the entire report because of provider credits.
            print(
                f"[WARN] OpenRouter unavailable: HTTP {response.status_code}. "
                "Using local fallback."
            )
            return None

        data = response.json()
        choices = data.get("choices") or []
        if not choices:
            return None

        message = choices[0].get("message") or {}
        content = message.get("content", "")
        return _extract_json(content)

    except requests.RequestException as exc:
        print(f"[WARN] OpenRouter request failed: {exc}")
        return None
    except (ValueError, TypeError, KeyError) as exc:
        print(f"[WARN] OpenRouter response parse failed: {exc}")
        return None


# -----------------------------
# Local fallback
# -----------------------------

GENRES = [
    "Thriller",
    "Crime",
    "Comedy",
    "Mystery",
    "Psychological Thriller",
    "Horror",
    "Tech Mystery",
]


def _trend_names(videos: list[dict[str, str]], limit: int = 5) -> list[str]:
    return [v["title"] for v in videos[:limit] if v.get("title")]


def _local_ideas(section_key: str, videos: list[dict[str, str]], count: int) -> list[dict[str, Any]]:
    trends = _trend_names(videos)
    trend_a = trends[0] if trends else "today's biggest YouTube trend"
    trend_b = trends[1] if len(trends) > 1 else "a surprising internet trend"

    templates: dict[str, list[tuple[str, str, str]]] = {
        "india_trends": [
            ("India Trend Test: {a} Ni Real Life Lo Try Chesthe?",
             "Trending format ni Telugu creator angle lo test chesi unexpected result reveal cheyyadam.",
             "Trend + curiosity + payoff"),
            ("{a} Venaka Unna Real Reason Enti?",
             "Trending topic ni surface-level ga kakunda mystery/reason angle lo break cheyyadam.",
             "Curiosity gap"),
            ("India Lo Andaru Discuss Chestunna {a} — But Nobody Asked This",
             "Popular topic lo overlooked question ni investigate cheyyadam.",
             "Contrarian hook"),
            ("{b} Ni 24 Hours Follow Chesthe Em Jaruguthundi?",
             "Trend ni challenge format lo convert chesi measurable result chupinchadam.",
             "Challenge + result"),
        ],
        "world_trends": [
            ("Why The World Is Suddenly Obsessed With {a}",
             "Global trend ni Telugu audience ki simple story format lo explain cheyyadam.",
             "Global curiosity"),
            ("I Tried The Internet's {a} Trend So You Don't Have To",
             "Popular global format ni creator experiment ga transform cheyyadam.",
             "Experiment"),
            ("The Strange Reason {a} Became Huge",
             "Trend rise ki possible cultural/format reasons ni explain cheyyadam.",
             "Why-now hook"),
            ("{b}: Global Trend Or Just Internet Hype?",
             "Trend longevity ni challenge chese analysis.",
             "Debate"),
        ],
        "genre_trends": [
            ("The New Telugu Thriller Formula Everyone Is Copying",
             "Thriller pacing, mystery reveals and cliffhangers ni creator-friendly format lo analyse cheyyadam.",
             "Thriller"),
            ("Crime + Comedy Is Getting More Addictive — Here's Why",
             "Crime stakes ni comedy timing tho combine chese format explain cheyyadam.",
             "Crime-Comedy"),
            ("Psychological Thriller Videos: The Hook That Makes People Stay",
             "First 20 seconds lo unanswered question create cheyyadam.",
             "Psychological Thriller"),
            ("Mystery Videos Without Expensive Production",
             "Low-budget locations tho mystery tension build cheyyadam.",
             "Mystery"),
        ],
        "trend_shorts": [
            ("You Have 15 Seconds To Find The Hidden Clue",
             "Fast visual mystery with one hidden clue and replay-friendly ending.",
             "Mystery"),
            ("Everyone Misses This Detail In {a}",
             "One visual clue ni highlight chesi comments lo answer adagadham.",
             "Curiosity"),
            ("Wait For The Last 3 Seconds...",
             "Delayed reveal structure with a strong payoff.",
             "Retention"),
            ("I Tested The Viral {b} Trick",
             "Quick experiment with a clear result.",
             "Experiment"),
        ],
        "trend_longform": [
            ("I Spent 24 Hours Inside The {a} Trend",
             "8–10 minute challenge: setup → rules → failures → final result.",
             "Challenge"),
            ("The Mystery Behind {a}: What Nobody Is Talking About",
             "8–10 minute investigation built around clues and a final explanation.",
             "Mystery"),
            ("I Recreated The Internet's {b} Trend With ₹500",
             "Budget challenge with escalating failures and final comparison.",
             "Experiment"),
            ("Why This Trend Exploded — And How It Could Die",
             "Trend lifecycle explained through story, examples and creator lessons.",
             "Analysis"),
        ],
        "general_shorts": [
            ("The Door Was Locked… But Something Was Moving Inside",
             "Solo suspense short with sound design and a final visual reveal.",
             "Thriller"),
            ("My Phone Recorded Something I Didn't See",
             "Found-footage style mystery designed around a replayable clue.",
             "Mystery"),
            ("I Heard My Own Voice From The Next Room",
             "Solo crime-thriller setup with a final explanation twist.",
             "Psychological Thriller"),
            ("The 10-Second Rule Nobody Should Break",
             "Simple rule-based story that escalates into a twist.",
             "Horror"),
        ],
        "general_longform": [
            ("I Followed A Stranger's Routine For 24 Hours",
             "Solo experiment that slowly turns into a mystery.",
             "Psychological Thriller"),
            ("I Tried To Solve A Crime With Only 5 Clues",
             "Audience gets the clues before the final reveal.",
             "Crime-Mystery"),
            ("I Turned My Room Into A Mystery Game",
             "Low-budget production with clues, false leads and a final reveal.",
             "Mystery"),
            ("I Spent One Night Following The Weirdest Internet Rule",
             "Story-first challenge with escalating consequences.",
             "Thriller"),
        ],
        "genre_fusion": [
            ("Crime-Comedy: The Worst Detective Solves A Serious Case",
             "Comedy character inside a genuine mystery so the stakes remain real.",
             "Crime + Comedy"),
            ("Thriller + Minecraft: The World Changes Every Night",
             "Solo gaming narrative where each night reveals a new real-world clue.",
             "Thriller + Gaming"),
            ("Comedy + Psychological Thriller: My App Knows My Next Move",
             "Funny setup gradually becomes unsettling when predictions come true.",
             "Comedy + Psychological Thriller"),
            ("Mystery + Challenge: 8 Clues, 1 Room, 10 Minutes",
             "Audience can solve the mystery alongside the creator.",
             "Mystery + Challenge"),
        ],
    }

    base = templates.get(section_key, templates["general_shorts"])
    output = []

    for i in range(count):
        title, logline, genre = base[i % len(base)]

        title = title.format(a=trend_a, b=trend_b)

        output.append(
            {
                "rank": i + 1,
                "title": title,
                "format": (
                    "Shorts"
                    if "shorts" in section_key
                    else "Longform 8–10 min"
                ),
                "genre": genre,
                "why_it_can_work": (
                    "Strong curiosity gap, simple premise, clear escalation, "
                    "and a payoff that can be understood from the title/thumbnail."
                ),
                "logline_roman_telugu": (
                    "Oka simple setup tho start ayyi, clues/escalation tho tension "
                    "perigi, last lo unexpected reveal tho payoff ivvali. "
                    + logline
                ),
                "trend_reference": trend_a if trends else "Evergreen concept",
            }
        )

    return output


def _normalize_ai_ideas(data: Any, count: int) -> list[dict[str, Any]]:
    if isinstance(data, dict):
        for key in ("ideas", "items", "results", "high_ctr_ideas"):
            if isinstance(data.get(key), list):
                data = data[key]
                break

    if not isinstance(data, list):
        return []

    result = []
    for i, item in enumerate(data[:count], start=1):
        if isinstance(item, str):
            result.append(
                {
                    "rank": i,
                    "title": item.strip(),
                    "format": "",
                    "genre": "",
                    "why_it_can_work": "",
                    "logline_roman_telugu": "",
                    "trend_reference": "",
                }
            )
        elif isinstance(item, dict):
            title = (
                item.get("title")
                or item.get("idea")
                or item.get("headline")
            )
            if not title:
                continue

            result.append(
                {
                    "rank": i,
                    "title": _clean_text(title),
                    "format": _clean_text(item.get("format")),
                    "genre": _clean_text(item.get("genre")),
                    "why_it_can_work": _clean_text(
                        item.get("why_it_can_work")
                        or item.get("why")
                        or item.get("reason")
                    ),
                    "logline_roman_telugu": _clean_text(
                        item.get("logline_roman_telugu")
                        or item.get("logline")
                    ),
                    "trend_reference": _clean_text(
                        item.get("trend_reference")
                        or item.get("source_video")
                    ),
                }
            )

    return result


def _generate_section(section_key: str, videos: list[dict[str, str]], count: int) -> list[dict[str, Any]]:
    """
    Try one compact AI call. If the account cannot afford it, immediately
    use local ideas. This prevents 8 sections from repeatedly generating
    the same HTTP 402 error.
    """
    compact = json.dumps(videos[:12], ensure_ascii=False)

    prompt = f"""
Create exactly {min(count, 4)} high-CTR YouTube ideas for section "{section_key}".

Input trend videos:
{compact}

Rules:
- Telugu creator audience.
- Ideas must be practical for a solo creator.
- Avoid generic/silly ideas.
- For entertainment, explicitly name the genre.
- Shorts should be fast and replayable.
- Longform means 8–10 minutes.
- Include a Roman Telugu logline.
- Return ONLY this JSON:
{{
  "ideas": [
    {{
      "title": "...",
      "format": "...",
      "genre": "...",
      "why_it_can_work": "...",
      "logline_roman_telugu": "...",
      "trend_reference": "..."
    }}
  ]
}}
"""

    ai_data = _openrouter_generate(prompt)
    ideas = _normalize_ai_ideas(ai_data, min(count, 4))

    # Always fill the complete requested count locally.
    local = _local_ideas(section_key, videos, count)

    used = {x["title"].lower() for x in ideas}
    for item in local:
        if len(ideas) >= count:
            break
        if item["title"].lower() not in used:
            item["rank"] = len(ideas) + 1
            ideas.append(item)
            used.add(item["title"].lower())

    for i, item in enumerate(ideas, start=1):
        item["rank"] = i

    return ideas[:count]


# -----------------------------
# Public API expected by app.py
# -----------------------------

def generate_report(*args, **kwargs) -> dict[str, Any]:
    """
    Flexible public function.

    It accepts positional/keyword arguments from older versions of the
    project so app.py does not have to be rewritten just because the
    generator was fixed.

    Recognized inputs:
      - india_videos
      - world_videos
      - videos / data / trend_data
      - ideas_per_section
    """
    count = int(
        kwargs.get("ideas_per_section")
        or kwargs.get("num_ideas")
        or IDEAS_PER_SECTION
    )
    count = max(1, min(count, 8))

    india_videos = kwargs.get("india_videos")
    world_videos = kwargs.get("world_videos")

    # Positional compatibility.
    if india_videos is None and len(args) >= 1:
        india_videos = args[0]
    if world_videos is None and len(args) >= 2:
        world_videos = args[1]

    if india_videos is None:
        india_videos = kwargs.get("videos") or kwargs.get("data") or kwargs.get("trend_data")
    if world_videos is None:
        world_videos = kwargs.get("world") or kwargs.get("world_data")

    india = _compact_videos(india_videos, 25)
    world = _compact_videos(world_videos, 25)

    # If only one dataset was supplied, use it as a general trend pool.
    if not world:
        world = list(india)
    if not india:
        india = list(world)

    report = {
        "title": "YOUTUBE HIGH CTR IDEA GENERATOR",
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(),
        "ideas_per_section": count,
        "ai_provider": "OpenRouter + local fallback",
        "sections": {},
    }

    for title, key in SECTIONS:
        videos = world if "world" in key else india
        if key in {"genre_trends", "general_shorts", "general_longform", "genre_fusion"}:
            videos = india + world

        print(f"[INFO] Generating: {title}")
        report["sections"][key] = {
            "title": title,
            "ideas": _generate_section(key, videos, count),
        }

    return report


def render_report(report: Any, output_path: str | Path | None = None) -> str:
    """
    Render report to a readable TXT file and return the text.
    If output_path is supplied, the text is written there.
    """
    if isinstance(report, str):
        text = report
    else:
        lines = [
            "=" * 60,
            "YOUTUBE HIGH CTR IDEA GENERATOR",
            "=" * 60,
            f"Generated: {report.get('generated_at', '')}",
            f"Ideas per section: {report.get('ideas_per_section', IDEAS_PER_SECTION)}",
            "",
        ]

        for number, (_, key) in enumerate(SECTIONS, start=1):
            section = report.get("sections", {}).get(key, {})
            lines.extend(
                [
                    f"SECTION {number}: {section.get('title', key)}",
                    "-" * 60,
                ]
            )

            ideas = section.get("ideas", [])
            if not ideas:
                lines.append("No ideas generated.")
                lines.append("")
                continue

            for item in ideas:
                lines.extend(
                    [
                        f"{item.get('rank', '')}. {item.get('title', '')}",
                        f"Format: {item.get('format', '')}",
                        f"Genre: {item.get('genre', '')}",
                        f"Why it can work: {item.get('why_it_can_work', '')}",
                        f"Roman Telugu logline: {item.get('logline_roman_telugu', '')}",
                        f"Trend reference: {item.get('trend_reference', '')}",
                        "",
                    ])

            lines.append("")

        lines.extend(
            [
                "=" * 60,
                "END OF YOUTUBE HIGH CTR IDEA REPORT",
                "=" * 60,
            ]
        )

        text = "\n".join(lines)

    if output_path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    return text


def save_json(report: dict[str, Any], path: str | Path | None = None) -> Path:
    path = Path(path or OUTPUT_DIR / "youtube_high_ctr_ideas.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


def save_txt(report: dict[str, Any], path: str | Path | None = None) -> Path:
    path = Path(path or OUTPUT_DIR / "youtube_high_ctr_report.txt")
    render_report(report, path)
    return path


if __name__ == "__main__":
    # Standalone test. It does not need YouTube API access.
    demo = generate_report(
        india_videos=[
            {"title": "Sample India Trend Video", "videoId": "demo1"},
            {"title": "Popular Telugu Mystery Video", "videoId": "demo2"},
        ],
        world_videos=[
            {"title": "Global Challenge Trend", "videoId": "demo3"},
            {"title": "Global Mystery Trend", "videoId": "demo4"},
        ],
        ideas_per_section=IDEAS_PER_SECTION,
    )

    txt = save_txt(demo)
    js = save_json(demo)

    print(f"[OK] TXT:  {txt}")
    print(f"[OK] JSON: {js}")
