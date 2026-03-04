import os
from typing import Optional
import praw


def _get_reddit():
    return praw.Reddit(
        client_id=os.getenv("REDDIT_CLIENT_ID"),
        client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
        user_agent=os.getenv("REDDIT_USER_AGENT", "groupme_bot/1.0"),
        read_only=True,
    )


def _extract_media(post) -> Optional[dict]:
    url = post.url

    # Reddit-hosted video (v.redd.it DASH)
    if getattr(post, "is_video", False) and post.media and "reddit_video" in post.media:
        video_url = post.media["reddit_video"]["fallback_url"].split("?")[0]
        preview_url = None
        if getattr(post, "preview", None):
            images = post.preview.get("images", [])
            if images:
                preview_url = images[0].get("source", {}).get("url", "").replace("&amp;", "&")
        return {"url": video_url, "type": "video", "preview_url": preview_url, "title": post.title}

    # Imgur .gifv → mp4
    if "imgur.com" in url and url.endswith(".gifv"):
        return {"url": url.replace(".gifv", ".mp4"), "type": "video", "preview_url": None, "title": post.title}

    # Direct mp4
    if url.endswith(".mp4"):
        return {"url": url, "type": "video", "preview_url": None, "title": post.title}

    # Direct image/gif
    if url.endswith((".jpg", ".jpeg", ".png")):
        return {"url": url, "type": "image", "preview_url": url, "title": post.title}

    if url.endswith(".gif"):
        return {"url": url, "type": "gif", "preview_url": url, "title": post.title}

    # i.redd.it hosted images
    if "i.redd.it" in url:
        media_type = "gif" if url.endswith(".gif") else "image"
        return {"url": url, "type": media_type, "preview_url": url, "title": post.title}

    # Imgur single image (no album, no extension) — append .jpg for direct link
    if "imgur.com" in url and "/a/" not in url and "/gallery/" not in url:
        direct = url if url.endswith((".jpg", ".jpeg", ".png", ".gif")) else url + ".jpg"
        return {"url": direct, "type": "image", "preview_url": direct, "title": post.title}

    # Fallback: use post preview image if available
    if getattr(post, "preview", None) and not getattr(post, "is_video", False):
        images = post.preview.get("images", [])
        if images:
            preview_url = images[0].get("source", {}).get("url", "").replace("&amp;", "&")
            if preview_url:
                return {"url": preview_url, "type": "image", "preview_url": preview_url, "title": post.title}

    return None


def get_media_posts(keyword: str, subreddits: list, limit: int = 50, nsfw: bool = False) -> list:
    reddit = _get_reddit()
    results = []
    subreddit_str = "+".join(subreddits)

    try:
        sub = reddit.subreddit(subreddit_str)
        for post in sub.search(keyword, sort="relevance", time_filter="all", limit=limit, include_over_18=nsfw):
            if not nsfw and post.over_18:
                continue
            media = _extract_media(post)
            if media:
                results.append(media)
    except Exception as e:
        print(f"[reddit] Search error for '{keyword}': {e}")

    return results
