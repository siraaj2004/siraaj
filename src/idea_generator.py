from __future__ import annotations

import json
import math
import os
import re
import statistics
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import requests
from dotenv import load_dotenv

load_dotenv()


# ============================================================
# CONFIG
# ============================================================

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "").strip()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "z-ai/glm-5.3-flash").strip()
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "output"))
WORLD_COUNTRIES = [x.strip().upper() for x in os.getenv(
    "WORLD_COUNTRIES", "US,GB,CA,AU,DE,FR,JP,KR,BR,MX"
).split(",") if x.strip()]

YOUTUBE_BASE = "https://www.googleapis.com/youtube/v3"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
TIMEOUT = 30
MAX_VIDEOS_PER_REGION = 50
MAX_TREND_VIDEOS_IN_REPORT = 10

# YouTube category IDs commonly used by the API.
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
# DATA MODEL
# ============================================================

@dataclass
class Video:
    video_id: str
    title: str
    channel: str
    channel_id: str
    views: int
    likes: int
    comments: int
    duration_seconds: int
    published_at: str
    category_id: str
    category: str
    region: str
    url: str

    @property
    def is_short(self) -> bool:
        return 0 < self.duration_seconds <= 180

    @property
    def is_long_8_10(self) -> bool:
        return 480 <= self.duration_seconds <= 600

    @property
    def format_name(self) -> str:
        if self.is_short:
            return "Shorts"
        if self.is_long_8_10:
            return "Long-form (8–10 min)"
        return "Other long-form"

    @property
    def duration_text(self) -> str:
        s = self.duration_seconds
        if s < 60:
            return f"{s}s"
        return f"{s // 60}:{s % 60:02d}"

    @property
    def views_text(self) -> str:
        return compact_number(self.views)


# ============================================================
# BASIC HELPERS
# ============================================================

def compact_number(n: int | float) -> str:
    n = float(n)
    if n >= 1_000_000_000:
        return f"{n / 1_000_000_000:.1f}B"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(int(n))


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()


def parse_iso_duration(value: str) -> int:
    m = re.fullmatch(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", value or "")
    if not m:
        return 0
    h, mi, s = (int(x or 0) for x in m.groups())
    return h * 3600 + mi * 60 + s


def safe_int(value: Any) -> int:
    try:
        return int(value or 0)
    except Exception:
        return 0


def parse_dt(value: str) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


def age_days(published_at: str) -> float:
    dt = parse_dt(published_at)
    if not dt:
        return 30.0
    return max(0.25, (datetime.now(timezone.utc) - dt).total_seconds() / 86400)


def title_words(title: str) -> List[str]:
    words = re.findall(r"[A-Za-z0-9']+", title.lower())
    stop = {
        "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "with",
        "is", "this", "that", "from", "by", "at", "it", "my", "your", "you",
        "i", "we", "our", "me", "vs", "part", "full", "official", "video",
        "shorts", "short", "new", "latest", "live", "hd", "4k", "episode",
    }
    return [w for w in words if len(w) > 2 and w not in stop and not w.isdigit()]


def safe_mean(values: Iterable[float]) -> float:
    vals = list(values)
    return statistics.mean(vals) if vals else 0.0


def dedupe_videos(videos: List[Video]) -> List[Video]:
    seen = set()
    out = []
    for v in videos:
        if v.video_id in seen:
            continue
        seen.add(v.video_id)
        out.append(v)
    return out


# ============================================================
# YOUTUBE API
# ============================================================

def youtube_get(endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
    if not YOUTUBE_API_KEY:
        raise RuntimeError("YOUTUBE_API_KEY is missing")
    p = dict(params)
    p["key"] = YOUTUBE_API_KEY
    r = requests.get(f"{YOUTUBE_BASE}/{endpoint}", params=p, timeout=TIMEOUT)
    if r.status_code != 200:
        raise RuntimeError(f"YouTube API {r.status_code}: {r.text[:500]}")
    return r.json()


def fetch_region(region: str, max_results: int = MAX_VIDEOS_PER_REGION) -> List[Video]:
    data = youtube_get(
        "videos",
        {
            "part": "snippet,statistics,contentDetails",
            "chart": "mostPopular",
            "regionCode": region,
            "maxResults": max_results,
        },
    )
    out: List[Video] = []
    for item in data.get("items", []):
        snippet = item.get("snippet", {})
        stats = item.get("statistics", {})
        details = item.get("contentDetails", {})
        vid = item.get("id", "")
        if not vid:
            continue
        cat_id = str(snippet.get("categoryId", ""))
        out.append(Video(
            video_id=vid,
            title=clean_text(snippet.get("title", "Untitled")),
            channel=clean_text(snippet.get("channelTitle", "Unknown channel")),
            channel_id=snippet.get("channelId", ""),
            views=safe_int(stats.get("viewCount")),
            likes=safe_int(stats.get("likeCount")),
            comments=safe_int(stats.get("commentCount")),
            duration_seconds=parse_iso_duration(details.get("duration", "")),
            published_at=snippet.get("publishedAt", ""),
            category_id=cat_id,
            category=CATEGORY_NAMES.get(cat_id, "Other"),
            region=region,
            url=f"https://www.youtube.com/watch?v={vid}",
        ))
    return out


def collect_data() -> Tuple[List[Video], List[Video], Dict[str, str]]:
    errors: Dict[str, str] = {}
    india: List[Video] = []
    world: List[Video] = []

    try:
        india = fetch_region("IN")
    except Exception as exc:
        errors["IN"] = str(exc)

    for country in WORLD_COUNTRIES:
        try:
            world.extend(fetch_region(country))
        except Exception as exc:
            errors[country] = str(exc)

    world = dedupe_videos(world)
    return india, world, errors


# ============================================================
# GENRE / SUBGENRE CLASSIFICATION
# ============================================================

GENRE_RULES: List[Tuple[str, str, List[str]]] = [
    ("Entertainment", "Thriller", ["thriller", "mystery", "killer", "crime", "murder", "suspense", "investigation", "case"]),
    ("Entertainment", "Comedy", ["comedy", "funny", "roast", "prank", "joke", "comedy", "standup"]),
    ("Entertainment", "Reaction", ["reaction", "reacts", "reacting", "first time watching"]),
    ("Entertainment", "Reality / Challenge", ["challenge", "survive", "24 hours", "last to", "competition"]),
    ("Entertainment", "Storytelling / Drama", ["story", "drama", "film", "movie", "short film", "episode"]),
    ("Entertainment", "Celebrity / Pop Culture", ["celebrity", "actor", "actress", "star", "interview", "bollywood", "tollywood"]),
    ("Music", "Song / Performance", ["song", "music", "lyric", "concert", "performance", "cover", "singer"]),
    ("Music", "Trailer / OST", ["trailer", "teaser", "ost", "audio", "theme"]),
    ("Gaming", "Gameplay", ["gameplay", "gaming", "minecraft", "gta", "valorant", "free fire", "bgmi", "fortnite"]),
    ("Gaming", "Story / Lore", ["lore", "ending", "story explained", "secret ending"]),
    ("News", "Current Affairs", ["news", "breaking", "update", "politics", "election"]),
    ("Education", "Explainer", ["explained", "how", "tutorial", "learn", "guide", "education"]),
    ("Science & Technology", "AI / Tech", ["ai", "artificial intelligence", "chatgpt", "tech", "iphone", "android", "robot"]),
    ("Sports", "Match / Highlights", ["match", "highlights", "cricket", "football", "goal", "ipl", "world cup"]),
    ("Lifestyle", "Food / Travel", ["food", "restaurant", "street food", "travel", "vlog", "hotel"]),
]


def infer_genre(video: Video) -> Tuple[str, str]:
    text = video.title.lower()
    # Category-first mapping, then title keywords.
    if video.category == "Music":
        if any(k in text for k in ["trailer", "teaser", "ost", "audio"]):
            return "Music", "Trailer / OST"
        return "Music", "Song / Performance"
    if video.category == "Gaming":
        if any(k in text for k in ["lore", "ending", "explained", "secret"]):
            return "Gaming", "Story / Lore"
        return "Gaming", "Gameplay"
    if video.category == "Comedy":
        return "Entertainment", "Comedy"
    if video.category == "Sports":
        return "Sports", "Match / Highlights"
    if video.category in {"Education", "Science & Technology"}:
        return ("Science & Technology", "AI / Tech") if video.category == "Science & Technology" else ("Education", "Explainer")
    if video.category == "News & Politics":
        return "News", "Current Affairs"

    for genre, subgenre, keywords in GENRE_RULES:
        if any(k in text for k in keywords):
            return genre, subgenre
    return "Entertainment", "General Entertainment"


# ============================================================
# TREND ANALYSIS
# ============================================================

def velocity_score(video: Video) -> float:
    # Approximate view velocity. It is an editorial signal, not an official YouTube metric.
    return video.views / max(age_days(video.published_at), 0.5)


def popularity_score(video: Video) -> float:
    return math.log10(max(video.views, 1)) * 10 + math.log10(max(velocity_score(video), 1)) * 6


def select_format(videos: List[Video], fmt: str) -> List[Video]:
    if fmt == "shorts":
        return [v for v in videos if v.is_short]
    if fmt == "long_8_10":
        return [v for v in videos if v.is_long_8_10]
    return videos


def top_videos(videos: List[Video], fmt: str, n: int = MAX_TREND_VIDEOS_IN_REPORT) -> List[Video]:
    subset = select_format(videos, fmt)
    return sorted(subset, key=popularity_score, reverse=True)[:n]


def trend_clusters(videos: List[Video], fmt: str, n: int = 8) -> List[Dict[str, Any]]:
    subset = select_format(videos, fmt)
    groups: Dict[Tuple[str, str], List[Video]] = defaultdict(list)
    for v in subset:
        genre, subgenre = infer_genre(v)
        groups[(genre, subgenre)].append(v)

    rows = []
    total_views = sum(v.views for v in subset) or 1
    for (genre, subgenre), items in groups.items():
        if len(items) < 1:
            continue
        items = sorted(items, key=popularity_score, reverse=True)
        views = sum(v.views for v in items)
        velocity = safe_mean(velocity_score(v) for v in items)
        score = (len(items) * 2.0) + math.log10(max(views, 1)) + math.log10(max(velocity, 1))
        rows.append({
            "genre": genre,
            "subgenre": subgenre,
            "count": len(items),
            "combined_views": views,
            "share": views / total_views,
            "velocity": velocity,
            "score": score,
            "videos": items[:5],
        })
    return sorted(rows, key=lambda x: x["score"], reverse=True)[:n]


def phrase_trends(videos: List[Video], fmt: str, n: int = 8) -> List[Dict[str, Any]]:
    subset = select_format(videos, fmt)
    if not subset:
        return []
    counter = Counter()
    for v in subset:
        counter.update(title_words(v.title))
    rows = []
    for word, count in counter.most_common(40):
        if count < 2:
            continue
        matches = [v for v in subset if re.search(rf"\b{re.escape(word)}\b", v.title.lower())]
        views = sum(v.views for v in matches)
        rows.append({"term": word, "count": count, "views": views, "videos": sorted(matches, key=lambda x: x.views, reverse=True)[:4]})
    return sorted(rows, key=lambda x: (x["count"], x["views"]), reverse=True)[:n]


def why_trending(videos: List[Video], fmt: str, genre: str, subgenre: str) -> str:
    subset = [v for v in videos if infer_genre(v) == (genre, subgenre) and ((fmt == "shorts" and v.is_short) or (fmt == "long_8_10" and v.is_long_8_10))]
    if not subset:
        return "Not enough matching videos to make a reliable explanation."
    avg_age = safe_mean(age_days(v.published_at) for v in subset)
    avg_views = safe_mean(v.views for v in subset)
    recent = sum(1 for v in subset if age_days(v.published_at) <= 3)
    velocities = [velocity_score(v) for v in subset]
    med_velocity = statistics.median(velocities) if velocities else 0

    reasons = []
    if recent / len(subset) >= 0.4:
        reasons.append("many high-performing examples are very recent")
    if med_velocity > 100_000:
        reasons.append("view velocity is strong relative to the age of the videos")
    if len(subset) >= 4:
        reasons.append("the format is appearing repeatedly across multiple channels")
    if genre == "Entertainment" and subgenre == "Thriller":
        reasons.append("mystery, stakes and reveal-driven packaging create a strong curiosity gap")
    elif genre == "Entertainment" and subgenre == "Comedy":
        reasons.append("fast emotional payoff and highly shareable moments fit short attention cycles")
    elif genre == "Music":
        reasons.append("new releases, teasers and performances naturally create repeat viewing and discussion")
    elif genre == "Gaming":
        reasons.append("game updates, gameplay moments and lore create strong community participation")
    elif genre == "News":
        reasons.append("freshness and information urgency make viewers check the topic quickly")
    else:
        reasons.append("the topic combines audience familiarity with a clear reason to click now")
    return "; ".join(reasons).capitalize() + "."


# ============================================================
# CREATIVE IDEA ENGINE
# ============================================================

ROMAN_TELUGU_PATTERNS = [
    "Ee story lo audience ki first nunchi oka doubt untundi: {question}. Kani ending varaku answer reveal avvadu; clues tho tension perigipothundi.",
    "Manam normal ga chuse {topic} venaka oka unexpected human story ni follow chestam. Prathi stage lo stakes periguthu, last lo meaning complete ga maaripothundi.",
    "Oka simple decision tho start ayye ee story, {escalation} varaku vellipothundi. Audience ki final reveal mundu varaku next step guess cheyyadam kashtam.",
    "Ee idea lo hook matrame kaadu, complete story engine untundi: {question}. Clues, conflict mariyu final reversal kalisi strong payoff istayi.",
]

# Deliberately avoids weak generic challenge/reaction formats.
STRONG_SHORTS = [
    ("The 60-Second Mystery", "Oka public place lo camera capture chesina 3 tiny clues ni connect chesi, 60 seconds lo hidden story ni audience tho solve cheyyadam.", "Ee video lo 3 clues kanipistayi kani real meaning last seconds varaku teliyadu. Audience comments lo theory build chestaru."),
    ("The Last Message", "Oka person delete cheyyaboye phone lo dorikina final voice note ni story ga reconstruct cheyyadam.", "Oka voice note venaka em jarigindo clues dwara reveal chestam; final line entire story meaning ni reverse chestundi."),
    ("Before / After: One Decision", "Oka ordinary decision ki two possible futures ni parallel visual storytelling tho chupinchadam.", "Oka chinna decision life ni ela completely marchestundo two timelines lo compare chestam; ending lo original choice reveal avvutundi."),
    ("The Object That Knows", "Old object/photo/receipt ni follow chestu, adi evaru use chesaro clues tho discover cheyyadam.", "Audience ki object first mystery laga untundi; final owner story emotional ga connect avvutundi."),
]

STRONG_LONG = [
    ("The 8-Minute Investigation", "Oka ordinary-looking incident ni clues, timeline mariyu contradictions tho investigate chesi final explanation reach avvadam.", "First 2 minutes lo question establish chestam; middle lo clues contradict avutayi; final lo simple-looking detail entire case ni solve chestundi."),
    ("One Night, Three Versions", "Oka incident ni three different people's perspective lo reconstruct chesi, last lo fourth truth reveal cheyyadam.", "Same night ki three stories untayi. Prathi version believable ga untundi; final evidence valla audience mundu assumptions anni reverse avutayi."),
    ("The Hidden Pattern", "Publicly available ordinary events/data/images lo repeated pattern ni investigate chesi, adi enduku repeat avutundo story-driven ga discover cheyyadam.", "Pattern first coincidence laga kanipistundi. Evidence perigina koddi mystery deep avutundi; payoff lo pattern ki human reason dorukutundi."),
    ("The Choice With a Cost", "Oka real-world decision ni follow chestu, immediate benefit mariyu long-term consequence rendu sides ni cinematic ga explore cheyyadam.", "First half lo decision correct anipistundi; second half lo hidden cost reveal avutundi; ending audience ni moral question tho vadilestundi."),
]

GENERAL_SHORT = [
    ("The Unanswered Question", "Daily life lo everyone ignore chese oka simple question ki visual investigation cheyyadam.", "Question simple ga untundi kani answer kosam unexpected places/persons ni follow chestam; payoff practical ga untundi."),
    ("A Story Hidden in Plain Sight", "Normal-looking location/object/person routine lo hidden narrative ni clues tho uncover cheyyadam.", "Audience first frame nunchi clues observe chestundi; final reveal mundu shots ki new meaning istundi."),
    ("One Rule, One Consequence", "Real life lo oka useful rule ni test cheyyadam kaadu; aa rule follow cheyyakapothe exact ga em consequence vastundo story ga chupinchadam.", "Concept practical + emotional ga untundi; final consequence audience expectation ni challenge chestundi."),
]

GENERAL_LONG = [
    ("The Story Behind an Ordinary Thing", "Manam rojoo use chese ordinary object/service/location venaka unna surprising chain of people and decisions ni investigate cheyyadam.", "Familiar object tho hook create chesi, origin nunchi present varaku hidden chain ni reveal chestam; final human consequence strongest payoff."),
    ("What Really Happens Between A and B", "Audience ki familiar process lo visible beginning/end madhya jarige invisible steps ni cinematic investigation ga explain cheyyadam.", "Known process ni fresh mystery laga present chestam; each hidden step stakes ni penchutundi."),
    ("The Day Everything Almost Changed", "Oka real-world event/decision almost different outcome ki vellina timeline ni evidence and storytelling tho reconstruct cheyyadam.", "Audience already knows the outcome, but story asks how close reality came to changing; tension comes from near-misses."),
]


def source_signals(videos: List[Video], fmt: str, limit: int = 8) -> List[Dict[str, Any]]:
    rows = []
    for v in top_videos(videos, fmt, limit):
        g, sg = infer_genre(v)
        rows.append({
            "title": v.title,
            "channel": v.channel,
            "views": v.views,
            "duration": v.duration_text,
            "genre": g,
            "subgenre": sg,
            "url": v.url,
        })
    return rows


def make_trend_ideas(region_name: str, videos: List[Video], fmt: str, count: int = 6) -> List[Dict[str, Any]]:
    clusters = trend_clusters(videos, fmt, 6)
    ideas = []
    library = STRONG_SHORTS if fmt == "shorts" else STRONG_LONG
    for i in range(count):
        genre = clusters[i % len(clusters)] if clusters else {"genre": "Entertainment", "subgenre": "Thriller"}
        base = library[i % len(library)]
        title, concept, logline_seed = base
        trend_name = f"{genre['genre']} → {genre['subgenre']}"
        if i % 2 == 0:
            idea_title = f"{trend_name}: {title} — The Clue They Missed"
        else:
            idea_title = f"{title}: {trend_name} With a Real Mystery"
        question = f"{trend_name.lower()} pattern lo audience miss ayye real clue enti?"
        roman = ROMAN_TELUGU_PATTERNS[i % len(ROMAN_TELUGU_PATTERNS)].format(
            question=question,
            topic=trend_name.lower(),
            escalation="simple clue nunchi complete mystery varaku",
        )
        ideas.append({
            "title": idea_title,
            "format": "Shorts" if fmt == "shorts" else "Long-form (8–10 min)",
            "region": region_name,
            "concept": concept,
            "why_click": f"Uses the current {trend_name} pattern without copying any source title; built around a curiosity gap and a clear payoff.",
            "roman_telugu_logline": roman,
            "trend_basis": trend_name,
            "editorial_ctr": 91 - i,
            "source_titles": [v.title for v in genre.get("videos", [])[:3]] if "videos" in genre else [],
        })
    return ideas


def make_general_ideas(region_name: str, fmt: str, count: int = 5) -> List[Dict[str, Any]]:
    library = GENERAL_SHORT if fmt == "shorts" else GENERAL_LONG
    ideas = []
    for i in range(count):
        title, concept, seed = library[i % len(library)]
        roman = ROMAN_TELUGU_PATTERNS[(i + 1) % len(ROMAN_TELUGU_PATTERNS)].format(
            question="manam ignore chese simple detail venaka real story enti",
            topic="ordinary-looking situation",
            escalation="small observation nunchi bigger discovery varaku",
        )
        ideas.append({
            "title": f"{title} — {region_name} Edition",
            "format": "Shorts" if fmt == "shorts" else "Long-form (8–10 min)",
            "region": region_name,
            "concept": concept,
            "why_click": "Not based on current YouTube trend data; designed around curiosity, story progression, visual evidence and payoff.",
            "roman_telugu_logline": roman,
            "trend_basis": "General original concept — not trend-derived",
            "editorial_ctr": 88 - i,
        })
    return ideas


def make_genre_combo_ideas(india: List[Video], world: List[Video], count: int = 8) -> List[Dict[str, Any]]:
    clusters = trend_clusters(india + world, "shorts", 5) + trend_clusters(india + world, "long_8_10", 5)
    pairs = []
    for a in clusters:
        for b in clusters:
            if a is b:
                continue
            key = (a["genre"], a["subgenre"], b["genre"], b["subgenre"])
            if key not in pairs:
                pairs.append(key)
    ideas = []
    for i, p in enumerate(pairs[:count]):
        g1, s1, g2, s2 = p
        title = f"{s1} × {s2}: The Story Nobody Expects"
        concept = f"Combine the audience language of {g1} → {s1} with the narrative engine of {g2} → {s2}: start with a familiar hook, introduce a real mystery/conflict, then resolve it with a human or emotional payoff."
        roman = f"{s1} mariyu {s2} rendu kalipi, first frame nunchi oka strong question create chestam. Story progress ayye koddi rendu genres collide avvutayi, final reveal audience expectation ni reverse chestundi."
        ideas.append({
            "title": title,
            "format": "Shorts" if i % 2 == 0 else "Long-form (8–10 min)",
            "region": "India + World",
            "concept": concept,
            "why_click": f"The novelty comes from combining two different audience expectations: {s1} + {s2}.",
            "roman_telugu_logline": roman,
            "trend_basis": f"{g1} → {s1} + {g2} → {s2}",
            "editorial_ctr": 94 - i,
        })
    return ideas


# ============================================================
# OPTIONAL ONE-SHOT LLM ENHANCEMENT
# ============================================================

def call_openrouter_once(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not OPENROUTER_API_KEY:
        return None
    system = """
You are a senior YouTube creative strategist. Improve ideas, never make them silly.
Rules:
- Exactly use the requested structure.
- Do not copy source video titles.
- Avoid generic reaction videos, random challenges, 24-hour challenges, top-10 lists,
  empty clickbait, fake statistics, or vague 'secret nobody knows' concepts.
- Every idea needs a concrete story engine: curiosity gap + conflict/question + escalation + payoff.
- For entertainment, explicitly name subgenre such as Thriller, Comedy, Mystery, Crime,
  Reaction, Drama, Celebrity/Pop Culture, etc.
- Roman Telugu loglines must sound natural and cinematic, not translated word-for-word.
- CTR scores are editorial estimates only, never real predictions.
- Preserve actual source video titles in trend evidence.
Return valid JSON only. No markdown fences.
"""
    body = {
        "model": OPENROUTER_MODEL,
        "temperature": 0.65,
        "max_tokens": 9000,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ],
    }
    try:
        r = requests.post(
            OPENROUTER_URL,
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/",
                "X-Title": "YouTube High CTR Idea Generator",
            },
            json=body,
            timeout=60,
        )
        if r.status_code != 200:
            print(f"[WARN] OpenRouter unavailable ({r.status_code}). Using local engine.")
            return None
        data = r.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        if not content:
            return None
        content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content.strip(), flags=re.I)
        parsed = json.loads(content)
        return parsed if isinstance(parsed, dict) else None
    except Exception as exc:
        print(f"[WARN] OpenRouter failed once: {exc}. Using local engine.")
        return None


# ============================================================
# REPORT RENDERING
# ============================================================

def md_escape(text: str) -> str:
    return clean_text(str(text)).replace("|", "\\|")


def video_md(v: Video) -> str:
    g, sg = infer_genre(v)
    return (
        f"- **{md_escape(v.title)}**\n"
        f"  - Channel: {md_escape(v.channel)}\n"
        f"  - Views: {v.views_text}\n"
        f"  - Duration: {v.duration_text}\n"
        f"  - Genre: {g}\n"
        f"  - Subgenre: {sg}\n"
        f"  - Published: {v.published_at[:10] if v.published_at else 'Unknown'}\n"
        f"  - Source region: {v.region}\n"
        f"  - YouTube: {v.url}"
    )


def render_trend_section(title: str, videos: List[Video]) -> str:
    out = [f"# {title}", ""]
    for fmt, label in [("shorts", "## YouTube Shorts"), ("long_8_10", "## YouTube Long-form (8–10 min)")]:
        out += [label, ""]
        selected = top_videos(videos, fmt)
        if not selected:
            out += ["_No matching videos were returned for this exact format from the selected YouTube API data._", ""]
            continue
        clusters = trend_clusters(videos, fmt, 6)
        for c in clusters:
            out.append(f"### {c['genre']} → {c['subgenre']}")
            out.append(f"- Trend strength: {c['count']} matching videos; combined views {compact_number(c['combined_views'])}")
            out.append(f"- Why it is trending: {why_trending(videos, fmt, c['genre'], c['subgenre'])}")
            out.append("- Supporting actual videos:")
            for v in c["videos"][:4]:
                out.append(video_md(v))
            out.append("")
    return "\n".join(out)


def render_genre_section(india: List[Video], world: List[Video]) -> str:
    out = ["# 3. YOUTUBE GENRE TRENDS", "", "This section uses the same live video pool but groups it into broad genre + specific subgenre.", ""]
    for fmt, label in [("shorts", "## Shorts Genre Trends"), ("long_8_10", "## Long-form (8–10 min) Genre Trends")]:
        out += [label, ""]
        clusters = trend_clusters(india + world, fmt, 10)
        if not clusters:
            out += ["_No matching videos._", ""]
            continue
        for c in clusters:
            out.append(f"### {c['genre']} → {c['subgenre']}")
            out.append(f"- Videos: {c['count']} | Combined views: {compact_number(c['combined_views'])}")
            out.append(f"- Why trending: {why_trending(india + world, fmt, c['genre'], c['subgenre'])}")
            out.append("- Actual supporting titles:")
            for v in c["videos"][:5]:
                out.append(video_md(v))
            out.append("")
    return "\n".join(out)


def render_ideas(title: str, ideas: List[Dict[str, Any]]) -> str:
    out = [f"# {title}", ""]
    for i, idea in enumerate(ideas, 1):
        out += [
            f"## {i}. {idea['title']}",
            f"- Format: {idea['format']}",
            f"- Region: {idea['region']}",
            f"- Concept: {idea['concept']}",
            f"- Why this can earn the click: {idea['why_click']}",
            f"- Roman Telugu logline: **{idea['roman_telugu_logline']}**",
            f"- Trend/genre basis: {idea['trend_basis']}",
            f"- Editorial CTR potential: **{idea['editorial_ctr']}/100** (not a real CTR prediction)",
        ]
        if idea.get("source_titles"):
            out.append("- Inspiration evidence (do not copy): " + " | ".join(idea["source_titles"]))
        out.append("")
    return "\n".join(out)


def choose_high_ctr(all_ideas: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not all_ideas:
        return {
            "title": "The Hidden Clue",
            "roman_telugu_logline": "Oka simple clue ni follow chestu, audience expect cheyyani story ni reveal cheyyadam.",
            "editorial_ctr": 80,
        }
    return max(all_ideas, key=lambda x: x.get("editorial_ctr", 0))


def build_report(india: List[Video], world: List[Video], errors: Dict[str, str]) -> Tuple[str, Dict[str, Any]]:
    trend_ideas = (
        make_trend_ideas("India", india, "shorts")
        + make_trend_ideas("World", world, "shorts")
        + make_trend_ideas("India", india, "long_8_10")
        + make_trend_ideas("World", world, "long_8_10")
    )
    general_ideas = (
        make_general_ideas("India", "shorts")
        + make_general_ideas("World", "shorts")
        + make_general_ideas("India", "long_8_10")
        + make_general_ideas("World", "long_8_10")
    )
    combo_ideas = make_genre_combo_ideas(india, world)
    all_ideas = trend_ideas + general_ideas + combo_ideas
    top = choose_high_ctr(all_ideas)

    payload = {
        "task": "Improve YouTube idea report quality while preserving the 8 requested sections.",
        "top_candidate": top,
        "india_trend_evidence": {
            "shorts": source_signals(india, "shorts"),
            "long_8_10": source_signals(india, "long_8_10"),
        },
        "world_trend_evidence": {
            "shorts": source_signals(world, "shorts"),
            "long_8_10": source_signals(world, "long_8_10"),
        },
        "draft_ideas": all_ideas,
    }
    llm = call_openrouter_once(payload)
    if llm:
        # Only replace ideas if the model returns a usable list. Trend evidence remains local/real.
        candidate = llm.get("ideas") if isinstance(llm, dict) else None
        if isinstance(candidate, list) and candidate:
            all_ideas = candidate
            top = choose_high_ctr(all_ideas)
            print("[OK] OpenRouter enhancement applied once.")
    else:
        print("[OK] Local deterministic idea engine used.")

    sections = [
        "# HIGH CTR IDEA",
        "",
        f"## {top.get('title', 'The Hidden Clue')}",
        f"**Roman Telugu logline:** {top.get('roman_telugu_logline', '')}",
        f"**Editorial CTR potential:** {top.get('editorial_ctr', 0)}/100 — not a real CTR prediction.",
        "",
        render_trend_section("1. INDIA YOUTUBE TRENDS", india),
        render_trend_section("2. WORLD YOUTUBE TRENDS", world),
        render_genre_section(india, world),
        render_ideas("4. INDIA/WORLD — TREND-BASED SHORTS IDEAS", [x for x in trend_ideas if x.get("format") == "Shorts"][:12]),
        render_ideas("5. INDIA/WORLD — TREND-BASED LONG-FORM (8–10 MIN) IDEAS", [x for x in trend_ideas if x.get("format") == "Long-form (8–10 min)"][:12]),
        render_ideas("6. INDIA/WORLD — GENERAL SHORTS IDEAS (NOT TREND-DERIVED)", [x for x in general_ideas if x.get("format") == "Shorts"]),
        render_ideas("7. INDIA/WORLD — GENERAL LONG-FORM (8–10 MIN) IDEAS (NOT TREND-DERIVED)", [x for x in general_ideas if x.get("format") == "Long-form (8–10 min)"] ),
        render_ideas("8. GENRE-COMBINATION HIGH CTR IDEAS", combo_ideas),
    ]
    report = "\n\n".join(sections)
    metadata = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "india_videos": len(india),
        "world_videos": len(world),
        "api_errors": errors,
        "openrouter_used": bool(llm),
        "top_idea": top,
    }
    return report, metadata


def save_outputs(report: str, metadata: Dict[str, Any]) -> Tuple[Path, Path]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    md_path = OUTPUT_DIR / "youtube_idea_report.md"
    json_path = OUTPUT_DIR / "youtube_idea_report.json"
    md_path.write_text(report, encoding="utf-8")
    json_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
    return md_path, json_path


def main() -> int:
    print("=" * 70)
    print("YOUTUBE HIGH CTR IDEA GENERATOR")
    print("=" * 70)
    print("Collecting India + World YouTube data...")
    india, world, errors = collect_data()
    if not india and not world:
        print("[FATAL] YouTube data collection failed completely.")
        for k, v in errors.items():
            print(f"  {k}: {v}")
        return 1

    print(f"[OK] India videos: {len(india)}")
    print(f"[OK] World videos: {len(world)}")
    if errors:
        print(f"[WARN] Partial region failures: {', '.join(errors)}")

    report, metadata = build_report(india, world, errors)
    md_path, json_path = save_outputs(report, metadata)
    print(f"[OK] Markdown: {md_path}")
    print(f"[OK] JSON: {json_path}")
    print(f"[OK] HIGH CTR IDEA: {metadata['top_idea'].get('title')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
