import os
import re
import json
import time
from datetime import datetime, timezone
from collections import Counter

import requests
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# CONFIGURATION
# ============================================================

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "").strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "").strip()

RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL", "").strip()
SENDER_EMAIL = os.getenv("SENDER_EMAIL", "").strip()

GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-2.5-flash"
).strip()

YOUTUBE_API = "https://www.googleapis.com/youtube/v3"

GEMINI_API = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_MODEL}:generateContent"
)

RESEND_API = "https://api.resend.com/emails"


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
# YOUTUBE CATEGORIES
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
    "29": "Nonprofits and Activism"
}


# ============================================================
# CHECK ENVIRONMENT
# ============================================================

def check_environment():

    required = {
        "YOUTUBE_API_KEY": YOUTUBE_API_KEY,
        "GEMINI_API_KEY": GEMINI_API_KEY,
        "RESEND_API_KEY": RESEND_API_KEY,
        "RECIPIENT_EMAIL": RECIPIENT_EMAIL,
        "SENDER_EMAIL": SENDER_EMAIL
    }

    missing = []

    for name, value in required.items():

        if not value:

            missing.append(name)

    if missing:

        raise RuntimeError(
            "Missing environment variables: "
            + ", ".join(missing)
        )


# ============================================================
# YOUTUBE API
# ============================================================

def youtube_get(endpoint, params):

    params = dict(params)

    params["key"] = YOUTUBE_API_KEY

    response = requests.get(
        f"{YOUTUBE_API}/{endpoint}",
        params=params,
        timeout=30
    )

    if response.status_code != 200:

        try:
            error = response.json()

        except Exception:
            error = response.text

        raise RuntimeError(
            f"YouTube API Error {response.status_code}: {error}"
        )

    return response.json()


# ============================================================
# GET TRENDING VIDEOS
# ============================================================

def get_trending_videos(
    region_code,
    max_results=50
):

    data = youtube_get(
        "videos",
        {
            "part": "snippet,statistics,contentDetails",
            "chart": "mostPopular",
            "regionCode": region_code,
            "maxResults": max_results
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

        video = {

            "id": item.get(
                "id",
                ""
            ),

            "title": snippet.get(
                "title",
                ""
            ),

            "channel": snippet.get(
                "channelTitle",
                ""
            ),

            "description": snippet.get(
                "description",
                ""
            )[:500],

            "category": CATEGORY_NAMES.get(
                snippet.get(
                    "categoryId",
                    ""
                ),
                "Other"
            ),

            "category_id": snippet.get(
                "categoryId",
                ""
            ),

            "published_at": snippet.get(
                "publishedAt",
                ""
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
        }

        videos.append(video)

    return videos


# ============================================================
# INDIA TRENDS
# ============================================================

def collect_india_trends():

    print("")
    print("Collecting India YouTube trends...")

    return get_trending_videos(
        "IN",
        50
    )


# ============================================================
# WORLD TRENDS
# ============================================================

def collect_world_trends():

    print("")
    print("Collecting World YouTube trends...")

    all_videos = []

    for region in WORLD_REGIONS:

        try:

            print(
                f"Scanning {region}..."
            )

            videos = get_trending_videos(
                region,
                30
            )

            all_videos.extend(
                videos
            )

            time.sleep(0.2)

        except Exception as error:

            print(
                f"Skipping {region}: {error}"
            )

    unique = {}

    for video in all_videos:

        video_id = video.get(
            "id"
        )

        if video_id:

            unique[video_id] = video

    return list(
        unique.values()
    )


# ============================================================
# BUILD TREND SUMMARY
# ============================================================

def build_summary(
    videos,
    region_name
):

    category_counter = Counter()

    word_counter = Counter()

    stop_words = {
        "the",
        "and",
        "for",
        "with",
        "this",
        "that",
        "from",
        "your",
        "you",
        "are",
        "was",
        "will",
        "what",
        "when",
        "where",
        "how",
        "why",
        "new",
        "official",
        "video",
        "part",
        "episode",
        "india",
        "world",
        "into",
        "have",
        "has",
        "more",
        "than",
        "just",
        "about",
        "after"
    }

    for video in videos:

        category = video.get(
            "category",
            "Other"
        )

        category_counter[
            category
        ] += 1

        title = re.sub(
            r"[^A-Za-z0-9\s]",
            " ",
            video.get(
                "title",
                ""
            ).lower()
        )

        for word in title.split():

            if (
                len(word) >= 4
                and word not in stop_words
            ):

                word_counter[word] += 1

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
            ),
            x.get(
                "comments",
                0
            )
        ),
        reverse=True
    )[:30]

    return {

        "region_name": region_name,

        "video_count": len(
            videos
        ),

        "top_genres": category_counter.most_common(
            12
        ),

        "title_signals": word_counter.most_common(
            35
        ),

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

        ]
    }


# ============================================================
# EXTRACT JSON FROM GEMINI
# ============================================================

def extract_json(text):

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

    try:

        return json.loads(
            text
        )

    except json.JSONDecodeError:
        pass

    start = text.find(
        "{"
    )

    end = text.rfind(
        "}"
    )

    if (
        start != -1
        and end != -1
        and end > start
    ):

        return json.loads(
            text[
                start:end + 1
            ]
        )

    raise RuntimeError(
        "Gemini returned invalid JSON:\n"
        + text[:5000]
    )


# ============================================================
# GEMINI API
# ============================================================

def generate_with_gemini(
    india_summary,
    world_summary
):

    print("")
    print("Generating ideas using Gemini...")

    system_instruction = """
You are an elite YouTube creative director,
YouTube trend analyst and viral content strategist.

Your job is NOT to produce ordinary YouTube ideas.

The user wants ideas that make people say:

WAH
WHAT AN IDEA

Every idea must have a powerful reason to click.

Avoid completely:

generic challenges
generic reaction videos
generic vlogs
ordinary daily vlogs
random pranks
boring street interviews
simple celebrity content
copying famous creators
ordinary 24 hour challenges
weak what-if ideas
weak motivational videos
basic facts videos
ordinary podcast ideas
ordinary travel videos
ideas with no conflict
ideas with no curiosity
ideas with no escalation
ideas with no payoff
ideas that feel copied
ideas that thousands of creators already make

A strong idea should preferably contain:

curiosity gap
mystery
unexpected premise
high stakes
contradiction
psychology
social observation
technology
hidden truth
countdown
investigation
unexpected reveal
strong visual premise
emotional tension
transformation
clever experiment
strong ending

SHORTS:

The first 1 to 3 seconds must be extremely strong.

The viewer must immediately understand
that something unusual is happening.

The story should escalate quickly.

The ending must provide a reveal,
payoff, twist or satisfying answer.

LONGFORM:

The concept must genuinely support
8 to 10 minutes.

Structure:

setup
mystery/problem
escalation
complication
turning point
payoff

ROMAN TELUGU:

Write natural conversational Roman Telugu.

Do NOT translate English word-by-word.

It should sound like a Telugu YouTube creator
explaining a movie-worthy video idea.

HIGH CTR:

The title must create curiosity without lying.

Choose ONE strongest idea from the entire report.

That idea must be the HIGH CTR WINNER.

Do not select the first idea automatically.

TREND BASED IDEAS:

Must be inspired by the supplied current
YouTube trend data.

GENERAL IDEAS:

Must NOT copy current trending videos.

They should be original evergreen concepts.

Return ONLY valid JSON.
"""

    user_prompt = f"""
Create a complete YouTube Idea Intelligence Report.

TODAY:

{datetime.now(timezone.utc).strftime("%Y-%m-%d")}


INDIA YOUTUBE TREND DATA:

{json.dumps(
    india_summary,
    ensure_ascii=False
)}


WORLD YOUTUBE TREND DATA:

{json.dumps(
    world_summary,
    ensure_ascii=False
)}


Return EXACTLY this JSON structure:

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
            "top_genres": []
        }},

        "shorts": {{
            "trend_summary": "",
            "top_patterns": [],
            "top_genres": []
        }}

    }},

    "world_youtube_trends": {{

        "longform_8_10_min": {{
            "trend_summary": "",
            "top_patterns": [],
            "top_genres": []
        }},

        "shorts": {{
            "trend_summary": "",
            "top_patterns": [],
            "top_genres": []
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

Generate exactly 8 ideas for EACH of these:

trend_based_shorts_ideas

trend_based_longform_ideas

general_shorts_ideas

general_longform_ideas


Every idea MUST contain:

{{
    "region": "India or World",
    "title": "",
    "format": "",
    "target_audience": "",
    "why_people_click": "",
    "core_hook": "",
    "roman_telugu_logline": "",
    "story_payoff": "",
    "ctr_score": 0,
    "originality_score": 0
}}


Mix India and World.

The trend based sections must actually use
the supplied trend evidence.

The general sections must be original
and NOT based on current trends.

The strongest idea from all 32 ideas
must become the High CTR Winner.

Do not generate silly ideas.

If an idea sounds ordinary,
replace it with a much stronger idea.
"""

    payload = {

        "system_instruction": {

            "parts": [

                {
                    "text": system_instruction
                }

            ]

        },

        "contents": [

            {

                "role": "user",

                "parts": [

                    {
                        "text": user_prompt
                    }

                ]

            }

        ],

        "generationConfig": {

            "temperature": 0.95,

            "topP": 0.9,

            "maxOutputTokens": 16000,

            "responseMimeType": "application/json"

        }

    }

    url = (
        GEMINI_API
        + "?key="
        + GEMINI_API_KEY
    )

    response = requests.post(
        url,
        headers={
            "Content-Type": "application/json"
        },
        json=payload,
        timeout=180
    )

    if response.status_code != 200:

        try:

            error = response.json()

        except Exception:

            error = response.text

        raise RuntimeError(
            f"Gemini API Error "
            f"{response.status_code}: "
            f"{error}"
        )

    data = response.json()

    candidates = data.get(
        "candidates",
        []
    )

    if not candidates:

        raise RuntimeError(
            "Gemini returned no candidates:\n"
            + json.dumps(
                data,
                indent=2
            )[:5000]
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

    generated = ""

    for part in parts:

        if "text" in part:

            generated += part[
                "text"
            ]

    if not generated.strip():

        raise RuntimeError(
            "Gemini returned empty response."
        )

    return extract_json(
        generated
    )


# ============================================================
# REMOVE REQUESTED SYMBOLS
# ============================================================

def clean_output(text):

    if text is None:

        return ""

    text = str(text)

    text = text.replace(
        "#",
        ""
    )

    text = text.replace(
        "$",
        ""
    )

    text = text.replace(
        "@",
        ""
    )

    return text.strip()


def safe(value):

    if isinstance(
        value,
        list
    ):

        return ", ".join(
            safe(x)
            for x in value
        )

    if isinstance(
        value,
        dict
    ):

        return "; ".join(
            f"{key}: {safe(val)}"
            for key, val in value.items()
        )

    return clean_output(
        value
    )


# ============================================================
# FORMAT IDEA
# ============================================================

def format_idea(
    number,
    idea
):

    return f"""
{number}. {safe(idea.get("title"))}

Region: {safe(idea.get("region"))}

Format: {safe(idea.get("format"))}

Target Audience: {safe(idea.get("target_audience"))}

CTR Score: {safe(idea.get("ctr_score"))}/100

Originality Score: {safe(idea.get("originality_score"))}/100

Why People Click:
{safe(idea.get("why_people_click"))}

Core Hook:
{safe(idea.get("core_hook"))}

Roman Telugu Logline:
{safe(idea.get("roman_telugu_logline"))}

Story and Payoff:
{safe(idea.get("story_payoff"))}

"""


# ============================================================
# BUILD REPORT
# ============================================================

def build_report(
    report,
    india_summary,
    world_summary
):

    lines = []

    winner = report.get(
        "high_ctr_winner",
        {}
    )

    # ========================================================
    # HIGH CTR WINNER AT TOP
    # ========================================================

    lines.append(
        "HIGH CTR WINNER"
    )

    lines.append(
        "=" * 72
    )

    lines.append(
        "TITLE: "
        + safe(
            winner.get(
                "title"
            )
        )
    )

    lines.append(
        "FORMAT: "
        + safe(
            winner.get(
                "format"
            )
        )
    )

    lines.append(
        "REGION: "
        + safe(
            winner.get(
                "region"
            )
        )
    )

    lines.append(
        "CTR SCORE: "
        + safe(
            winner.get(
                "ctr_score"
            )
        )
        + "/100"
    )

    lines.append(
        "ROMAN TELUGU LOGLINE:"
    )

    lines.append(
        safe(
            winner.get(
                "roman_telugu_logline"
            )
        )
    )

    lines.append(
        "WHY THIS IS THE WINNER:"
    )

    lines.append(
        safe(
            winner.get(
                "why_this_is_the_winner"
            )
        )
    )

    # ========================================================
    # TREND INTELLIGENCE
    # ========================================================

    lines.append("")
    lines.append(
        "YOUTUBE TREND INTELLIGENCE"
    )
    lines.append(
        "=" * 72
    )

    # ========================================================
    # INDIA
    # ========================================================

    lines.append("")
    lines.append(
        "1. INDIA YOUTUBE TRENDS"
    )

    lines.append(
        "-" * 72
    )

    india = report.get(
        "india_youtube_trends",
        {}
    )

    for key, heading in [

        (
            "longform_8_10_min",
            "India Longform 8 to 10 Minutes"
        ),

        (
            "shorts",
            "India Shorts"
        )

    ]:

        section = india.get(
            key,
            {}
        )

        lines.append("")
        lines.append(
            heading
        )

        lines.append(
            "Trend Summary: "
            + safe(
                section.get(
                    "trend_summary"
                )
            )
        )

        lines.append(
            "Top Patterns: "
            + safe(
                section.get(
                    "top_patterns",
                    []
                )
            )
        )

        lines.append(
            "Top Genres: "
            + safe(
                section.get(
                    "top_genres",
                    []
                )
            )
        )

    # ========================================================
    # WORLD
    # ========================================================

    lines.append("")
    lines.append(
        "2. WORLD YOUTUBE TRENDS"
    )

    lines.append(
        "-" * 72
    )

    world = report.get(
        "world_youtube_trends",
        {}
    )

    for key, heading in [

        (
            "longform_8_10_min",
            "World Longform 8 to 10 Minutes"
        ),

        (
            "shorts",
            "World Shorts"
        )

    ]:

        section = world.get(
            key,
            {}
        )

        lines.append("")
        lines.append(
            heading
        )

        lines.append(
            "Trend Summary: "
            + safe(
                section.get(
                    "trend_summary"
                )
            )
        )

        lines.append(
            "Top Patterns: "
            + safe(
                section.get(
                    "top_patterns",
                    []
                )
            )
        )

        lines.append(
            "Top Genres: "
            + safe(
                section.get(
                    "top_genres",
                    []
                )
            )
        )

    # ========================================================
    # GENRE TRENDS
    # ========================================================

    lines.append("")
    lines.append(
        "3. YOUTUBE GENRE TRENDS"
    )

    lines.append(
        "-" * 72
    )

    genres = report.get(
        "youtube_genre_trends",
        {}
    )

    lines.append(
        "Longform 8 to 10 Minutes: "
        + safe(
            genres.get(
                "longform_8_10_min",
                []
            )
        )
    )

    lines.append(
        "Shorts: "
        + safe(
            genres.get(
                "shorts",
                []
            )
        )
    )

    # ========================================================
    # IDEA SECTIONS
    # ========================================================

    sections = [

        (
            "4. TREND BASED SHORTS IDEAS",
            "trend_based_shorts_ideas"
        ),

        (
            "5. TREND BASED LONGFORM 8 TO 10 MINUTE IDEAS",
            "trend_based_longform_ideas"
        ),

        (
            "6. GENERAL SHORTS IDEAS NOT FROM CURRENT TRENDS",
            "general_shorts_ideas"
        ),

        (
            "7. GENERAL LONGFORM 8 TO 10 MINUTE IDEAS NOT FROM CURRENT TRENDS",
            "general_longform_ideas"
        )

    ]

    for heading, key in sections:

        lines.append("")
        lines.append(
            heading
        )

        lines.append(
            "=" * 72
        )

        ideas = report.get(
            key,
            []
        )

        for number, idea in enumerate(
            ideas,
            start=1
        ):

            lines.append(
                format_idea(
                    number,
                    idea
                )
            )

    # ========================================================
    # COLLECTION STATS
    # ========================================================

    lines.append("")
    lines.append(
        "TREND COLLECTION STATS"
    )

    lines.append(
        "=" * 72
    )

    lines.append(
        "India videos analyzed: "
        + safe(
            india_summary.get(
                "video_count"
            )
        )
    )

    lines.append(
        "World videos analyzed: "
        + safe(
            world_summary.get(
                "video_count"
            )
        )
    )

    lines.append(
        "India top genres: "
        + safe(
            india_summary.get(
                "top_genres",
                []
            )
        )
    )

    lines.append(
        "World top genres: "
        + safe(
            world_summary.get(
                "top_genres",
                []
            )
        )
    )

    return clean_output(
        "\n".join(
            lines
        )
    )


# ============================================================
# HTML EMAIL
# ============================================================

def report_to_html(
    report_text
):

    escaped = (
        report_text
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
            '"',
            "&quot;"
        )
    )

    return f"""
<!DOCTYPE html>

<html>

<head>

<meta charset="UTF-8">

<title>
YouTube Idea Generator
</title>

</head>

<body>

<pre style="
font-family: Arial, sans-serif;
font-size: 14px;
line-height: 1.6;
white-space: pre-wrap;
">

{escaped}

</pre>

</body>

</html>
"""


# ============================================================
# RESEND API
# ============================================================

def send_email(
    subject,
    report_text
):

    print("")
    print(
        "Sending report using Resend..."
    )

    payload = {

        "from": SENDER_EMAIL,

        "to": [
            RECIPIENT_EMAIL
        ],

        "subject": subject,

        "html": report_to_html(
            report_text
        ),

        "text": report_text

    }

    response = requests.post(

        RESEND_API,

        headers={

            "Authorization":
                f"Bearer {RESEND_API_KEY}",

            "Content-Type":
                "application/json"

        },

        json=payload,

        timeout=60
    )

    if response.status_code >= 300:

        try:

            error = response.json()

        except Exception:

            error = response.text

        raise RuntimeError(
            f"Resend API Error "
            f"{response.status_code}: "
            f"{error}"
        )

    return response.json()


# ============================================================
# SAVE REPORT
# ============================================================

def save_report(
    report_text
):

    os.makedirs(
        "reports",
        exist_ok=True
    )

    filename = (
        "reports/"
        "youtube_idea_generator_"
        + datetime.now().strftime(
            "%Y%m%d_%H%M%S"
        )
        + ".txt"
    )

    with open(
        filename,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(
            report_text
        )

    return filename


# ============================================================
# MAIN
# ============================================================

def main():

    print("")
    print("=" * 72)
    print(
        "YOUTUBE IDEA GENERATOR"
    )
    print(
        "YouTube API + Gemini + Resend"
    )
    print("=" * 72)

    check_environment()

    # --------------------------------------------------------
    # INDIA
    # --------------------------------------------------------

    india_videos = (
        collect_india_trends()
    )

    # --------------------------------------------------------
    # WORLD
    # --------------------------------------------------------

    world_videos = (
        collect_world_trends()
    )

    # --------------------------------------------------------
    # SUMMARIZE
    # --------------------------------------------------------

    india_summary = build_summary(
        india_videos,
        "India"
    )

    world_summary = build_summary(
        world_videos,
        "World"
    )

    print("")
    print(
        "India videos analyzed:",
        india_summary[
            "video_count"
        ]
    )

    print(
        "World videos analyzed:",
        world_summary[
            "video_count"
        ]
    )

    # --------------------------------------------------------
    # GEMINI
    # --------------------------------------------------------

    report = generate_with_gemini(
        india_summary,
        world_summary
    )

    # --------------------------------------------------------
    # FORMAT REPORT
    # --------------------------------------------------------

    report_text = build_report(
        report,
        india_summary,
        world_summary
    )

    # --------------------------------------------------------
    # SAVE
    # --------------------------------------------------------

    filename = save_report(
        report_text
    )

    # --------------------------------------------------------
    # WINNER
    # --------------------------------------------------------

    winner = report.get(
        "high_ctr_winner",
        {}
    )

    winner_title = safe(
        winner.get(
            "title",
            "High CTR YouTube Ideas"
        )
    )

    subject = (
        "YouTube High CTR Idea Generator | "
        + winner_title
    )

    # --------------------------------------------------------
    # RESEND
    # --------------------------------------------------------

    send_email(
        subject,
        report_text
    )

    print("")
    print("=" * 72)
    print(
        "SUCCESS"
    )
    print("=" * 72)
    print(
        "Report saved:",
        filename
    )
    print(
        "Email sent successfully."
    )
    print("=" * 72)


if __name__ == "__main__":

    main()
