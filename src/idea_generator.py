````python
"""
===============================================================
YOUTUBE HIGH CTR IDEA GENERATOR
===============================================================

OUTPUT STRUCTURE

TOP:
    HIGH CTR IDEA
    Roman Telugu logline

1. India YouTube Trends
    - Shorts
    - Long-form 8–10 minutes
    - Actual videos

2. World YouTube Trends
    - Shorts
    - Long-form 8–10 minutes
    - Actual videos

3. YouTube Genre Trends
    - Shorts
    - Long-form 8–10 minutes
    - Genre -> Subgenre
    - Actual videos

4. Trend-Based Shorts Ideas
    - India + World
    - Very engaging
    - Roman Telugu logline

5. Trend-Based Long-form Ideas
    - India + World
    - 8–10 minutes
    - Very engaging
    - Roman Telugu logline

6. General Shorts Ideas
    - NOT based on current trends
    - Very engaging
    - Roman Telugu logline

7. General Long-form Ideas
    - NOT based on current trends
    - 8–10 minutes
    - Very engaging
    - Roman Telugu logline

8. Genre Combination Ideas
    - Based on genre trends
    - High CTR
    - Very engaging
    - Roman Telugu logline

IMPORTANT:
    - No silly ideas
    - No generic reaction ideas
    - No lazy challenges
    - No fake clickbait
    - No copying source video titles
    - Actual source video titles are displayed
    - OpenRouter is attempted ONLY ONCE
    - Any OpenRouter failure -> local fallback
===============================================================
"""

import os
import re
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import (
    getSampleStyleSheet,
    ParagraphStyle,
)
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
)

# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv()

YOUTUBE_API_KEY = os.getenv(
    "YOUTUBE_API_KEY",
    ""
).strip()

OPENROUTER_API_KEY = os.getenv(
    "OPENROUTER_API_KEY",
    ""
).strip()

OPENROUTER_MODEL = os.getenv(
    "OPENROUTER_MODEL",
    "z-ai/glm-5.3-flash"
).strip()

OUTPUT_DIR = Path(
    os.getenv(
        "OUTPUT_DIR",
        "output"
    )
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

# India
INDIA_CODE = "IN"

# World sample regions.
# You can change these from GitHub Secrets / .env.
WORLD_COUNTRIES = [
    x.strip().upper()
    for x in os.getenv(
        "WORLD_COUNTRIES",
        "US,GB,CA,AU,DE,FR,JP,KR,BR,MX"
    ).split(",")
    if x.strip()
]

YOUTUBE_API_URL = (
    "https://www.googleapis.com/youtube/v3/videos"
)

OPENROUTER_URL = (
    "https://openrouter.ai/api/v1/chat/completions"
)

# ============================================================
# VIDEO FORMAT
# ============================================================

SHORT_MAX_SECONDS = 180

LONGFORM_MIN_SECONDS = 8 * 60
LONGFORM_MAX_SECONDS = 10 * 60

SOURCE_VIDEO_LIMIT = 10
IDEAS_PER_SECTION = 8

# ============================================================
# GENRE SYSTEM
# ============================================================

GENRE_KEYWORDS = {

    "Entertainment": [
        "movie",
        "film",
        "cinema",
        "trailer",
        "actor",
        "actress",
        "celebrity",
        "entertainment",
        "reaction",
        "comedy",
        "thriller",
        "series",
        "web series",
    ],

    "Music": [
        "song",
        "music",
        "lyrics",
        "singer",
        "concert",
        "album",
        "cover",
        "audio",
        "music video",
    ],

    "Gaming": [
        "gaming",
        "gameplay",
        "minecraft",
        "gta",
        "roblox",
        "free fire",
        "pubg",
        "bgmi",
        "valorant",
        "fortnite",
    ],

    "Technology": [
        "technology",
        "tech",
        "iphone",
        "android",
        "ai",
        "artificial intelligence",
        "robot",
        "coding",
        "python",
        "software",
        "google",
        "apple",
    ],

    "Education": [
        "education",
        "learn",
        "tutorial",
        "course",
        "exam",
        "study",
        "science",
        "math",
        "history",
        "explained",
    ],

    "News & Current Affairs": [
        "news",
        "breaking",
        "politics",
        "election",
        "government",
        "minister",
        "current affairs",
    ],

    "Lifestyle": [
        "vlog",
        "lifestyle",
        "travel",
        "food",
        "restaurant",
        "cooking",
        "fitness",
        "gym",
        "fashion",
        "beauty",
    ],

    "Sports": [
        "cricket",
        "football",
        "soccer",
        "basketball",
        "tennis",
        "match",
        "ipl",
        "wwe",
        "sports",
    ],

    "Business & Finance": [
        "business",
        "finance",
        "money",
        "investment",
        "stock",
        "startup",
        "entrepreneur",
        "economy",
    ],

    "True Crime & Mystery": [
        "crime",
        "murder",
        "killer",
        "case",
        "investigation",
        "missing",
        "mystery",
        "scam",
        "fraud",
    ],
}


SUBGENRE_KEYWORDS = {

    "Thriller": [
        "thriller",
        "suspense",
        "chase",
        "escape",
        "danger",
        "survival",
    ],

    "Mystery": [
        "mystery",
        "unknown",
        "secret",
        "missing",
        "disappearance",
        "unsolved",
        "clue",
    ],

    "Crime": [
        "crime",
        "murder",
        "killer",
        "criminal",
        "police",
        "case",
        "scam",
        "fraud",
    ],

    "Comedy": [
        "comedy",
        "funny",
        "laugh",
        "roast",
        "parody",
        "meme",
    ],

    "Reaction": [
        "reaction",
        "react",
        "reacting",
        "review",
    ],

    "Storytelling": [
        "story",
        "storytime",
        "journey",
        "experience",
        "life story",
    ],

    "Documentary": [
        "documentary",
        "investigation",
        "explained",
        "history",
        "untold",
    ],

    "Technology": [
        "ai",
        "iphone",
        "android",
        "robot",
        "coding",
        "python",
        "tech",
    ],

    "Gaming": [
        "gaming",
        "gameplay",
        "minecraft",
        "gta",
        "roblox",
        "valorant",
        "pubg",
        "bgmi",
    ],

    "Food": [
        "food",
        "restaurant",
        "cooking",
        "recipe",
        "street food",
    ],

    "Travel": [
        "travel",
        "trip",
        "airport",
        "flight",
        "hotel",
        "tour",
    ],

    "Fitness": [
        "gym",
        "workout",
        "fitness",
        "muscle",
        "weight loss",
    ],

    "Music": [
        "song",
        "music",
        "concert",
        "lyrics",
        "cover",
    ],

    "Sports": [
        "cricket",
        "football",
        "soccer",
        "basketball",
        "match",
        "wwe",
    ],
}


# ============================================================
# BASIC HELPERS
# ============================================================

def clean_text(value: Any) -> str:

    if value is None:
        return ""

    text = str(value)

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


def safe_int(
    value: Any,
    default: int = 0
) -> int:

    try:
        return int(value)
    except Exception:
        return default


def format_views(
    views: int
) -> str:

    if views >= 1_000_000_000:
        return f"{views / 1_000_000_000:.1f}B"

    if views >= 1_000_000:
        return f"{views / 1_000_000:.1f}M"

    if views >= 1_000:
        return f"{views / 1_000:.1f}K"

    return str(views)


def parse_duration(
    duration: str
) -> int:

    if not duration:
        return 0

    h = re.search(
        r"(\d+)H",
        duration
    )

    m = re.search(
        r"(\d+)M",
        duration
    )

    s = re.search(
        r"(\d+)S",
        duration
    )

    hours = (
        int(h.group(1))
        if h
        else 0
    )

    minutes = (
        int(m.group(1))
        if m
        else 0
    )

    seconds = (
        int(s.group(1))
        if s
        else 0
    )

    return (
        hours * 3600
        + minutes * 60
        + seconds
    )


def format_duration(
    seconds: int
) -> str:

    minutes = seconds // 60
    remaining = seconds % 60

    if minutes >= 60:

        hours = minutes // 60
        minutes = minutes % 60

        return (
            f"{hours}:"
            f"{minutes:02d}:"
            f"{remaining:02d}"
        )

    return (
        f"{minutes}:"
        f"{remaining:02d}"
    )


# ============================================================
# FORMAT
# ============================================================

def classify_format(
    seconds: int
) -> str:

    if seconds <= 0:
        return "Unknown"

    if seconds <= SHORT_MAX_SECONDS:
        return "Shorts"

    if (
        LONGFORM_MIN_SECONDS
        <= seconds
        <= LONGFORM_MAX_SECONDS
    ):
        return "Long-form 8–10 min"

    return "Other Long-form"


# ============================================================
# GENRE
# ============================================================

def classify_genre(
    title: str
) -> str:

    text = clean_text(
        title
    ).lower()

    scores = {}

    for genre, keywords in GENRE_KEYWORDS.items():

        score = 0

        for keyword in keywords:

            if keyword in text:
                score += 1

        scores[genre] = score

    best = max(
        scores,
        key=scores.get
    )

    if scores[best] == 0:
        return "Entertainment"

    return best


def classify_subgenre(
    title: str
) -> str:

    text = clean_text(
        title
    ).lower()

    scores = {}

    for subgenre, keywords in SUBGENRE_KEYWORDS.items():

        score = 0

        for keyword in keywords:

            if keyword in text:
                score += 1

        scores[subgenre] = score

    best = max(
        scores,
        key=scores.get
    )

    if scores[best] == 0:
        return "General"

    return best


# ============================================================
# YOUTUBE API
# ============================================================

def fetch_country_videos(
    country_code: str
) -> List[Dict[str, Any]]:

    if not YOUTUBE_API_KEY:

        raise RuntimeError(
            "YOUTUBE_API_KEY is missing."
        )

    params = {
        "part": (
            "snippet,"
            "statistics,"
            "contentDetails"
        ),
        "chart": "mostPopular",
        "regionCode": country_code,
        "maxResults": 50,
        "key": YOUTUBE_API_KEY,
    }

    response = requests.get(
        YOUTUBE_API_URL,
        params=params,
        timeout=40,
    )

    response.raise_for_status()

    data = response.json()

    videos = []

    for item in data.get(
        "items",
        []
    ):

        video_id = item.get(
            "id"
        )

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

        if not video_id:
            continue

        title = clean_text(
            snippet.get(
                "title"
            )
        )

        if not title:
            continue

        seconds = parse_duration(
            content.get(
                "duration",
                ""
            )
        )

        video = {

            "video_id": video_id,

            # ACTUAL YOUTUBE TITLE
            "title": title,

            "channel": clean_text(
                snippet.get(
                    "channelTitle"
                )
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

            "duration_seconds": seconds,

            "duration": format_duration(
                seconds
            ),

            "format": classify_format(
                seconds
            ),

            "genre": classify_genre(
                title
            ),

            "subgenre": classify_subgenre(
                title
            ),

            "country": country_code,

            "url": (
                "https://www.youtube.com/watch?v="
                + video_id
            ),
        }

        videos.append(
            video
        )

    return videos


def collect_youtube_data():

    all_videos = []

    errors = []

    countries = [
        INDIA_CODE
    ] + WORLD_COUNTRIES

    for country in countries:

        try:

            videos = fetch_country_videos(
                country
            )

            print(
                f"[YouTube] {country}: "
                f"{len(videos)} videos"
            )

            all_videos.extend(
                videos
            )

        except Exception as exc:

            message = (
                f"{country}: "
                f"{type(exc).__name__}: "
                f"{exc}"
            )

            print(
                "[YouTube ERROR] "
                + message
            )

            errors.append(
                message
            )

    # Remove duplicate video IDs.
    unique = {}

    for video in all_videos:

        unique[
            video["video_id"]
        ] = video

    return (
        list(unique.values()),
        errors
    )


# ============================================================
# VIDEO FILTERS
# ============================================================

def india_videos(
    videos
):

    return [
        v
        for v in videos
        if v["country"] == "IN"
    ]


def world_videos(
    videos
):

    return [
        v
        for v in videos
        if v["country"] != "IN"
    ]


def shorts_videos(
    videos
):

    return [
        v
        for v in videos
        if v["format"] == "Shorts"
    ]


def longform_videos(
    videos
):

    return [
        v
        for v in videos
        if v["format"]
        == "Long-form 8–10 min"
    ]


# ============================================================
# TREND RANKING
# ============================================================

def trend_score(
    video: Dict[str, Any]
) -> float:

    views = safe_int(
        video.get(
            "views",
            0
        )
    )

    likes = safe_int(
        video.get(
            "likes",
            0
        )
    )

    comments = safe_int(
        video.get(
            "comments",
            0
        )
    )

    # Log-like weighting without
    # needing numpy.
    return (
        (views ** 0.60)
        + (likes ** 0.35) * 20
        + (comments ** 0.30) * 15
    )


def rank_videos(
    videos: List[Dict[str, Any]],
    limit: int = SOURCE_VIDEO_LIMIT
):

    return sorted(
        videos,
        key=trend_score,
        reverse=True
    )[:limit]


# ============================================================
# GENRE TREND ANALYSIS
# ============================================================

def genre_analysis(
    videos
):

    result = {}

    for video in videos:

        genre = video[
            "genre"
        ]

        subgenre = video[
            "subgenre"
        ]

        if genre not in result:

            result[
                genre
            ] = {}

        if subgenre not in result[
            genre
        ]:

            result[
                genre
            ][
                subgenre
            ] = []

        result[
            genre
        ][
            subgenre
        ].append(
            video
        )

    return result


def sorted_genre_analysis(
    videos
):

    groups = genre_analysis(
        videos
    )

    output = []

    for genre, subgenres in groups.items():

        all_items = []

        for items in subgenres.values():
            all_items.extend(
                items
            )

        total_views = sum(
            v["views"]
            for v in all_items
        )

        output.append(
            {
                "genre": genre,
                "count": len(
                    all_items
                ),
                "views": total_views,
                "subgenres": subgenres,
            }
        )

    return sorted(
        output,
        key=lambda x: (
            x["count"],
            x["views"]
        ),
        reverse=True
    )


# ============================================================
# SOURCE VIDEO REPORT
# ============================================================

def render_source_videos(
    videos
):

    if not videos:

        return (
            "No matching videos were "
            "returned by the YouTube API."
        )

    lines = []

    ranked = rank_videos(
        videos
    )

    for index, video in enumerate(
        ranked,
        start=1
    ):

        lines.append(
            f"{index}. **{video['title']}**"
        )

        lines.append(
            f"   - Channel: "
            f"{video['channel']}"
        )

        lines.append(
            f"   - Views: "
            f"{format_views(video['views'])}"
        )

        lines.append(
            f"   - Duration: "
            f"{video['duration']}"
        )

        lines.append(
            f"   - Genre: "
            f"{video['genre']}"
        )

        lines.append(
            f"   - Subgenre: "
            f"{video['subgenre']}"
        )

        lines.append(
            f"   - YouTube: "
            f"{video['url']}"
        )

        lines.append("")

    return "\n".join(
        lines
    )


# ============================================================
# CREATIVE QUALITY CONTROL
# ============================================================

BANNED_PATTERNS = [

    "reaction to",

    "reacting to",

    "i reacted",

    "24 hour challenge",

    "24 hours",

    "last to leave",

    "i tried",

    "top 10",

    "top 5",

    "you won't believe",

    "secret nobody knows",

    "why this is going viral",

    "this went viral",

    "viral because",

]


def is_silly_or_generic(
    title: str
) -> bool:

    text = clean_text(
        title
    ).lower()

    for pattern in BANNED_PATTERNS:

        if pattern in text:
            return True

    return False


# ============================================================
# LOCAL FALLBACK IDEAS
# ============================================================

LOCAL_IDEA_LIBRARY = {

    "trend_shorts": [

        {
            "title":
                "The One Detail Everyone Saw But Nobody Questioned",

            "logline":
                "Andaru aa detail ni chusaru kani evaru question cheyyaledu; protagonist danini follow avvagane simple incident venaka unna shocking connection bayata padutundi.",

            "concept":
                "A familiar visual detail becomes the first clue in a compact mystery. Every 10 seconds adds a new interpretation, and the final reveal changes the meaning of the opening shot."
        },

        {
            "title":
                "The Last 10 Seconds Change Everything You Saw Before",

            "logline":
                "First 40 seconds lo audience ki oka story anipistundi, kani last 10 seconds lo oka small reveal motham previous scenes ni different ga explain chestundi.",

            "concept":
                "Build a short around controlled misdirection. The audience thinks they understand the situation until one final piece of evidence forces a reinterpretation."
        },

        {
            "title":
                "One Missing Message Explains the Whole Mystery",

            "logline":
                "Oka ordinary conversation lo missing message ni protagonist kanipettinappudu, mundu jarigina prathi incident ki completely different meaning vastundi.",

            "concept":
                "The story revolves around a missing digital message. Instead of simply revealing the message, show how each person remembers the event differently."
        },

        {
            "title":
                "The Camera Captured Something Nobody Was Looking For",

            "logline":
                "Camera lo accidental ga capture ayina oka tiny detail ni protagonist notice chestadu; danini follow chesthe expected story completely reverse avutundi.",

            "concept":
                "Use visual evidence as the protagonist. The audience can see the clue before the character understands its importance."
        },

        {
            "title":
                "Everyone Has the Same Story — Except One Detail",

            "logline":
                "Andaru same incident gurinchi same story cheptaru, kani oka person cheppina single detail valla entire truth doubt lo padutundi.",

            "concept":
                "A short investigation built around conflicting memories. The final answer is not simply who lied, but why the versions differ."
        },

        {
            "title":
                "The Object That Was Never Supposed to Be There",

            "logline":
                "Normal place lo undakudadani oka object kanipistundi; dani owner ni trace chestu vellinappudu story completely unexpected direction lo turn avutundi.",

            "concept":
                "An ordinary object becomes a mystery engine. Each owner adds another layer until the final owner connects back to the opening."
        },

        {
            "title":
                "A Normal Door With One Impossible Clue",

            "logline":
                "Door chala normal ga untundi kani dani meeda unna oka tiny clue protagonist ni follow cheyyamani force chestundi, final lo aa clue story motham marchestundi.",

            "concept":
                "A visually simple mystery with escalating evidence and a clean final reveal."
        },

        {
            "title":
                "The Person Who Knew What Would Happen Next",

            "logline":
                "Oka stranger next event mundhe exact ga cheptadu; protagonist adi coincidence anukuntadu kani third prediction tarvatha danger real ani ardham avutundi.",

            "concept":
                "Start with a seemingly impossible prediction and escalate from coincidence to consequence."
        },
    ],

    "trend_long": [

        {
            "title":
                "I Followed One Strange Clue Until It Connected to Everything",

            "logline":
                "Modatlo insignificant ga kanipinchina oka clue ni follow chestu vellinappudu, adi completely unrelated anukunna incidents anni connect chestundani protagonist discover chestadu.",

            "concept":
                "An 8–10 minute investigation. Start with one compelling clue, introduce competing explanations, eliminate them through evidence, and finish with a human consequence rather than a cheap twist."
        },

        {
            "title":
                "The Story Behind the Thing Everyone Scrolls Past",

            "logline":
                "Andaru daily chusi ignore chese oka ordinary thing venaka actual story enti ani investigate chesthe, expected answer kanna emotional ga stronger truth bayata padutundi.",

            "concept":
                "Take an ordinary object, location or routine and investigate its hidden history through people, evidence and unexpected connections."
        },

        {
            "title":
                "Three Clues. One Answer. But the Obvious Answer Is Wrong.",

            "logline":
                "Audience ki three strong clues istaru; first answer obvious ga anipistundi kani investigation advance ayye koddi aa answer impossible ani prove avutundi.",

            "concept":
                "Audience participates in solving the mystery. Every clue should be useful, not filler, and the final explanation should be logically satisfying."
        },

        {
            "title":
                "The Version of the Story We Were Never Shown",

            "logline":
                "Popular version simple ga anipinchina, missing perspective ni investigate chesthe story lo important piece intentionally kanipinchakunda poyindani telustundi.",

            "concept":
                "Reconstruct a familiar narrative from the perspective that is usually absent."
        },

        {
            "title":
                "What Really Happened Between These Two Moments?",

            "logline":
                "Story lo before mariyu after clear ga unnayi kani madhyalo jarigina few minutes complete mystery; evidence tho aa missing timeline ni reconstruct chestam.",

            "concept":
                "A timeline mystery where every discovery reveals another missing minute."
        },

        {
            "title":
                "The Detail That Explains the Entire Mystery",

            "logline":
                "Motham investigation confusing ga unna time lo protagonist repeated ga ignore chesina oka tiny detail final ga complete answer ki key avutundi.",

            "concept":
                "Build the entire video around a clue viewers can theoretically notice themselves."
        },

        {
            "title":
                "One Decision That Quietly Changed Everything",

            "logline":
                "Ordinary decision laga kanipinchina oka choice next events ni silently influence chestundi; final lo aa first decision importance reveal avutundi.",

            "concept":
                "A cause-and-effect story where each consequence leads naturally to the next."
        },

        {
            "title":
                "The Mystery Hidden Inside an Ordinary Place",

            "logline":
                "Normal place lo years nunchi ignore ayina pattern ni protagonist notice chestadu; evidence collect chestu vellaga place gurinchi audience ki unna perception completely change avutundi.",

            "concept":
                "Turn an ordinary location into a story world through clues, people, history and escalating discovery."
        },
    ],

    "general_shorts": [

        {
            "title":
                "The Question Nobody Asks About an Ordinary Thing",

            "logline":
                "Daily life lo andariki familiar ayina oka thing gurinchi simple question adigithe, answer expected ga undadu; aa answer venaka interesting story untundi.",

            "concept":
                "Curiosity comes from making viewers reconsider something they see every day."
        },

        {
            "title":
                "A Story That Looks Simple Until the Final Detail",

            "logline":
                "First lo ordinary incident laga start ayina story final detail reveal ayye sariki audience beginning ni malli think cheyyalsi vastundi.",

            "concept":
                "A compact narrative with a fair-play twist."
        },

        {
            "title":
                "One Choice. Two Futures.",

            "logline":
                "Oka character mundu rendu choices untayi; video parallel ga rendu futures ni chupinchi, final lo unexpected choice impact ni reveal chestundi.",

            "concept":
                "Use parallel storytelling to make a simple decision feel high stakes."
        },

        {
            "title":
                "The Smallest Detail That Changes a Decision",

            "logline":
                "Decision almost final ayina moment lo tiny information dorukutundi; aa information valla character complete opposite choice teesukuntadu.",

            "concept":
                "Show how one piece of information changes human behaviour."
        },

        {
            "title":
                "Three People Remember the Same Event Differently",

            "logline":
                "Oke incident ni three people completely different ga remember chestaru; final evidence vallandari memories lo oka hidden common point ni reveal chestundi.",

            "concept":
                "A psychological mini-mystery told through conflicting perspectives."
        },

        {
            "title":
                "The Experiment Nobody Expected to Work",

            "logline":
                "Simple experiment fail avutundi ani andariki anipistundi, kani unexpected result vachinappudu real question experiment work ayyinda kaada kaadu — enduku work ayyindo.",

            "concept":
                "The result creates a second, more interesting question."
        },

        {
            "title":
                "The Place With Three Completely Different Stories",

            "logline":
                "Oke location ni three different people perspective lo chusthe, same place ki three completely different meanings untayani telustundi.",

            "concept":
                "Use one physical location to tell three interconnected human stories."
        },

        {
            "title":
                "The Five-Second Decision",

            "logline":
                "Audience ki five seconds lo decision teesukomani situation istam; taruvatha aa choice ki unexpected consequences chupinchi viewer ni story lo involve chestam.",

            "concept":
                "Interactive storytelling where the viewer mentally chooses before seeing the consequence."
        },
    ],

    "general_long": [

        {
            "title":
                "I Investigated an Ordinary Place That Had an Unusual Pattern",

            "logline":
                "Normal place lo repeated ga jarugutunna unusual pattern ni protagonist notice chestadu; evidence collect chestu vellaga pattern venaka human story bayata padutundi.",

            "concept":
                "8–10 minute investigation with a visual location, evidence gathering and emotional payoff."
        },

        {
            "title":
                "The Hidden Story Behind an Everyday Object",

            "logline":
                "Daily use chese ordinary object ni trace chestu vellaga dani history lo unexpected people, decisions mariyu consequences connect avutayi.",

            "concept":
                "Transform an ordinary object into a narrative journey."
        },

        {
            "title":
                "What Happens When You Follow One Question Too Far?",

            "logline":
                "Simple question ki answer kosam start ayina journey, successive questions valla much bigger story ni uncover chestundi.",

            "concept":
                "Every answer should create a more interesting question."
        },

        {
            "title":
                "The Missing Piece That Changes the Entire Story",

            "logline":
                "Story lo important piece missing undani protagonist realize chestadu; aa piece dorikina tarvatha already telisina facts anni new meaning pondutayi.",

            "concept":
                "Use missing information as the central storytelling device."
        },

        {
            "title":
                "The Mystery That Can Be Solved From Three Details",

            "logline":
                "Audience mundu three details petti mystery solve cheyyamani invite chestam; clues connect chestu vellaga obvious answer wrong ani prove avutundi.",

            "concept":
                "Fair-play mystery where the audience has enough information to theorize."
        },

        {
            "title":
                "The Day One Small Problem Became a Much Bigger Story",

            "logline":
                "Tiny problem solve cheyyadaniki teesukunna first step next problem create chestundi; chain reaction final ga original problem kanna completely bigger situation create chestundi.",

            "concept":
                "A tightly escalating cause-and-effect story."
        },

        {
            "title":
                "The Real Story Behind a Familiar Story",

            "logline":
                "Andariki already telisina version ni pakkana petti missing evidence ni search chesthe, familiar story ki emotional ga stronger explanation dorukutundi.",

            "concept":
                "Separate the popular narrative from the evidence and reconstruct the story."
        },

        {
            "title":
                "One Detail Everyone Ignored for Years",

            "logline":
                "Years ga andariki visible ga unna detail ni evaru serious ga teesukoledu; protagonist danini investigate chesthe unexpected connection bayata padutundi.",

            "concept":
                "A long-form investigation built around one overlooked piece of evidence."
        },
    ],

    "genre_combo": [

        {
            "title":
                "Mystery + Thriller: The Clue That Was Waiting for Someone to Notice",

            "logline":
                "Simple clue laga kanipinchina detail actually countdown ki first signal ani protagonist late ga realize chestadu; truth kosam race start avutundi.",

            "concept":
                "Mystery provides the question; thriller provides the ticking clock."
        },

        {
            "title":
                "Comedy + Mystery: Everyone Has a Different Explanation",

            "logline":
                "Strange incident ki prathi person funny explanation istadu, kani clues serious truth vaipu point chestu vellaga comedy slowly genuine mystery ga marutundi.",

            "concept":
                "Begin lightly, then allow the mystery to become increasingly serious."
        },

        {
            "title":
                "Crime + Technology: The Digital Detail Nobody Noticed",

            "logline":
                "Ordinary digital record lo unna tiny timestamp protagonist ki dorukutundi; aa one detail entire case timeline ni reverse chestundi.",

            "concept":
                "Combine digital evidence with a human investigation."
        },

        {
            "title":
                "Documentary + Thriller: The Countdown Hidden in Plain Sight",

            "logline":
                "Documentary-style evidence collect chestu vellaga protagonist ki situation already countdown mode lo undani telustundi.",

            "concept":
                "Real-world investigation structure with thriller pacing."
        },

        {
            "title":
                "Drama + Mystery: The Memory That Does Not Match",

            "logline":
                "Emotional incident gurinchi protagonist ki oka memory untundi kani evidence aa memory ni contradict chestundi; truth search emotional conflict ga marutundi.",

            "concept":
                "The mystery is also a character relationship problem."
        },

        {
            "title":
                "Gaming + Thriller: The Prediction That Appears in Real Life",

            "logline":
                "Game lo random prediction laga kanipinchina event real life lo repeat ayye sariki player next prediction ni stop cheyyadaniki try chestadu.",

            "concept":
                "Use gaming mechanics as the logic of a suspense story."
        },

        {
            "title":
                "Technology + Mystery: The Pattern Hidden in Ordinary Data",

            "logline":
                "Huge data lo random laga kanipinchina pattern actually one human story ni reveal chestundi; pattern ni trace chestu vellaga stakes perigipothayi.",

            "concept":
                "Data becomes the clue system for a human mystery."
        },

        {
            "title":
                "Entertainment + Crime: The Perfect Public Story",

            "logline":
                "Public ki perfect ga kanipinche story lo tiny contradictions ni investigate chesthe, image venaka completely different conflict reveal avutundi.",

            "concept":
                "Combine entertainment-world glamour with investigation and human stakes."
        },
    ],
}


# ============================================================
# LOCAL IDEA BUILDER
# ============================================================

def build_local_ideas():

    result = {}

    for section, items in LOCAL_IDEA_LIBRARY.items():

        result[
            section
        ] = []

        for index in range(
            IDEAS_PER_SECTION
        ):

            source = items[
                index % len(items)
            ]

            result[
                section
            ].append(
                {
                    "title":
                        source["title"],

                    "logline":
                        source["logline"],

                    "concept":
                        source["concept"],

                    "format":
                        (
                            "Shorts"
                            if section
                            in {
                                "trend_shorts",
                                "general_shorts",
                            }
                            else
                            "8–10 min"
                        ),

                    "source_inspiration":
                        "Original concept",

                    "editorial_score":
                        {
                            "curiosity": 9,
                            "story": 9,
                            "visual": 8,
                            "payoff": 9,
                            "overall": 9,
                        },
                }
            )

    return result


# ============================================================
# OPENROUTER PROMPT
# ============================================================

SYSTEM_PROMPT = r"""
You are an elite YouTube creative director and story strategist.

Your job is to generate ideas that make the creator say:

"WAH. WHAT A IDEA."

NOT generic YouTube ideas.

NOT silly ideas.

NOT low-effort ideas.

NOT random challenges.

NOT reaction videos.

NOT "I tried X".

NOT "24 hours".

NOT "Top 10".

NOT fake mystery clickbait.

NOT empty "you won't believe" titles.

Every concept must have a real story engine.

A great idea should contain several of these:

1. Strong curiosity gap
2. Specific premise
3. Human stakes
4. Conflict
5. Escalation
6. Visual storytelling
7. A question viewers genuinely want answered
8. A reversal / discovery / emotional payoff
9. A reason to watch until the end
10. Something the creator can realistically produce

The idea must be ORIGINAL.

Trend source videos are inspiration only.
NEVER copy the source title.
NEVER simply remake the source video.

ROMAN TELUGU:

Loglines must sound like natural spoken Roman Telugu.

Avoid awkward translated Telugu.

Use conversational Roman Telugu such as:

"Modatlo simple incident laga kanipistundi kani..."

"Protagonist aa clue ni follow chestu vellaga..."

"Last lo audience beginning ni malli different angle lo chudalsi vastundi."

Do NOT produce silly loglines.

--------------------------------------------------
SECTION DEFINITIONS
--------------------------------------------------

trend_shorts:
Current India/World YouTube trend-inspired Shorts.
Must be original.

trend_long:
Current India/World YouTube trend-inspired 8–10 minute videos.
Must be original.

general_shorts:
NOT based on current YouTube trends.
Purely strong original ideas.

general_long:
NOT based on current YouTube trends.
8–10 minute strong original ideas.

genre_combo:
Combine genre/subgenre patterns intelligently.
Examples:
Mystery + Thriller
Comedy + Mystery
Crime + Technology
Drama + Investigation
Gaming + Thriller
Documentary + Thriller

--------------------------------------------------
HIGH CTR TOP IDEA
--------------------------------------------------

Also generate one single BEST idea.

This must be the strongest idea in the entire report.

It should be:
- highly clickable
- emotionally interesting
- easy to understand
- visually strong
- story-driven
- not silly
- not generic
- capable of carrying an 8–10 minute video

Return:

{
  "high_ctr": {
    "title": "...",
    "logline": "...",
    "concept": "...",
    "why_it_works": "...",
    "editorial_score": 9.5
  },

  "trend_shorts": [8 objects],
  "trend_long": [8 objects],
  "general_shorts": [8 objects],
  "general_long": [8 objects],
  "genre_combo": [8 objects]
}

Each idea object:

{
  "title": "...",
  "logline": "...",
  "concept": "...",
  "format": "Shorts" or "8–10 min",
  "source_inspiration": "...",
  "editorial_score": {
      "curiosity": 1-10,
      "story": 1-10,
      "visual": 1-10,
      "payoff": 1-10,
      "overall": 1-10
  }
}

Scores are EDITORIAL ESTIMATES.
They are NOT real YouTube CTR measurements.

Return ONLY valid JSON.
No markdown.
No explanation.
"""


def build_ai_input(
    videos
):

    # Send only strongest source videos
    # to keep prompt size manageable.

    top = rank_videos(
        videos,
        45
    )

    sources = []

    for video in top:

        sources.append(
            {
                "actual_title":
                    video["title"],

                "channel":
                    video["channel"],

                "views":
                    video["views"],

                "duration":
                    video["duration"],

                "format":
                    video["format"],

                "genre":
                    video["genre"],

                "subgenre":
                    video["subgenre"],

                "country":
                    video["country"],

                "url":
                    video["url"],
            }
        )

    return sources


# ============================================================
# JSON PARSER
# ============================================================

def parse_model_json(
    text: str
):

    if not text:
        return None

    text = text.strip()

    # Direct JSON
    try:

        data = json.loads(
            text
        )

        if isinstance(
            data,
            dict
        ):
            return data

    except Exception:
        pass

    # Remove fences
    text = re.sub(
        r"```json",
        "",
        text,
        flags=re.I
    )

    text = text.replace(
        "```",
        ""
    ).strip()

    try:

        data = json.loads(
            text
        )

        if isinstance(
            data,
            dict
        ):
            return data

    except Exception:
        pass

    # Find object
    start = text.find(
        "{"
    )

    end = text.rfind(
        "}"
    )

    if (
        start >= 0
        and end > start
    ):

        candidate = text[
            start:end + 1
        ]

        try:

            data = json.loads(
                candidate
            )

            if isinstance(
                data,
                dict
            ):
                return data

        except Exception:
            pass

    return None


# ============================================================
# OPENROUTER - ONE REQUEST ONLY
# ============================================================

def generate_ai_ideas(
    videos
):

    if not OPENROUTER_API_KEY:

        print(
            "[OpenRouter] "
            "API key missing."
        )

        return None

    sources = build_ai_input(
        videos
    )

    user_prompt = (
        "Use the following CURRENT YouTube "
        "source videos to identify patterns. "
        "Create ORIGINAL ideas.\n\n"
        "SOURCE VIDEOS:\n"
        + json.dumps(
            sources,
            ensure_ascii=False
        )
    )

    payload = {

        "model":
            OPENROUTER_MODEL,

        "temperature":
            0.9,

        "max_tokens":
            9000,

        "messages": [

            {
                "role":
                    "system",

                "content":
                    SYSTEM_PROMPT,
            },

            {
                "role":
                    "user",

                "content":
                    user_prompt,
            },
        ],
    }

    print(
        "[OpenRouter] "
        f"ONE request using "
        f"{OPENROUTER_MODEL}"
    )

    try:

        response = requests.post(

            OPENROUTER_URL,

            headers={
                "Authorization":
                    "Bearer "
                    + OPENROUTER_API_KEY,

                "Content-Type":
                    "application/json",
            },

            json=payload,

            timeout=90,
        )

    except Exception as exc:

        print(
            "[OpenRouter] "
            f"Request error: {exc}"
        )

        return None

    # NO RETRY.
    if response.status_code != 200:

        print(
            "[OpenRouter] "
            f"HTTP {response.status_code}"
        )

        print(
            "[OpenRouter] "
            "Using local fallback."
        )

        return None

    try:

        response_json = (
            response.json()
        )

    except Exception:

        print(
            "[OpenRouter] "
            "Invalid response JSON."
        )

        return None

    try:

        content = (
            response_json[
                "choices"
            ][0][
                "message"
            ][
                "content"
            ]
        )

    except Exception:

        print(
            "[OpenRouter] "
            "No model content."
        )

        return None

    parsed = parse_model_json(
        content
    )

    if not parsed:

        print(
            "[OpenRouter] "
            "Malformed model JSON."
        )

        print(
            "[OpenRouter] "
            "Using local fallback."
        )

        return None

    required = {
        "high_ctr",
        "trend_shorts",
        "trend_long",
        "general_shorts",
        "general_long",
        "genre_combo",
    }

    missing = (
        required
        - set(parsed.keys())
    )

    if missing:

        print(
            "[OpenRouter] "
            f"Missing: {missing}"
        )

        return None

    print(
        "[OpenRouter] "
        "Valid creative JSON received."
    )

    return parsed


# ============================================================
# VALIDATION
# ============================================================

def clean_idea(
    idea,
    fallback
):

    if not isinstance(
        idea,
        dict
    ):
        return fallback

    title = clean_text(
        idea.get(
            "title"
        )
    )

    logline = clean_text(
        idea.get(
            "logline"
        )
    )

    concept = clean_text(
        idea.get(
            "concept"
        )
    )

    if not title or not logline:

        return fallback

    if is_silly_or_generic(
        title
    ):

        return fallback

    score = idea.get(
        "editorial_score",
        {}
    )

    if not isinstance(
        score,
        dict
    ):
        score = {}

    scores = {}

    for key in [
        "curiosity",
        "story",
        "visual",
        "payoff",
        "overall",
    ]:

        value = safe_int(
            score.get(
                key,
                9
            ),
            9
        )

        value = max(
            1,
            min(
                10,
                value
            )
        )

        scores[
            key
        ] = value

    return {

        "title":
            title,

        "logline":
            logline,

        "concept":
            concept,

        "format":
            clean_text(
                idea.get(
                    "format"
                )
            ),

        "source_inspiration":
            clean_text(
                idea.get(
                    "source_inspiration"
                )
            ),

        "editorial_score":
            scores,
    }


def validate_ai_output(
    ai_data,
    local_data
):

    final = {}

    sections = [
        "trend_shorts",
        "trend_long",
        "general_shorts",
        "general_long",
        "genre_combo",
    ]

    for section in sections:

        final[
            section
        ] = []

        ai_items = ai_data.get(
            section,
            []
        )

        if not isinstance(
            ai_items,
            list
        ):
            ai_items = []

        for index in range(
            IDEAS_PER_SECTION
        ):

            fallback = local_data[
                section
            ][index]

            item = (
                ai_items[index]
                if index < len(
                    ai_items
                )
                else None
            )

            final[
                section
            ].append(
                clean_idea(
                    item,
                    fallback
                )
            )

    # High CTR
    high_ctr = ai_data.get(
        "high_ctr"
    )

    if not isinstance(
        high_ctr,
        dict
    ):
        high_ctr = {}

    high_title = clean_text(
        high_ctr.get(
            "title"
        )
    )

    high_logline = clean_text(
        high_ctr.get(
            "logline"
        )
    )

    high_concept = clean_text(
        high_ctr.get(
            "concept"
        )
    )

    if (
        not high_title
        or not high_logline
        or is_silly_or_generic(
            high_title
        )
    ):

        # Use the strongest trend long idea
        fallback = final[
            "trend_long"
        ][0]

        high_ctr = {

            "title":
                fallback["title"],

            "logline":
                fallback["logline"],

            "concept":
                fallback["concept"],

            "why_it_works":
                "Strong curiosity gap, "
                "clear story engine, "
                "escalation and payoff.",

            "editorial_score":
                9.2,
        }

    else:

        high_ctr = {

            "title":
                high_title,

            "logline":
                high_logline,

            "concept":
                high_concept,

            "why_it_works":
                clean_text(
                    high_ctr.get(
                        "why_it_works"
                    )
                ),

            "editorial_score":
                high_ctr.get(
                    "editorial_score",
                    9.2
                ),
        }

    final[
        "high_ctr"
    ] = high_ctr

    return final


# ============================================================
# IDEA MARKDOWN
# ============================================================

def render_ideas(
    ideas
):

    lines = []

    for index, idea in enumerate(
        ideas,
        start=1
    ):

        score = idea.get(
            "editorial_score",
            {}
        )

        overall = score.get(
            "overall",
            9
        )

        lines.append(
            f"### {index}. "
            f"{idea['title']}"
        )

        lines.append("")

        lines.append(
            "**Roman Telugu Logline:** "
            + idea["logline"]
        )

        lines.append("")

        lines.append(
            "**Concept:** "
            + idea["concept"]
        )

        lines.append("")

        if idea.get(
            "source_inspiration"
        ):

            source = idea[
                "source_inspiration"
            ]

            if source != (
                "Original concept"
            ):

                lines.append(
                    "**Trend inspiration:** "
                    + source
                )

                lines.append("")

        lines.append(
            "**Editorial score:** "
            f"{overall}/10"
        )

        lines.append("")

    return "\n".join(
        lines
    )


# ============================================================
# FULL REPORT
# ============================================================

def build_report(
    videos,
    ideas,
    errors
):

    india = india_videos(
        videos
    )

    world = world_videos(
        videos
    )

    india_shorts = shorts_videos(
        india
    )

    india_long = longform_videos(
        india
    )

    world_shorts = shorts_videos(
        world
    )

    world_long = longform_videos(
        world
    )

    lines = []

    # ========================================================
    # TOP HIGH CTR IDEA
    # ========================================================

    high = ideas[
        "high_ctr"
    ]

    lines.append(
        "# YOUTUBE HIGH CTR IDEA GENERATOR"
    )

    lines.append("")

    lines.append(
        "# HIGH CTR IDEA"
    )

    lines.append("")

    lines.append(
        f"## {high['title']}"
    )

    lines.append("")

    lines.append(
        "**Roman Telugu Logline:** "
        + high["logline"]
    )

    lines.append("")

    lines.append(
        "**Concept:** "
        + high["concept"]
    )

    lines.append("")

    lines.append(
        "**Why this can work:** "
        + high["why_it_works"]
    )

    lines.append("")

    lines.append(
        "**Editorial score:** "
        f"{high['editorial_score']}/10"
    )

    lines.append("")

    lines.append(
        "---"
    )

    lines.append("")

    # ========================================================
    # 1 INDIA
    # ========================================================

    lines.append(
        "# 1. INDIA YOUTUBE TRENDS"
    )

    lines.append("")

    lines.append(
        "## Shorts — Which videos are driving the pattern?"
    )

    lines.append("")

    lines.append(
        render_source_videos(
            india_shorts
        )
    )

    lines.append("")

    lines.append(
        "## Long-form 8–10 minutes — Which videos are driving the pattern?"
    )

    lines.append("")

    lines.append(
        render_source_videos(
            india_long
        )
    )

    lines.append("")

    # ========================================================
    # 2 WORLD
    # ========================================================

    lines.append(
        "# 2. WORLD YOUTUBE TRENDS"
    )

    lines.append("")

    lines.append(
        "## Shorts — Which videos are driving the pattern?"
    )

    lines.append("")

    lines.append(
        render_source_videos(
            world_shorts
        )
    )

    lines.append("")

    lines.append(
        "## Long-form 8–10 minutes — Which videos are driving the pattern?"
    )

    lines.append("")

    lines.append(
        render_source_videos(
            world_long
        )
    )

    lines.append("")

    # ========================================================
    # 3 GENRE
    # ========================================================

    lines.append(
        "# 3. YOUTUBE GENRE TRENDS"
    )

    lines.append("")

    lines.append(
        "## Shorts Genre Trends"
    )

    lines.append("")

    render_genre_section(
        lines,
        shorts_videos(
            videos
        )
    )

    lines.append(
        "## Long-form 8–10 min Genre Trends"
    )

    lines.append("")

    render_genre_section(
        lines,
        longform_videos(
            videos
        )
    )

    # ========================================================
    # 4 TREND SHORTS
    # ========================================================

    lines.append(
        "# 4. INDIA/WORLD TREND-BASED SHORTS IDEAS"
    )

    lines.append("")

    lines.append(
        "These ideas are inspired by current "
        "India/World YouTube patterns, "
        "but are ORIGINAL concepts."
    )

    lines.append("")

    lines.append(
        render_ideas(
            ideas[
                "trend_shorts"
            ]
        )
    )

    # ========================================================
    # 5 TREND LONG
    # ========================================================

    lines.append(
        "# 5. INDIA/WORLD TREND-BASED LONG-FORM IDEAS"
    )

    lines.append("")

    lines.append(
        "Target duration: 8–10 minutes."
    )

    lines.append("")

    lines.append(
        render_ideas(
            ideas[
                "trend_long"
            ]
        )
    )

    # ========================================================
    # 6 GENERAL SHORTS
    # ========================================================

    lines.append(
        "# 6. INDIA/WORLD GENERAL SHORTS IDEAS"
    )

    lines.append("")

    lines.append(
        "These are NOT based on current YouTube trends."
    )

    lines.append("")

    lines.append(
        render_ideas(
            ideas[
                "general_shorts"
            ]
        )
    )

    # ========================================================
    # 7 GENERAL LONG
    # ========================================================

    lines.append(
        "# 7. INDIA/WORLD GENERAL LONG-FORM IDEAS"
    )

    lines.append("")

    lines.append(
        "These are NOT based on current YouTube trends."
    )

    lines.append("")

    lines.append(
        "Target duration: 8–10 minutes."
    )

    lines.append("")

    lines.append(
        render_ideas(
            ideas[
                "general_long"
            ]
        )
    )

    # ========================================================
    # 8 GENRE COMBINATIONS
    # ========================================================

    lines.append(
        "# 8. GENRE-COMBINATION HIGH CTR IDEAS"
    )

    lines.append("")

    lines.append(
        "These concepts combine genre/subgenre "
        "patterns such as Thriller + Mystery, "
        "Comedy + Mystery, Crime + Technology, "
        "Drama + Investigation, etc."
    )

    lines.append("")

    lines.append(
        render_ideas(
            ideas[
                "genre_combo"
            ]
        )
    )

    # ========================================================
    # DATA NOTES
    # ========================================================

    lines.append(
        "# DATA NOTES"
    )

    lines.append("")

    lines.append(
        f"- Total videos collected: "
        f"{len(videos)}"
    )

    lines.append(
        f"- India videos: "
        f"{len(india)}"
    )

    lines.append(
        f"- World videos: "
        f"{len(world)}"
    )

    lines.append(
        f"- India Shorts: "
        f"{len(india_shorts)}"
    )

    lines.append(
        f"- India 8–10 min: "
        f"{len(india_long)}"
    )

    lines.append(
        f"- World Shorts: "
        f"{len(world_shorts)}"
    )

    lines.append(
        f"- World 8–10 min: "
        f"{len(world_long)}"
    )

    lines.append("")

    if errors:

        lines.append(
            "## YouTube collection warnings"
        )

        lines.append("")

        for error in errors:

            lines.append(
                "- " + error
            )

        lines.append("")

    lines.append(
        "NOTE: Editorial scores are creative "
        "estimates, not actual CTR predictions."
    )

    return "\n".join(
        lines
    )


def render_genre_section(
    lines,
    videos
):

    groups = sorted_genre_analysis(
        videos
    )

    if not groups:

        lines.append(
            "No genre data available."
        )

        lines.append("")

        return

    for group in groups:

        genre = group[
            "genre"
        ]

        lines.append(
            f"### {genre}"
        )

        lines.append(
            f"- Videos: "
            f"{group['count']}"
        )

        lines.append(
            f"- Combined views: "
            f"{format_views(group['views'])}"
        )

        lines.append("")

        sorted_subgenres = sorted(
            group[
                "subgenres"
            ].items(),
            key=lambda item: (
                len(item[1]),
                sum(
                    v["views"]
                    for v in item[1]
                )
            ),
            reverse=True
        )

        for subgenre, items in (
            sorted_subgenres[:6]
        ):

            lines.append(
                f"#### "
                f"{genre} → "
                f"{subgenre}"
            )

            lines.append(
                f"- Videos: "
                f"{len(items)}"
            )

            lines.append(
                f"- Combined views: "
                f"{format_views(sum(v['views'] for v in items))}"
            )

            lines.append(
                "- Actual supporting videos:"
            )

            for video in rank_videos(
                items,
                3
            ):

                lines.append(
                    f"  - **{video['title']}** "
                    f"— {video['channel']} "
                    f"— {format_views(video['views'])} views "
                    f"— {video['url']}"
                )

            lines.append("")


# ============================================================
# PDF
# ============================================================

def create_pdf(
    markdown,
    pdf_path
):

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Title"],
        alignment=TA_CENTER,
        fontSize=19,
        leading=23,
        spaceAfter=12
    )

    h1 = ParagraphStyle(
        "CustomH1",
        parent=styles["Heading1"],
        fontSize=16,
        leading=20,
        spaceBefore=12,
        spaceAfter=7
    )

    h2 = ParagraphStyle(
        "CustomH2",
        parent=styles["Heading2"],
        fontSize=13,
        leading=17,
        spaceBefore=9,
        spaceAfter=5
    )

    h3 = ParagraphStyle(
        "CustomH3",
        parent=styles["Heading3"],
        fontSize=10.5,
        leading=14,
        spaceBefore=7,
        spaceAfter=4
    )

    body = ParagraphStyle(
        "CustomBody",
        parent=styles["BodyText"],
        fontSize=8.5,
        leading=11.5,
        spaceAfter=4
    )

    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        rightMargin=13 * mm,
        leftMargin=13 * mm,
        topMargin=13 * mm,
        bottomMargin=13 * mm
    )

    story = []

    for raw in markdown.splitlines():

        line = raw.strip()

        if not line:

            story.append(
                Spacer(
                    1,
                    3
                )
            )

            continue

        safe = (
            line
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
        )

        safe = re.sub(
            r"\*\*(.+?)\*\*",
            r"<b>\1</b>",
            safe
        )

        if line.startswith(
            "# "
        ):

            story.append(
                Paragraph(
                    safe[2:],
                    title_style
                )
            )

        elif line.startswith(
            "## "
        ):

            story.append(
                Paragraph(
                    safe[3:],
                    h1
                )
            )

        elif line.startswith(
            "### "
        ):

            story.append(
                Paragraph(
                    safe[4:],
                    h2
                )
            )

        elif line.startswith(
            "#### "
        ):

            story.append(
                Paragraph(
                    safe[5:],
                    h3
                )
            )

        elif line.startswith(
            "- "
        ):

            story.append(
                Paragraph(
                    "• "
                    + safe[2:],
                    body
                )
            )

        else:

            story.append(
                Paragraph(
                    safe,
                    body
                )
            )

    doc.build(
        story
    )


# ============================================================
# JSON
# ============================================================

def save_json(
    videos,
    ideas,
    errors,
    path
):

    payload = {

        "generated_at":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "video_count":
            len(videos),

        "collection_errors":
            errors,

        "videos":
            videos,

        "ideas":
            ideas,
    }

    path.write_text(
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False
        ),
        encoding="utf-8"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)

    print(
        "YOUTUBE HIGH CTR IDEA GENERATOR"
    )

    print("=" * 70)

    print(
        "Starting..."
    )

    # --------------------------------------------------------
    # 1. YOUTUBE
    # --------------------------------------------------------

    print()
    print(
        "[1/5] Collecting YouTube data..."
    )

    videos, errors = (
        collect_youtube_data()
    )

    if not videos:

        print(
            "[FATAL] "
            "No YouTube videos collected."
        )

        return 1

    print(
        f"Collected {len(videos)} "
        "unique videos."
    )

    # --------------------------------------------------------
    # 2. LOCAL IDEAS
    # --------------------------------------------------------

    print()
    print(
        "[2/5] Building local creative fallback..."
    )

    local_ideas = (
        build_local_ideas()
    )

    # --------------------------------------------------------
    # 3. OPENROUTER
    # --------------------------------------------------------

    print()
    print(
        "[3/5] Generating premium ideas..."
    )

    ai_data = (
        generate_ai_ideas(
            videos
        )
    )

    if ai_data:

        ideas = validate_ai_output(
            ai_data,
            local_ideas
        )

        mode = (
            "OpenRouter + validation"
        )

    else:

        ideas = local_ideas

        # Local high CTR idea
        ideas[
            "high_ctr"
        ] = {

            "title":
                "The One Detail That Changes the Entire Story",

            "logline":
                "Andaru normal incident ani anukunna oka small detail ni protagonist serious ga investigate chestadu; aa detail follow chestu vellaga story motham completely different meaning pondutundi.",

            "concept":
                "Start with a visual clue that looks insignificant. Turn it into an investigation with escalating discoveries and finish with a reveal that makes the audience rethink the opening.",

            "why_it_works":
                "Strong curiosity gap, clear investigation engine, visual clues, escalation and a payoff that recontextualizes the opening.",

            "editorial_score":
                9.2
        }

        mode = (
            "Local deterministic fallback"
        )

    print(
        f"Generation mode: {mode}"
    )

    # --------------------------------------------------------
    # 4. REPORT
    # --------------------------------------------------------

    print()
    print(
        "[4/5] Creating report..."
    )

    markdown = build_report(
        videos,
        ideas,
        errors
    )

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    md_path = (
        OUTPUT_DIR
        / f"youtube_ideas_{timestamp}.md"
    )

    json_path = (
        OUTPUT_DIR
        / f"youtube_ideas_{timestamp}.json"
    )

    pdf_path = (
        OUTPUT_DIR
        / f"youtube_ideas_{timestamp}.pdf"
    )

    md_path.write_text(
        markdown,
        encoding="utf-8"
    )

    save_json(
        videos,
        ideas,
        errors,
        json_path
    )

    create_pdf(
        markdown,
        pdf_path
    )

    # --------------------------------------------------------
    # 5. FINISH
    # --------------------------------------------------------

    print()
    print(
        "[5/5] Finished."
    )

    print()
    print("=" * 70)

    print(
        "SUCCESS"
    )

    print("=" * 70)

    print(
        f"Markdown: {md_path}"
    )

    print(
        f"JSON:     {json_path}"
    )

    print(
        f"PDF:      {pdf_path}"
    )

    print("=" * 70)

    return 0


if __name__ == "__main__":

    raise SystemExit(
        main()
    )
````
