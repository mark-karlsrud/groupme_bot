#!/usr/bin/python    
import configparser
import os
from flask import Flask, request
import requests
import random
import io

config = configparser.RawConfigParser()
config.read(os.path.join(os.path.dirname(__file__), 'groupme.properties'))

access_token = config.get('GroupMe', 'access_token')
bot_name = config.get('GroupMe', 'bot_name')

rapid_api_key = config.get('RapidApi', 'key')
rapid_api_safe_search = config.get('RapidApi', 'safe_search')

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
        if not send_bing_image(search_terms, bot_id):
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

def send_bing_image(search_terms, bot_id):
    url = "https://bing-image-search1.p.rapidapi.com/images/search"

    querystring = {
        "q": search_terms,
        "safeSearch": rapid_api_safe_search
    }

    headers = {
        "X-RapidAPI-Key": rapid_api_key,
        "X-RapidAPI-Host": "bing-image-search1.p.rapidapi.com"
    }

    response = requests.get(url, headers=headers, params=querystring)

    results = response.json()["value"]
    random.shuffle(results)
    for result in results:
        image_url = result["contentUrl"]
        try:
            if image_url:
                reply(image_url, bot_id)
                return True
        except Exception as e:
            print(e)
    return False

################################################################################

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=config.get('Server', 'port'))
