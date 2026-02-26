import requests
import os

GROUP_ID = os.environ["GROUP_ID"]
ZOTERO_API_KEY = os.environ["ZOTERO_API_KEY"]
SLACK_WEBHOOK = os.environ["SLACK_WEBHOOK"]

LAST_ITEM_FILE = "last_item.txt"

headers = {"Zotero-API-Key": ZOTERO_API_KEY}

def get_last_saved():
    try:
        with open(LAST_ITEM_FILE, "r") as f:
            return f.read().strip()
    except:
        return "none"

def save_last(key):
    with open(LAST_ITEM_FILE, "w") as f:
        f.write(key)

def main():
    last_seen = get_last_saved()

    url = f"https://api.zotero.org/groups/{GROUP_ID}/items/top?sort=dateAdded&direction=desc&limit=1"
    r = requests.get(url, headers=headers)
    r.raise_for_status()

    items = r.json()
    if not items:
        print("No items found.")
        return

    item = items[0]
    item_key = item["key"]

    if item_key == last_seen:
        print("No new items.")
        return

    data = item["data"]
    title = data.get("title", "No title")
    abstract = data.get("abstractNote", "No abstract available")

    message = {
        "text": f"📚 *New Zotero item added*\n"
                f"*{title}*\n\n"
                f"*Abstract:*\n{abstract[:1500]}"
    }

    requests.post(SLACK_WEBHOOK, json=message)

    save_last(item_key)
    print("Posted new item.")

if __name__ == "__main__":
    main()