from apscheduler.schedulers.blocking import BlockingScheduler
from datetime import datetime
import requests

from config import YOUTUBE_API_KEY


def run_youtube_trend_agent():
    print("\nRunning YouTube Trend Agent")
    print("Time:", datetime.now())

    url = (
        "https://www.googleapis.com/youtube/v3/videos"
        "?part=snippet"
        "&chart=mostPopular"
        "&regionCode=IN"
        "&maxResults=5"
        f"&key={YOUTUBE_API_KEY}"
    )

    try:
        response = requests.get(url, timeout=20)
        response.raise_for_status()

        data = response.json()

        print("\nTrending Videos:\n")

        for video in data.get("items", []):
            print("Title   :", video["snippet"]["title"])
            print("Channel :", video["snippet"]["channelTitle"])
            print("-" * 50)

    except Exception as e:
        print("Error:", e)


if __name__ == "__main__":
    scheduler = BlockingScheduler()

    run_youtube_trend_agent()

    scheduler.add_job(
        run_youtube_trend_agent,
        trigger="interval",
        minutes=5
    )

    print("Scheduler started...")
    scheduler.start()