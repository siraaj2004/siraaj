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
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"

if load_dotenv:
    load_dotenv(ENV_FILE)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "").strip()

OPENROUTER_MODEL = os.getenv(
    "OPENROUTER_MODEL",
    "google/gemini-2.0-flash-001"
).strip()

OUTPUT_DIR = BASE_DIR / "summaries"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# YOUTUBE
# ============================================================

def get_youtube_videos():
    """
    Get recent YouTube videos using YouTube Data API.
    If the API key is missing or the request fails,
    return an empty list instead of crashing.
    """

    if not YOUTUBE_API_KEY:
        print("WARNING: YOUTUBE_API_KEY not found.")
        return []

    if requests is None:
        print("ERROR: requests package is not installed.")
        return []

    url = "https://www.googleapis.com/youtube/v3/search"

    params = {
        "part": "snippet",
        "q": "India entertainment comedy thriller",
        "type": "video",
        "order": "date",
        "maxResults": 10,
        "key": YOUTUBE_API_KEY,
    }

    try:
        response = requests.get(
            url,
            params=params,
            timeout=30
        )

        response.raise_for_status()

        data = response.json()

        videos = []

        for item in data.get("items", []):
            snippet = item.get("snippet", {})
            video_id = item.get("id", {}).get("videoId")

            if not video_id:
                continue

            videos.append({
                "title": snippet.get("title", ""),
                "description": snippet.get("description", ""),
                "channel": snippet.get("channelTitle", ""),
                "published_at": snippet.get("publishedAt", ""),
                "url": f"https://www.youtube.com/watch?v={video_id}",
            })

        return videos

    except Exception as exc:
        print(f"WARNING: YouTube collection failed: {exc}")
        return []


# ============================================================
# OPENROUTER
# ============================================================

def generate_ai_ideas(videos):
    """
    Generate YouTube content ideas using OpenRouter.
    """

    if not OPENROUTER_API_KEY:
        print("WARNING: OPENROUTER_API_KEY not found.")
        return generate_fallback_ideas(videos)

    if requests is None:
        print("ERROR: requests package is not installed.")
        return generate_fallback_ideas(videos)

    video_text = ""

    for index, video in enumerate(videos, start=1):
        video_text += (
            f"\n{index}. {video['title']}\n"
            f"Channel: {video['channel']}\n"
            f"Description: {video['description'][:500]}\n"
        )

    if not video_text:
        video_text = "No YouTube trend data was available."

    prompt = f"""
You are a YouTube entertainment trend analyst.

Create original YouTube video ideas for an Indian audience.

Focus on:
- Thriller
- Mystery
- Suspense
- Comedy
- Relatable everyday situations
- Telugu audience
- Solo-shoot friendly concepts
- YouTube Shorts and 8-10 minute videos

Do NOT copy existing videos.
Do NOT create silly or childish ideas.

For every idea provide:

1. Title
2. English meaning
3. Story log
4. Hook
5. Twist
6. Comedy element
7. Recommended format

Recent YouTube data:

{video_text}

Return valid JSON only in this format:

{{
  "ideas": [
    {{
      "title": "...",
      "english_meaning": "...",
      "story_log": "...",
      "hook": "...",
      "twist": "...",
      "comedy": "...",
      "format": "Short / 8-10 minute"
    }}
  ]
}}
"""

    url = "https://openrouter.ai/api/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/",
        "X-Title": "YouTube Trend Idea Generator",
    }

    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {
                "role": "user",
                "content": prompt,
            }
        ],
        "temperature": 0.8,
        "max_tokens": 4000,
    }

    try:
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=120
        )

        response.raise_for_status()

        data = response.json()

        choices = data.get("choices", [])

        if not choices:
            print("WARNING: OpenRouter returned no choices.")
            return generate_fallback_ideas(videos)

        content = choices[0].get("message", {}).get("content", "")

        if not content:
            print("WARNING: OpenRouter returned empty content.")
            return generate_fallback_ideas(videos)

        return parse_ai_response(content)

    except Exception as exc:
        print(f"WARNING: OpenRouter failed: {exc}")
        return generate_fallback_ideas(videos)


# ============================================================
# PARSE AI RESPONSE
# ============================================================

def parse_ai_response(content):
    """
    Safely parse JSON returned by the AI.
    """

    content = content.strip()

    # Remove accidental Markdown fences if AI returns them.
    if content.startswith("```"):
        lines = content.splitlines()

        if lines and lines[0].startswith("```"):
            lines = lines[1:]

        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        content = "\n".join(lines).strip()

    try:
        data = json.loads(content)

        if isinstance(data, dict):
            return data

        return {"ideas": []}

    except json.JSONDecodeError:
        print("WARNING: AI response was not valid JSON.")

        return {
            "ideas": [
                {
                    "title": "AI Response",
                    "english_meaning": "Generated response",
                    "story_log": content[:2000],
                    "hook": "",
                    "twist": "",
                    "comedy": "",
                    "format": "8-10 minute",
                }
            ]
        }


# ============================================================
# FALLBACK IDEAS
# ============================================================

def generate_fallback_ideas(videos):
    """
    Creates ideas even when YouTube/OpenRouter is unavailable.
    """

    return {
        "ideas": [
            {
                "title": "Nenu Terrace Meeda Oka Small Mistake Chesanu... Kani",
                "english_meaning": "I made a small mistake on the terrace... but",
                "story_log": (
                    "Terrace meeda oka small mistake jarugutundi. "
                    "Adi cover cheyyadaniki try chestunte, "
                    "akkada already evaro observe chestunnaru ani "
                    "hero ki doubt vastundi. Finally, mystery "
                    "antha oka innocent misunderstanding ani reveal avutundi."
                ),
                "hook": "Why is someone watching me?",
                "twist": "The mysterious clue was caused by an innocent mistake.",
                "comedy": "Hero overthinks every small clue.",
                "format": "8-10 minute",
            },
            {
                "title": "Nenu Phone Akkada Petti Vachesa... Kani Phone Malli",
                "english_meaning": "I left my phone there... but the phone came back",
                "story_log": (
                    "Hero phone ni terrace lo oka place lo petti "
                    "konchem distance velthadu. Tirigi vachaka phone "
                    "different place lo kanipistundi. Suspense perigina "
                    "tarvata actual reason simple ga reveal avutundi."
                ),
                "hook": "Who moved my phone?",
                "twist": "The phone was moved accidentally while cleaning.",
                "comedy": "Hero imagines an elaborate mystery.",
                "format": "Short",
            },
            {
                "title": "Nenu Oka Sound Ignore Chesanu... Tarvata",
                "english_meaning": "I ignored one strange sound... then",
                "story_log": (
                    "Morning terrace lo repeated sound vinipistundi. "
                    "Hero first ignore chestadu. Sound repeat avvadamto "
                    "investigate chestadu. Finally, terrifying clue "
                    "anipinchindhi actually normal household object "
                    "valla vachina sound ani telustundi."
                ),
                "hook": "What is making that sound?",
                "twist": "The scary sound has a completely ordinary explanation.",
                "comedy": "Hero's investigation becomes unnecessarily serious.",
                "format": "8-10 minute",
            },
        ]
    }


# ============================================================
# SAVE RESULTS
# ============================================================

def save_results(data):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    json_file = OUTPUT_DIR / f"youtube_ideas_{timestamp}.json"
    txt_file = OUTPUT_DIR / f"youtube_ideas_{timestamp}.txt"

    with open(json_file, "w", encoding="utf-8") as file:
        json.dump(
            data,
            file,
            indent=2,
            ensure_ascii=False
        )

    with open(txt_file, "w", encoding="utf-8") as file:
        file.write("=" * 70 + "\n")
        file.write("YOUTUBE HIGH-ENGAGEMENT IDEA GENERATOR\n")
        file.write("=" * 70 + "\n\n")

        ideas = data.get("ideas", [])

        for index, idea in enumerate(ideas, start=1):
            file.write(f"IDEA {index}\n")
            file.write("-" * 70 + "\n")

            file.write(f"Title: {idea.get('title', '')}\n")
            file.write(
                f"English Meaning: "
                f"{idea.get('english_meaning', '')}\n"
            )
            file.write(
                f"Story Log: "
                f"{idea.get('story_log', '')}\n"
            )
            file.write(
                f"Hook: "
                f"{idea.get('hook', '')}\n"
            )
            file.write(
                f"Twist: "
                f"{idea.get('twist', '')}\n"
            )
            file.write(
                f"Comedy: "
                f"{idea.get('comedy', '')}\n"
            )
            file.write(
                f"Format: "
                f"{idea.get('format', '')}\n"
            )

            file.write("\n")

    return json_file, txt_file


# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 70)
    print("YOUTUBE HIGH-ENGAGEMENT IDEA GENERATOR")
    print("=" * 70)

    print("\n[1/5] Checking configuration...")

    print(
        "OpenRouter:",
        "Configured" if OPENROUTER_API_KEY else "Not configured"
    )

    print(
        "YouTube:",
        "Configured" if YOUTUBE_API_KEY else "Not configured"
    )

    print("\n[2/5] Collecting YouTube trends...")

    videos = get_youtube_videos()

    print(f"Collected {len(videos)} videos.")

    print("\n[3/5] Generating content ideas...")

    ideas = generate_ai_ideas(videos)

    print(
        f"Generated {len(ideas.get('ideas', []))} ideas."
    )

    print("\n[4/5] Saving results...")

    json_file, txt_file = save_results(ideas)

    print(f"JSON: {json_file}")
    print(f"TXT : {txt_file}")

    print("\n[5/5] Complete.")

    print("\n" + "=" * 70)
    print("GENERATION COMPLETED SUCCESSFULLY")
    print("=" * 70)


if __name__ == "__main__":
    main()
