import os
import re
import json
import time
from datetime import datetime, timezone
from collections import Counter

import requests
from dotenv import load_dotenv


# ============================================================
# LOAD ENVIRONMENT
# ============================================================

load_dotenv()

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "").strip()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "").strip()

RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL", "").strip()

SENDER_EMAIL = os.getenv(
    "SENDER_EMAIL",
    "onboarding@resend.dev"
).strip()

OPENROUTER_MODEL = os.getenv(
    "OPENROUTER_MODEL",
    "google/gemini-2.5-flash"
).strip()


# ============================================================
# API URLS
# ============================================================

YOUTUBE_API_URL = "https://www.googleapis.com/youtube/v3"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
RESEND_URL = "https://api.resend.com/emails"


# ============================================================
# WORLD REGIONS
# ============================================================

WORLD_REGIONS = [
    "US",
    "GB",
    "CA",
    "AU",
    "JP",
    "KR",
    "BR",
    "DE",
    "FR",
    "MX"
]


# ============================================================
# YOUTUBE CATEGORY NAMES
# ============================================================

CATEGORY_NAMES = {
    "1": "Film and Animation",
    "2": "Autos and Vehicles",
    "10": "Music",
    "15": "Pets and Animals",
    "17": "Sports",
    "19": "Travel and Events",
    "20": "Gaming",
    "22": "People and Blogs",
    "23": "Comedy",
    "24": "Entertainment",
    "25": "News and Politics",
    "26": "Howto and Style",
    "27": "Education",
    "28": "Science and Technology",
    "29": "Nonprofits and Activism",
}


# ============================================================
# VALIDATE ENVIRONMENT
# ============================================================

def check_environment():

    required = {
        "YOUTUBE_API_KEY": YOUTUBE_API_KEY,
        "OPENROUTER_API_KEY": OPENROUTER_API_KEY,
        "RESEND_API_KEY": RESEND_API_KEY,
        "RECIPIENT_EMAIL": RECIPIENT_EMAIL,
    }

    missing = [
        key
        for key, value in required.items()
        if not value
    ]

    if missing:

        raise RuntimeError(
            "Missing environment variables:\n"
            + "\n".join(missing)
        )

    print("Environment check: OK")


# ============================================================
# YOUTUBE API
# ============================================================

def youtube_request(endpoint, params):

    params = dict(params)

    params["key"] = YOUTUBE_API_KEY

    response = requests.get(
        f"{YOUTUBE_API_URL}/{endpoint}",
        params=params,
        timeout=40
    )

    if response.status_code != 200:

        try:
            error = response.json()
        except Exception:
            error = response.text

        raise RuntimeError(
            f"YouTube API error {response.status_code}: {error}"
        )

    return response.json()


# ============================================================
# GET TRENDING VIDEOS
# ============================================================

def get_trending_videos(
    region_code,
    max_results=50
):

    data = youtube_request(
        "videos",
        {
            "part": "snippet,statistics,contentDetails",
            "chart": "mostPopular",
            "regionCode": region_code,
            "maxResults": max_results,
        }
    )

    videos = []

    for item in data.get("items", []):

        snippet = item.get(
            "snippet",
            {}
        )

        statistics = item.get(
            "statistics",
            {}
        )

        content = item.get(
            "contentDetails",
            {}
        )

        videos.append({

            "id": item.get(
                "id",
                ""
            ),

            "title": snippet.get(
                "title",
                ""
            ),

            "description": snippet.get(
                "description",
                ""
            )[:500],

            "channel": snippet.get(
                "channelTitle",
                ""
            ),

            "published_at": snippet.get(
                "publishedAt",
                ""
            ),

            "category_id": snippet.get(
                "categoryId",
                ""
            ),

            "category": CATEGORY_NAMES.get(
                snippet.get(
                    "categoryId",
                    ""
                ),
                "Other"
            ),

            "views": int(
                statistics.get(
                    "viewCount",
                    0
                ) or 0
            ),

            "likes": int(
                statistics.get(
                    "likeCount",
                    0
                ) or 0
            ),

            "comments": int(
                statistics.get(
                    "commentCount",
                    0
                ) or 0
            ),

            "duration": content.get(
                "duration",
                ""
            ),

            "region": region_code
        })

    return videos


# ============================================================
# INDIA DATA
# ============================================================

def collect_india_trends():

    print()
    print("Collecting India YouTube trends...")

    videos = get_trending_videos(
        "IN",
        50
    )

    print(
        f"India videos collected: {len(videos)}"
    )

    return videos


# ============================================================
# WORLD DATA
# ============================================================

def collect_world_trends():

    print()
    print("Collecting World YouTube trends...")

    all_videos = []

    for region in WORLD_REGIONS:

        try:

            videos = get_trending_videos(
                region,
                30
            )

            all_videos.extend(videos)

            print(
                f"{region}: {len(videos)} videos"
            )

            time.sleep(0.2)

        except Exception as error:

            print(
                f"{region} skipped: {error}"
            )

    unique_videos = {}

    for video in all_videos:

        video_id = video.get(
            "id"
        )

        if video_id:

            unique_videos[
                video_id
            ] = video

    videos = list(
        unique_videos.values()
    )

    print(
        f"Unique world videos: {len(videos)}"
    )

    return videos


# ============================================================
# TREND ANALYSIS
# ============================================================

def analyze_trends(
    videos,
    region_name
):

    category_counter = Counter()

    keyword_counter = Counter()

    for video in videos:

        category = video.get(
            "category",
            "Other"
        )

        category_counter[
            category
        ] += 1

        title = video.get(
            "title",
            ""
        )

        title = re.sub(
            r"[^A-Za-z0-9\s]",
            " ",
            title.lower()
        )

        stopwords = {
            "the",
            "and",
            "for",
            "with",
            "this",
            "that",
            "you",
            "your",
            "from",
            "are",
            "was",
            "will",
            "what",
            "when",
            "where",
            "how",
            "why",
            "new",
            "video",
            "official",
            "part",
            "episode",
            "india",
            "a",
            "an",
            "to",
            "of",
            "in",
            "on",
            "is",
            "it",
            "my",
            "we",
            "i"
        }

        for word in title.split():

            if (
                len(word) >= 4
                and word not in stopwords
            ):

                keyword_counter[
                    word
                ] += 1

    top_videos = sorted(
        videos,
        key=lambda x: (
            x.get(
                "views",
                0
            ),
            x.get(
                "likes",
                0
            )
        ),
        reverse=True
    )[:30]

    return {

        "region": region_name,

        "video_count": len(videos),

        "top_videos": [

            {
                "title": video.get(
                    "title",
                    ""
                ),

                "channel": video.get(
                    "channel",
                    ""
                ),

                "category": video.get(
                    "category",
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

                "region": video.get(
                    "region",
                    ""
                )
            }

            for video in top_videos
        ],

        "top_genres":
            category_counter.most_common(
                10
            ),

        "title_keywords":
            keyword_counter.most_common(
                40
            )
    }


# ============================================================
# OPENROUTER AI
# ============================================================

def call_openrouter(
    system_prompt,
    user_prompt
):

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

        "temperature":
            0.9,

        "max_tokens":
            16000,

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
        ]
    }

    response = requests.post(

        OPENROUTER_URL,

        headers=headers,

        json=payload,

        timeout=180
    )

    if response.status_code != 200:

        try:
            error = response.json()

        except Exception:
            error = response.text

        raise RuntimeError(
            f"OpenRouter error "
            f"{response.status_code}: "
            f"{error}"
        )

    data = response.json()

    content = (
        data
        .get("choices", [{}])[0]
        .get("message", {})
        .get("content", "")
        .strip()
    )

    if not content:

        raise RuntimeError(
            "OpenRouter returned empty response."
        )

    # Remove accidental markdown JSON fences.
    content = re.sub(
        r"^```json\s*",
        "",
        content,
        flags=re.IGNORECASE
    )

    content = re.sub(
        r"^```\s*",
        "",
        content
    )

    content = re.sub(
        r"\s*```$",
        "",
        content
    )

    try:

        return json.loads(
            content
        )

    except json.JSONDecodeError:

        match = re.search(
            r"\{.*\}",
            content,
            flags=re.DOTALL
        )

        if match:

            return json.loads(
                match.group(0)
            )

        raise RuntimeError(
            "AI returned invalid JSON.\n\n"
            + content[:5000]
        )


# ============================================================
# GENERATE IDEAS
# ============================================================

def generate_ideas(
    india_data,
    world_data
):

    system_prompt = """

You are an elite YouTube creative director,
viral-content strategist and story-concept developer.

Your standard is extremely high.

The user does NOT want ordinary YouTube ideas.

The desired reaction is:

"WAAH... WHAT AN IDEA!"

The concept must immediately create curiosity.

Do NOT produce silly ideas.

Do NOT produce generic creator advice.

Do NOT produce concepts such as:

"I tried this for 24 hours."

"I asked strangers..."

"Funny reactions."

"Random prank."

"Morning routine."

"Day in my life."

"Challenge video."

"Reacting to..."

"Top 10..."

"Things you didn't know..."

"Random experiment."

"Generic mystery."

"Generic haunted house."

"Generic social experiment."

"Generic AI challenge."

Do not copy famous creators.

Do not simply change the location of an existing viral idea.

Every concept needs a UNIQUE CENTRAL PREMISE.

The viewer should understand why they need to click.

The concept should have a powerful curiosity gap.

The idea must contain:

1. Strong opening hook
2. Curiosity
3. Escalation
4. Conflict or mystery
5. A meaningful payoff
6. A memorable final moment

For Shorts:

The first 1 to 3 seconds must be extremely strong.

The concept must work within a short runtime.

For 8 to 10 minute videos:

Create a genuine story engine.

There must be enough material for:

Opening
Setup
Discovery
Escalation
Complication
Turning point
Reveal
Payoff

Do not stretch a 30-second idea into 10 minutes.

ROMAN TELUGU:

Write natural conversational Roman Telugu.

Do not translate word-for-word.

The logline should sound like something a Telugu filmmaker or YouTube creator
would actually say.

HIGH CTR:

The title should create curiosity without lying.

Do not use fake clickbait.

IMPORTANT:

Sections 4 and 5 must be inspired by the supplied current YouTube trend data.

Sections 6 and 7 must be ORIGINAL and must NOT depend on current trend titles.

They may use universal human psychology, mystery, technology, Indian life,
relationships, fear, ambition, secrets, social behavior, unexpected systems,
science, money, history, or other strong concepts.

The final winner must be selected from ALL generated ideas.

It must be the strongest concept in the entire report.

Return ONLY valid JSON.

No markdown.

No explanations outside JSON.
"""

    current_date = datetime.now(
        timezone.utc
    ).strftime("%Y-%m-%d")

    user_prompt = f"""

TODAY:

{current_date}


INDIA YOUTUBE TREND DATA:

{json.dumps(
    india_data,
    ensure_ascii=False
)}


WORLD YOUTUBE TREND DATA:

{json.dumps(
    world_data,
    ensure_ascii=False
)}


CREATE THIS REPORT:


HIGH CTR WINNER

Select the single strongest idea from the entire report.

Return:

title

format

region

ctr_score

roman_telugu_logline

why_this_is_the_winner


SECTION 1

India YouTube trends.

Separate:

Longform 8-10 minutes

Shorts


SECTION 2

World YouTube trends.

Separate:

Longform 8-10 minutes

Shorts


SECTION 3

YouTube genre trends.

Separate:

Longform

Shorts


SECTION 4

Trend-based Shorts ideas.

Generate 10.

Mix India and World.

Each idea must include:

title

region

format

target_audience

why_people_click

core_hook

roman_telugu_logline

story_payoff

ctr_score

originality_score


SECTION 5

Trend-based 8-10 minute longform ideas.

Generate 10.

Mix India and World.

Each idea must include:

title

region

format

target_audience

why_people_click

core_hook

roman_telugu_logline

story_payoff

ctr_score

originality_score


SECTION 6

Original general Shorts ideas.

These MUST NOT be based on current YouTube trends.

Generate 10.

Mix India and World.

Each idea must include:

title

region

format

target_audience

why_people_click

core_hook

roman_telugu_logline

story_payoff

ctr_score

originality_score


SECTION 7

Original general 8-10 minute longform ideas.

These MUST NOT be based on current YouTube trends.

Generate 10.

Mix India and World.

Each idea must include:

title

region

format

target_audience

why_people_click

core_hook

roman_telugu_logline

story_payoff

ctr_score

originality_score


JSON STRUCTURE:

{{
    "high_ctr_winner": {{
        "title": "",
        "format": "",
        "region": "",
        "ctr_score": 0,
        "roman_telugu_logline": "",
        "why_this_is_the_winner": ""
    }},

    "india_youtube_trends": {{
        "longform_8_10_min": {{
            "trend_summary": "",
            "top_patterns": [],
            "genres": []
        }},
        "shorts": {{
            "trend_summary": "",
            "top_patterns": [],
            "genres": []
        }}
    }},

    "world_youtube_trends": {{
        "longform_8_10_min": {{
            "trend_summary": "",
            "top_patterns": [],
            "genres": []
        }},
        "shorts": {{
            "trend_summary": "",
            "top_patterns": [],
            "genres": []
        }}
    }},

    "youtube_genre_trends": {{
        "longform_8_10_min": [],
        "shorts": []
    }},

    "trend_based_shorts_ideas": [],

    "trend_based_longform_ideas": [],

    "general_shorts_ideas": [],

    "general_longform_ideas": []
}}

"""


    return call_openrouter(
        system_prompt,
        user_prompt
    )


# ============================================================
# REMOVE SYMBOLS
# ============================================================

def clean_text(value):

    if value is None:
        return ""

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

    value = str(value)

    value = value.replace(
        "#",
        ""
    )

    value = value.replace(
        "$",
        ""
    )

    value = value.replace(
        "@",
        ""
    )

    return value.strip()


# ============================================================
# FORMAT IDEA
# ============================================================

def format_idea(
    number,
    idea
):

    return f"""

{number}. {clean_text(idea.get("title"))}

Region: {clean_text(idea.get("region"))}

Format: {clean_text(idea.get("format"))}

Target Audience: {clean_text(idea.get("target_audience"))}

CTR Score: {clean_text(idea.get("ctr_score"))}/100

Originality Score: {clean_text(idea.get("originality_score"))}/100

Why People Click:
{clean_text(idea.get("why_people_click"))}

Core Hook:
{clean_text(idea.get("core_hook"))}

Roman Telugu Logline:
{clean_text(idea.get("roman_telugu_logline"))}

Story and Payoff:
{clean_text(idea.get("story_payoff"))}

"""


# ============================================================
# BUILD REPORT
# ============================================================

def build_report(
    report,
    india_data,
    world_data
):

    lines = []

    winner = report.get(
        "high_ctr_winner",
        {}
    )

    lines.append(
        "HIGH CTR WINNER"
    )

    lines.append(
        "=" * 70
    )

    lines.append(
        f"TITLE: "
        f"{clean_text(winner.get('title'))}"
    )

    lines.append(
        f"FORMAT: "
        f"{clean_text(winner.get('format'))}"
    )

    lines.append(
        f"REGION: "
        f"{clean_text(winner.get('region'))}"
    )

    lines.append(
        f"CTR SCORE: "
        f"{clean_text(winner.get('ctr_score'))}/100"
    )

    lines.append(
        "ROMAN TELUGU LOGLINE:"
    )

    lines.append(
        clean_text(
            winner.get(
                "roman_telugu_logline"
            )
        )
    )

    lines.append(
        "WHY THIS IS THE WINNER:"
    )

    lines.append(
        clean_text(
            winner.get(
                "why_this_is_the_winner"
            )
        )
    )


    # --------------------------------------------------------
    # INDIA
    # --------------------------------------------------------

    lines.extend([
        "",
        "",
        "1. INDIA YOUTUBE TRENDS",
        "=" * 70
    ])

    india = report.get(
        "india_youtube_trends",
        {}
    )

    for key, title in [
        (
            "longform_8_10_min",
            "INDIA LONGFORM 8-10 MINUTES"
        ),
        (
            "shorts",
            "INDIA SHORTS"
        )
    ]:

        section = india.get(
            key,
            {}
        )

        lines.extend([

            "",
            title,

            "Trend Summary:",
            clean_text(
                section.get(
                    "trend_summary"
                )
            ),

            "Top Patterns:",
            clean_text(
                section.get(
                    "top_patterns",
                    []
                )
            ),

            "Genres:",
            clean_text(
                section.get(
                    "genres",
                    []
                )
            )
        ])


    # --------------------------------------------------------
    # WORLD
    # --------------------------------------------------------

    lines.extend([
        "",
        "",
        "2. WORLD YOUTUBE TRENDS",
        "=" * 70
    ])

    world = report.get(
        "world_youtube_trends",
        {}
    )

    for key, title in [
        (
            "longform_8_10_min",
            "WORLD LONGFORM 8-10 MINUTES"
        ),
        (
            "shorts",
            "WORLD SHORTS"
        )
    ]:

        section = world.get(
            key,
            {}
        )

        lines.extend([

            "",
            title,

            "Trend Summary:",
            clean_text(
                section.get(
                    "trend_summary"
                )
            ),

            "Top Patterns:",
            clean_text(
                section.get(
                    "top_patterns",
                    []
                )
            ),

            "Genres:",
            clean_text(
                section.get(
                    "genres",
                    []
                )
            )
        ])


    # --------------------------------------------------------
    # GENRES
    # --------------------------------------------------------

    lines.extend([
        "",
        "",
        "3. YOUTUBE GENRE TRENDS",
        "=" * 70
    ])

    genres = report.get(
        "youtube_genre_trends",
        {}
    )

    lines.extend([

        "Longform 8-10 Minutes:",

        clean_text(
            genres.get(
                "longform_8_10_min",
                []
            )
        ),

        "",

        "Shorts:",

        clean_text(
            genres.get(
                "shorts",
                []
            )
        )
    ])


    # --------------------------------------------------------
    # IDEA SECTIONS
    # --------------------------------------------------------

    sections = [

        (
            "4. TREND BASED SHORTS IDEAS",
            "trend_based_shorts_ideas"
        ),

        (
            "5. TREND BASED LONGFORM IDEAS",
            "trend_based_longform_ideas"
        ),

        (
            "6. GENERAL SHORTS IDEAS NOT BASED ON CURRENT TRENDS",
            "general_shorts_ideas"
        ),

        (
            "7. GENERAL LONGFORM IDEAS NOT BASED ON CURRENT TRENDS",
            "general_longform_ideas"
        )
    ]


    for section_title, key in sections:

        lines.extend([
            "",
            "",
            section_title,
            "=" * 70
        ])

        ideas = report.get(
            key,
            []
        )

        for index, idea in enumerate(
            ideas,
            start=1
        ):

            lines.append(
                format_idea(
                    index,
                    idea
                )
            )


    # --------------------------------------------------------
    # DATA SUMMARY
    # --------------------------------------------------------

    lines.extend([

        "",
        "",
        "TREND DATA SUMMARY",
        "=" * 70,

        f"India videos analyzed: "
        f"{india_data.get('video_count', 0)}",

        f"World videos analyzed: "
        f"{world_data.get('video_count', 0)}",

        "India top genres:",

        clean_text(
            india_data.get(
                "top_genres",
                []
            )
        ),

        "World top genres:",

        clean_text(
            world_data.get(
                "top_genres",
                []
            )
        )
    ])


    return "\n".join(lines)


# ============================================================
# RESEND EMAIL
# ============================================================

def send_resend_email(
    subject,
    report
):

    headers = {

        "Authorization":
            f"Bearer {RESEND_API_KEY}",

        "Content-Type":
            "application/json"
    }


    html_report = clean_text(
        report
    )

    html_report = (
        html_report
        .replace(
            "&",
            "&amp;"
        )
        .replace(
            "<",
            "&lt;"
        )
        .replace(
            ">",
            "&gt;"
        )
        .replace(
            "\n",
            "<br>"
        )
    )


    payload = {

        "from":
            SENDER_EMAIL,

        "to": [
            RECIPIENT_EMAIL
        ],

        "subject":
            subject,

        "text":
            report,

        "html":
            f"""
            <html>
            <body
                style="
                font-family:Arial;
                line-height:1.6;
                white-space:normal;
                "
            >
                {html_report}
            </body>
            </html>
            """
    }


    response = requests.post(

        RESEND_URL,

        headers=headers,

        json=payload,

        timeout=60
    )


    if response.status_code >= 300:

        try:
            error = response.json()

        except Exception:
            error = response.text

        raise RuntimeError(
            f"Resend error "
            f"{response.status_code}: "
            f"{error}"
        )


    print(
        "Resend email sent successfully."
    )

    return response.json()


# ============================================================
# SAVE REPORT
# ============================================================

def save_report(report):

    os.makedirs(
        "reports",
        exist_ok=True
    )

    filename = os.path.join(
        "reports",
        "youtube_idea_intelligence.txt"
    )

    with open(
        filename,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(
            report
        )

    print(
        f"Report saved: {filename}"
    )

    return filename


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 70)
    print(
        "YOUTUBE HIGH CTR IDEA GENERATOR"
    )
    print("=" * 70)
    print()

    check_environment()


    # --------------------------------------------------------
    # COLLECT DATA
    # --------------------------------------------------------

    india_videos = (
        collect_india_trends()
    )

    world_videos = (
        collect_world_trends()
    )


    # --------------------------------------------------------
    # ANALYZE
    # --------------------------------------------------------

    print()
    print(
        "Analyzing YouTube trend patterns..."
    )

    india_data = analyze_trends(
        india_videos,
        "India"
    )

    world_data = analyze_trends(
        world_videos,
        "World"
    )


    # --------------------------------------------------------
    # AI
    # --------------------------------------------------------

    print()
    print(
        "Generating high CTR ideas..."
    )

    report_json = generate_ideas(
        india_data,
        world_data
    )


    # --------------------------------------------------------
    # BUILD REPORT
    # --------------------------------------------------------

    report = build_report(
        report_json,
        india_data,
        world_data
    )


    # --------------------------------------------------------
    # SAVE
    # --------------------------------------------------------

    save_report(
        report
    )


    # --------------------------------------------------------
    # EMAIL
    # --------------------------------------------------------

    winner = report_json.get(
        "high_ctr_winner",
        {}
    )

    winner_title = clean_text(
        winner.get(
            "title",
            "High CTR YouTube Ideas"
        )
    )

    subject = (
        "YouTube High CTR Idea "
        + winner_title
    )

    print()
    print(
        "Sending report through Resend..."
    )

    send_resend_email(
        subject,
        report
    )


    # --------------------------------------------------------
    # SUCCESS
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print(
        "IDEA GENERATOR COMPLETED SUCCESSFULLY"
    )
    print("=" * 70)

    print()
    print(
        "HIGH CTR WINNER:"
    )

    print(
        clean_text(
            winner.get(
                "title"
            )
        )
    )

    print()

    print(
        "ROMAN TELUGU LOGLINE:"
    )

    print(
        clean_text(
            winner.get(
                "roman_telugu_logline"
            )
        )
    )

    print()


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    main()
