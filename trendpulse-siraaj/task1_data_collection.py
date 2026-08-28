import requests
import json
import time
from pathlib import Path
from datetime import datetime

# HackerNews API URLs

TOP_STORIES_URL = "https://hacker-news.firebaseio.com/v0/topstories.json"
ITEM_URL = "https://hacker-news.firebaseio.com/v0/item/{}.json"

# Required header for API requests

HEADERS = {
"User-Agent": "TrendPulse/1.0"
}

# Keywords used to classify stories

CATEGORIES = {
"technology": [
"ai", "software", "tech", "code", "computer",
"data", "cloud", "api", "gpu", "llm"
],

"worldnews": [
    "war", "government", "country", "president",
    "election", "climate", "attack", "global"
],

"sports": [
    "nfl", "nba", "fifa", "sport", "game",
    "team", "player", "league", "championship"
],

"science": [
    "research", "study", "space", "physics",
    "biology", "discovery", "nasa", "genome"
],

"entertainment": [
    "movie", "film", "music", "netflix",
    "game", "book", "show", "award", "streaming"
]

}

def get_top_story_ids():
    """
    Fetch the list of top HackerNews story IDs.
    Returns only the first 500 IDs.
    """

    try:
        response = requests.get(
            TOP_STORIES_URL,
            headers=HEADERS,
            timeout=10
        )

        response.raise_for_status()

        story_ids = response.json()

        # Requirement: fetch the first 500 story IDs
        return story_ids[:500]

    except requests.RequestException as error:
        print(f"Failed to fetch top stories: {error}")
        return []

def get_story_details(story_id):
    """
    Fetch details for one HackerNews story.
    """

    try:
        url = ITEM_URL.format(story_id)

        response = requests.get(
            url,
            headers=HEADERS,
            timeout=10
        )

        response.raise_for_status()

        return response.json()

    except requests.RequestException as error:
        print(f"Failed to fetch story {story_id}: {error}")
        return None

def find_categories(title):
    """
    Check the story title against every category.

    A story can belong to more than one category because
    some keywords, such as 'game', may appear in multiple
    category keyword lists.
    """

    if not title:
        return []

    title_lower = title.lower()
    matched_categories = []

    for category, keywords in CATEGORIES.items():

        for keyword in keywords:

            # Case-insensitive keyword matching
            if keyword.lower() in title_lower:
                matched_categories.append(category)
                break

    return matched_categories

def collect_stories():
    """
    Fetch top stories and collect a maximum of
    25 stories for each category.
    """

    story_ids = get_top_story_ids()

    if not story_ids:
        print("No story IDs were fetched.")
        return []

    # Store collected stories
    collected_stories = []

    # Keep track of how many stories each category has
    category_counts = {
        category: 0
        for category in CATEGORIES
    }

    # Cache story details so the same API story is not
    # requested again unnecessarily
    story_cache = {}

    # Process one category at a time.
    # This also makes the required 2-second sleep easy to apply.
    for category, keywords in CATEGORIES.items():

        print(f"\nCollecting {category} stories...")

        for story_id in story_ids:

            # Stop when this category has 25 stories
            if category_counts[category] >= 25:
                break

            # Fetch the story only once
            if story_id not in story_cache:
                story_cache[story_id] = get_story_details(story_id)

            story = story_cache[story_id]

            # Skip failed or deleted stories
            if not story:
                continue

            # Only collect HackerNews stories
            if story.get("type") != "story":
                continue

            title = story.get("title", "")

            # Check whether this story belongs to the
            # current category
            title_lower = title.lower()

            matched = False

            for keyword in keywords:
                if keyword.lower() in title_lower:
                    matched = True
                    break

            if not matched:
                continue

            # Create a dictionary with all 7 required fields
            story_data = {
                "post_id": story.get("id"),
                "title": title,
                "category": category,
                "score": story.get("score", 0),
                "num_comments": story.get("descendants", 0),
                "author": story.get("by", "unknown"),
                "collected_at": datetime.now().isoformat()
            }

            collected_stories.append(story_data)

            category_counts[category] += 1

        print(
            f"{category}: "
            f"{category_counts[category]} stories collected"
        )

        # Requirement:
        # Wait 2 seconds between each category,
        # not between individual story requests.
        time.sleep(2)

    return collected_stories

def save_to_json(stories):
    """
    Create the data folder if necessary and save
    the collected stories to a date-based JSON file.
    """

    # Create data folder
    data_folder = Path("data")
    data_folder.mkdir(exist_ok=True)

    # Create filename using today's date
    date_string = datetime.now().strftime("%Y%m%d")

    file_path = data_folder / f"trends_{date_string}.json"

    try:
        with open(
            file_path,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                stories,
                file,
                indent=4,
                ensure_ascii=False
            )

        print(
            f"\nCollected {len(stories)} stories. "
            f"Saved to {file_path}"
        )

    except OSError as error:
        print(f"Failed to save JSON file: {error}")

def main():
    """
    Main function that runs the complete
    TrendPulse data collection pipeline.
    """

    print("=" * 50)
    print("TRENDPULSE DATA COLLECTION")
    print("=" * 50)

    stories = collect_stories()

    if stories:
        save_to_json(stories)
    else:
        print("No stories were collected.")

if __name__ == "__main__":
    main()
