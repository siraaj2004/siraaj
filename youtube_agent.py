import requests
from config import YOUTUBE_API_KEY


def get_trending_videos():

    url = (
        "https://www.googleapis.com/youtube/v3/videos"
        "?part=snippet"
        "&chart=mostPopular"
        "&regionCode=IN"
        "&maxResults=10"
        f"&key={YOUTUBE_API_KEY}"
    )

    try:
        response = requests.get(url)

        # Check API response
        if response.status_code != 200:
            print("YouTube API Error")
            print("Status Code:", response.status_code)
            return []

        data = response.json()

        videos = []

        for item in data.get("items", []):

            title = item["snippet"]["title"]
            channel = item["snippet"]["channelTitle"]

            video_data = {
                "title": title,
                "channel": channel
            }

            videos.append(video_data)

        return videos

    except Exception as error:
        print("Error fetching YouTube trends:")
        print(error)

        return []


# Test Run
if __name__ == "__main__":

    trending_videos = get_trending_videos()

    print("\nTrending YouTube Videos\n")

    for video in trending_videos:

        print("Title   :", video["title"])
        print("Channel :", video["channel"])
        print("-" * 50)
