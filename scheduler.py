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
        response = requests.get(url)

        if response.status_code == 200:

            data = response.json()

            print("\nTrending Videos:\n")

            for video in data.get("items", []):

                title = video["snippet"]["title"]
                channel = video["snippet"]["channelTitle"]

                print(f"Title   : {title}")
                print(f"Channel : {channel}")
                print("-" * 50)

        else:
            print("YouTube API Error")
            print("Status Code:", response.status_code)

    except Exception as error:
        print("Error:", error)


# Scheduler
scheduler = BlockingScheduler()

# Runs every 5 minutes
scheduler.add_job(run_youtube_trend_agent, "interval", minutes=5)

print("Scheduler started...")

# Run once immediately
run_youtube_trend_agent()

# Start scheduler
scheduler.start()
