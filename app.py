
from flask import Flask, request, jsonify
import requests, os, base64, uuid, subprocess
from PIL import Image

app = Flask(__name__)
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
DOWNLOAD_URL = "https://api.telegram.org/bot{}/getFile?file_id=".format(BOT_TOKEN)
FILE_URL = "https://api.telegram.org/file/bot{}/".format(BOT_TOKEN)

def extract_frames(video_path, output_folder, interval_sec=2):
    os.makedirs(output_folder, exist_ok=True)
    command = [
        "ffmpeg", "-i", video_path,
        "-vf", f"fps=1/{interval_sec}",
        os.path.join(output_folder, "frame_%03d.jpg")
    ]
    subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

@app.route("/process", methods=["POST"])
def process_video():
    data = request.get_json()
    file_id = data.get("file_id")
    if not file_id:
        return jsonify({"error": "Missing file_id"}), 400

    get_info = requests.get(DOWNLOAD_URL + file_id).json()
    file_path = get_info["result"]["file_path"]
    video_url = FILE_URL + file_path

    temp_video = "/tmp/video_{}.mp4".format(uuid.uuid4().hex)
    with open(temp_video, "wb") as f:
        f.write(requests.get(video_url).content)

    output_folder = "/tmp/frames_{}".format(uuid.uuid4().hex)
    extract_frames(temp_video, output_folder)

    frames = []
    for fname in sorted(os.listdir(output_folder)):
        fpath = os.path.join(output_folder, fname)
        with open(fpath, "rb") as img_file:
            encoded = base64.b64encode(img_file.read()).decode("utf-8")
        frames.append({"filename": fname, "image_base64": encoded})

    os.remove(temp_video)
    return jsonify({"frames": frames})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7860)
