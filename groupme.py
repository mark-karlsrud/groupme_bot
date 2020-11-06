#!/usr/bin/python    
import configparser
import os
from flask import Flask, request
import requests
import random
import praw
import io
from bs4 import BeautifulSoup

config = configparser.RawConfigParser()
config.read(os.path.join(os.path.dirname(__file__), 'groupme.properties'))

subreddits = config.get('Reddit', 'subreddits')
backup_subreddit = config.get('Reddit', 'backup_subreddit')

access_token = config.get('GroupMe', 'access_token')
bot_name = config.get('GroupMe', 'bot_name')

reddit_id = config.get('Reddit', 'reddit_id')
reddit_secret = config.get('Reddit', 'reddit_secret')
reddit_username = config.get('Reddit', 'reddit_username')
reddit_token = config.get('Reddit', 'reddit_token')
reddit_useragent = 'rpi:com.' + reddit_username + '.groupme:v1 (by /u/' + reddit_username + ')'
reddit_nsfw = config.get('Reddit', 'reddit_nsfw')

reddit = praw.Reddit(client_id=reddit_id, client_secret=reddit_secret, user_agent=reddit_useragent)
reddit.read_only = True

app = Flask(__name__)

# Called every time a message is sent in the group
@app.route('/groupme/<channel>', methods=['POST'])
def webhook(channel):
    # 'message' is an object that represents a single GroupMe message.
    message = request.get_json()
    if sender_is_bot(message):
        return "ok", 200
    bot_id = config.get('GroupMeRooms', channel)

    text = message['text']
    if text.startswith('@' + bot_name):
        search_terms = text.replace('@' + bot_name,'')
        if not send_reddit_image(search_terms, bot_id):
            if not send_reddit_image_subreddit(search_terms, bot_id, backup_subreddit):
                reply("Can't help you there...", bot_id)
    
    print('returning...')
    return "ok", 200

################################################################################

def send_error(message):
    bod_id = config.get('GroupMeRooms', 'test')
    reply('error: ' + str(message), bod_id)

# Send a message in the groupchat
def reply(msg, bot_id):
    url = 'https://api.groupme.com/v3/bots/post'
    body = {
        'bot_id'                : bot_id,
        'text'                  : msg
    }
    requests.post(url, json=body)

# Send a message with an image attached in the groupchat
def reply_with_image(msg, imgURL, bot_id):
    url = 'https://api.groupme.com/v3/bots/post'
    urlOnGroupMeService = upload_image_to_groupme(imgURL)
    body = {
        'bot_id'                : bot_id,
        'text'                  : msg,
        'picture_url'           : urlOnGroupMeService
    }
    requests.post(url, json=body)
    return urlOnGroupMeService
        
# Uploads image to GroupMe's services and returns the new URL
def upload_image_to_groupme(imgURL):
    imgRequest = requests.get(imgURL, stream=True)
    for response in imgRequest.history:
        if response.status_code == 302:
            return
    print(imgURL)
    if imgRequest.status_code == 200:
        # Upload Image
        url = 'https://image.groupme.com/pictures'
        streamFile = io.BytesIO(imgRequest.content).getvalue()
        files = {'file': streamFile}
        payload = {'access_token': access_token}
        r = requests.post(url, files=files, params=payload)
        imageurl = r.json()['payload']['url']
        return imageurl

# Checks whether the message sender is a bot
def sender_is_bot(message):
        return message['sender_type'] == "bot"

################################################################################

def send_reddit_image(search_terms, bot_id):
    return send_reddit_image_subreddit(search_terms, bot_id, subreddits.replace(',','+'))

def send_reddit_image_subreddit(search_terms, bot_id, subreddits):
    results = list(reddit.subreddit(subreddits).search(search_terms, params={'include_over_18': reddit_nsfw}))
    random.shuffle(results)
    for result in results:
        image_url = result.url
        try:
            # print(str(vars(result)))
            if image_url:
                if 'gfycat' in image_url:
                    print('gfycat: ' + image_url)
                    try:
                        # get redirected url
                        response = requests.get(image_url)
                        print('redirected gfycat: ' + response.url)
                        gifSource = BeautifulSoup(response.content, 'html.parser').find(id='gifSource')['src']
                        print('gifSource: ' + gifSource)
                        reply(gifSource, bot_id)
                        reply('source: ' + response.url, bot_id)
                        return True
                    except Exception as e:
                        print('gfycat exception: ' + e)
                else:
                    if image_url.endswith('.gifv'):
                        print('streaming image: ' + image_url)
                        if reply_with_image('', image_url, bot_id):
                            return True
                    else:
                        print('returning image: ' + image_url)
                        reply(image_url, bot_id) # For most devices, the groupme app will automatically load the image within the app.
                        reply('source: ' + image_url, bot_id) # For devices where this doesn't work, provide the source URL
                        return True
            else:
                #TODO fallback to other site?
                send_error('no image url')
        except Exception as e:
            print(e)
    return False

"""
def get_gfycat_url(url):
        base_url = 'https://api.gfycat.com/v1/gfycats/'
        id = url.split('/')[-1]
        response = requests.get(base_url + id)
        if response.status_code == 200:
            return response.json()['gfyItem']['gifUrl']
        else:
            send_error(response.status_code)
            return None
"""

################################################################################

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=config.get('Server', 'port'))
