import os
import random
import re

from dotenv import load_dotenv
from flask import Flask, jsonify, request

from groupme_client import send_message, upload_image
from reddit_search import get_media_posts

load_dotenv()

app = Flask(__name__)

BOT_ID = os.getenv("GROUPME_BOT_ID")
ACCESS_TOKEN = os.getenv("GROUPME_ACCESS_TOKEN")
SUBREDDITS = [s.strip() for s in os.getenv("SUBREDDITS", "gifs,funny,videos,aww").split(",")]
TRIGGER = os.getenv("BOT_TRIGGER", "@bot").lower()
NSFW = os.getenv("NSFW", "false").lower() == "true"

# Per-keyword cache: keyword -> {"results": [...shuffled...], "index": int}
_cache: dict = {}


def next_result(keyword: str) -> dict | None:
    """
    Returns the next media result for a keyword, cycling through a shuffled list.
    Re-fetches and re-shuffles once all results have been exhausted.
    """
    entry = _cache.get(keyword)
    if not entry or entry["index"] >= len(entry["results"]):
        print(f"[reddit] Searching for '{keyword}' across r/{'+'.join(SUBREDDITS)} (NSFW={NSFW})")
        results = get_media_posts(keyword, SUBREDDITS, nsfw=NSFW)
        if not results:
            print(f"[reddit] No media found for '{keyword}'")
            return None
        random.shuffle(results)
        _cache[keyword] = {"results": results, "index": 0}
        entry = _cache[keyword]
        print(f"[reddit] Found {len(results)} media result(s) for '{keyword}'")

    result = entry["results"][entry["index"]]
    total = len(entry["results"])
    print(f"[reddit] Serving result {entry['index'] + 1}/{total} for '{keyword}': [{result['type']}] {result['url']}")
    entry["index"] += 1
    return result


@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"status": "bad_request"}), 400

    sender_type = data.get("sender_type")
    sender_name = data.get("name", "unknown")
    text = data.get("text", "").strip()

    if sender_type == "bot":
        return jsonify({"status": "ignored"}), 200

    print(f"[webhook] From '{sender_name}': {text!r}")

    match = re.search(rf"(?i){re.escape(TRIGGER)}\s+(.+)", text)
    if not match:
        return jsonify({"status": "no_trigger"}), 200

    keyword = match.group(1).strip()
    print(f"[webhook] Trigger matched — keyword: '{keyword}'")

    result = next_result(keyword)
    if not result:
        send_message(BOT_ID, f"Couldn't find anything for '{keyword}'.")
        return jsonify({"status": "no_results"}), 200

    media_type = result["type"]
    url = result["url"]
    title = result.get("title", "")

    if media_type == "video":
        # GroupMe bot API doesn't support video attachments — send thumbnail as image + URL as text
        preview_url = result.get("preview_url")
        text_body = f"{title}\n{url}" if title else url
        if preview_url:
            print(f"[groupme] Uploading video thumbnail to GroupMe CDN...")
            groupme_url = upload_image(preview_url, ACCESS_TOKEN)
            if groupme_url:
                print(f"[groupme] Sending video thumbnail + URL")
                send_message(BOT_ID, text_body, {"type": "image", "url": groupme_url})
            else:
                print(f"[groupme] Thumbnail upload failed — sending URL as text")
                send_message(BOT_ID, text_body)
        else:
            print(f"[groupme] No thumbnail — sending video URL as text")
            send_message(BOT_ID, text_body)
    else:
        print(f"[groupme] Uploading {media_type} to GroupMe CDN...")
        groupme_url = upload_image(url, ACCESS_TOKEN)
        if groupme_url:
            print(f"[groupme] Upload success — sending image attachment")
            send_message(BOT_ID, title, {"type": "image", "url": groupme_url})
        else:
            print(f"[groupme] Upload failed — sending raw URL as text")
            send_message(BOT_ID, f"{title}\n{url}" if title else url)

    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    print(f"[bot] Starting — port={port} trigger='{TRIGGER}' subreddits={SUBREDDITS} nsfw={NSFW}")
    app.run(host="0.0.0.0", port=port, debug=False)
