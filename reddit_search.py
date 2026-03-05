import os
from typing import Optional
import praw


def _get_reddit():
    refresh_token = os.getenv("REDDIT_REFRESH_TOKEN")
    if refresh_token:
        return praw.Reddit(
            client_id=os.getenv("REDDIT_CLIENT_ID"),
            client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
            user_agent=os.getenv("REDDIT_USER_AGENT", "groupme_bot/1.0"),
            refresh_token=refresh_token,
        )
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


def _collect_media(posts, keyword: str, nsfw: bool) -> list:
    results = []
    total = skipped_nsfw = skipped_no_media = 0
    kw = keyword.lower()
    for post in posts:
        total += 1
        if not nsfw and post.over_18:
            skipped_nsfw += 1
            continue
        media = _extract_media(post)
        if media:
            results.append(media)
        else:
            skipped_no_media += 1
    print(f"[reddit] {total} posts scanned, {len(results)} with media, {skipped_nsfw} skipped (nsfw), {skipped_no_media} skipped (no media)")
    return results


def get_media_posts(keyword: str, subreddits: list, limit: int = 50, nsfw: bool = False) -> list:
    reddit = _get_reddit()
    subreddit_str = "+".join(subreddits)

    try:
        sub = reddit.subreddit(subreddit_str)

        # Try search first
        print(f"[reddit] Searching r/{subreddit_str} for '{keyword}'")
        results = _collect_media(
            sub.search(keyword, sort="relevance", time_filter="all", limit=limit),
            keyword, nsfw
        )

        # Reddit blocks search on NSFW subreddits anonymously — fall back to hot/top filtered by title
        if not results:
            print(f"[reddit] Search returned nothing — falling back to hot/top filtered by title keyword")
            kw = keyword.lower()
            candidates = list(sub.hot(limit=limit)) + list(sub.top(time_filter="month", limit=limit))
            matching = [p for p in candidates if kw in p.title.lower()]
            results = _collect_media(matching if matching else candidates, keyword, nsfw)
            if not matching:
                print(f"[reddit] No title matches for '{keyword}' — returning unfiltered hot/top results")

    except Exception as e:
        print(f"[reddit] Failed for '{keyword}': {type(e).__name__}: {e}")
        return []

    return results
