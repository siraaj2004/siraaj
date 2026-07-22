"""
youtube_agent.py

- Lazily creates the YouTube Data API client so importing this module doesn't
  fail when the API key is missing.
- Exposes get_trending_videos(...) and a compatibility wrapper run_agent(...).
- Raises clear errors when YOUTUBE_API_KEY is not set.
"""

from typing import List, Dict, Optional
import os

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv

load_dotenv()


__all__ = ["get_trending_videos", "run_agent"]


def _get_api_key() -> str:
    """Return the YOUTUBE_API_KEY from env or raise a clear error."""
    api_key = os.getenv("YOUTUBE_API_KEY")
    if not api_key:
        raise RuntimeError(
            "YOUTUBE_API_KEY environment variable is not set. "
            "Set it in your environment or in the workflow/secrets."
        )
    return api_key


def _get_youtube_client():
    """Create and return a googleapiclient.discovery.Resource for YouTube."""
    api_key = _get_api_key()
    return build("youtube", "v3", developerKey=api_key)


def get_trending_videos(
    region_code: str = "IN",
    max_results: int = 20,
) -> List[Dict[str, Optional[object]]]:
    """
    Returns the current trending YouTube videos.

    Args:
      region_code: ISO 3166-1 alpha-2 country code (e.g., "US", "IN").
      max_results: number of results to return (max 50 per API restrictions).

    Returns:
      A list of dicts with keys: title, channel, published_at, views, likes,
      comments, video_url, thumbnail.

    Raises:
      RuntimeError if API key missing, HttpError for API errors.
    """
    if max_results < 1:
        raise ValueError("max_results must be >= 1")
    if max_results > 50:
        # YouTube API maxResults allowed is 50 for this endpoint
        max_results = 50

    youtube = _get_youtube_client()

    try:
        response = (
            youtube.videos()
            .list(
                part="snippet,statistics",
                chart="mostPopular",
                regionCode=region_code,
                maxResults=max_results,
            )
            .execute()
        )
    except HttpError as e:
        # Bubble up a descriptive error for CI logs
        raise RuntimeError(f"YouTube Data API request failed: {e}") from e

    videos: List[Dict[str, Optional[object]]] = []

    for item in response.get("items", []):
        snippet = item.get("snippet", {})
        stats = item.get("statistics", {})

        # Defensive extraction with defaults
        title = snippet.get("title", "<no title>")
        channel = snippet.get("channelTitle", "<unknown channel>")
        published_at = snippet.get("publishedAt")
        # statistics fields are strings per API; convert with fallback
        def _int(val):
            try:
                return int(val)
            except Exception:
                return 0

        views = _int(stats.get("viewCount", 0))
        likes = _int(stats.get("likeCount", 0))
        comments = _int(stats.get("commentCount", 0))

        video_id = item.get("id") or item.get("id", "")
        video_url = f"https://www.youtube.com/watch?v={video_id}"

        # thumbnail selection: prefer high, then default to any available url
        thumbnail = None
        thumbs = snippet.get("thumbnails", {}) or {}
        if "high" in thumbs and thumbs["high"].get("url"):
            thumbnail = thumbs["high"]["url"]
        else:
            # pick first available thumbnail url if present
            for t in thumbs.values():
                if isinstance(t, dict) and t.get("url"):
                    thumbnail = t["url"]
                    break

        videos.append(
            {
                "title": title,
                "channel": channel,
                "published_at": published_at,
                "views": views,
                "likes": likes,
                "comments": comments,
                "video_url": video_url,
                "thumbnail": thumbnail,
            }
        )

    return videos


def run_agent(region_code: str = "IN", max_results: int = 20) -> List[Dict[str, Optional[object]]]:
    """
    Compatibility wrapper expected by callers that import `run_agent` from this module.

    Returns the same output as get_trending_videos.
    """
    return get_trending_videos(region_code=region_code, max_results=max_results)


if __name__ == "__main__":
    try:
        videos = run_agent(max_results=10)
    except Exception as e:
        # Print a helpful message for local runs / CI logs
        print("Error:", e)
        raise

    print("=" * 80)
    print("🔥 Trending YouTube Videos")
    print("=" * 80)

    for i, video in enumerate(videos, start=1):
        print(f"\n{i}. {video['title']}")
        print(f"Channel   : {video['channel']}")
        print(f"Views     : {video['views']:,}")
        print(f"Likes     : {video['likes']:,}")
        print(f"Comments  : {video['comments']:,}")
        print(f"Published : {video['published_at']}")
        print(f"Video     : {video['video_url']}")
