from flask import Flask, render_template, request
import requests
import json
import re
import ffmpeg
from bs4 import BeautifulSoup
import os


app = Flask(__name__)

DJANGO_SERVER_URL = "https://nakedreels.com/"

session = requests.Session()

def sanitize_filename(title):
    return re.sub(r'\W+', '-', title.lower()).strip('-')


def check_or_create_profile(username, creator_url):
    url = f"{DJANGO_SERVER_URL}/api/check_or_create_profile/"
    data = {"username": username}
    response = requests.post(url, json=data, verify=False)
    return response.status_code == 200


def get_redgifs_video(url):
    video_id = url.split("/")[-1]
    headers = {"User-Agent": "Mozilla/5.0"}
    session = requests.Session()
    
    # Get temporary token
    token_url = "https://api.redgifs.com/v2/auth/temporary"
    token_response = session.get(token_url, headers=headers)
    if token_response.status_code != 200:
        return None
    token = token_response.json().get("token")
    headers["Authorization"] = f"Bearer {token}"
    
    # Fetch video metadata
    api_url = f"https://api.redgifs.com/v2/gifs/{video_id}"
    api_response = session.get(api_url, headers=headers)
    if api_response.status_code != 200:
        return None
    data = api_response.json()
    
    video_url = data.get("gif", {}).get("urls", {}).get("hd")
    if not video_url:
        print("NOTTTTTTTTTTTT EXIISISIIISSSSSSST")
        video_url = data.get("gif", {}).get("urls", {}).get("sd")
    return video_url


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
    temp_output = f"temp_{output_path}"  # Temporary file to avoid in-place modification
    try:
        ffmpeg.input(input_path).output(temp_output, vcodec="libx264", crf=18).run(overwrite_output=True)
        return temp_output  # Return the correct compressed filename
    except ffmpeg.Error as e:
        print(f"FFmpeg error: {e}")
        return None



def generate_thumbnail(video_path, thumbnail_path, watermark_image_path="/home/antorzuck/Desktop/plak/water.png"):
    try:
        temp_thumbnail = f"temp_{thumbnail_path}"
        
        # Step 1: Extract thumbnail frame
        ffmpeg.input(video_path, ss="00:00:05").output(temp_thumbnail, vframes=1).run(overwrite_output=True, quiet=True)

        # Step 2: Apply watermark overlay with scaling
        (
            ffmpeg
            .input(temp_thumbnail)
            .overlay(
                ffmpeg.input(watermark_image_path).filter("scale", "iw*0.20", "-1"),  # 15% width of thumbnail
		x="(main_w-overlay_w)", 
		y="(main_h-overlay_h)/2"
            )
            .output(thumbnail_path)
            .run(overwrite_output=True, quiet=True)
        )

        os.remove(temp_thumbnail)
    except ffmpeg.Error as e:
        print(f"FFmpeg thumbnail error: {e.stderr.decode()}")
        return None

    return thumbnail_path


def add_watermark(video_path, output_path, watermark_image_path="/home/antorzuck/Desktop/plak/water.png"):
    try:
        (
            ffmpeg
            .overlay(
                ffmpeg.input(video_path),
                ffmpeg.input(watermark_image_path).filter("scale", "iw*0.20", "-1"),  # 15% of video width
       		x="(main_w-overlay_w)", 
        	y="(main_h-overlay_h)/2"
            )
            .output(output_path)
            .run(overwrite_output=True)
        )
        return output_path
    except ffmpeg.Error as e:
        print(f"FFmpeg video watermark error: {e.stderr.decode()}")
        return None


def upload_to_server(username, title, video_path, thumbnail_path):
    url = f"{DJANGO_SERVER_URL}/api/upload_video/"
    files = {"video": open(video_path, "rb"), "thumbnail": open(thumbnail_path, "rb")}
    data = {"username": username, "title": title, "desc": f"Watch {title.lower()}"}
    response = requests.post(url, files=files, data=data, verify=False)
    return response.status_code == 201


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        url = request.form["url"]
        headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Referer": "https://www.redgifs.com/",
    "Accept": "video/webm,video/ogg,video/*;q=0.9,application/ogg;q=0.7,audio/*;q=0.6,*/*;q=0.5",
    "Origin": "https://www.redgifs.com",
}

        
        response = session.get(url, headers=headers)
        response.raise_for_status()
        
        print("fucking response", response)
        
        
        
        soup = BeautifulSoup(response.text, 'html.parser')
        title_tag = soup.find("title").text
        model_username = title_tag.split(" ")[-1]
        video_title = request.form["video_title"]

        sanitized_title = sanitize_filename(video_title)
        video_filename = f"{sanitized_title}.mp4"
        compressed_filename = f"{sanitized_title}_compressed.mp4"
        thumbnail_filename = f"{sanitized_title}.jpg"

        if not check_or_create_profile(model_username, creator_url=f"https://www.redgifs.com/users/{model_username}"):
            return "Failed to create or check profile", 400

        video_url = get_redgifs_video(url)
        if video_url:
            downloaded_video = download_video(video_url, video_filename)
            if downloaded_video:
                compressed_video = compress_video(downloaded_video, compressed_filename)
                
                generate_thumbnail(compressed_video, thumbnail_filename)
                watermarked_video = add_watermark(compressed_video, compressed_filename)
                if watermarked_video and upload_to_server(model_username, video_title, watermarked_video, thumbnail_filename):
                    return f"Video '{video_title}' uploaded successfully!", 200
                return "Failed to upload video", 500
        return "Failed to fetch video", 400
    return render_template("index.html")


if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)

