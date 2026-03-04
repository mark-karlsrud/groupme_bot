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
        results = get_media_posts(keyword, SUBREDDITS, nsfw=NSFW)
        if not results:
            return None
        random.shuffle(results)
        _cache[keyword] = {"results": results, "index": 0}
        entry = _cache[keyword]

    result = entry["results"][entry["index"]]
    entry["index"] += 1
    return result


@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"status": "bad_request"}), 400

    # Ignore messages sent by bots (including ourselves)
    if data.get("sender_type") == "bot":
        return jsonify({"status": "ignored"}), 200

    text = data.get("text", "").strip()
    match = re.search(rf"(?i){re.escape(TRIGGER)}\s+(.+)", text)
    if not match:
        return jsonify({"status": "no_trigger"}), 200

    keyword = match.group(1).strip()
    print(f"[bot] Trigger received. Keyword: '{keyword}'")

    result = next_result(keyword)
    if not result:
        send_message(BOT_ID, f"Couldn't find anything for '{keyword}'.")
        return jsonify({"status": "no_results"}), 200

    media_type = result["type"]
    url = result["url"]
    title = result.get("title", "")

    if media_type == "video":
        attachment = {
            "type": "video",
            "url": url,
            "preview_url": result.get("preview_url") or url,
        }
        send_message(BOT_ID, title, attachment)
    else:
        # Images and GIFs must be hosted on GroupMe's CDN to embed properly
        groupme_url = upload_image(url, ACCESS_TOKEN)
        if groupme_url:
            send_message(BOT_ID, title, {"type": "image", "url": groupme_url})
        else:
            # Fallback: post raw URL as text if upload fails (e.g. no access token)
            send_message(BOT_ID, f"{title}\n{url}" if title else url)

    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    print(f"[bot] Starting on port {port}. Trigger: '{TRIGGER}'. Subreddits: {SUBREDDITS}. NSFW: {NSFW}")
    app.run(host="0.0.0.0", port=port, debug=False)
