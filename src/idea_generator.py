import os
import re
import json
import time
from pathlib import Path
from datetime import datetime, timedelta
from collections import Counter

import requests
from dotenv import load_dotenv


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

ENV_FILE = BASE_DIR / ".env"

DATA_DIR = BASE_DIR / "data"
SUMMARY_DIR = BASE_DIR / "summaries"

DATA_DIR.mkdir(parents=True, exist_ok=True)
SUMMARY_DIR.mkdir(parents=True, exist_ok=True)

load_dotenv(ENV_FILE)


YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

OPENROUTER_MODEL = os.getenv(
    "OPENROUTER_MODEL",
    "openai/gpt-4o-mini"
)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

TODAY = datetime.now().strftime("%Y-%m-%d")


# ============================================================
# SETTINGS
# ============================================================

# Representative world markets.
# "World" is not a single YouTube API region, so we sample
# several major markets.

WORLD_REGIONS = [
    "US",
    "GB",
    "CA",
    "AU",
    "BR",
    "JP",
    "KR",
    "ID",
    "DE",
    "FR",
]

INDIA_REGION = "IN"

MAX_TREND_VIDEOS_PER_REGION = 50

MAX_SHORTS_TRENDS = 40
MAX_LONGFORM_TRENDS = 40
MAX_GENRE_TRENDS = 30


# ============================================================
# YOUTUBE CATEGORY NAMES
# ============================================================

CATEGORY_NAMES = {
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


# ============================================================
# HELPERS
# ============================================================

def require_environment():

    missing = []

    if not YOUTUBE_API_KEY:
        missing.append("YOUTUBE_API_KEY")

    if not OPENROUTER_API_KEY:
        missing.append("OPENROUTER_API_KEY")

    if missing:
        print()
        print("=" * 70)
        print("ERROR: REQUIRED ENVIRONMENT VARIABLES ARE MISSING")
        print("=" * 70)

        for item in missing:
            print(f"❌ {item}")

        print()
        print("Add them to your .env file or GitHub Actions Secrets.")
        print()

        raise SystemExit(1)


def safe_int(value, default=0):
    try:
        return int(value)
    except Exception:
        return default


def parse_duration(duration):
    """
    Convert ISO 8601 YouTube duration into seconds.

    Example:
    PT45S -> 45
    PT8M20S -> 500
    PT1H2M -> 3720
    """

    if not duration:
        return 0

    match = re.match(
        r"PT"
        r"(?:(\d+)H)?"
        r"(?:(\d+)M)?"
        r"(?:(\d+)S)?",
        duration
    )

    if not match:
        return 0

    hours = safe_int(match.group(1))
    minutes = safe_int(match.group(2))
    seconds = safe_int(match.group(3))

    return hours * 3600 + minutes * 60 + seconds


def format_duration(seconds):

    minutes = seconds // 60
    secs = seconds % 60

    if minutes >= 60:
        hours = minutes // 60
        minutes = minutes % 60
        return f"{hours}h {minutes}m"

    return f"{minutes}m {secs}s"


def clean_text(text):

    if not text:
        return ""

    return re.sub(r"\s+", " ", text).strip()


# ============================================================
# YOUTUBE API
# ============================================================

def youtube_get(endpoint, params):

    url = f"https://www.googleapis.com/youtube/v3/{endpoint}"

    params = dict(params)
    params["key"] = YOUTUBE_API_KEY

    response = requests.get(
        url,
        params=params,
        timeout=30
    )

    if response.status_code != 200:

        print()
        print("YouTube API ERROR")
        print(response.status_code)
        print(response.text[:1000])

        response.raise_for_status()

    return response.json()


# ============================================================
# GET MOST POPULAR VIDEOS
# ============================================================

def get_most_popular(region_code, max_results=50):

    data = youtube_get(
        "videos",
        {
            "part": "snippet,contentDetails,statistics",
            "chart": "mostPopular",
            "regionCode": region_code,
            "maxResults": min(max_results, 50),
        }
    )

    videos = []

    for item in data.get("items", []):

        snippet = item.get("snippet", {})
        stats = item.get("statistics", {})
        details = item.get("contentDetails", {})

        video_id = item.get("id")

        duration_seconds = parse_duration(
            details.get("duration")
        )

        category_id = str(
            snippet.get("categoryId", "")
        )

        video = {
            "id": video_id,
            "title": clean_text(snippet.get("title")),
            "description": clean_text(
                snippet.get("description", "")
            )[:500],
            "channel": clean_text(
                snippet.get("channelTitle")
            ),
            "category_id": category_id,
            "category": CATEGORY_NAMES.get(
                category_id,
                "Other"
            ),
            "published_at": snippet.get(
                "publishedAt",
                ""
            ),
            "duration_seconds": duration_seconds,
            "duration": format_duration(
                duration_seconds
            ),
            "views": safe_int(
                stats.get("viewCount")
            ),
            "likes": safe_int(
                stats.get("likeCount")
            ),
            "comments": safe_int(
                stats.get("commentCount")
            ),
            "region": region_code,
        }

        videos.append(video)

    return videos


# ============================================================
# CLASSIFY FORMAT
# ============================================================

def classify_format(video):

    seconds = video.get("duration_seconds", 0)

    # Approximate Shorts candidates.
    # YouTube API does not expose a universal "Short" boolean
    # through mostPopular.

    if seconds <= 60:
        return "shorts"

    # Longform target window.
    if 7 * 60 <= seconds <= 12 * 60:
        return "longform"

    return "other"


# ============================================================
# INDIA TRENDS
# ============================================================

def collect_india_trends():

    print()
    print("=" * 70)
    print("COLLECTING INDIA YOUTUBE TRENDS")
    print("=" * 70)

    videos = get_most_popular(
        INDIA_REGION,
        MAX_TREND_VIDEOS_PER_REGION
    )

    shorts = []
    longform = []

    for video in videos:

        fmt = classify_format(video)

        if fmt == "shorts":
            shorts.append(video)

        elif fmt == "longform":
            longform.append(video)

    return {
        "shorts": shorts,
        "longform": longform,
        "all": videos,
    }


# ============================================================
# WORLD TRENDS
# ============================================================

def collect_world_trends():

    print()
    print("=" * 70)
    print("COLLECTING WORLD YOUTUBE TRENDS")
    print("=" * 70)

    all_videos = []

    for region in WORLD_REGIONS:

        print(f"Fetching {region}...")

        try:

            videos = get_most_popular(
                region,
                MAX_TREND_VIDEOS_PER_REGION
            )

            all_videos.extend(videos)

        except Exception as e:

            print(
                f"⚠ Could not fetch {region}: {e}"
            )

        # Avoid hammering API.
        time.sleep(0.2)

    shorts = []
    longform = []

    for video in all_videos:

        fmt = classify_format(video)

        if fmt == "shorts":
            shorts.append(video)

        elif fmt == "longform":
            longform.append(video)

    return {
        "shorts": shorts,
        "longform": longform,
        "all": all_videos,
    }


# ============================================================
# GENRE ANALYSIS
# ============================================================

def analyze_genres(videos):

    category_counter = Counter()

    for video in videos:

        category = video.get(
            "category",
            "Other"
        )

        category_counter[category] += 1

    result = []

    for category, count in category_counter.most_common():

        result.append(
            {
                "genre": category,
                "video_count": count,
            }
        )

    return result


# ============================================================
# TREND ANALYSIS
# ============================================================

def summarize_trends(videos, limit=30):

    if not videos:
        return []

    # Remove duplicate video IDs.
    unique = {}

    for video in videos:
        unique[video["id"]] = video

    videos = list(unique.values())

    # Sort by views.
    videos.sort(
        key=lambda x: x.get("views", 0),
        reverse=True
    )

    return videos[:limit]


def extract_trend_titles(videos):

    output = []

    for video in videos:

        output.append(
            {
                "title": video.get("title"),
                "category": video.get("category"),
                "duration": video.get("duration"),
                "views": video.get("views"),
                "region": video.get("region"),
            }
        )

    return output


# ============================================================
# OPENROUTER
# ============================================================

def openrouter_generate(
    system_prompt,
    user_prompt,
    temperature=0.85,
    max_tokens=12000
):

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/",
        "X-Title": "YouTube Trend Intelligence Idea Generator",
    }

    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    response = requests.post(
        OPENROUTER_URL,
        headers=headers,
        json=payload,
        timeout=180
    )

    if response.status_code != 200:

        print()
        print("OPENROUTER ERROR")
        print(response.status_code)
        print(response.text[:2000])

        response.raise_for_status()

    data = response.json()

    try:
        return data["choices"][0]["message"]["content"]
    except Exception:

        print("Unexpected OpenRouter response:")
        print(json.dumps(data, indent=2)[:5000])

        raise RuntimeError(
            "Could not extract AI response."
        )


# ============================================================
# AI SYSTEM PROMPT
# ============================================================

SYSTEM_PROMPT = """
You are an elite YouTube content strategist, creative director,
screenwriter and viral-format researcher.

Your job is NOT to produce generic YouTube ideas.

You create concepts that make a creator hear the idea and think:

"WAH. WHAT AN IDEA."

The concepts must feel:
- fresh
- clever
- highly clickable
- emotionally strong
- curiosity driven
- visually understandable
- easy to explain in one sentence
- capable of creating comments and discussion
- suitable for Indian/Indian-Telugu audiences when requested
- capable of working as YouTube content rather than sounding like
  generic movie plots

IMPORTANT:

DO NOT generate:
- childish ideas
- silly prank concepts
- generic "24 hours challenge"
- generic "I tried..."
- generic reaction videos
- generic motivational videos
- generic relationship drama
- boring daily-vlog concepts
- obvious horror clichés
- random AI concepts without a strong hook
- concepts that require a huge production
- ideas that depend entirely on expensive locations
- ideas copied from existing creators
- simple variations of already famous videos
- weak concepts with no central mystery
- concepts that are interesting only because of a title

A strong idea must have a CENTRAL HOOK.

The viewer should immediately ask:

"WHAT HAPPENS?"
"WHY?"
"HOW IS THAT POSSIBLE?"
"WHAT IF...?"

For longform:
- target approximately 8-10 minutes
- strong opening
- escalating curiosity
- meaningful middle
- strong reveal/payoff
- ending that feels worth watching
- should work with one creator or a small creator setup where possible

For Shorts:
- immediate hook
- no slow setup
- one strong premise
- escalating curiosity
- satisfying payoff/twist
- highly understandable within seconds

HIGH CTR does NOT mean clickbait lying.

The title should create curiosity while accurately representing
the actual premise.

Roman Telugu loglines must sound natural when spoken by a Telugu
person using English letters.

Do NOT translate word-by-word awkwardly.

Example of desired style:

"Prathi roju tana phone lo repu jarige oka notification vastundi.
Modati rendu rojulu ignore chestadu... kani moodo roju vachina
notification tana own death time ni chupistundi."

This is only an example of style.
Do not reuse the concept.

Every idea should have:
1. Title
2. Hook
3. Core concept
4. Roman Telugu logline
5. Why people will click
6. Opening 10-second hook
7. Payoff/twist
8. Production difficulty
9. Originality check

You should aggressively reject weak ideas internally before
returning them.

Quality is more important than quantity.
"""


# ============================================================
# BUILD TREND CONTEXT
# ============================================================

def build_trend_context(
    india,
    world
):

    india_shorts = summarize_trends(
        india["shorts"],
        MAX_SHORTS_TRENDS
    )

    india_long = summarize_trends(
        india["longform"],
        MAX_LONGFORM_TRENDS
    )

    world_shorts = summarize_trends(
        world["shorts"],
        MAX_SHORTS_TRENDS
    )

    world_long = summarize_trends(
        world["longform"],
        MAX_LONGFORM_TRENDS
    )

    india_genres = analyze_genres(
        india["all"]
    )

    world_genres = analyze_genres(
        world["all"]
    )

    context = {
        "date": TODAY,

        "india": {
            "shorts": extract_trend_titles(
                india_shorts
            ),
            "longform": extract_trend_titles(
                india_long
            ),
            "genres": india_genres,
        },

        "world": {
            "shorts": extract_trend_titles(
                world_shorts
            ),
            "longform": extract_trend_titles(
                world_long
            ),
            "genres": world_genres,
        },
    }

    return context


# ============================================================
# AI GENERATION
# ============================================================

def generate_ideas(trend_context):

    trend_json = json.dumps(
        trend_context,
        indent=2,
        ensure_ascii=False
    )

    user_prompt = f"""
TODAY:
{TODAY}

Here is the actual YouTube trend research collected from
India and multiple major world markets:

{trend_json}


Create a COMPLETE YouTube IDEA INTELLIGENCE REPORT.

The report must contain exactly these sections:

============================================================
SECTION 0 — HIGH CTR IDEA OF THE DAY
============================================================

Give 5 exceptional ideas.

These are the strongest concepts in the entire report.

For each:

TITLE:
HOOK:
CORE IDEA:
ROMAN TELUGU LOGLINE:
WHY THIS HAS HIGH CTR:
FIRST 10 SECONDS:
PAYOFF:
PRODUCTION DIFFICULTY:

Do not choose an idea merely because it resembles a current trend.

Choose concepts with exceptional curiosity.

============================================================
SECTION 1 — INDIA YOUTUBE TRENDS
============================================================

A. India Shorts Trends

Give:
- major patterns
- recurring hooks
- recurring subjects
- audience curiosity patterns
- format patterns
- genre patterns

Then give 10 strong Shorts concepts inspired by these patterns.

B. India Longform 8-10 Minute Trends

Analyze:
- topics
- formats
- hooks
- storytelling structures
- genres

Then give 10 strong 8-10 minute concepts.

============================================================
SECTION 2 — WORLD YOUTUBE TRENDS
============================================================

A. World Shorts Trends

Analyze major patterns.

Then give 10 strong Shorts concepts.

B. World Longform 8-10 Minute Trends

Analyze major patterns.

Then give 10 strong 8-10 minute concepts.

============================================================
SECTION 3 — YOUTUBE GENRE TRENDS
============================================================

Analyze the genre data.

Separate:

Shorts:
- strongest genres
- emerging combinations
- interesting genre crossovers

Longform:
- strongest genres
- emerging combinations
- interesting genre crossovers

Then give:
5 Shorts concepts
5 Longform concepts

============================================================
SECTION 4 — INDIA/WORLD TREND-BASED SHORTS
============================================================

Use actual trend patterns from the research.

Do NOT copy existing videos.

Transform trend signals into ORIGINAL concepts.

Give 15 ideas.

For every idea provide:

TITLE:
HOOK:
CORE CONCEPT:
ROMAN TELUGU LOGLINE:
WHY PEOPLE WILL CLICK:
FIRST 3 SECONDS:
PAYOFF:

============================================================
SECTION 5 — INDIA/WORLD TREND-BASED LONGFORM
============================================================

Use actual trend signals.

Do NOT copy existing videos.

Create original 8-10 minute concepts.

Give 15 ideas.

For every idea provide:

TITLE:
HOOK:
CORE CONCEPT:
ROMAN TELUGU LOGLINE:
WHY PEOPLE WILL WATCH:
OPENING:
STORY ESCALATION:
PAYOFF:

============================================================
SECTION 6 — GENERAL ORIGINAL SHORTS
============================================================

These must NOT depend on current YouTube trends.

They must be original concepts based on universal human
curiosity, psychology, mystery, comedy, thriller, technology,
social situations, unexpected consequences, etc.

Give 15 ideas.

The ideas should work even if today's trends disappear.

For every idea provide:

TITLE:
HOOK:
CORE CONCEPT:
ROMAN TELUGU LOGLINE:
WHY PEOPLE WILL CLICK:
PAYOFF:

============================================================
SECTION 7 — GENERAL ORIGINAL LONGFORM
============================================================

These must NOT depend on current YouTube trends.

Give 15 ORIGINAL 8-10 minute concepts.

Strong preference for concepts that can be produced by a
small creator.

For every idea provide:

TITLE:
HOOK:
CORE CONCEPT:
ROMAN TELUGU LOGLINE:
8-10 MINUTE STORY STRUCTURE:
OPENING:
ESCALATION:
REVEAL:
ENDING:
WHY PEOPLE WILL WATCH:

============================================================
FINAL QUALITY FILTER
============================================================

Before returning the report, silently remove every concept that
is:

- generic
- predictable
- childish
- low curiosity
- obvious clickbait
- expensive without reason
- copied
- too similar to another concept
- impossible to explain clearly
- dependent on a famous creator
- just a normal activity with a dramatic title

The final report should feel like a professional YouTube
creative director prepared it for a creator who wants people to
say:

"WAH... WHAT A CONCEPT."

Do not apologize.
Do not explain these instructions.
Just provide the final report.
"""

    print()
    print("=" * 70)
    print("GENERATING HIGH-QUALITY AI IDEAS")
    print("=" * 70)
    print()

    return openrouter_generate(
        SYSTEM_PROMPT,
        user_prompt,
        temperature=0.88,
        max_tokens=16000
    )


# ============================================================
# SAVE JSON TREND DATA
# ============================================================

def save_trend_data(context):

    output_file = DATA_DIR / (
        f"youtube_trends_{TODAY}.json"
    )

    with open(
        output_file,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            context,
            file,
            indent=2,
            ensure_ascii=False
        )

    print(
        f"✓ Trend data saved: {output_file}"
    )


# ============================================================
# SAVE AI REPORT
# ============================================================

def save_report(report):

    markdown_file = SUMMARY_DIR / (
        f"youtube_idea_report_{TODAY}.md"
    )

    text_file = SUMMARY_DIR / (
        f"youtube_idea_report_{TODAY}.txt"
    )

    with open(
        markdown_file,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(
            "# YOUTUBE TREND INTELLIGENCE + IDEA GENERATOR\n\n"
        )

        file.write(
            f"Generated: {TODAY}\n\n"
        )

        file.write(report)

    with open(
        text_file,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(
            "YOUTUBE TREND INTELLIGENCE + IDEA GENERATOR\n"
        )

        file.write(
            f"Generated: {TODAY}\n"
        )

        file.write(
            "=" * 70
            + "\n\n"
        )

        file.write(report)

    print()
    print("=" * 70)
    print("REPORT SAVED")
    print("=" * 70)

    print(f"Markdown: {markdown_file}")
    print(f"Text   : {text_file}")

    return markdown_file, text_file


# ============================================================
# MAIN
# ============================================================

def main():

    start_time = time.time()

    print("=" * 70)
    print("YOUTUBE TREND INTELLIGENCE + IDEA GENERATOR")
    print("=" * 70)

    print()
    print(f"Project root : {BASE_DIR}")
    print(f"Data folder  : {DATA_DIR}")
    print(f"Summary      : {SUMMARY_DIR}")
    print(f"Generated    : {TODAY}")
    print(f"AI Model     : {OPENROUTER_MODEL}")

    require_environment()

    # --------------------------------------------------------
    # INDIA
    # --------------------------------------------------------

    india = collect_india_trends()

    print()
    print(
        f"India Shorts collected   : "
        f"{len(india['shorts'])}"
    )

    print(
        f"India Longform collected : "
        f"{len(india['longform'])}"
    )

    # --------------------------------------------------------
    # WORLD
    # --------------------------------------------------------

    world = collect_world_trends()

    print()
    print(
        f"World Shorts collected   : "
        f"{len(world['shorts'])}"
    )

    print(
        f"World Longform collected : "
        f"{len(world['longform'])}"
    )

    # --------------------------------------------------------
    # BUILD CONTEXT
    # --------------------------------------------------------

    trend_context = build_trend_context(
        india,
        world
    )

    save_trend_data(
        trend_context
    )

    # --------------------------------------------------------
    # AI
    # --------------------------------------------------------

    report = generate_ideas(
        trend_context
    )

    # --------------------------------------------------------
    # SAVE
    # --------------------------------------------------------

    save_report(report)

    elapsed = time.time() - start_time

    print()
    print("=" * 70)
    print("COMPLETED SUCCESSFULLY")
    print("=" * 70)

    print(
        f"Execution time: {elapsed:.1f} seconds"
    )

    print()
    print(
        "✓ YouTube trend research completed"
    )

    print(
        "✓ India trends analyzed"
    )

    print(
        "✓ World trends analyzed"
    )

    print(
        "✓ Genre trends analyzed"
    )

    print(
        "✓ Shorts ideas generated"
    )

    print(
        "✓ 8-10 minute ideas generated"
    )

    print(
        "✓ Roman Telugu loglines generated"
    )

    print(
        "✓ High CTR ideas generated"
    )

    print()


if __name__ == "__main__":
    main()
