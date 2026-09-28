import os
import requests


def normalize_collection_target(raw_value):
    value = (raw_value or "").strip()
    if not value:
        return "", ""

    group_id_from_url = ""
    if "/groups/" in value:
        group_part = value.split("/groups/", 1)[1]
        group_id_from_url = group_part.split("/", 1)[0].strip()

    if "/collections/" in value:
        value = value.split("/collections/", 1)[1]
        value = value.split("/", 1)[0]

    value = value.split("?", 1)[0].split("#", 1)[0].strip()
    return value, group_id_from_url


# ============================================================
# Configuration
# ============================================================

GROUP_ID = os.environ["GROUP_ID"]
ZOTERO_API_KEY = os.environ["ZOTERO_API_KEY"]
SLACK_WEBHOOK = os.environ["SLACK_WEBHOOK"]
COLLECTION_KEY_RAW = (
    os.getenv("COLLECTION_KEY")
    or os.getenv("SUBCOLLECTION_KEY")
    or os.getenv("COLLECTION_ID")
    or ""
).strip()
COLLECTION_KEY, GROUP_ID_FROM_COLLECTION_URL = normalize_collection_target(COLLECTION_KEY_RAW)
ACTIVE_GROUP_ID = GROUP_ID_FROM_COLLECTION_URL or GROUP_ID

INCLUDE_SUBCOLLECTIONS = os.getenv("INCLUDE_SUBCOLLECTIONS", "false").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}


# ============================================================
# State file
# ============================================================

if COLLECTION_KEY:
    LAST_ITEM_FILE = f"last_item_{COLLECTION_KEY}.txt"
else:
    LAST_ITEM_FILE = "last_item_group.txt"


headers = {
    "Zotero-API-Key": ZOTERO_API_KEY
}


# ============================================================
# State functions
# ============================================================

def get_last_saved():
    """
    Return the last item key that was processed.

    If this is the first run for this group/collection,
    return None.
    """
    try:
        with open(LAST_ITEM_FILE, "r") as f:
            value = f.read().strip()

            if value:
                return value

    except FileNotFoundError:
        pass

    return None


def save_last(key):
    """
    Save the newest processed item key.
    """
    with open(LAST_ITEM_FILE, "w") as f:
        f.write(key)


# ============================================================
# Zotero helpers
# ============================================================

def format_authors(creators):
    """
    Convert Zotero creator information into a readable
    author string.
    """
    authors = []

    for creator in creators:
        if creator.get("creatorType") == "author":

            first = creator.get("firstName", "")
            last = creator.get("lastName", "")

            name = f"{first} {last}".strip()

            if name:
                authors.append(name)

    return ", ".join(authors) if authors else "Unknown authors"


def has_pdf(item_key):
    """
    Check whether a Zotero item has a PDF attachment.
    """

    url = (
        f"https://api.zotero.org/groups/"
        f"{ACTIVE_GROUP_ID}/items/{item_key}/children"
    )

    response = requests.get(
        url,
        headers=headers,
        timeout=30
    )

    if not response.ok:
        return False

    children = response.json()

    for child in children:

        data = child.get("data", {})

        if data.get("itemType") == "attachment":

            if data.get("contentType") == "application/pdf":
                return True

    return False


def get_items():
    """
    Retrieve the newest Zotero items.

    If COLLECTION_KEY is provided:
        retrieve items from that collection only.

    Otherwise:
        retrieve items from the entire group.
    """

    params = {
        "sort": "dateAdded",
        "direction": "desc",
        "limit": 20,
        "include": "data",
    }

    if not COLLECTION_KEY:
        print(f"Monitoring entire Zotero group: {ACTIVE_GROUP_ID}")
        url = f"https://api.zotero.org/groups/{ACTIVE_GROUP_ID}/items/top"
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        return response.json()

    print(f"Monitoring Zotero collection: {COLLECTION_KEY}")

    collection_keys = [COLLECTION_KEY]

    if INCLUDE_SUBCOLLECTIONS:
        queue = [COLLECTION_KEY]
        seen = set()

        while queue:
            current = queue.pop(0)
            if current in seen:
                continue

            seen.add(current)

            url = f"https://api.zotero.org/groups/{ACTIVE_GROUP_ID}/collections/{current}/collections"
            response = requests.get(
                url,
                headers=headers,
                params={"limit": 100, "format": "json"},
                timeout=30,
            )

            if not response.ok:
                if current == COLLECTION_KEY:
                    response.raise_for_status()
                continue

            for collection in response.json():
                key = collection.get("key")
                if key and key not in seen:
                    collection_keys.append(key)
                    queue.append(key)

    items = []
    seen_items = set()

    for collection_key in collection_keys:
        url = (
            f"https://api.zotero.org/groups/{ACTIVE_GROUP_ID}/collections/"
            f"{collection_key}/items/top"
        )

        response = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=30,
        )

        response.raise_for_status()

        for item in response.json():
            item_key = item.get("key")
            if item_key and item_key not in seen_items:
                seen_items.add(item_key)
                items.append(item)

    items.sort(
        key=lambda item: item.get("data", {}).get("dateAdded", ""),
        reverse=True,
    )

    return items


# ============================================================
# Slack
# ============================================================

def post_to_slack(message):
    """
    Send a message to Slack.
    """

    response = requests.post(
        SLACK_WEBHOOK,
        json=message,
        timeout=30
    )

    response.raise_for_status()


# ============================================================
# Main
# ============================================================

def main():

    last_seen = get_last_saved()

    items = get_items()

    if not items:

        print("No items found.")

        return


    # --------------------------------------------------------
    # First run
    # --------------------------------------------------------
    #
    # If there is no state file yet, simply record the newest
    # item and do NOT send Slack notifications.
    #
    # This prevents a new collection from generating alerts
    # for all of its existing items.
    # --------------------------------------------------------

    if last_seen is None:

        newest_key = items[0]["key"]

        save_last(newest_key)

        print(
            f"First run detected. "
            f"Saved newest item ({newest_key}) "
            f"without sending Slack alerts."
        )

        return


    # --------------------------------------------------------
    # Find new items
    # --------------------------------------------------------

    new_items = []

    for item in items:

        item_key = item["key"]

        # Ignore attachments and other non-item records.
        data = item.get("data", {})

        if data.get("itemType") == "attachment":
            continue

        # We have reached the last item we processed.
        if item_key == last_seen:
            break

        new_items.append(item)


    if not new_items:

        print("No new items.")

        return


    # --------------------------------------------------------
    # Process oldest → newest
    # --------------------------------------------------------

    new_items.reverse()


    for item in new_items:

        item_key = item["key"]

        data = item.get("data", {})
        meta = item.get("meta", {})


        # ----------------------------------------------------
        # Basic metadata
        # ----------------------------------------------------

        title = data.get(
            "title",
            "No title"
        )

        abstract = data.get(
            "abstractNote",
            ""
        ).strip()

        creators = data.get(
            "creators",
            []
        )

        doi = data.get(
            "DOI",
            ""
        ).strip()


        authors = format_authors(creators)


        # ----------------------------------------------------
        # User who added the item
        # ----------------------------------------------------

        created_by = meta.get(
            "createdByUser",
            {}
        )

        creator_name = created_by.get(
            "name",
            "Unknown user"
        )


        # ----------------------------------------------------
        # Zotero link
        # ----------------------------------------------------

        zotero_link = (
            f"https://www.zotero.org/groups/"
                f"{ACTIVE_GROUP_ID}/items/{item_key}"
        )


        # ----------------------------------------------------
        # PDF
        # ----------------------------------------------------

        pdf_status = (
            "Yes"
            if has_pdf(item_key)
            else "No"
        )


        # ----------------------------------------------------
        # Abstract
        # ----------------------------------------------------

        if not abstract:

            abstract = (
                "_No abstract available._"
            )


        # ----------------------------------------------------
        # DOI
        # ----------------------------------------------------

        if doi:

            doi_link = (
                f"https://doi.org/{doi}"
            )

            doi_text = (
                f"<{doi_link}|{doi}>"
            )

        else:

            doi_text = "Not available"


        # ----------------------------------------------------
        # Slack message
        # ----------------------------------------------------

        message = {

            "text":
                f"📚 *New Zotero item added*\n"

                f"*Title:* {title}\n"

                f"*Authors:* {authors}\n"

                f"*Added by:* {creator_name}\n"

                f"*DOI:* {doi_text}\n"

                f"*PDF attached:* {pdf_status}\n\n"

                f"*Abstract:*\n"
                f"{abstract[:1500]}\n\n"

                f"<{zotero_link}|Open in Zotero>"
        }


        # ----------------------------------------------------
        # Send
        # ----------------------------------------------------

        post_to_slack(message)

        print(
            f"Posted: {title}"
        )


    # --------------------------------------------------------
    # Save newest item
    # --------------------------------------------------------

    save_last(
        items[0]["key"]
    )

    print(
        f"State updated: {items[0]['key']}"
    )


# ============================================================
# Run
# ============================================================

if __name__ == "__main__":
    main()

