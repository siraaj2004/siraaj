import os
import sys
import json
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
# PATH CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
SRC_DIR = BASE_DIR / "src"
DATA_DIR = BASE_DIR / "data"
REPORTS_DIR = BASE_DIR / "reports"
SUMMARIES_DIR = BASE_DIR / "summaries"

DATA_DIR.mkdir(exist_ok=True)
REPORTS_DIR.mkdir(exist_ok=True)
SUMMARIES_DIR.mkdir(exist_ok=True)


# ============================================================
# LOAD ENVIRONMENT
# ============================================================

ENV_FILE = BASE_DIR / ".env"

if load_dotenv:
    if ENV_FILE.exists():
        load_dotenv(ENV_FILE)
    else:
        print("⚠ Project .env not found.")
        print("Using GitHub Actions environment variables.")


# ============================================================
# CONFIGURATION
# ============================================================

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_TO = os.getenv("GMAIL_TO")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")


# Gemini is intentionally NOT required.
# This project now uses OpenRouter for AI generation.

OPENROUTER_MODEL = os.getenv(
    "OPENROUTER_MODEL",
    "openai/gpt-oss-20b:free"
)


# ============================================================
# PRINT HEADER
# ============================================================

print()
print("=" * 60)
print("YOUTUBE TREND INTELLIGENCE")
print("=" * 60)
print()

print(f"Project root : {BASE_DIR}")
print(f"Source folder: {SRC_DIR}")
print(f"Data folder  : {DATA_DIR}")
print(f"Reports      : {REPORTS_DIR}")
print(f"Summaries    : {SUMMARIES_DIR}")
print()


# ============================================================
# CHECK ENVIRONMENT VARIABLES
# ============================================================

print("Checking environment variables...")
print()

missing = []


def check_env(name, value, required=True):
    if value:
        print(f"✓ {name} found")
    else:
        print(f"✗ {name} is missing")
        if required:
            missing.append(name)


check_env("YOUTUBE_API_KEY", YOUTUBE_API_KEY)

# IMPORTANT:
# Gemini is NOT required anymore.
check_env("OPENROUTER_API_KEY", OPENROUTER_API_KEY)

check_env("GMAIL_USER", GMAIL_USER)
check_env("GMAIL_TO", GMAIL_TO)
check_env("GMAIL_APP_PASSWORD", GMAIL_APP_PASSWORD)


# ============================================================
# STOP ONLY IF ACTUALLY REQUIRED VARIABLES ARE MISSING
# ============================================================

if missing:
    print()
    print("=" * 60)
    print("ERROR: REQUIRED ENVIRONMENT VARIABLES ARE MISSING")
    print("=" * 60)

    for item in missing:
        print(f"  - {item}")

    print()
    print("Add these values to GitHub Repository Secrets.")
    print()

    sys.exit(1)


print()
print("=" * 60)
print("ENVIRONMENT CHECK PASSED")
print("=" * 60)
print()


# ============================================================
# OPENROUTER AI
# ============================================================

def ask_openrouter(prompt):
    """
    Send prompt to OpenRouter and return AI response.
    """

    if not OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY is missing.")

    if requests is None:
        raise RuntimeError(
            "requests package is not installed. "
            "Run: pip install requests"
        )

    url = "https://openrouter.ai/api/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/",
        "X-Title": "YouTube Trend Intelligence"
    }

    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a YouTube trend intelligence analyst. "
                    "Analyze YouTube trend data and generate practical "
                    "video ideas for an Indian/Telugu creator."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.7,
        "max_tokens": 4000
    }

    response = requests.post(
        url,
        headers=headers,
        json=payload,
        timeout=120
    )

    print(f"OpenRouter HTTP status: {response.status_code}")

    if response.status_code != 200:
        print("OpenRouter response:")
        print(response.text[:2000])

        raise RuntimeError(
            f"OpenRouter API failed with HTTP {response.status_code}"
        )

    result = response.json()

    try:
        return result["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        print("Unexpected OpenRouter response:")
        print(json.dumps(result, indent=2)[:4000])

        raise RuntimeError(
            "Could not extract AI response from OpenRouter."
        )


# ============================================================
# YOUTUBE API
# ============================================================

def get_youtube_trending_videos(region_code="IN", max_results=50):

    if requests is None:
        raise RuntimeError("requests package is not installed.")

    url = "https://www.googleapis.com/youtube/v3/videos"

    params = {
        "part": "snippet,statistics,contentDetails",
        "chart": "mostPopular",
        "regionCode": region_code,
        "maxResults": max_results,
        "key": YOUTUBE_API_KEY
    }

    response = requests.get(
        url,
        params=params,
        timeout=60
    )

    print(f"YouTube API HTTP status: {response.status_code}")

    if response.status_code != 200:
        print(response.text[:2000])

        raise RuntimeError(
            f"YouTube API failed with HTTP {response.status_code}"
        )

    return response.json()


# ============================================================
# SAVE JSON DATA
# ============================================================

def save_json(data, filename):

    path = DATA_DIR / filename

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

    print(f"✓ Saved: {path}")

    return path


# ============================================================
# FORMAT TREND DATA FOR AI
# ============================================================

def prepare_trend_data(youtube_data):

    videos = []

    for item in youtube_data.get("items", []):

        snippet = item.get("snippet", {})
        statistics = item.get("statistics", {})

        video_id = item.get("id", "")

        title = snippet.get("title", "")
        channel = snippet.get("channelTitle", "")
        published = snippet.get("publishedAt", "")
        category_id = snippet.get("categoryId", "")

        views = statistics.get("viewCount", "0")
        likes = statistics.get("likeCount", "0")
        comments = statistics.get("commentCount", "0")

        videos.append({
            "video_id": video_id,
            "title": title,
            "channel": channel,
            "published_at": published,
            "category_id": category_id,
            "views": views,
            "likes": likes,
            "comments": comments
        })

    return videos


# ============================================================
# AI TREND ANALYSIS
# ============================================================

def generate_ai_report(videos):

    if not videos:
        raise RuntimeError(
            "No YouTube videos were collected."
        )

    compact_data = []

    for video in videos:

        compact_data.append({
            "title": video["title"],
            "channel": video["channel"],
            "views": video["views"],
            "likes": video["likes"],
            "comments": video["comments"],
            "published_at": video["published_at"]
        })

    data_text = json.dumps(
        compact_data,
        ensure_ascii=False,
        indent=2
    )

    prompt = f"""
Analyze the following current YouTube trending videos from India.

DATA:

{data_text}

Create a YouTube Trend Intelligence Report.

Include:

1. Trend Summary

Explain the major patterns visible in the data.

2. Content Patterns

Identify:
- recurring topics
- formats
- hooks
- titles
- audience interests
- engagement patterns

3. Top 10 Video Ideas

Generate 10 original video ideas inspired by the trends.

For every idea provide:

Title:
Concept:
Why it may attract viewers:
Hook:
Suggested format:

4. Telugu/Indian Creator Opportunities

Give ideas suitable for:
- Telugu audience
- Indian audience
- YouTube Shorts
- YouTube videos

5. Final Action Plan

Give practical steps for creating content from these trends.

Do NOT claim that any idea is guaranteed to go viral.
Use the supplied data only as trend evidence.
"""

    print("Sending trend data to OpenRouter...")
    print(f"Model: {OPENROUTER_MODEL}")
    print()

    report = ask_openrouter(prompt)

    return report


# ============================================================
# SAVE REPORT
# ============================================================

def save_report(report):

    timestamp = datetime.now().strftime(
        "%Y-%m-%d_%H-%M-%S"
    )

    filename = (
        f"youtube_trend_report_{timestamp}.txt"
    )

    path = REPORTS_DIR / filename

    with open(
        path,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(
            "YOUTUBE TREND INTELLIGENCE REPORT\n"
        )

        file.write("=" * 60)
        file.write("\n\n")

        file.write(report)

        file.write("\n\n")
        file.write("=" * 60)
        file.write("\n")

        file.write(
            f"Generated: {datetime.now().isoformat()}\n"
        )

    print()
    print(f"✓ AI report saved: {path}")

    return path


# ============================================================
# SAVE SUMMARY
# ============================================================

def save_summary(report):

    timestamp = datetime.now().strftime(
        "%Y-%m-%d_%H-%M-%S"
    )

    filename = (
        f"youtube_summary_{timestamp}.txt"
    )

    path = SUMMARIES_DIR / filename

    with open(
        path,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(report)

    print(f"✓ Summary saved: {path}")

    return path


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 60)
    print("COLLECTING YOUTUBE TRENDING VIDEOS")
    print("=" * 60)
    print()

    youtube_data = get_youtube_trending_videos(
        region_code="IN",
        max_results=50
    )

    videos = prepare_trend_data(
        youtube_data
    )

    print()
    print(
        f"✓ Collected {len(videos)} trending videos"
    )

    if not videos:
        print("ERROR: YouTube returned zero videos.")
        sys.exit(1)

    # Save raw data
    save_json(
        youtube_data,
        "youtube_trending_raw.json"
    )

    # Save processed data
    save_json(
        videos,
        "youtube_trending_processed.json"
    )

    print()
    print("=" * 60)
    print("GENERATING AI TREND REPORT")
    print("=" * 60)
    print()

    report = generate_ai_report(
        videos
    )

    save_report(report)

    save_summary(report)

    print()
    print("=" * 60)
    print("YOUTUBE TREND INTELLIGENCE COMPLETED")
    print("=" * 60)
    print()


if __name__ == "__main__":
    try:
        main()

    except KeyboardInterrupt:
        print()
        print("Process interrupted.")
        sys.exit(1)

    except Exception as error:

        print()
        print("=" * 60)
        print("ERROR")
        print("=" * 60)

        print(str(error))

        print()
        print("Full traceback:")

        import traceback
        traceback.print_exc()

        sys.exit(1)
