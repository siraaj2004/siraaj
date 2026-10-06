import os
import json
import re
import time
from datetime import datetime, timezone, timedelta
from collections import Counter

import requests
from dotenv import load_dotenv
from google import genai
from google.genai import types


# ============================================================
# YOUTUBE HIGH-CTR IDEA GENERATOR
# ============================================================
#
# PURPOSE:
# 1. India YouTube trends
# 2. World YouTube trends
# 3. Genre/category trends
# 4. Trend-based Shorts ideas
# 5. Trend-based 8-10 minute long-form ideas
# 6. General non-trend Shorts ideas
# 7. General non-trend 8-10 minute long-form ideas
#
# OUTPUT:
# output/
#   trend_data.json
#   ideas.json
#   youtube_idea_report.md
#
# ENVIRONMENT VARIABLES:
#
# YOUTUBE_API_KEY
# GEMINI_API_KEY
# GEMINI_MODEL
#
# Optional:
# VIDEOS_PER_REGION
# IDEAS_PER_SECTION
# OUTPUT_DIR
#
# ============================================================


# ============================================================
# LOAD ENVIRONMENT
# ============================================================

load_dotenv()


YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "").strip()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-2.5-flash"
).strip()

OUTPUT_DIR = os.getenv(
    "OUTPUT_DIR",
    "output"
).strip()

VIDEOS_PER_REGION = int(
    os.getenv(
        "VIDEOS_PER_REGION",
        "50"
    )
)

IDEAS_PER_SECTION = int(
    os.getenv(
        "IDEAS_PER_SECTION",
        "8"
    )
)


# ============================================================
# VALIDATION
# ============================================================

if not YOUTUBE_API_KEY:
    raise RuntimeError(
        "ERROR: YOUTUBE_API_KEY is missing."
    )

if not GEMINI_API_KEY:
    raise RuntimeError(
        "ERROR: GEMINI_API_KEY is missing."
    )


# ============================================================
# CREATE OUTPUT DIRECTORY
# ============================================================

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)


# ============================================================
# API CLIENT
# ============================================================

gemini_client = genai.Client(
    api_key=GEMINI_API_KEY
)


# ============================================================
# CONSTANTS
# ============================================================

YOUTUBE_API_URL = (
    "https://www.googleapis.com/youtube/v3"
)


INDIA_REGION = "IN"


WORLD_REGIONS = [
    "US",
    "GB",
    "CA",
    "AU",
    "BR",
    "JP",
    "KR",
    "DE",
    "FR",
    "MX"
]


GENERIC_TITLE_PATTERNS = [
    "top 10",
    "top 5",
    "top 7",
    "top 10 facts",
    "amazing facts",
    "interesting facts",
    "unknown facts",
    "shocking facts",
    "you won't believe",
    "you will not believe",
    "mind blowing facts",
    "motivational video",
    "motivation",
    "success story",
    "ai will change",
    "things you didn't know",
    "things you did not know"
]


# ============================================================
# TEXT HELPERS
# ============================================================

def clean_text(value):
    if value is None:
        return ""

    value = str(value)

    value = re.sub(
        r"\s+",
        " ",
        value
    )

    return value.strip()


def safe_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def safe_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def truncate(text, limit=400):
    text = clean_text(text)

    if len(text) <= limit:
        return text

    return text[:limit - 3] + "..."


# ============================================================
# YOUTUBE API REQUEST
# ============================================================

def youtube_request(endpoint, params):
    url = f"{YOUTUBE_API_URL}/{endpoint}"

    request_params = dict(params)

    request_params["key"] = YOUTUBE_API_KEY

    response = requests.get(
        url,
        params=request_params,
        timeout=40
    )

    if response.status_code != 200:
        try:
            error_data = response.json()
            message = error_data.get(
                "error",
                {}
            ).get(
                "message",
                response.text
            )
        except Exception:
            message = response.text

        raise RuntimeError(
            f"YouTube API error "
            f"{response.status_code}: "
            f"{message}"
        )

    return response.json()


# ============================================================
# GET YOUTUBE CATEGORIES
# ============================================================

def get_category_map(region_code):
    data = youtube_request(
        "videoCategories",
        {
            "part": "snippet",
            "regionCode": region_code
        }
    )

    category_map = {}

    for item in data.get("items", []):
        category_id = item.get("id")

        title = (
            item.get("snippet", {})
            .get("title", "")
        )

        if category_id and title:
            category_map[
                str(category_id)
            ] = clean_text(title)

    return category_map


# ============================================================
# GET MOST POPULAR VIDEOS
# ============================================================

def get_trending_videos(
    region_code,
    max_results=50
):
    max_results = max(
        1,
        min(
            int(max_results),
            50
        )
    )

    data = youtube_request(
        "videos",
        {
            "part": (
                "snippet,"
                "statistics,"
                "contentDetails"
            ),
            "chart": "mostPopular",
            "regionCode": region_code,
            "maxResults": max_results
        }
    )

    videos = []

    for item in data.get(
        "items",
        []
    ):
        snippet = item.get(
            "snippet",
            {}
        )

        statistics = item.get(
            "statistics",
            {}
        )

        content_details = item.get(
            "contentDetails",
            {}
        )

        videos.append(
            {
                "video_id": item.get(
                    "id",
                    ""
                ),
                "title": clean_text(
                    snippet.get(
                        "title",
                        ""
                    )
                ),
                "description": truncate(
                    snippet.get(
                        "description",
                        ""
                    ),
                    500
                ),
                "channel": clean_text(
                    snippet.get(
                        "channelTitle",
                        ""
                    )
                ),
                "category_id": str(
                    snippet.get(
                        "categoryId",
                        ""
                    )
                ),
                "published_at": snippet.get(
                    "publishedAt",
                    ""
                ),
                "views": safe_int(
                    statistics.get(
                        "viewCount",
                        0
                    )
                ),
                "likes": safe_int(
                    statistics.get(
                        "likeCount",
                        0
                    )
                ),
                "comments": safe_int(
                    statistics.get(
                        "commentCount",
                        0
                    )
                ),
                "duration": content_details.get(
                    "duration",
                    ""
                )
            }
        )

    return videos


# ============================================================
# YOUTUBE DURATION
# ============================================================

def parse_iso_duration(duration):
    if not duration:
        return 0

    pattern = re.compile(
        r"^PT"
        r"(?:(\d+)H)?"
        r"(?:(\d+)M)?"
        r"(?:(\d+)S)?$"
    )

    match = pattern.match(
        duration
    )

    if not match:
        return 0

    hours = safe_int(
        match.group(1)
    )

    minutes = safe_int(
        match.group(2)
    )

    seconds = safe_int(
        match.group(3)
    )

    return (
        hours * 3600
        + minutes * 60
        + seconds
    )


def classify_format(video):
    seconds = parse_iso_duration(
        video.get(
            "duration",
            ""
        )
    )

    if seconds <= 180:
        return "short"

    return "longform"


# ============================================================
# ANALYZE TRENDS
# ============================================================

def analyze_videos(
    videos,
    category_map
):
    category_counter = Counter()

    format_counter = Counter()

    for video in videos:
        category_id = str(
            video.get(
                "category_id",
                ""
            )
        )

        category_name = category_map.get(
            category_id,
            "Unknown"
        )

        category_counter[
            category_name
        ] += 1

        video_format = classify_format(
            video
        )

        format_counter[
            video_format
        ] += 1

    sorted_videos = sorted(
        videos,
        key=lambda video: video.get(
            "views",
            0
        ),
        reverse=True
    )

    categories = []

    for category, count in (
        category_counter.most_common()
    ):
        categories.append(
            {
                "category": category,
                "video_count": count
            }
        )

    return {
        "total_videos": len(videos),
        "formats": dict(
            format_counter
        ),
        "categories": categories,
        "top_videos": sorted_videos[:25]
    }


# ============================================================
# INDIA DATA
# ============================================================

def collect_india_data():
    print()
    print("=" * 70)
    print("INDIA YOUTUBE TREND RESEARCH")
    print("=" * 70)

    category_map = get_category_map(
        INDIA_REGION
    )

    videos = get_trending_videos(
        INDIA_REGION,
        VIDEOS_PER_REGION
    )

    for video in videos:
        video["source_region"] = "IN"

    analysis = analyze_videos(
        videos,
        category_map
    )

    print(
        f"India videos collected: "
        f"{len(videos)}"
    )

    return {
        "region": "India",
        "region_code": INDIA_REGION,
        "videos": videos,
        "analysis": analysis
    }


# ============================================================
# WORLD DATA
# ============================================================

def collect_world_data():
    print()
    print("=" * 70)
    print("WORLD YOUTUBE TREND RESEARCH")
    print("=" * 70)

    category_map = get_category_map(
        "US"
    )

    all_videos = []

    for region in WORLD_REGIONS:

        print(
            f"Collecting region: {region}"
        )

        try:
            videos = get_trending_videos(
                region,
                VIDEOS_PER_REGION
            )

            for video in videos:
                video["source_region"] = region

            all_videos.extend(
                videos
            )

            time.sleep(0.25)

        except Exception as error:
            print(
                f"WARNING: "
                f"{region} failed: "
                f"{error}"
            )

    analysis = analyze_videos(
        all_videos,
        category_map
    )

    print(
        f"World videos collected: "
        f"{len(all_videos)}"
    )

    return {
        "region": "World",
        "regions_used": WORLD_REGIONS,
        "videos": all_videos,
        "analysis": analysis
    }


# ============================================================
# COMPACT TREND DATA
# ============================================================

def compact_video(video):
    return {
        "title": video.get(
            "title",
            ""
        ),
        "channel": video.get(
            "channel",
            ""
        ),
        "views": video.get(
            "views",
            0
        ),
        "likes": video.get(
            "likes",
            0
        ),
        "comments": video.get(
            "comments",
            0
        ),
        "format": classify_format(
            video
        ),
        "region": video.get(
            "source_region",
            ""
        )
    }


def build_evidence(data):
    analysis = data.get(
        "analysis",
        {}
    )

    top_videos = analysis.get(
        "top_videos",
        []
    )

    return {
        "region": data.get(
            "region",
            ""
        ),
        "regions_used": data.get(
            "regions_used",
            []
        ),
        "total_videos": data.get(
            "analysis",
            {}
        ).get(
            "total_videos",
            0
        ),
        "format_distribution": analysis.get(
            "formats",
            {}
        ),
        "category_trends": analysis.get(
            "categories",
            []
        )[:20],
        "top_videos": [
            compact_video(video)
            for video in top_videos
        ]
    }


# ============================================================
# GEMINI SYSTEM PROMPT
# ============================================================

SYSTEM_PROMPT = """
You are an elite YouTube creative strategist,
viral-content researcher, storyteller and
showrunner.

Your job is to create genuinely strong YouTube
video concepts.

The user specifically does NOT want silly,
generic or low-effort ideas.

The target reaction is:

"WAHH... WHAT AN IDEA."

Every concept must have a strong CENTRAL PREMISE.

==================================================
DO NOT GENERATE
==================================================

- Generic Top 10 videos
- Generic Top 5 videos
- Generic facts videos
- Generic motivation
- Generic reaction videos
- Generic AI news
- Generic celebrity news
- Generic challenges
- Generic "you won't believe this"
- Generic "things you didn't know"
- Generic listicles
- Fake mysteries
- Fake facts
- Fake statistics
- Copied viral videos
- Reworded versions of existing titles
- Weak "what if" concepts
- Random combinations of unrelated topics
- Ideas requiring impossible production
- Ideas that depend entirely on a celebrity
- Ideas with no payoff
- Ideas with no visual storytelling
- Ideas that sound interesting only because of clickbait

==================================================
WHAT A GREAT IDEA NEEDS
==================================================

A strong concept should ideally contain:

1. A unique premise.
2. A strong curiosity gap.
3. Immediate emotional interest.
4. A visual storytelling opportunity.
5. Escalation.
6. A meaningful payoff/reveal.
7. A strong thumbnail possibility.
8. A strong title possibility.
9. Originality.
10. Realistic execution for a solo/small creator.

==================================================
TREND-BASED IDEAS
==================================================

When trend data is supplied:

DO NOT COPY TRENDING VIDEOS.

Instead identify:

- audience interests
- emotional patterns
- subjects
- formats
- curiosity triggers
- storytelling structures
- visual patterns
- audience behavior

Then transform those signals into NEW concepts.

A trend is evidence.

A trend is NOT the idea.

==================================================
GENERAL IDEAS
==================================================

When asked for general ideas:

DO NOT depend on today's trends.

Use evergreen creative mechanisms such as:

- curiosity
- mystery
- human psychology
- unusual experiments
- social behavior
- technology
- internet culture
- real-world observations
- hidden systems
- unexpected consequences
- emotional storytelling
- transformation
- investigation
- discovery
- contrast
- extreme constraints
- unusual places
- unusual people
- unexpected rules

==================================================
SHORTS
==================================================

Target:

20-60 seconds.

A Short needs:

HOOK
+
CURIOSITY
+
ESCALATION
+
PAYOFF

The viewer should understand why they should
continue watching within the first few seconds.

==================================================
LONGFORM
==================================================

Target:

8-10 minutes.

A long-form concept needs enough material for:

0:00-0:30
Strong hook

0:30-2:00
Setup

2:00-4:00
First development

4:00-6:00
Escalation

6:00-8:00
Major discovery/conflict

8:00-10:00
Payoff

Do not create an idea that is only interesting
for 20 seconds.

==================================================
ROMAN TELUGU
==================================================

Roman Telugu must sound natural.

Do NOT translate English word-for-word.

Write like a Telugu creator explaining the concept
to a friend using Roman Telugu.

==================================================
CTR
==================================================

High CTR does NOT mean fake clickbait.

A strong CTR concept creates a legitimate question
in the viewer's mind.

The title should create:

"I NEED TO KNOW WHAT HAPPENS."

==================================================
ORIGINALITY
==================================================

Avoid concepts that are obvious clones.

If an idea resembles an existing trend,
change the mechanism, setting, conflict,
perspective or payoff enough to become
a genuinely new concept.

==================================================
OUTPUT QUALITY
==================================================

Think deeply before generating.

Generate more concepts internally.

Reject weak concepts internally.

Only output the strongest concepts.

Return valid JSON only.
"""


# ============================================================
# GEMINI GENERATOR
# ============================================================

def generate_ideas(
    evidence,
    region,
    source_type
):

    if source_type == "trend_based":

        source_instruction = """
Use the YouTube trend evidence as research.

Extract deeper audience patterns.

Do not copy titles.

Do not copy creators.

Do not copy video concepts.

Create original concepts inspired by
the underlying audience behavior.
"""

    else:

        source_instruction = """
These ideas must NOT depend on current YouTube trends.

Use the trend data only as background context.

The concepts must work as evergreen/original
YouTube concepts even if today's trends disappear.
"""

    prompt = f"""
{source_instruction}

REGION:
{region}

TREND RESEARCH:
{json.dumps(
    evidence,
    ensure_ascii=False,
    indent=2
)}

Generate exactly:

{IDEAS_PER_SECTION} SHORTS ideas

and

{IDEAS_PER_SECTION} LONGFORM ideas.

LONGFORM = 8-10 minutes.

SHORTS = 20-60 seconds.

==================================================
EACH IDEA MUST CONTAIN
==================================================

title
one_line_concept
logline
roman_telugu_logline
opening_hook
curiosity_gap
escalation
payoff
thumbnail_concept
why_people_click
why_this_is_not_silly
production_difficulty
trend_connection

Scores:

high_ctr_score: 0-100
originality_score: 0-100
hook_score: 0-100
visual_score: 0-100

==================================================
QUALITY RULE
==================================================

Do NOT fill the requested number with weak ideas.

Think like a creative director.

A weak idea is worse than fewer excellent ideas.

However, return the requested number whenever
possible.

==================================================
JSON FORMAT
==================================================

{{
    "region": "{region}",
    "source_type": "{source_type}",
    "shorts": [
        {{
            "title": "",
            "one_line_concept": "",
            "logline": "",
            "roman_telugu_logline": "",
            "opening_hook": "",
            "curiosity_gap": "",
            "escalation": "",
            "payoff": "",
            "thumbnail_concept": "",
            "why_people_click": "",
            "why_this_is_not_silly": "",
            "production_difficulty": "",
            "trend_connection": "",
            "high_ctr_score": 0,
            "originality_score": 0,
            "hook_score": 0,
            "visual_score": 0
        }}
    ],
    "longform": [
        {{
            "title": "",
            "one_line_concept": "",
            "logline": "",
            "roman_telugu_logline": "",
            "opening_hook": "",
            "curiosity_gap": "",
            "escalation": "",
            "payoff": "",
            "thumbnail_concept": "",
            "why_people_click": "",
            "why_this_is_not_silly": "",
            "production_difficulty": "",
            "trend_connection": "",
            "high_ctr_score": 0,
            "originality_score": 0,
            "hook_score": 0,
            "visual_score": 0
        }}
    ]
}}
"""

    print(
        f"\nGenerating {source_type} ideas "
        f"for {region}..."
    )

    response = gemini_client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.9,
            max_output_tokens=20000,
            response_mime_type="application/json"
        )
    )

    response_text = (
        response.text or ""
    ).strip()

    if not response_text:
        raise RuntimeError(
            "Gemini returned an empty response."
        )

    response_text = clean_json_text(
        response_text
    )

    try:
        data = json.loads(
            response_text
        )

    except json.JSONDecodeError as error:

        print(
            "\nGemini returned invalid JSON."
        )

        print(
            response_text[:2000]
        )

        raise RuntimeError(
            "Could not parse Gemini JSON."
        ) from error

    data["region"] = region
    data["source_type"] = source_type

    return data


# ============================================================
# CLEAN GEMINI JSON
# ============================================================

def clean_json_text(text):

    text = text.strip()

    if text.startswith(
        "```json"
    ):
        text = text[
            len("```json"):
        ]

    elif text.startswith(
        "```"
    ):
        text = text[
            len("```"):
        ]

    if text.endswith(
        "```"
    ):
        text = text[
            :-len("```")
        ]

    text = text.strip()

    # Find first JSON object if extra text exists.
    first_brace = text.find("{")

    last_brace = text.rfind("}")

    if (
        first_brace >= 0
        and last_brace > first_brace
    ):
        text = text[
            first_brace:
            last_brace + 1
        ]

    return text.strip()


# ============================================================
# IDEA QUALITY SCORE
# ============================================================

def calculate_creative_score(idea):

    ctr = safe_float(
        idea.get(
            "high_ctr_score",
            0
        )
    )

    originality = safe_float(
        idea.get(
            "originality_score",
            0
        )
    )

    hook = safe_float(
        idea.get(
            "hook_score",
            0
        )
    )

    visual = safe_float(
        idea.get(
            "visual_score",
            0
        )
    )

    score = (
        ctr * 0.35
        + originality * 0.30
        + hook * 0.20
        + visual * 0.15
    )

    title = clean_text(
        idea.get(
            "title",
            ""
        )
    ).lower()

    for pattern in GENERIC_TITLE_PATTERNS:

        if pattern in title:
            score -= 12

    return round(
        max(
            0,
            min(
                100,
                score
            )
        ),
        1
    )


# ============================================================
# FILTER AND SORT IDEAS
# ============================================================

def filter_ideas(ideas):

    valid = []

    for idea in ideas:

        if not isinstance(
            idea,
            dict
        ):
            continue

        title = clean_text(
            idea.get(
                "title",
                ""
            )
        )

        logline = clean_text(
            idea.get(
                "logline",
                ""
            )
        )

        roman_logline = clean_text(
            idea.get(
                "roman_telugu_logline",
                ""
            )
        )

        if not title:
            continue

        if not logline:
            continue

        if not roman_logline:
            continue

        idea[
            "final_creative_score"
        ] = calculate_creative_score(
            idea
        )

        if (
            idea[
                "final_creative_score"
            ] >= 60
        ):
            valid.append(
                idea
            )

    valid.sort(
        key=lambda item: item.get(
            "final_creative_score",
            0
        ),
        reverse=True
    )

    return valid


# ============================================================
# REMOVE DUPLICATES
# ============================================================

def remove_duplicate_ideas(ideas):

    unique = []

    seen = set()

    for idea in ideas:

        normalized = re.sub(
            r"[^a-z0-9]+",
            "",
            clean_text(
                idea.get(
                    "title",
                    ""
                )
            ).lower()
        )

        if not normalized:
            continue

        if normalized in seen:
            continue

        seen.add(
            normalized
        )

        unique.append(
            idea
        )

    return unique


# ============================================================
# TOP IDEAS
# ============================================================

def get_top_ideas(
    results,
    count=15
):

    candidates = []

    for result in results:

        region = result.get(
            "region",
            ""
        )

        source_type = result.get(
            "source_type",
            ""
        )

        for idea in result.get(
            "shorts",
            []
        ):

            copy = dict(
                idea
            )

            copy["format"] = "Shorts"

            copy["region"] = region

            copy[
                "source_type"
            ] = source_type

            candidates.append(
                copy
            )

        for idea in result.get(
            "longform",
            []
        ):

            copy = dict(
                idea
            )

            copy["format"] = (
                "Longform 8-10 min"
            )

            copy["region"] = region

            copy[
                "source_type"
            ] = source_type

            candidates.append(
                copy
            )

    candidates = filter_ideas(
        candidates
    )

    candidates = remove_duplicate_ideas(
        candidates
    )

    return candidates[:count]


# ============================================================
# MARKDOWN FORMAT
# ============================================================

def format_idea_markdown(
    idea,
    number
):

    title = clean_text(
        idea.get(
            "title",
            "Untitled"
        )
    )

    return f"""
## {number}. {title}

**High CTR Score:** {idea.get("high_ctr_score", 0)}/100

**Final Creative Score:** {idea.get("final_creative_score", 0)}/100

**Originality:** {idea.get("originality_score", 0)}/100

**Hook:** {idea.get("hook_score", 0)}/100

**Visual:** {idea.get("visual_score", 0)}/100

### One-Line Concept

{idea.get("one_line_concept", "")}

### Logline

{idea.get("logline", "")}

### Roman Telugu Logline

{idea.get("roman_telugu_logline", "")}

### Opening Hook

{idea.get("opening_hook", "")}

### Curiosity Gap

{idea.get("curiosity_gap", "")}

### Escalation

{idea.get("escalation", "")}

### Payoff

{idea.get("payoff", "")}

### Thumbnail Concept

{idea.get("thumbnail_concept", "")}

### Why People Click

{idea.get("why_people_click", "")}

### Why This Is Not Silly

{idea.get("why_this_is_not_silly", "")}

### Production Difficulty

{idea.get("production_difficulty", "")}

### Trend Connection

{idea.get("trend_connection", "")}

---
"""


# ============================================================
# TREND REPORT SECTION
# ============================================================

def format_trend_section(
    title,
    evidence
):

    lines = []

    lines.append(
        f"\n# {title}\n"
    )

    lines.append(
        "## Format Distribution\n"
    )

    formats = evidence.get(
        "format_distribution",
        {}
    )

    for name, count in formats.items():

        lines.append(
            f"- {name}: {count}"
        )

    lines.append(
        "\n## Genre / Category Trends\n"
    )

    categories = evidence.get(
        "category_trends",
        []
    )

    for item in categories:

        category = item.get(
            "category",
            "Unknown"
        )

        count = item.get(
            "video_count",
            0
        )

        lines.append(
            f"- {category}: {count} videos"
        )

    lines.append(
        "\n## Top Videos\n"
    )

    top_videos = evidence.get(
        "top_videos",
        []
    )

    for index, video in enumerate(
        top_videos[:20],
        1
    ):

        title_text = video.get(
            "title",
            ""
        )

        views = safe_int(
            video.get(
                "views",
                0
            )
        )

        region = video.get(
            "region",
            ""
        )

        video_format = video.get(
            "format",
            ""
        )

        lines.append(
            f"{index}. {title_text} "
            f"| {views:,} views "
            f"| {region} "
            f"| {video_format}"
        )

    return "\n".join(
        lines
    )


# ============================================================
# IDEA SECTION
# ============================================================

def format_idea_section(
    title,
    results,
    format_name
):

    lines = []

    lines.append(
        f"\n# {title}\n"
    )

    counter = 1

    for result in results:

        region = result.get(
            "region",
            ""
        )

        source_type = result.get(
            "source_type",
            ""
        )

        ideas = result.get(
            format_name,
            []
        )

        ideas = filter_ideas(
            ideas
        )

        lines.append(
            f"\n## {region} "
            f"({source_type})\n"
        )

        for idea in ideas:

            lines.append(
                format_idea_markdown(
                    idea,
                    counter
                )
            )

            counter += 1

    return "\n".join(
        lines
    )


# ============================================================
# CREATE FINAL REPORT
# ============================================================

def create_report(
    india_evidence,
    world_evidence,
    results,
    top_ideas
):

    india_date = datetime.now(
        timezone.utc
    ).astimezone(
        timezone(
            timedelta(
                hours=5,
                minutes=30
            )
        )
    )

    report = []

    report.append(
        "# 🔥 YOUTUBE HIGH CTR IDEA GENERATOR"
    )

    report.append(
        f"\nGenerated: "
        f"{india_date.strftime('%Y-%m-%d %H:%M:%S IST')}"
    )

    report.append(
        "\n\n> High CTR scores are creative "
        "evaluation scores, not guaranteed YouTube CTR."
    )

    # --------------------------------------------------------
    # TOP IDEAS
    # --------------------------------------------------------

    report.append(
        "\n\n# 🚀 TOP HIGH-CTR IDEAS"
    )

    report.append(
        "\nThese are the strongest concepts "
        "selected from the complete idea pool."
    )

    for index, idea in enumerate(
        top_ideas,
        1
    ):

        report.append(
            format_idea_markdown(
                idea,
                index
            )
        )

    # --------------------------------------------------------
    # INDIA TRENDS
    # --------------------------------------------------------

    report.append(
        format_trend_section(
            "🇮🇳 INDIA YOUTUBE TRENDS",
            india_evidence
        )
    )

    # --------------------------------------------------------
    # WORLD TRENDS
    # --------------------------------------------------------

    report.append(
        format_trend_section(
            "🌍 WORLD YOUTUBE TRENDS",
            world_evidence
        )
    )

    trend_results = [
        result
        for result in results
        if result.get(
            "source_type"
        ) == "trend_based"
    ]

    general_results = [
        result
        for result in results
        if result.get(
            "source_type"
        ) == "general"
    ]

    # --------------------------------------------------------
    # TREND SHORTS
    # --------------------------------------------------------

    report.append(
        format_idea_section(
            "4. 🔥 INDIA / WORLD TREND-BASED SHORTS",
            trend_results,
            "shorts"
        )
    )

    # --------------------------------------------------------
    # TREND LONGFORM
    # --------------------------------------------------------

    report.append(
        format_idea_section(
            "5. 🎬 INDIA / WORLD TREND-BASED LONGFORM (8-10 MIN)",
            trend_results,
            "longform"
        )
    )

    # --------------------------------------------------------
    # GENERAL SHORTS
    # --------------------------------------------------------

    report.append(
        format_idea_section(
            "6. 💡 INDIA / WORLD GENERAL ORIGINAL SHORTS",
            general_results,
            "shorts"
        )
    )

    # --------------------------------------------------------
    # GENERAL LONGFORM
    # --------------------------------------------------------

    report.append(
        format_idea_section(
            "7. 🎥 INDIA / WORLD GENERAL ORIGINAL LONGFORM (8-10 MIN)",
            general_results,
            "longform"
        )
    )

    return "\n".join(
        report
    )


# ============================================================
# SAVE JSON
# ============================================================

def save_json(
    path,
    data
):

    with open(
        path,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2
        )


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 70)
    print(
        "STARTING YOUTUBE HIGH CTR IDEA GENERATOR"
    )
    print("=" * 70)

    print(
        f"Gemini model: {GEMINI_MODEL}"
    )

    print(
        f"Videos per region: "
        f"{VIDEOS_PER_REGION}"
    )

    print(
        f"Ideas per section: "
        f"{IDEAS_PER_SECTION}"
    )

    # --------------------------------------------------------
    # 1. COLLECT INDIA
    # --------------------------------------------------------

    india_data = collect_india_data()

    # --------------------------------------------------------
    # 2. COLLECT WORLD
    # --------------------------------------------------------

    world_data = collect_world_data()

    # --------------------------------------------------------
    # 3. BUILD EVIDENCE
    # --------------------------------------------------------

    india_evidence = build_evidence(
        india_data
    )

    world_evidence = build_evidence(
        world_data
    )

    # --------------------------------------------------------
    # 4. SAVE TREND DATA
    # --------------------------------------------------------

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    trend_file = os.path.join(
        OUTPUT_DIR,
        "trend_data.json"
    )

    save_json(
        trend_file,
        {
            "generated_at": timestamp,
            "india": india_evidence,
            "world": world_evidence
        }
    )

    print(
        f"\nTrend data saved: "
        f"{trend_file}"
    )

    # --------------------------------------------------------
    # 5. GENERATE IDEAS
    # --------------------------------------------------------

    results = []

    india_trend = generate_ideas(
        india_evidence,
        "India",
        "trend_based"
    )

    results.append(
        india_trend
    )

    world_trend = generate_ideas(
        world_evidence,
        "World",
        "trend_based"
    )

    results.append(
        world_trend
    )

    india_general = generate_ideas(
        india_evidence,
        "India",
        "general"
    )

    results.append(
        india_general
    )

    world_general = generate_ideas(
        world_evidence,
        "World",
        "general"
    )

    results.append(
        world_general
    )

    # --------------------------------------------------------
    # 6. TOP IDEAS
    # --------------------------------------------------------

    top_ideas = get_top_ideas(
        results,
        15
    )

    # --------------------------------------------------------
    # 7. SAVE JSON
    # --------------------------------------------------------

    ideas_file = os.path.join(
        OUTPUT_DIR,
        "ideas.json"
    )

    save_json(
        ideas_file,
        {
            "generated_at": timestamp,
            "top_ideas": top_ideas,
            "results": results
        }
    )

    print(
        f"\nIdeas JSON saved: "
        f"{ideas_file}"
    )

    # --------------------------------------------------------
    # 8. CREATE MARKDOWN
    # --------------------------------------------------------

    report = create_report(
        india_evidence,
        world_evidence,
        results,
        top_ideas
    )

    report_file = os.path.join(
        OUTPUT_DIR,
        "youtube_idea_report.md"
    )

    with open(
        report_file,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(
            report
        )

    print(
        f"\nMarkdown report saved: "
        f"{report_file}"
    )

    # --------------------------------------------------------
    # 9. PRINT TOP IDEAS
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print(
        "TOP HIGH-CTR IDEAS"
    )
    print("=" * 70)

    if not top_ideas:

        print(
            "No ideas passed the quality filter."
        )

    else:

        for index, idea in enumerate(
            top_ideas,
            1
        ):

            print()
            print(
                f"{index}. "
                f"{idea.get('title', '')}"
            )

            print(
                "   Score: "
                f"{idea.get('final_creative_score', 0
