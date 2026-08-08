"""
youtube_agent.py
Fetch trending YouTube videos using YouTube Data API v3.
"""

import os
from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

load_dotenv()

__all__ = ["get_trending_videos", "run_agent"]


def get_youtube():
    api_key = os.getenv("YOUTUBE_API_KEY")

    if not api_key:
        raise RuntimeError("YOUTUBE_API_KEY not found.")

    return build(
        "youtube",
        "v3",
        developerKey=api_key
    )


def get_trending_videos(region_code="IN", max_results=20):
    youtube = get_youtube()

    try:
        request = youtube.videos().list(
            part="snippet,statistics",
            chart="mostPopular",
            regionCode=region_code,
            maxResults=max_results
        )

        response = request.execute()

        videos = []

        for item in response.get("items", []):

            snippet = item.get("snippet", {})
            stats = item.get("statistics", {})

            videos.append(
                {
                    "title": snippet.get("title"),
                    "channel": snippet.get("channelTitle"),
                    "published_at": snippet.get("publishedAt"),
                    "views": int(stats.get("viewCount", 0)),
                    "likes": int(stats.get("likeCount", 0)),
                    "comments": int(stats.get("commentCount", 0)),
                    "video_id": item.get("id"),
                    "video_url": f"https://www.youtube.com/watch?v={item.get('id')}",
                    "thumbnail": snippet.get("thumbnails", {})
                    .get("high", {})
                    .get("url"),
                }
            )

        return videos

    except HttpError as e:
        raise RuntimeError(f"YouTube API Error: {e}")


def run_agent(region_code="IN", max_results=20):
    """
    Main function used by app.py
    """
    return get_trending_videos(
        region_code=region_code,
        max_results=max_results
    )


if __name__ == "__main__":

    try:
        videos = run_agent()

        print("=" * 80)
        print("🔥 Trending YouTube Videos")
        print("=" * 80)

        for i, video in enumerate(videos, 1):
            print(f"\n{i}. {video['title']}")
            print(f"Channel   : {video['channel']}")
            print(f"Views     : {video['views']:,}")
            print(f"Likes     : {video['likes']:,}")
            print(f"Comments  : {video['comments']:,}")
            print(f"Published : {video['published_at']}")
            print(f"URL       : {video['video_url']}")

    except Exception as e:
        print(e)
