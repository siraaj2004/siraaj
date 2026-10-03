import os
import sys
import json
import re
from pathlib import Path
from datetime import datetime

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

try:
    import requests
except ImportError:
    requests = None


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"

if load_dotenv:
    load_dotenv(ENV_FILE)

OPENROUTER_API_KEY = os.getenv(
    "OPENROUTER_API_KEY",
    ""
).strip()

YOUTUBE_API_KEY = os.getenv(
    "YOUTUBE_API_KEY",
    ""
).strip()

OPENROUTER_MODEL = os.getenv(
    "OPENROUTER_MODEL",
    "google/gemini-2.0-flash-001"
).strip()

OUTPUT_DIR = BASE_DIR / "summaries"
OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

TODAY = datetime.now().strftime(
    "%Y-%m-%d %H:%M:%S"
)

TIMEOUT = int(
    os.getenv(
        "REQUEST_TIMEOUT",
        "120"
    )
)


# ============================================================
# YOUTUBE REGION CONFIGURATION
# ============================================================

# India
INDIA_REGION = "IN"

# There is no single official "WORLD" YouTube region.
# We collect several large/current markets and let AI
# identify cross-market patterns.
WORLD_REGIONS = {
    "United States": "US",
    "United Kingdom": "GB",
    "Canada": "CA",
    "Australia": "AU",
    "Brazil": "BR",
    "Japan": "JP"
}


# ============================================================
# YOUTUBE CATEGORY NAMES
# ============================================================

YOUTUBE_CATEGORIES = {
    "1": "Film & Animation",
    "2": "Autos & Vehicles",
    "10": "Music",
    "15": "Pets & Animals",
    "17": "Sports",
    "18": "Short Movies",
    "19": "Travel & Events",
    "20": "Gaming",
    "21": "Videoblogging",
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
# BASIC HELPERS
# ============================================================

def print_status(message):
    print(message)
    sys.stdout.flush()


def clean_text(value):
    if value is None:
        return ""

    value = str(value)

    value = re.sub(
        r"```json",
        "",
        value,
        flags=re.IGNORECASE
    )

    value = re.sub(
        r"```",
        "",
        value
    )

    return value.strip()


def extract_json(content):
    """
    Safely extract JSON from an AI response.
    Handles:
    - pure JSON
    - ```json ... ```
    - JSON surrounded by explanation
    """

    if not content:
        return None

    content = content.strip()

    # First attempt
    try:
        return json.loads(content)
    except Exception:
        pass

    # Remove markdown fences
    content = re.sub(
        r"```json\s*",
        "",
        content,
        flags=re.IGNORECASE
    )

    content = re.sub(
        r"```",
        "",
        content
    )

    content = content.strip()

    try:
        return json.loads(content)
    except Exception:
        pass

    # Find JSON object
    object_start = content.find("{")
    object_end = content.rfind("}")

    if (
        object_start != -1
        and object_end != -1
        and object_end > object_start
    ):
        try:
            return json.loads(
                content[
                    object_start:
                    object_end + 1
                ]
            )
        except Exception:
            pass

    # Find JSON array
    array_start = content.find("[")
    array_end = content.rfind("]")

    if (
        array_start != -1
        and array_end != -1
        and array_end > array_start
    ):
        try:
            return json.loads(
                content[
                    array_start:
                    array_end + 1
                ]
            )
        except Exception:
            pass

    return None


# ============================================================
# YOUTUBE API
# ============================================================

def youtube_api_request(
    endpoint,
    params
):
    """
    Generic YouTube API request.
    """

    if requests is None:
        raise RuntimeError(
            "requests package is not installed."
        )

    if not YOUTUBE_API_KEY:
        raise RuntimeError(
            "YOUTUBE_API_KEY is missing."
        )

    params = dict(params)
    params["key"] = YOUTUBE_API_KEY

    url = (
        "https://www.googleapis.com/"
        "youtube/v3/"
        + endpoint
    )

    response = requests.get(
        url,
        params=params,
        timeout=TIMEOUT
    )

    response.raise_for_status()

    return response.json()


# ============================================================
# GET YOUTUBE MOST POPULAR VIDEOS
# ============================================================

def get_region_trends(
    region_code,
    region_name,
    max_results=50
):
    """
    Collect current YouTube mostPopular videos
    for a specific region.
    """

    if not YOUTUBE_API_KEY:
        print_status(
            f"WARNING: YouTube API key missing. "
            f"Skipping {region_name}."
        )
        return []

    print_status(
        f"Collecting YouTube data: {region_name}"
    )

    try:

        data = youtube_api_request(
            "videos",
            {
                "part":
                    "snippet,statistics,contentDetails",

                "chart":
                    "mostPopular",

                "regionCode":
                    region_code,

                "maxResults":
                    min(max_results, 50)
            }
        )

    except Exception as exc:

        print_status(
            f"WARNING: {region_name} collection failed: "
            f"{exc}"
        )

        return []

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

        video_id = item.get(
            "id",
            ""
        )

        category_id = str(
            snippet.get(
                "categoryId",
                ""
            )
        )

        category_name = (
            YOUTUBE_CATEGORIES.get(
                category_id,
                "Unknown"
            )
        )

        videos.append({

            "region":
                region_name,

            "region_code":
                region_code,

            "video_id":
                video_id,

            "title":
                snippet.get(
                    "title",
                    ""
                ),

            "description":
                snippet.get(
                    "description",
                    ""
                )[:1000],

            "channel":
                snippet.get(
                    "channelTitle",
                    ""
                ),

            "published_at":
                snippet.get(
                    "publishedAt",
                    ""
                ),

            "category_id":
                category_id,

            "category":
                category_name,

            "views":
                int(
                    statistics.get(
                        "viewCount",
                        0
                    )
                ),

            "likes":
                int(
                    statistics.get(
                        "likeCount",
                        0
                    )
                ),

            "comments":
                int(
                    statistics.get(
                        "commentCount",
                        0
                    )
                ),

            "duration":
                content_details.get(
                    "duration",
                    ""
                ),

            "url":
                (
                    "https://www.youtube.com/watch?v="
                    + video_id
                )
        })

    return videos


# ============================================================
# GET SEARCH-BASED TREND DATA
# ============================================================

def get_search_trends(
    query,
    region_code,
    region_name,
    max_results=10
):
    """
    Additional YouTube search discovery.

    This helps find topics outside the
    mostPopular list.
    """

    if not YOUTUBE_API_KEY:
        return []

    try:

        data = youtube_api_request(
            "search",
            {
                "part":
                    "snippet",

                "q":
                    query,

                "type":
                    "video",

                "order":
                    "date",

                "regionCode":
                    region_code,

                "maxResults":
                    min(max_results, 50)
            }
        )

    except Exception as exc:

        print_status(
            f"Search warning "
            f"{region_name}/{query}: {exc}"
        )

        return []

    videos = []

    for item in data.get(
        "items",
        []
    ):

        snippet = item.get(
            "snippet",
            {}
        )

        video_id = (
            item.get(
                "id",
                {}
            ).get(
                "videoId"
            )
        )

        if not video_id:
            continue

        videos.append({

            "region":
                region_name,

            "region_code":
                region_code,

            "video_id":
                video_id,

            "title":
                snippet.get(
                    "title",
                    ""
                ),

            "description":
                snippet.get(
                    "description",
                    ""
                )[:700],

            "channel":
                snippet.get(
                    "channelTitle",
                    ""
                ),

            "published_at":
                snippet.get(
                    "publishedAt",
                    ""
                ),

            "category":
                "Search discovery",

            "views":
                0,

            "likes":
                0,

            "comments":
                0,

            "url":
                (
                    "https://www.youtube.com/watch?v="
                    + video_id
                )
        })

    return videos


# ============================================================
# COLLECT ALL TREND DATA
# ============================================================

def collect_all_trends():

    india = get_region_trends(
        INDIA_REGION,
        "India",
        50
    )

    world = {}

    for region_name, region_code in WORLD_REGIONS.items():

        world[region_name] = get_region_trends(
            region_code,
            region_name,
            30
        )

    # Additional topic discovery
    search_topics = [
        "viral",
        "trending",
        "entertainment",
        "comedy",
        "thriller",
        "mystery",
        "AI",
        "technology",
        "gaming",
        "movie"
    ]

    india_search = []

    for topic in search_topics:

        results = get_search_trends(
            topic,
            "IN",
            "India",
            5
        )

        india_search.extend(
            results
        )

    world_search = []

    # Use selected large markets
    for region_name, region_code in list(
        WORLD_REGIONS.items()
    )[:4]:

        for topic in search_topics[:6]:

            results = get_search_trends(
                topic,
                region_code,
                region_name,
                3
            )

            world_search.extend(
                results
            )

    return {
        "india":
            india,

        "world":
            world,

        "india_search":
            india_search,

        "world_search":
            world_search
    }


# ============================================================
# OPENROUTER
# ============================================================

def call_openrouter(
    system_prompt,
    user_prompt,
    temperature=0.8,
    max_tokens=18000
):

    if not OPENROUTER_API_KEY:
        raise RuntimeError(
            "OPENROUTER_API_KEY not found."
        )

    if requests is None:
        raise RuntimeError(
            "requests package is not installed."
        )

    url = (
        "https://openrouter.ai/api/v1/"
        "chat/completions"
    )

    headers = {

        "Authorization":
            f"Bearer {OPENROUTER_API_KEY}",

        "Content-Type":
            "application/json",

        "HTTP-Referer":
            "https://github.com/",

        "X-Title":
            "YouTube Trend Intelligence Generator"
    }

    payload = {

        "model":
            OPENROUTER_MODEL,

        "messages": [

            {
                "role":
                    "system",

                "content":
                    system_prompt
            },

            {
                "role":
                    "user",

                "content":
                    user_prompt
            }
        ],

        "temperature":
            temperature,

        "max_tokens":
            max_tokens
    }

    response = requests.post(
        url,
        headers=headers,
        json=payload,
        timeout=TIMEOUT
    )

    if response.status_code != 200:

        raise RuntimeError(
            "OpenRouter failed "
            f"{response.status_code}: "
            f"{response.text[:3000]}"
        )

    data = response.json()

    choices = data.get(
        "choices",
        []
    )

    if not choices:
        raise RuntimeError(
            "OpenRouter returned no choices."
        )

    content = (
        choices[0]
        .get("message", {})
        .get("content", "")
    )

    if isinstance(
        content,
        list
    ):
        content = "".join(
            str(x)
            for x in content
        )

    if not content:
        raise RuntimeError(
            "OpenRouter returned empty content."
        )

    return content


# ============================================================
# PREPARE DATA FOR AI
# ============================================================

def prepare_trend_data(
    collected
):
    """
    Keep the AI prompt manageable while retaining
    useful current trend information.
    """

    india = collected.get(
        "india",
        []
    )

    world = collected.get(
        "world",
        {}
    )

    india_compact = []

    for video in india[:50]:

        india_compact.append({

            "title":
                video.get(
                    "title",
                    ""
                ),

            "channel":
                video.get(
                    "channel",
                    ""
                ),

            "category":
                video.get(
                    "category",
                    ""
                ),

            "views":
                video.get(
                    "views",
                    0
                ),

            "likes":
                video.get(
                    "likes",
                    0
                ),

            "comments":
                video.get(
                    "comments",
                    0
                ),

            "published_at":
                video.get(
                    "published_at",
                    ""
                )
        })

    world_compact = {}

    for region, videos in world.items():

        world_compact[region] = []

        for video in videos[:30]:

            world_compact[region].append({

                "title":
                    video.get(
                        "title",
                        ""
                    ),

                "channel":
                    video.get(
                        "channel",
                        ""
                    ),

                "category":
                    video.get(
                        "category",
                        ""
                    ),

                "views":
                    video.get(
                        "views",
                        0
                    ),

                "likes":
                    video.get(
                        "likes",
                        0
                    ),

                "comments":
                    video.get(
                        "comments",
                        0
                    )
            })

    return {
        "india":
            india_compact,

        "world":
            world_compact,

        "india_search":
            collected.get(
                "india_search",
                []
            )[:50],

        "world_search":
            collected.get(
                "world_search",
                []
            )[:80]
    }


# ============================================================
# TREND ANALYSIS
# ============================================================

def analyze_trends(
    trend_data
):

    print_status(
        "\nAnalyzing current YouTube patterns..."
    )

    system_prompt = """
You are a professional YouTube trend intelligence
analyst.

You receive current YouTube API data.

Your job is to identify evidence-based patterns.

Do NOT invent trends.

Do NOT claim that something is "the biggest trend"
unless the supplied data supports that conclusion.

Separate India from the broader world.

For WORLD:
The supplied countries are only a sample of global
markets. Describe them as world/international signals,
not as a perfect representation of every country.

Analyze:

1. YouTube trends in India
2. YouTube trends in the world
3. Trending genres in India
4. Trending genres in world markets
5. Trending topics
6. Repeated content formats
7. Repeated hooks
8. Curiosity patterns
9. Viewer-interest signals
10. Opportunities for a Telugu creator

Important:
A genre being present in the data does not automatically
mean it is universally trending.

Return ONLY valid JSON.
"""

    user_prompt = f"""
CURRENT DATE:
{TODAY}

YOUTUBE DATA:

{json.dumps(
    trend_data,
    ensure_ascii=False,
    indent=2
)}

Return EXACTLY this structure:

{{
    "india_trends": [
        {{
            "trend": "",
            "evidence": "",
            "genre": "",
            "why_it_is_getting_attention": "",
            "content_pattern": ""
        }}
    ],

    "world_trends": [
        {{
            "trend": "",
            "evidence": "",
            "countries_seen": [],
            "genre": "",
            "why_it_is_getting_attention": "",
            "content_pattern": ""
        }}
    ],

    "india_genres": [
        {{
            "genre": "",
            "evidence": "",
            "content_pattern": ""
        }}
    ],

    "world_genres": [
        {{
            "genre": "",
            "evidence": "",
            "content_pattern": ""
        }}
    ],

    "common_hooks": [],

    "common_topics": [],

    "creator_opportunities": []
}}

Give multiple useful entries.
Do not produce vague one-line answers.
"""

    try:

        response = call_openrouter(
            system_prompt,
            user_prompt,
            temperature=0.4,
            max_tokens=9000
        )

        result = extract_json(
            response
        )

        if result is None:

            print_status(
                "WARNING: Trend analysis JSON "
                "could not be parsed."
            )

            return {
                "raw_response":
                    response
            }

        return result

    except Exception as exc:

        print_status(
            f"WARNING: Trend analysis failed: {exc}"
        )

        return {
            "india_trends": [],
            "world_trends": [],
            "india_genres": [],
            "world_genres": [],
            "common_hooks": [],
            "common_topics": [],
            "creator_opportunities": []
        }


# ============================================================
# IDEA GENERATION
# ============================================================

def generate_ideas(
    trend_analysis
):

    print_status(
        "\nGenerating high-engagement ideas..."
    )

    system_prompt = """
You are an elite YouTube creative strategist
for a Telugu/Indian creator.

Generate ORIGINAL, HIGH-ENGAGEMENT ideas.

The creator wants:
- Roman Telugu
- Mystery
- Thriller
- Suspense
- Comedy twists
- Relatable situations
- Strong curiosity
- Unexpected reveals
- Realistic concepts
- Solo creator friendly production
- Strong titles
- Strong hooks
- Strong thumbnails

DO NOT generate:
- silly ideas
- childish ideas
- boring daily-vlog ideas
- generic challenges
- generic motivation
- random prank ideas
- weak "what if" concepts
- copied viral videos
- concepts requiring many actors
- concepts requiring expensive production

============================================================
ROMAN TELUGU
============================================================

ALL titles must be Roman Telugu.

Use natural Telugu written in English letters.

Example:

"Nenu Aa Message Ignore Chesanu... Kani
5 Minutes Tarvata Ade Message Malli Vachindi"

NOT:

"నేను ఆ మెసేజ్..."

Do not use Telugu script.

============================================================
TREND-BASED IDEAS
============================================================

Use the supplied trend analysis as inspiration.

Do NOT copy the actual trending video's title,
story or characters.

Instead:
Trend -> extract audience interest -> create
a completely original concept.

============================================================
SHORTS
============================================================

Shorts should have:

0-2 sec:
Very strong hook

2-10 sec:
Situation

10-30 sec:
Escalation

30-50 sec:
Reveal / twist

50-60 sec:
Memorable ending

============================================================
LONG FORM
============================================================

8-10 minute videos should have:

0:00 - Strong opening
0:30 - Setup
1:30 - First clue/problem
3:00 - Escalation
5:00 - Bigger mystery
6:30 - False explanation
8:00 - Reveal
9:00 - Final twist/payoff

============================================================
CTR POTENTIAL
============================================================

You must calculate an EDITORIAL CTR POTENTIAL score.

This is NOT actual YouTube CTR.

Score from 0-100 using:

1. Curiosity gap
2. Information gap
3. Emotional tension
4. Novelty
5. Title strength
6. Thumbnail potential
7. Specificity
8. Stakes
9. Immediate understanding
10. Payoff promise

Do NOT give every idea 90+.

============================================================
VERY IMPORTANT
============================================================

The ideas must be genuinely different.

Do not generate ten versions of:
"Someone is watching me."

Use different situations such as:
- strange messages
- unexpected object
- missing item
- wrong delivery
- locked room
- unusual sound
- technology
- social situation
- money
- coincidence
- time pressure
- misunderstanding
- suspicious discovery
- everyday problem becoming serious
- psychological mystery

But do not force these examples.

Return ONLY valid JSON.
"""

    user_prompt = f"""
CURRENT DATE:
{TODAY}

TREND ANALYSIS:

{json.dumps(
    trend_analysis,
    ensure_ascii=False,
    indent=2
)}

Generate EXACTLY these sections:

1.
shorts_based_on_india_trends

2.
shorts_based_on_world_trends

3.
shorts_general

4.
long_based_on_india_trends

5.
long_based_on_world_trends

6.
long_general

7.
top_ctr_ranked

Generate:

10 India trend Shorts

10 World trend Shorts

10 General Shorts

10 India trend 8-10 minute ideas

10 World trend 8-10 minute ideas

10 General 8-10 minute ideas

Then rank the strongest 20 ideas by CTR potential.

Every idea MUST contain:

{{
    "title": "",
    "english_meaning": "",
    "hook": "",
    "story_log": "",
    "twist": "",
    "comedy": "",
    "thumbnail_text": "",
    "genre": "",
    "format": "",
    "trend_connection": "",
    "ctr_score": 0,
    "why_clickable": "",
    "shooting_difficulty": ""
}}

For "format", use exactly:

"Short"

or

"8-10 minute"

Return:

{{
    "shorts_based_on_india_trends": [],
    "shorts_based_on_world_trends": [],
    "shorts_general": [],
    "long_based_on_india_trends": [],
    "long_based_on_world_trends": [],
    "long_general": [],
    "top_ctr_ranked": []
}}
"""

    try:

        response = call_openrouter(
            system_prompt,
            user_prompt,
            temperature=0.9,
            max_tokens=24000
        )

        result = extract_json(
            response
        )

        if result is None:

            print_status(
                "WARNING: Idea JSON could not be parsed."
            )

            return {
                "raw_response":
                    response
            }

        return result

    except Exception as exc:

        print_status(
            f"WARNING: Idea generation failed: {exc}"
        )

        return generate_fallback_ideas()


# ============================================================
# LOCAL CTR RANKING
# ============================================================

def rank_all_ideas(
    data
):
    """
    Do not blindly trust the AI's top list.

    Collect all generated ideas and locally sort them
    using the AI's editorial CTR score.
    """

    sections = [

        "shorts_based_on_india_trends",

        "shorts_based_on_world_trends",

        "shorts_general",

        "long_based_on_india_trends",

        "long_based_on_world_trends",

        "long_general"
    ]

    all_ideas = []

    for section in sections:

        ideas = data.get(
            section,
            []
        )

        if not isinstance(
            ideas,
            list
        ):
            continue

        for idea in ideas:

            if not isinstance(
                idea,
                dict
            ):
                continue

            try:

                score = int(
                    idea.get(
                        "ctr_score",
                        0
                    )
                )

            except Exception:

                score = 0

            score = max(
                0,
                min(
                    100,
                    score
                )
            )

            idea["ctr_score"] = score

            idea["_source_section"] = section

            all_ideas.append(
                idea
            )

    all_ideas.sort(
        key=lambda item:
            item.get(
                "ctr_score",
                0
            ),
        reverse=True
    )

    # Remove internal ranking metadata
    top_ideas = []

    for idea in all_ideas[:20]:

        clean_idea = dict(
            idea
        )

        clean_idea.pop(
            "_source_section",
            None
        )

        top_ideas.append(
            clean_idea
        )

    data[
        "top_ctr_ranked"
    ] = top_ideas

    return data


# ============================================================
# FALLBACK
# ============================================================

def generate_fallback_ideas():

    return {

        "shorts_based_on_india_trends": [],

        "shorts_based_on_world_trends": [],

        "shorts_general": [

            {
                "title":
                    "Nenu Oka Small Mistake Chesanu... Kani",

                "english_meaning":
                    "I made a small mistake... but",

                "hook":
                    "Aa mistake taruvata situation completely change ayindi.",

                "story_log":
                    "Simple mistake gradually becomes a mystery.",

                "twist":
                    "The thing I feared had a completely different explanation.",

                "comedy":
                    "Hero situation ni unnecessarily serious ga tiskuntadu.",

                "thumbnail_text":
                    "IDI ELA JARIGINDI?",

                "genre":
                    "Mystery Comedy",

                "format":
                    "Short",

                "trend_connection":
                    "Fallback",

                "ctr_score":
                    65,

                "why_clickable":
                    "Open loop and curiosity.",

                "shooting_difficulty":
                    "Easy"
            }
        ],

        "long_based_on_india_trends": [],

        "long_based_on_world_trends": [],

        "long_general": [],

        "top_ctr_ranked": []
    }


# ============================================================
# SAVE JSON
# ============================================================

def save_json(
    filename,
    data
):

    path = OUTPUT_DIR / filename

    with open(
        path,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            data,
            file,
            indent=2,
            ensure_ascii=False
        )

    return path


# ============================================================
# REPORT HELPERS
# ============================================================

def write_idea(
    file,
    index,
    idea
):

    file.write(
        f"\nIDEA {index}\n"
    )

    file.write(
        "-" * 70 + "\n"
    )

    file.write(
        f"Title: "
        f"{clean_text(idea.get('title'))}\n"
    )

    file.write(
        f"English Meaning: "
        f"{clean_text(idea.get('english_meaning'))}\n"
    )

    file.write(
        f"Hook: "
        f"{clean_text(idea.get('hook'))}\n"
    )

    file.write(
        f"Story: "
        f"{clean_text(idea.get('story_log'))}\n"
    )

    file.write(
        f"Twist: "
        f"{clean_text(idea.get('twist'))}\n"
    )

    file.write(
        f"Comedy: "
        f"{clean_text(idea.get('comedy'))}\n"
    )

    file.write(
        f"Thumbnail: "
        f"{clean_text(idea.get('thumbnail_text'))}\n"
    )

    file.write(
        f"Genre: "
        f"{clean_text(idea.get('genre'))}\n"
    )

    file.write(
        f"Format: "
        f"{clean_text(idea.get('format'))}\n"
    )

    file.write(
        f"Trend Connection: "
        f"{clean_text(idea.get('trend_connection'))}\n"
    )

    file.write(
        f"CTR Potential: "
        f"{idea.get('ctr_score', 0)}/100\n"
    )

    file.write(
        f"Why Clickable: "
        f"{clean_text(idea.get('why_clickable'))}\n"
    )

    file.write(
        f"Shooting Difficulty: "
        f"{clean_text(idea.get('shooting_difficulty'))}\n"
    )

    file.write("\n")


# ============================================================
# CREATE TXT REPORT
# ============================================================

def create_text_report(
    trend_analysis,
    ideas
):

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    txt_file = (
        OUTPUT_DIR /
        f"youtube_trend_report_{timestamp}.txt"
    )

    with open(
        txt_file,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(
            "YOUTUBE TREND INTELLIGENCE REPORT\n"
        )

        file.write(
            "=" * 70 + "\n"
        )

        file.write(
            f"Generated: {TODAY}\n\n"
        )

        # ----------------------------------------------------
        # 1 INDIA
        # ----------------------------------------------------

        file.write(
            "1. YOUTUBE TRENDS IN INDIA\n"
        )

        file.write(
            "=" * 70 + "\n"
        )

        for index, trend in enumerate(
            trend_analysis.get(
                "india_trends",
                []
            ),
            1
        ):

            file.write(
                f"\n{index}. "
                f"{clean_text(trend.get('trend'))}\n"
            )

            file.write(
                "Evidence: "
                + clean_text(
                    trend.get(
                        "evidence"
                    )
                )
                + "\n"
            )

            file.write(
                "Genre: "
                + clean_text(
                    trend.get(
                        "genre"
                    )
                )
                + "\n"
            )

            file.write(
                "Why attention: "
                + clean_text(
                    trend.get(
                        "why_it_is_getting_attention"
                    )
                )
                + "\n"
            )

            file.write(
                "Content pattern: "
                + clean_text(
                    trend.get(
                        "content_pattern"
                    )
                )
                + "\n"
            )

        file.write("\n")

        # ----------------------------------------------------
        # 2 WORLD
        # ----------------------------------------------------

        file.write(
            "2. YOUTUBE TRENDS IN THE WORLD\n"
        )

        file.write(
            "=" * 70 + "\n"
        )

        for index, trend in enumerate(
            trend_analysis.get(
                "world_trends",
                []
            ),
            1
        ):

            file.write(
                f"\n{index}. "
                f"{clean_text(trend.get('trend'))}\n"
            )

            file.write(
                "Evidence: "
                + clean_text(
                    trend.get(
                        "evidence"
                    )
                )
                + "\n"
            )

            countries = trend.get(
                "countries_seen",
                []
            )

            file.write(
                "Countries: "
                + ", ".join(
                    str(x)
                    for x in countries
                )
                + "\n"
            )

            file.write(
                "Genre: "
                + clean_text(
                    trend.get(
                        "genre"
                    )
                )
                + "\n"
            )

            file.write(
                "Why attention: "
                + clean_text(
                    trend.get(
                        "why_it_is_getting_attention"
                    )
                )
                + "\n"
            )

        file.write("\n")

        # ----------------------------------------------------
        # 3 GENRES
        # ----------------------------------------------------

        file.write(
            "3. WHICH YOUTUBE GENRES ARE TRENDING\n"
        )

        file.write(
            "=" * 70 + "\n"
        )

        file.write(
            "\nINDIA\n"
        )

        for item in trend_analysis.get(
            "india_genres",
            []
        ):

            if isinstance(
                item,
                dict
            ):

                file.write(
                    "\nGenre: "
                    + clean_text(
                        item.get(
                            "genre"
                        )
                    )
                    + "\n"
                )

                file.write(
                    "Evidence: "
                    + clean_text(
                        item.get(
                            "evidence"
                        )
                    )
                    + "\n"
                )

                file.write(
                    "Pattern: "
                    + clean_text(
                        item.get(
                            "content_pattern"
                        )
                    )
                    + "\n"
                )

            else:

                file.write(
                    "- "
                    + clean_text(item)
                    + "\n"
                )

        file.write(
            "\nWORLD\n"
        )

        for item in trend_analysis.get(
            "world_genres",
            []
        ):

            if isinstance(
                item,
                dict
            ):

                file.write(
                    "\nGenre: "
                    + clean_text(
                        item.get(
                            "genre"
                        )
                    )
                    + "\n"
                )

                file.write(
                    "Evidence: "
                    + clean_text(
                        item.get(
                            "evidence"
                        )
                    )
                    + "\n"
                )

                file.write(
                    "Pattern: "
                    + clean_text(
                        item.get(
                            "content_pattern"
                        )
                    )
                    + "\n"
                )

            else:

                file.write(
                    "- "
                    + clean_text(item)
                    + "\n"
                )

        # ----------------------------------------------------
        # 4-7 IDEA SECTIONS
        # ----------------------------------------------------

        sections = [

            (
                "4. YOUTUBE SHORTS IDEAS "
                "BASED ON INDIA TRENDS",
                "shorts_based_on_india_trends"
            ),

            (
                "5. YOUTUBE SHORTS IDEAS "
                "BASED ON WORLD TRENDS",
                "shorts_based_on_world_trends"
            ),

            (
                "6. YOUTUBE SHORTS IDEAS "
                "GENERAL",
                "shorts_general"
            ),

            (
                "7. YOUTUBE LONG FORM "
                "8-10 MINUTES BASED ON INDIA TRENDS",
                "long_based_on_india_trends"
            ),

            (
                "8. YOUTUBE LONG FORM "
                "8-10 MINUTES BASED ON WORLD TRENDS",
                "long_based_on_world_trends"
            ),

            (
                "9. YOUTUBE LONG FORM "
                "8-10 MINUTES GENERAL",
                "long_general"
            )
        ]

        for heading, key in sections:

            file.write(
                "\n\n"
                + heading
                + "\n"
            )

            file.write(
                "=" * 70
                + "\n"
            )

            section_ideas = ideas.get(
                key,
                []
            )

            for index, idea in enumerate(
                section_ideas,
                1
            ):

                write_idea(
                    file,
                    index,
                    idea
                )

        # ----------------------------------------------------
        # 8 TOP CTR
        # ----------------------------------------------------

        file.write(
            "\n\n"
            + "=" * 70
            + "\n"
        )

        file.write(
            "10. TOP IDEAS BY CTR POTENTIAL\n"
        )

        file.write(
            "=" * 70
            + "\n"
        )

        file.write(
            "\nIMPORTANT:\n"
        )

        file.write(
            "CTR Potential is an editorial AI score, "
            "not actual YouTube Analytics CTR.\n"
        )

        file.write(
            "Actual CTR can only be measured after "
            "publishing a video.\n\n"
        )

        top_ideas = ideas.get(
            "top_ctr_ranked",
            []
        )

        for index, idea in enumerate(
            top_ideas,
            1
        ):

            file.write(
                f"\nRANK {index}\n"
            )

            file.write(
                "=" * 70
                + "\n"
            )

            file.write(
                f"CTR POTENTIAL: "
                f"{idea.get('ctr_score', 0)}/100\n"
            )

            file.write(
                f"TITLE: "
                f"{clean_text(idea.get('title'))}\n"
            )

            file.write(
                f"FORMAT: "
                f"{clean_text(idea.get('format'))}\n"
            )

            file.write(
                f"HOOK: "
                f"{clean_text(idea.get('hook'))}\n"
            )

            file.write(
                f"THUMBNAIL: "
                f"{clean_text(idea.get('thumbnail_text'))}\n"
            )

            file.write(
                f"WHY CLICKABLE: "
                f"{clean_text(idea.get('why_clickable'))}\n"
            )

            file.write(
                f"STORY: "
                f"{clean_text(idea.get('story_log'))}\n"
            )

            file.write(
                f"TWIST: "
                f"{clean_text(idea.get('twist'))}\n"
            )

            file.write(
                "\n"
            )

    return txt_file


# ============================================================
# SAVE RAW DATA
# ============================================================

def save_raw_data(
    collected
):

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    path = (
        OUTPUT_DIR /
        f"youtube_raw_data_{timestamp}.json"
    )

    with open(
        path,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            collected,
            file,
            indent=2,
            ensure_ascii=False
        )

    return path


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "=" * 70
    )

    print(
        "YOUTUBE TREND INTELLIGENCE "
        "+ IDEA GENERATOR"
    )

    print(
        "=" * 70
    )

    print(
        f"Project root : {BASE_DIR}"
    )

    print(
        f"Output folder: {OUTPUT_DIR}"
    )

    print(
        f"Generated    : {TODAY}"
    )

    print()

    # ========================================================
    # CHECK DEPENDENCIES
    # ========================================================

    if requests is None:

        print(
            "ERROR: requests is not installed."
        )

        print(
            "Run: pip install requests"
        )

        sys.exit(1)

    if load_dotenv is None:

        print(
            "WARNING: python-dotenv is not installed."
        )

        print(
            "Run: pip install python-dotenv"
        )

    if not OPENROUTER_API_KEY:

        print(
            "ERROR: OPENROUTER_API_KEY is missing."
        )

        print(
            "Add it to your .env file."
        )

        sys.exit(1)

    # ========================================================
    # 1. COLLECT
    # ========================================================

    print(
        "\n[1/6] COLLECTING YOUTUBE TREND DATA"
    )

    print(
        "-" * 70
    )

    collected = collect_all_trends()

    raw_file = save_raw_data(
        collected
    )

    print(
        f"\nRaw trend data saved:"
        f"\n{raw_file}"
    )

    # ========================================================
    # 2. PREPARE
    # ========================================================

    print(
        "\n[2/6] PREPARING TREND DATA"
    )

    trend_data = prepare_trend_data(
        collected
    )

    # ========================================================
    # 3. ANALYZE
    # ========================================================

    print(
        "\n[3/6] ANALYZING INDIA + WORLD TRENDS"
    )

    trend_analysis = analyze_trends(
        trend_data
    )

    # ========================================================
    # 4. GENERATE
    # ========================================================

    print(
        "\n[4/6] GENERATING ORIGINAL IDEAS"
    )

    ideas = generate_ideas(
        trend_analysis
    )

    # ========================================================
    # 5. RANK
    # ========================================================

    print(
        "\n[5/6] RANKING IDEAS BY CTR POTENTIAL"
    )

    ideas = rank_all_ideas(
        ideas
    )

    # ========================================================
    # 6. SAVE
    # ========================================================

    print(
        "\n[6/6] SAVING FINAL REPORT"
    )

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    json_file = (
        OUTPUT_DIR /
        f"youtube_idea_generator_{timestamp}.json"
    )

    with open(
        json_file,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            {
                "generated_at":
                    TODAY,

                "trend_analysis":
                    trend_analysis,

                "ideas":
                    ideas
            },
            file,
            indent=2,
            ensure_ascii=False
        )

    txt_file = create_text_report(
        trend_analysis,
        ideas
    )

    # ========================================================
    # SHOW TOP IDEAS
    # ========================================================

    print(
        "\n"
        + "=" * 70
    )

    print(
        "TOP IDEAS BY CTR POTENTIAL"
    )

    print(
        "=" * 70
    )

    top_ideas = ideas.get(
        "top_ctr_ranked",
        []
    )

    for index, idea in enumerate(
        top_ideas[:10],
        1
    ):

        print(
            f"\n{index}. "
            f"{idea.get('title', '')}"
        )

        print(
            f"   CTR Potential: "
            f"{idea.get('ctr_score', 0)}/100"
        )

        print(
            f"   Format: "
            f"{idea.get('format', '')}"
        )

    # ========================================================
    # COMPLETE
    # ========================================================

    print(
        "\n"
        + "=" * 70
    )

    print(
        "GENERATION COMPLETED SUCCESSFULLY"
    )

    print(
        "=" * 70
    )

    print(
        f"\nJSON:"
        f"\n{json_file}"
    )

    print(
        f"\nTXT:"
        f"\n{txt_file}"
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    main()
