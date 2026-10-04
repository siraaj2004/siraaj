import os
import json
import time
from datetime import datetime, timezone

import requests


# =========================================================
# CONFIGURATION
# =========================================================

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

OPENROUTER_MODELS = [
    "openrouter/free"
]

YOUTUBE_API_URL = (
    "https://www.googleapis.com/youtube/v3/videos"
)

INDIA_REGION = "IN"
WORLD_REGION = "US"

MAX_TREND_VIDEOS = 50

OUTPUT_DIR = "data"
OUTPUT_FILE = os.path.join(
    OUTPUT_DIR,
    "youtube_high_ctr_ideas.json"
)


# =========================================================
# ENVIRONMENT CHECK
# =========================================================

def check_environment():

    required = [
        "OPENROUTER_API_KEY",
        "YOUTUBE_API_KEY"
    ]

    missing = []

    for name in required:

        value = os.getenv(name)

        if not value:
            missing.append(name)

    if missing:

        raise RuntimeError(
            "Missing environment variables: "
            + ", ".join(missing)
        )

    print("Environment check: OK")

    print(
        "OpenRouter primary model: openrouter/free"
    )


# =========================================================
# YOUTUBE API
# =========================================================

def collect_youtube_trends(
    region_code,
    max_results=50
):

    youtube_key = os.getenv(
        "YOUTUBE_API_KEY"
    )

    if not youtube_key:
        raise RuntimeError(
            "YOUTUBE_API_KEY is missing."
        )

    print(
        f"Collecting YouTube mostPopular data: "
        f"{region_code}"
    )

    params = {
        "part": "snippet,statistics",
        "chart": "mostPopular",
        "regionCode": region_code,
        "maxResults": min(
            max_results,
            50
        ),
        "key": youtube_key
    }

    try:

        response = requests.get(
            YOUTUBE_API_URL,
            params=params,
            timeout=60
        )

    except requests.exceptions.RequestException as e:

        raise RuntimeError(
            f"YouTube API connection failed: {e}"
        )

    if response.status_code != 200:

        raise RuntimeError(
            "YouTube API error "
            f"{response.status_code}: "
            f"{response.text}"
        )

    data = response.json()

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

        videos.append(
            {
                "video_id": item.get(
                    "id"
                ),

                "title": snippet.get(
                    "title",
                    ""
                ),

                "channel": snippet.get(
                    "channelTitle",
                    ""
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
                    )
                ),

                "likes": int(
                    statistics.get(
                        "likeCount",
                        0
                    )
                ),

                "comments": int(
                    statistics.get(
                        "commentCount",
                        0
                    )
                )
            }
        )

    print(
        f"Collected {len(videos)} videos."
    )

    return videos


# =========================================================
# TREND SUMMARY
# =========================================================

def format_trends_for_ai(
    videos,
    country
):

    lines = []

    lines.append(
        f"{country} YouTube Trending Videos:"
    )

    lines.append("")

    for index, video in enumerate(
        videos,
        start=1
    ):

        lines.append(
            f"{index}. "
            f"{video['title']} | "
            f"Channel: {video['channel']} | "
            f"Views: {video['views']} | "
            f"Likes: {video['likes']} | "
            f"Comments: {video['comments']}"
        )

    return "\n".join(lines)


# =========================================================
# OPENROUTER JSON SCHEMA
# =========================================================

IDEA_SCHEMA = {

    "type": "object",

    "properties": {

        "high_ctr_idea": {

            "type": "object",

            "properties": {

                "title": {
                    "type": "string"
                },

                "genre": {
                    "type": "string"
                },

                "english_logline": {
                    "type": "string"
                },

                "roman_telugu_logline": {
                    "type": "string"
                },

                "hook": {
                    "type": "string"
                },

                "why_this_is_best": {
                    "type": "string"
                }

            },

            "required": [
                "title",
                "genre",
                "english_logline",
                "roman_telugu_logline",
                "hook",
                "why_this_is_best"
            ],

            "additionalProperties": False
        },

        "current_shorts": {

            "type": "array",

            "items": {

                "type": "object",

                "properties": {

                    "title": {
                        "type": "string"
                    },

                    "genre": {
                        "type": "string"
                    },

                    "english_logline": {
                        "type": "string"
                    },

                    "roman_telugu_logline": {
                        "type": "string"
                    },

                    "hook": {
                        "type": "string"
                    },

                    "content_summary": {
                        "type": "string"
                    }

                },

                "required": [
                    "title",
                    "genre",
                    "english_logline",
                    "roman_telugu_logline",
                    "hook",
                    "content_summary"
                ],

                "additionalProperties": False
            }
        }
    },

    "required": [
        "high_ctr_idea",
        "current_shorts"
    ],

    "additionalProperties": False
}


# =========================================================
# OPENROUTER CALL
# =========================================================

def openrouter_call(
    prompt,
    system_prompt,
    temperature=0.4,
    max_tokens=5000,
    retries=3,
    use_json_schema=True
):

    api_key = os.getenv(
        "OPENROUTER_API_KEY"
    )

    if not api_key:

        raise RuntimeError(
            "OPENROUTER_API_KEY is missing."
        )

    headers = {

        "Authorization":
            f"Bearer {api_key}",

        "Content-Type":
            "application/json",

        "HTTP-Referer":
            "https://github.com/",

        "X-OpenRouter-Title":
            "YouTube High CTR Idea Generator"
    }

    last_error = None

    for model in OPENROUTER_MODELS:

        for attempt in range(
            1,
            retries + 1
        ):

            print()
            print("=" * 70)
            print("OPENROUTER REQUEST")
            print("=" * 70)

            print(
                "Trying OpenRouter model:",
                model
            )

            print(
                "Attempt:",
                attempt
            )

            payload = {

                "model": model,

                "messages": [

                    {
                        "role": "system",
                        "content": system_prompt
                    },

                    {
                        "role": "user",
                        "content": prompt
                    }
                ],

                "temperature": temperature,

                "max_tokens": max_tokens
            }

            # -------------------------------------------------
            # ASK OPENROUTER FOR JSON
            # -------------------------------------------------

            if use_json_schema:

                payload["response_format"] = {

                    "type": "json_schema",

                    "json_schema": {

                        "name":
                            "youtube_ideas",

                        "strict":
                            True,

                        "schema":
                            IDEA_SCHEMA
                    }
                }

            try:

                response = requests.post(

                    OPENROUTER_URL,

                    headers=headers,

                    json=payload,

                    timeout=120
                )

            except requests.exceptions.Timeout:

                last_error = (
                    "OpenRouter request timed out."
                )

                print(
                    last_error
                )

                time.sleep(
                    5 * attempt
                )

                continue

            except requests.exceptions.RequestException as e:

                last_error = str(e)

                print(
                    "OpenRouter connection error:",
                    e
                )

                time.sleep(
                    5 * attempt
                )

                continue

            print(
                "HTTP status:",
                response.status_code
            )

            # =================================================
            # SUCCESS
            # =================================================

            if response.status_code == 200:

                try:

                    data = response.json()

                except ValueError as e:

                    last_error = (
                        f"Invalid API response JSON: {e}"
                    )

                    print(
                        last_error
                    )

                    continue

                choices = data.get(
                    "choices",
                    []
                )

                if not choices:

                    last_error = (
                        "OpenRouter returned no choices."
                    )

                    print(
                        last_error
                    )

                    continue

                message = choices[0].get(
                    "message",
                    {}
                )

                content = message.get(
                    "content"
                )

                if not content:

                    last_error = (
                        "OpenRouter returned empty content."
                    )

                    print(
                        last_error
                    )

                    continue

                print(
                    "OpenRouter SUCCESS"
                )

                print(
                    "Model used:",
                    data.get(
                        "model",
                        model
                    )
                )

                return content

            # =================================================
            # RATE LIMIT
            # =================================================

            if response.status_code == 429:

                last_error = (
                    f"HTTP 429: {response.text}"
                )

                print(
                    "OpenRouter rate limited."
                )

                wait_time = 10 * attempt

                print(
                    f"Waiting {wait_time} seconds..."
                )

                time.sleep(
                    wait_time
                )

                continue

            # =================================================
            # BAD REQUEST
            # =================================================

            if response.status_code == 400:

                print(
                    "OpenRouter request error:"
                )

                print(
                    response.text
                )

                # Structured output might not be supported
                # by the model selected by the free router.
                #
                # Retry once without response_format.

                if use_json_schema:

                    print(
                        "Retrying without "
                        "structured-output parameter..."
                    )

                    return openrouter_call(

                        prompt=prompt,

                        system_prompt=system_prompt,

                        temperature=temperature,

                        max_tokens=max_tokens,

                        retries=2,

                        use_json_schema=False
                    )

                last_error = (
                    f"HTTP 400: {response.text}"
                )

                break

            # =================================================
            # SERVER ERROR
            # =================================================

            if response.status_code >= 500:

                last_error = (
                    f"HTTP {response.status_code}: "
                    f"{response.text}"
                )

                print(
                    "OpenRouter server error."
                )

                time.sleep(
                    5 * attempt
                )

                continue

            # =================================================
            # OTHER ERROR
            # =================================================

            last_error = (
                f"HTTP {response.status_code}: "
                f"{response.text}"
            )

            print(
                "OpenRouter error:"
            )

            print(
                response.text
            )

            time.sleep(3)

    raise RuntimeError(
        "ALL OPENROUTER REQUESTS FAILED.\n"
        f"Last error: {last_error}"
    )


# =========================================================
# JSON EXTRACTION
# =========================================================

def extract_json(text):

    if not text:

        raise ValueError(
            "AI returned empty response."
        )

    text = text.strip()

    # -------------------------------------------------
    # Remove markdown fences
    # -------------------------------------------------

    text = text.replace(
        "```json",
        ""
    )

    text = text.replace(
        "```JSON",
        ""
    )

    text = text.replace(
        "```",
        ""
    )

    text = text.strip()

    # -------------------------------------------------
    # Direct JSON
    # -------------------------------------------------

    try:

        return json.loads(text)

    except json.JSONDecodeError:
        pass

    # -------------------------------------------------
    # Find JSON object
    # -------------------------------------------------

    start = text.find("{")

    end = text.rfind("}")

    if (
        start >= 0
        and end > start
    ):

        candidate = text[
            start:end + 1
        ]

        try:

            return json.loads(
                candidate
            )

        except json.JSONDecodeError as e:

            print()
            print(
                "JSON parsing error:"
            )

            print(e)

            print()
            print(
                "AI RESPONSE:"
            )

            print(
                candidate[:20000]
            )

    raise ValueError(
        "AI returned invalid JSON."
    )


# =========================================================
# JSON REPAIR
# =========================================================

def repair_json(raw):

    print()
    print("=" * 70)
    print("ATTEMPTING JSON REPAIR")
    print("=" * 70)

    repair_prompt = f"""
Convert the following AI response into valid JSON.

Return ONLY valid JSON.

Do not use markdown.

Do not use code fences.

Do not explain anything.

Preserve the information.

The final answer MUST be parseable by Python json.loads().

AI RESPONSE:

{raw[:16000]}
"""

    repair_system = """
You are a strict JSON repair assistant.

Return ONLY valid JSON.

Never return markdown.
Never return explanations.
Never return text outside the JSON object.
"""

    repaired = openrouter_call(

        prompt=repair_prompt,

        system_prompt=repair_system,

        temperature=0,

        max_tokens=5000,

        retries=2,

        use_json_schema=False
    )

    return extract_json(
        repaired
    )


# =========================================================
# GENERATE CURRENT IDEAS
# =========================================================

def generate_current_ideas(
    india_videos,
    worldwide_videos
):

    print()
    print(
        "3. Generating monetization strategy..."
    )

    india_text = format_trends_for_ai(
        india_videos,
        "INDIA"
    )

    world_text = format_trends_for_ai(
        worldwide_videos,
        "WORLDWIDE"
    )

    system_prompt = """
You are an expert YouTube trend intelligence strategist.

Your task is to generate highly clickable YouTube ideas.

Focus on:

- curiosity
- mystery
- strong hooks
- emotional tension
- unusual concepts
- high click-through potential
- YouTube Shorts
- Indian/Telugu audience appeal
- globally understandable ideas

IMPORTANT:

Roman Telugu MUST use English alphabet only.

Correct:
"Marvel fan video kosam research chestunte..."

Wrong:
"మార్వెల్ ఫ్యాన్ వీడియో కోసం..."

Never output Telugu Unicode characters.

Do not invent real facts about real people.

Do not claim that an actor, celebrity or company secretly did something unless it is directly supported by the trend data.

Return JSON only.
"""

    prompt = f"""
Analyze these current YouTube trends.

========================
INDIA
========================

{india_text}

========================
WORLDWIDE
========================

{world_text}

========================
TASK
========================

Create:

1 HIGH CTR IDEA

and

5 CURRENT YOUTUBE SHORTS IDEAS.

The ideas must NOT be generic.

Avoid boring ideas like:

"Top 10 facts"

"5 things you didn't know"

"Daily vlog"

"Funny video"

Make the concepts feel like:

"Wait... what?"

The viewer should immediately want to know what happens.

For each idea provide:

title

genre

english_logline

roman_telugu_logline

hook

content_summary

For the main idea also provide:

why_this_is_best

Roman Telugu must contain ONLY English alphabet characters.

No Telugu Unicode.

Keep the output concise.
"""

    print()
    print(
        "4. Generating HIGH CTR + YouTube ideas..."
    )

    raw = openrouter_call(

        prompt=prompt,

        system_prompt=system_prompt,

        temperature=0.4,

        max_tokens=6000,

        retries=3,

        use_json_schema=True
    )

    try:

        result = extract_json(
            raw
        )

    except Exception as e:

        print()
        print(
            "Initial JSON parsing failed:"
        )

        print(e)

        result = repair_json(
            raw
        )

    return result


# =========================================================
# SAVE RESULT
# =========================================================

def save_result(
    result,
    india_videos,
    worldwide_videos
):

    os.makedirs(
        OUTPUT_DIR,
        exist_ok=True
    )

    final_data = {

        "generated_at": datetime.now(
            timezone.utc
        ).isoformat(),

        "india_trending_count":
            len(india_videos),

        "worldwide_trending_count":
            len(worldwide_videos),

        "india_trends":
            india_videos,

        "worldwide_trends":
            worldwide_videos,

        "ideas":
            result
    }

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            final_data,
            f,
            indent=2,
            ensure_ascii=False
        )

    print()
    print("=" * 70)
    print("RESULT SAVED")
    print("=" * 70)

    print(
        OUTPUT_FILE
    )


# =========================================================
# PRINT RESULT
# =========================================================

def print_result(result):

    print()
    print("=" * 70)
    print("HIGH CTR IDEA")
    print("=" * 70)

    best = result.get(
        "high_ctr_idea",
        {}
    )

    print()
    print(
        "TITLE:",
        best.get(
            "title",
            ""
        )
    )

    print(
        "GENRE:",
        best.get(
            "genre",
            ""
        )
    )

    print()
    print(
        "ENGLISH:",
        best.get(
            "english_logline",
            ""
        )
    )

    print()
    print(
        "ROMAN TELUGU:",
        best.get(
            "roman_telugu_logline",
            ""
        )
    )

    print()
    print(
        "HOOK:",
        best.get(
            "hook",
            ""
        )
    )

    print()
    print(
        "WHY BEST:",
        best.get(
            "why_this_is_best",
            ""
        )
    )

    print()
    print("=" * 70)
    print("CURRENT SHORTS")
    print("=" * 70)

    shorts = result.get(
        "current_shorts",
        []
    )

    for index, idea in enumerate(
        shorts,
        start=1
    ):

        print()
        print(
            f"{index}. "
            f"{idea.get('title', '')}"
        )

        print(
            "Genre:",
            idea.get(
                "genre",
                ""
            )
        )

        print(
            "English:",
            idea.get(
                "english_logline",
                ""
            )
        )

        print(
            "Roman Telugu:",
            idea.get(
                "roman_telugu_logline",
                ""
            )
        )

        print(
            "Hook:",
            idea.get(
                "hook",
                ""
            )
        )


# =========================================================
# MAIN
# =========================================================

def main():

    print()
    print("=" * 70)
    print("STARTING YOUTUBE HIGH CTR IDEA GENERATOR")
    print("=" * 70)

    check_environment()

    # =====================================================
    # INDIA
    # =====================================================

    print()
    print(
        "1. Collecting India trends..."
    )

    india_videos = collect_youtube_trends(
        INDIA_REGION,
        MAX_TREND_VIDEOS
    )

    # =====================================================
    # WORLDWIDE PROXY
    # =====================================================

    print()
    print(
        "2. Collecting worldwide proxy trends..."
    )

    worldwide_videos = collect_youtube_trends(
        WORLD_REGION,
        MAX_TREND_VIDEOS
    )

    # =====================================================
    # AI
    # =====================================================

    result = generate_current_ideas(

        india_videos,

        worldwide_videos
    )

    # =====================================================
    # SAVE
    # =====================================================

    save_result(

        result,

        india_videos,

        worldwide_videos
    )

    # =====================================================
    # PRINT
    # =====================================================

    print_result(
        result
    )

    print()
    print("=" * 70)
    print("YOUTUBE HIGH CTR IDEA GENERATOR COMPLETED")
    print("=" * 70)


# =========================================================
# ENTRY POINT
# =========================================================

if __name__ == "__main__":

    try:

        main()

    except Exception as e:

        print()
        print("=" * 70)
        print("FATAL ERROR")
        print("=" * 70)

        print(
            str(e)
        )

        raise
