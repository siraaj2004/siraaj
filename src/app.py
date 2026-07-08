import requests
import feedparser

from config import (
    OPENROUTER_API_KEY,
    RESEND_API_KEY,
    RECIPIENT_EMAIL,
    YOUTUBE_RSS_URL
)

# Read RSS feed
feed = feedparser.parse(YOUTUBE_RSS_URL)

videos = []

for entry in feed.entries[:10]:
    videos.append(
        f"Title: {entry.title}\n"
        f"Link: {entry.link}\n"
    )

video_text = "\n\n".join(videos)

prompt = f"""
Analyze these YouTube videos.

Give:
1. Trending topics
2. Video ideas
3. Shorts ideas
4. Viral title suggestions

Videos:

{video_text}
"""

# OpenRouter
ai_response = requests.post(
    "https://openrouter.ai/api/v1/chat/completions",
    headers={
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    },
    json={
        "model": "openrouter/free",
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ]
    }
)

analysis = ai_response.json()["choices"][0]["message"]["content"]

# Resend
email_response = requests.post(
    "https://api.resend.com/emails",
    headers={
        "Authorization": f"Bearer {RESEND_API_KEY}",
        "Content-Type": "application/json"
    },
    json={
        "from": "onboarding@resend.dev",
        "to": [RECIPIENT_EMAIL],
        "subject": "YouTube Trends & Ideas",
        "html": f"""
        <h1>YouTube Trends Report</h1>
        <pre>{analysis}</pre>
        """
    }
)

print("Email Status:", email_response.status_code)
print(email_response.text)
