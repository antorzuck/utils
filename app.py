from flask import Flask, render_template, request
import requests
import json
import re
import ffmpeg
from bs4 import BeautifulSoup

app = Flask(__name__)

DJANGO_SERVER_URL = "https://leaksgram.com"

def sanitize_filename(title):
    return re.sub(r'\W+', '-', title.lower()).strip('-')

def check_or_create_profile(username):
    url = f"{DJANGO_SERVER_URL}/api/check_or_create_profile/"
    data = {"username": username}
    response = requests.post(url, json=data)
    return response.status_code == 200

def get_video_link(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        return None
    soup = BeautifulSoup(response.text, "html.parser")
    script_tag = soup.find("script", {"id": "__NEXT_DATA__"})
    if not script_tag:
        return None
    try:
        data = json.loads(script_tag.string)
        video_link = data["props"]["pageProps"]["videoData"]["link"]
        return f"https://imgs.reelsmunkey.com/{video_link}"
    except (KeyError, json.JSONDecodeError):
        return None

def download_video(video_url, save_path):
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(video_url, headers=headers, stream=True)
    if response.status_code == 200:
        with open(save_path, "wb") as file:
            for chunk in response.iter_content(chunk_size=1024):
                file.write(chunk)
        return save_path
    return None

def compress_video(input_path, output_path):
    try:
        ffmpeg.input(input_path).output(output_path, vcodec="libx264", crf=28).run(overwrite_output=True)
    except ffmpeg.Error:
        return None
    return output_path

def generate_thumbnail(video_path, thumbnail_path):
    try:
        ffmpeg.input(video_path, ss="00:00:05").output(thumbnail_path, vframes=1).run(overwrite_output=True, quiet=True)
    except ffmpeg.Error:
        return None
    return thumbnail_path

def process_thumbnail(thumbnail_path, filename):
    output_image = "processed_thumbnail.jpg"
    final_output = filename
    new_watermark_text = "leaksgram.com"
    try:
        ffmpeg.input(thumbnail_path).output(
            output_image, vf="delogo=x=20:y=905:w=115:h=30"
        ).run(overwrite_output=True)
        ffmpeg.input(output_image).output(
            final_output, vf=f"drawtext=text='{new_watermark_text}':x=20:y=908:fontcolor=white:fontsize=20"
        ).run(overwrite_output=True)
        return final_output
    except ffmpeg.Error:
        return None

def upload_to_server(username, title, video_path, thumbnail_path):
    url = f"{DJANGO_SERVER_URL}/api/upload_video/"
    files = {"video": open(video_path, "rb"), "thumbnail": open(thumbnail_path, "rb")}
    data = {"username": username, "title": title, "desc": f"Watch {title.lower()}"}
    response = requests.post(url, files=files, data=data)
    return response.status_code == 201

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        url = request.form["url"]
        model_username = request.form["model_username"]
        video_title = request.form["video_title"]

        sanitized_title = sanitize_filename(video_title)
        video_filename = f"{sanitized_title}.mp4"
        compressed_filename = f"{sanitized_title}_compressed.mp4"
        thumbnail_filename = f"{sanitized_title}.jpg"

        if not check_or_create_profile(model_username):
            return "Failed to create or check profile", 400

        video_url = get_video_link(url)
        if video_url:
            downloaded_video = download_video(video_url, video_filename)
            if downloaded_video:
                compress_video(downloaded_video, compressed_filename)
                generate_thumbnail(compressed_filename, thumbnail_filename)
                processed_thumbnail = process_thumbnail(thumbnail_filename, thumbnail_filename)
                if processed_thumbnail and upload_to_server(model_username, video_title, compressed_filename, processed_thumbnail):
                    return f"Video '{video_title}' uploaded successfully!", 200
                return "Failed to upload video", 500
        return "Failed to scrape video", 400
    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)
