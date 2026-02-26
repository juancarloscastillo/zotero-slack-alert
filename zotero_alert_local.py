import requests
import time

GROUP_ID = "6308411"
ZOTERO_API_KEY = "zzdhXdyeeO2ujQuR75OxwhjC"
SLACK_WEBHOOK = ""

headers = {
    "Zotero-API-Key": ZOTERO_API_KEY
}

last_seen = None

def get_latest_item():
    url = f"https://api.zotero.org/groups/{GROUP_ID}/items?sort=dateAdded&direction=desc&limit=1"
    r = requests.get(url, headers=headers)
    r.raise_for_status()
    return r.json()[0]

def send_to_slack(title, creators, abstract, url):
    message = {
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*📚 New Zotero Item Added*\n*{title}*"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Authors:* {creators}"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Abstract:*\n{abstract[:3000]}"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"<{url}|Open in Zotero>"
                }
            }
        ]
    }

    requests.post(SLACK_WEBHOOK, json=message)

while True:
    item = get_latest_item()
    item_key = item["key"]

    if item_key != last_seen:
        last_seen = item_key

        data = item["data"]
        title = data.get("title", "No title")
        abstract = data.get("abstractNote", "No abstract available")
        url = data.get("url", "")
        
        creators = ", ".join(
            f"{c.get('lastName','')}"
            for c in data.get("creators", [])
        )

        send_to_slack(title, creators, abstract, url)

    time.sleep(300)