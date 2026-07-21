import os
import requests
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


def generate_video_ideas(videos):
    """
    videos: List of dictionaries returned from youtube_agent.py
    """

    if not videos:
        return "No videos found."

    video_list = ""

    for i, video in enumerate(videos, start=1):
        video_list += f"""
{i}.
Title: {video['title']}
Channel: {video['channel']}
Views: {video['views']}
Published: {video['published']}
Video: {video['video_url']}

"""

    prompt = f"""
You are a professional YouTube strategist.

Analyze the following latest YouTube videos.

{video_list}

Tasks:

1. Identify trending topics.
2. Explain why these videos are performing well.
3. Find common patterns.
4. Predict upcoming trends.
5. Suggest 15 unique viral YouTube video ideas.
6. Suggest titles.
7. Suggest thumbnails.
8. Suggest target audience.
9. Suggest upload timing.
10. Suggest SEO keywords.
11. Give a final summary.

Return the response in clean Markdown.
"""

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": "openai/gpt-4.1-mini",
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ]
    }

    response = requests.post(
        OPENROUTER_URL,
        headers=headers,
        json=payload,
        timeout=120
    )

    response.raise_for_status()

    data = response.json()

    return data["choices"][0]["message"]["content"]
