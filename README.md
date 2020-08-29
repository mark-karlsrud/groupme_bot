# GroupMe Bot

A bot to reply with an image or image link related to your search terms.

## How to use
In a GroupMe rooms, type `@computer <search terms>`

## Setup
1. Create a GroupMe application here: https://dev.groupme.com/
2. In `groupme.properties`, set the `access_token`
3. Create a bot for each room here: https://dev.groupme.com/bots
4. In `groupme.properties`, add the Bot ID to the rooms list like this:
```
room_name=bod_id
```
5. Figure out your public IP address of the device you will be running this code on
https://www.whatismyip.com/what-is-my-public-ip-address/
6. Open the port
https://www.noip.com/support/knowledgebase/general-port-forwarding-guide/
7. Set the Callback URL for each bot to `http://<your_ip_address>/groupme/<room_name>`
8. Register a Reddit app
https://www.reddit.com/wiki/api#wiki_reddit_api_access
9. Update `groupme.properties` with `reddit_id`, `reddit_secret`, `reddit_username`, `reddit_token`
10. Configure as you please the following: `reddit_nsfw`, `subreddits`, `backup_subreddit`, `bot_name`

## How to run
`python3 groupme.py`
You may need to install the appropriate python packages.
