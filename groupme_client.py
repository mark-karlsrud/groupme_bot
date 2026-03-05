import requests

BOT_POST_URL = "https://api.groupme.com/v3/bots/post"
IMAGE_UPLOAD_URL = "https://image.groupme.com/pictures"

def send_message(bot_id: str, text: str, attachment: dict = None):
    payload = {"bot_id": bot_id, "text": text or " "}
    if attachment:
        payload["attachments"] = [attachment]
    try:
        resp = requests.post(BOT_POST_URL, json=payload, timeout=10)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"[groupme] Send failed: {e} | payload={payload}")


def upload_image(image_url: str, access_token: str) -> str | None:
    """
    Downloads an image from image_url and re-uploads it to GroupMe's image service.
    Returns the GroupMe-hosted picture_url, or None on failure.
    Required for image attachments — GroupMe only embeds i.groupme.com URLs.
    """
    if not access_token:
        return None
    try:
        img_resp = requests.get(image_url, timeout=15, headers={"User-Agent": "groupme_bot/1.0"})
        img_resp.raise_for_status()
        content_type = img_resp.headers.get("Content-Type", "image/jpeg").split(";")[0]

        upload_resp = requests.post(
            IMAGE_UPLOAD_URL,
            headers={"X-Access-Token": access_token, "Content-Type": content_type},
            data=img_resp.content,
            timeout=30,
        )
        upload_resp.raise_for_status()
        return upload_resp.json()["payload"]["picture_url"]
    except Exception as e:
        print(f"[groupme] Image upload failed ({image_url}): {type(e).__name__}: {e}")
        return None
