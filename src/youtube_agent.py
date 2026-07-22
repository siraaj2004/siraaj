import os
from dotenv import load_dotenv
from googleapiclient.discovery import build

# Load environment variables
load_dotenv()

API_KEY = os.getenv("YOUTUBE_API_KEY")

if not API_KEY:
    raise ValueError("YOUTUBE_API_KEY not found in .env")

youtube = build(
    "youtube",
    "v3",
    developerKey=API_KEY
)


def get_trending_videos(region_code="IN", max_results=20):
    """
    Fetch trending YouTube videos.
    """

    response = youtube.videos().list(
        part="snippet,statistics",
        chart="mostPopular",
        regionCode=region_code,
        maxResults=max_results,
    ).execute()

    videos = []

    for item in response.get("items", []):
        snippet = item["snippet"]
        stats = item.get("statistics", {})

        videos.append({
            "title": snippet["title"],
            "channel": snippet["channelTitle"],
            "published_at": snippet["publishedAt"],
            "views": int(stats.get("viewCount", 0)),
            "likes": int(stats.get("likeCount", 0)),
            "comments": int(stats.get("commentCount", 0)),
            "video_url": f"https://www.youtube.com/watch?v={item['id']}",
            "thumbnail": snippet["thumbnails"]["high"]["url"],
        })

    return videos


def run_agent():
    """
    Function called by app.py
    """

    print("=" * 80)
    print("🔥 Fetching Trending YouTube Videos...")
    print("=" * 80)

    videos = get_trending_videos()

    if not videos:
        print("No trending videos found.")
        return

    for i, video in enumerate(videos, start=1):
        print(f"\n{i}. {video['title']}")
        print(f"Channel   : {video['channel']}")
        print(f"Views     : {video['views']:,}")
        print(f"Likes     : {video['likes']:,}")
        print(f"Comments  : {video['comments']:,}")
        print(f"Published : {video['published_at']}")
        print(f"Video     : {video['video_url']}")
        print("-" * 80)

    return videos


if __name__ == "__main__":
    run_agent()
