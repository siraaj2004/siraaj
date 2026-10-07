"""
src/app.py
----------
Entry point for the YouTube High CTR Idea Generator.

Data flow:
1. Load trend data from data/trends.json if present.
2. If YOUTUBE_API_KEY exists, collect fresh YouTube data automatically.
3. Generate the 8-section high-CTR report.
4. Save:
   output/youtube_high_ctr_report.txt
   output/youtube_high_ctr_report.json

Required for fresh data:
YOUTUBE_API_KEY=your_key

Recommended for stronger creative ideas:
OPENROUTER_API_KEY=your_key
OPENROUTER_MODEL=google/gemini-2.5-flash

Install:
pip install requests python-dotenv
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List

import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from idea_generator import generate_report, render_report


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "output"
DATA_FILE = Path(os.getenv("TREND_DATA_FILE", str(DATA_DIR / "trends.json")))

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

YOUTUBE_API_URL = "https://www.googleapis.com/youtube/v3/videos"


# ---------------------------------------------------------------------------
# YOUTUBE DATA API
# ---------------------------------------------------------------------------

# YouTube category IDs used by most current API responses.
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


def iso_duration_seconds(value: str) -> int:
    """
    Parse YouTube ISO 8601 durations, e.g. PT1M12S.
    """
    if not value:
        return 0
    m = re.fullmatch(
        r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?",
        value.upper()
    )
    if not m:
        return 0
    h = int(m.group(1) or 0)
    mi = int(m.group(2) or 0)
    s = int(m.group(3) or 0)
    return h * 3600 + mi * 60 + s


def fetch_most_popular(api_key: str, region_code: str, max_results: int = 50) -> List[Dict[str, Any]]:
    params = {
        "part": "snippet,contentDetails,statistics",
        "chart": "mostPopular",
        "regionCode": region_code,
        "maxResults": min(max_results, 50),
        "key": api_key,
    }
    response = requests.get(YOUTUBE_API_URL, params=params, timeout=60)
    response.raise_for_status()
    return response.json().get("items", [])


def _clean_title(title: str) -> str:
    title = re.sub(r"\[[^\]]*\]", " ", title)
    title = re.sub(r"\([^)]*\)", " ", title)
    title = re.sub(r"[^A-Za-z0-9\u0080-\uffff ]+", " ", title)
    return re.sub(r"\s+", " ", title).strip()


def _keywords(title: str) -> List[str]:
    stop = {
        "the", "and", "for", "with", "this", "that", "you", "your", "from",
        "official", "video", "full", "episode", "new", "live", "shorts",
        "short", "watch", "part", "day", "to", "of", "in", "on", "a", "an",
        "is", "it", "me", "my", "we", "our", "at", "by", "as", "be", "or",
    }
    words = re.findall(r"[A-Za-z][A-Za-z0-9']{2,}", title.lower())
    return [w for w in words if w not in stop][:8]


def _subgenre(title: str, category: str) -> str:
    t = title.lower()

    if category in ("Music",):
        return "Music"
    if category == "Gaming":
        if "horror" in t or "scary" in t:
            return "Horror Gaming"
        if "story" in t or "lore" in t:
            return "Story / Lore Gaming"
        return "Gaming"
    if category not in ("Entertainment", "Film & Animation"):
        return ""

    mapping = [
        ("Thriller", ["thriller", "suspense", "killer", "chase"]),
        ("Crime", ["crime", "criminal", "police", "cop", "gangster", "heist"]),
        ("Mystery", ["mystery", "secret", "hidden", "case", "unknown"]),
        ("Horror", ["horror", "ghost", "haunted", "demon", "scary"]),
        ("Comedy", ["comedy", "funny", "comed", "prank"]),
        ("Action", ["action", "fight", "battle", "war"]),
        ("Romance", ["love", "romance", "couple"]),
        ("Drama", ["drama", "family", "emotional"]),
        ("Anime", ["anime", "crunchyroll", "manga"]),
        ("Sci-Fi", ["sci-fi", "future", "space", "robot"]),
        ("Fantasy", ["fantasy", "dragon", "magic"]),
    ]
    for genre, words in mapping:
        if any(w in t for w in words):
            return genre
    return "Movies & Entertainment"


def build_region_trends(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Converts actual videos into keyword trend signals.
    A video <= 60 seconds is treated as Shorts.
    """
    buckets = {"longform": {}, "shorts": {}}

    for item in items:
        snippet = item.get("snippet", {})
        stats = item.get("statistics", {})
        duration = iso_duration_seconds(
            item.get("contentDetails", {}).get("duration", "")
        )
        is_short = duration <= 60

        title = _clean_title(snippet.get("title", ""))
        category_id = str(snippet.get("categoryId", ""))
        category = CATEGORY_NAMES.get(category_id, "Other")
        views = int(stats.get("viewCount", 0) or 0)

        words = _keywords(title)

        # Include a few semantically useful title tokens.
        # Generic tokens are filtered above.
        for word in words[:5]:
            bucket = buckets["shorts" if is_short else "longform"]
            x = bucket.setdefault(word, {
                "trend": word.title(),
                "mentions": 0,
                "combined_views": 0,
                "avg_views": 0,
                "category": category,
                "subgenre": _subgenre(title, category),
                "titles": [],
            })
            x["mentions"] += 1
            x["combined_views"] += views
            if title and len(x["titles"]) < 5:
                x["titles"].append(title)

    result = {}
    for mode, bucket in buckets.items():
        values = []
        for x in bucket.values():
            x["avg_views"] = x["combined_views"] / max(x["mentions"], 1)
            values.append(x)
        values.sort(
            key=lambda z: (z["combined_views"], z["mentions"]),
            reverse=True
        )
        result[mode] = values[:20]
    return result


def build_genre_trends(regional_data: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    result = {"longform": [], "shorts": []}

    for mode in ("longform", "shorts"):
        buckets = {}
        for region in ("india", "world"):
            for x in regional_data[region][mode]:
                category = x.get("category", "Other")
                b = buckets.setdefault(category, {
                    "trend": category,
                    "mentions": 0,
                    "combined_views": 0,
                    "avg_views": 0,
                    "category": category,
                    "subgenres": {},
                    "examples": [],
                })
                b["mentions"] += int(x.get("mentions", 0))
                b["combined_views"] += int(x.get("combined_views", 0))
                sg = x.get("subgenre")
                if sg:
                    b["subgenres"][sg] = b["subgenres"].get(sg, 0) + int(
                        x.get("mentions", 1)
                    )
                for title in x.get("titles", [])[:2]:
                    if title not in b["examples"] and len(b["examples"]) < 8:
                        b["examples"].append(title)

        for b in buckets.values():
            b["avg_views"] = b["combined_views"] / max(b["mentions"], 1)
            if b["subgenres"]:
                b["subgenre"] = max(
                    b["subgenres"], key=b["subgenres"].get
                )
            else:
                b["subgenre"] = ""

        result[mode] = sorted(
            buckets.values(),
            key=lambda z: z["combined_views"],
            reverse=True
        )
    return result


def collect_fresh_trends(api_key: str) -> Dict[str, Any]:
    """
    India = IN.
    World = blended global signal from US, GB, CA, AU, JP, KR.
    This avoids treating a single country as "the world".
    """
    india_videos = fetch_most_popular(api_key, "IN", 50)

    world_regions = os.getenv(
        "WORLD_REGION_CODES",
        "US,GB,CA,AU,JP,KR"
    ).split(",")

    world_videos = []
    seen = set()
    for region in world_regions:
        region = region.strip().upper()
        if not region:
            continue
        try:
            for item in fetch_most_popular(api_key, region, 50):
                video_id = item.get("id")
                if video_id and video_id not in seen:
                    seen.add(video_id)
                    world_videos.append(item)
        except requests.RequestException as exc:
            print(f"[youtube] Could not collect {region}: {exc}")

    regions = {
        "india": build_region_trends(india_videos),
        "world": build_region_trends(world_videos),
    }
    genres = build_genre_trends(regions)

    return {
        "india": regions["india"],
        "world": regions["world"],
        "genre": genres,
        "meta": {
            "india_videos_collected": len(india_videos),
            "world_videos_collected": len(world_videos),
            "world_regions": world_regions,
        },
    }


# ---------------------------------------------------------------------------
# LOAD / SAVE
# ---------------------------------------------------------------------------

def load_existing_data() -> Dict[str, Any] | None:
    if not DATA_FILE.exists():
        return None
    try:
        with DATA_FILE.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        print(f"[data] Could not read {DATA_FILE}: {exc}")
        return None


def main() -> None:
    print("=" * 60)
    print("STARTING YOUTUBE HIGH CTR IDEA GENERATOR")
    print("=" * 60)

    api_key = os.getenv("YOUTUBE_API_KEY", "").strip()
    data = None

    if api_key:
        print("[1/4] Collecting fresh YouTube trend data...")
        try:
            data = collect_fresh_trends(api_key)
            with DATA_FILE.open("w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"[data] Saved fresh trend data -> {DATA_FILE}")
        except Exception as exc:
            print(f"[youtube] Fresh collection failed: {exc}")

    if data is None:
        data = load_existing_data()

    if data is None:
        raise RuntimeError(
            "No trend data available. Set YOUTUBE_API_KEY or create "
            f"{DATA_FILE}."
        )

    print("[2/4] Generating 8-section high-CTR ideas...")
    report = generate_report(data)

    print("[3/4] Rendering report...")
    text = render_report(report)

    txt_file = OUTPUT_DIR / "youtube_high_ctr_report.txt"
    json_file = OUTPUT_DIR / "youtube_high_ctr_report.json"

    txt_file.write_text(text, encoding="utf-8")
    json_file.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print("[4/4] DONE")
    print(f"TXT : {txt_file}")
    print(f"JSON: {json_file}")
    print()
    print(text)


if __name__ == "__main__":
    main()
