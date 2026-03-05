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

## Deploying on Fly.io

Fly.io runs the app as a real VM — no sleep, no dropped webhooks, and the in-memory result cache persists across requests. Deploys happen automatically on every push to `master` via GitHub Actions.

### One-time setup

1. **Install `flyctl`:**
   - macOS/Linux: `curl -L https://fly.io/install.sh | sh`
   - Windows (PowerShell): `iwr https://fly.io/install.ps1 -useb | iex`

2. **Login:** `flyctl auth login`

3. **Initialize the app** (run once from the project directory):
   ```bash
   flyctl launch
   ```
   This creates a `fly.toml` config file — commit it to the repo. Fly will auto-detect Python via nixpacks; no Dockerfile needed.

4. **Set your app secrets** (stored on Fly, never in GitHub):
   ```bash
   flyctl secrets set GROUPME_BOT_ID=xxx GROUPME_ACCESS_TOKEN=xxx \
     REDDIT_CLIENT_ID=xxx REDDIT_CLIENT_SECRET=xxx \
     REDDIT_USER_AGENT="groupme_bot/1.0 by u/username" \
     SUBREDDITS="gifs,funny,videos,aww" NSFW=false
   ```

5. **Add `FLY_API_TOKEN` to GitHub** — this allows GitHub Actions to deploy on your behalf:
   - Run `flyctl tokens create deploy` and copy the token
   - In your GitHub repo → *Settings* → *Secrets and variables* → *Actions* → add secret named `FLY_API_TOKEN`

6. **Push to `master`** — the GitHub Actions workflow (`.github/workflows/fly.yml`) will build and deploy automatically. Fly gives you a URL like `https://your-app.fly.dev`. Set the GroupMe bot's callback URL to `https://your-app.fly.dev/webhook` in the GroupMe developer portal.

All future deploys are automatic on push — no manual steps needed.

## Required credentials

See `.env.example`. Key ones:
- `GROUPME_BOT_ID` — from dev.groupme.com after creating a bot
- `GROUPME_ACCESS_TOKEN` — personal access token from dev.groupme.com (needed for image uploads)
- `REDDIT_CLIENT_ID` / `REDDIT_CLIENT_SECRET` — from reddit.com/prefs/apps (create a "script" app)
- `SUBREDDITS` — comma-separated, searched as a combined multi-subreddit
