from flask import Flask, request
import requests
import re
from datetime import datetime
import os
import urllib.parse

twitter_regex = "((https?):\/\/)?(www.)?twitter\.com(\/@?(\w){1,15})\/status\/([0-9]{19})"
tiktok_regex = r"(?:http(?:s)?:\/\/)?(?:(?:www)\.(?:tiktok\.com)(?:\/)(?!foryou)(@[a-zA-z0-9]+)(?:\/)(?:video)(?:\/)([\d]+)|(?:m)\.(?:tiktok\.com)(?:\/)(?!foryou)(?:v)(?:\/)?(?=([\d]+)\.html))"
instagram_regex = "(?:https?:\/\/)?(?:www.)?instagram.com\/?([a-zA-Z0-9\.\_\-]+)?\/([p]+)?([reel]+)?([tv]+)?([stories]+)?\/([a-zA-Z0-9\-\_\.]+)\/?([0-9]+)?"

app = Flask(__name__)

def get_tweet_video(tweet_url: str):
    match = re.match(twitter_regex, tweet_url)
    if match is not None:
        tweet_id = match.groups()[-1]
        tweet_media_resp = requests.get(f"https://cdn.syndication.twimg.com/tweet-result?id={tweet_id}")
        media = tweet_media_resp.json()["mediaDetails"][0]
        if media.get("type") == "video" or media.get("type") == "animated_gif":
            variants = media.get("video_info").get("variants")
            best = max(variants, key=lambda variant: variant.get("bitrate") is not None and variant.get("bitrate"))
            return best.get("url")
    return ""


def login_to_instagram():
    session = requests.Session()
    shared_data = session.get("https://www.instagram.com/data/shared_data/")
    csrf_token = shared_data.json()["config"]["csrf_token"]
    def create_enc_password(pwd: str):
        return f"#PWD_INSTAGRAM_BROWSER:0:{int(datetime.now().timestamp())}:{pwd}"
    login_resp = session.post("https://www.instagram.com/accounts/login/ajax/", data={"username": os.environ.get("INSTAGRAM_USERNAME"), "enc_password": create_enc_password(os.environ.get("INSTAGRAM_PASSWORD"))}, headers={
        "Content-Type": "application/x-www-form-urlencoded",
        "X-CSRFToken": csrf_token,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 Safari/537.36 OPR/92.0.0.0",
        "Referer": "https://www.instagram.com/accounts/login/"
    })
    return session

def get_tiktok_video(tiktok_url: str):
    full_url = requests.get(tiktok_url)
    match = re.match(tiktok_regex, full_url.url)
    if match is not None:
        tiktok_id = match.groups()[1]
        tiktok_media_resp = requests.get(f"https://tiktokv.com/aweme/v1/feed/?aweme_id={tiktok_id}", headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 Safari/537.36 OPR/92.0.0.0"
        })
        video = tiktok_media_resp.json()["aweme_list"][0]
        return video["video"]["play_addr"]["url_list"][-1]  

def get_instagram_video(instagram_url: str):
    instagram_session = login_to_instagram()
    instagram_url_cleaned = instagram_url.replace("reels", "p").split("?")[0]+"?__a=1&__d=dis"
    instagram_media_resp = instagram_session.get(instagram_url_cleaned)
    data = instagram_media_resp.json()["items"][0]
    if "video_versions" in data:
        return data["video_versions"][0]["url"]
    elif "image_versions2" in data:
        return data["image_versions2"]["candidates"][0]["url"] 


def shorten_url(url):
    resp = requests.get(f"https://api.shrtco.de/v2/shorten?url={urllib.parse.quote(url)}")
    return resp.json()["result"]["full_short_link"]


@app.route("/")
def hello_world():
    return "Hello world!"

@app.route("/getVideo", methods=["GET"])
def get_video():
    args = request.args
    video_url = ""
    if args.get("url") is None: 
        return "No url found!"
    if re.match(twitter_regex, args.get("url")) is not None:
        video_url = get_tweet_video(args.get("url"))
    if "tiktok.com" in args.get('url'):
        video_url = get_tiktok_video(args.get("url"))
    if re.match(instagram_regex, args.get("url")) is not None:
        video_url = get_instagram_video(args.get("url"))
    print(args.get("short"))
    if args.get("short") == "1":
        video_url = shorten_url(video_url)
    return {
        "videoUrl": video_url
    }
