# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the bot

```bash
pip install -r requirements.txt
cp .env.example .env   # fill in credentials
python app.py
```

The server listens on `POST /webhook`. GroupMe must be configured to POST to this URL (set in the GroupMe developer portal when creating the bot).

For local development, expose the server with a tunnel (e.g. `ngrok http 5000`) and paste that URL as the bot's callback URL.

## Architecture

Three modules with clear responsibilities:

- **`app.py`** — Flask webhook handler. Parses the incoming GroupMe message for the trigger pattern (`@bot <keyword>`), drives the result cache, and dispatches to `groupme_client`.
- **`reddit_search.py`** — Uses PRAW (read-only) to search a multi-subreddit (`sub1+sub2+...`) and extracts media metadata. Returns a list of dicts: `{url, type, preview_url, title}` where `type` is `"image"`, `"gif"`, or `"video"`.
- **`groupme_client.py`** — Two functions: `send_message` (bot post API) and `upload_image` (downloads from source URL, re-uploads to GroupMe's image CDN). GroupMe only embeds images hosted at `i.groupme.com`, so the upload step is required for images/GIFs.

## Shuffling / result cycling

`app.py` maintains an in-memory `_cache` dict keyed by lowercase keyword. Each entry holds a shuffled list of results and a cursor index. When the cursor reaches the end, the results are re-fetched and re-shuffled. This means each keyword cycles through all Reddit results before repeating.

## Media type handling

- **Images / GIFs**: uploaded to GroupMe image service (`image.groupme.com/pictures`) using `GROUPME_ACCESS_TOKEN`, then sent as `{"type": "image", "url": "https://i.groupme.com/..."}` attachment.
- **Videos (MP4)**: sent as `{"type": "video", "url": "...", "preview_url": "..."}` attachment using the direct MP4 URL — no upload needed.
- Reddit-hosted videos (`v.redd.it`): the `fallback_url` from `post.media['reddit_video']` is a direct MP4.
- Imgur `.gifv` links are converted to `.mp4`.
- If image upload fails (missing token or network error), falls back to posting the raw URL as text.

## Deploying on Koyeb

Koyeb's free tier is always-on (no sleep), has no outbound network restrictions, and auto-installs `requirements.txt`.

1. **Push code to GitHub** (make sure `.env` is in `.gitignore` — it is).

2. **Sign up** at [koyeb.com](https://www.koyeb.com) and create a new **Web Service** → *Deploy from GitHub* → select your repo.

3. **Configure the service:**
   - **Run command:** `python app.py`
   - **Port:** `5000`

4. **Add environment variables** — In the *Environment* tab, add each key from `.env.example` with your actual values.

5. **Deploy** — Koyeb gives you a public URL like `https://your-app.koyeb.app`. Set the GroupMe bot's callback URL to `https://your-app.koyeb.app/webhook` in the GroupMe developer portal.

To redeploy after changes, just push to GitHub — Koyeb redeploys automatically.

## Required credentials

See `.env.example`. Key ones:
- `GROUPME_BOT_ID` — from dev.groupme.com after creating a bot
- `GROUPME_ACCESS_TOKEN` — personal access token from dev.groupme.com (needed for image uploads)
- `REDDIT_CLIENT_ID` / `REDDIT_CLIENT_SECRET` — from reddit.com/prefs/apps (create a "script" app)
- `SUBREDDITS` — comma-separated, searched as a combined multi-subreddit
