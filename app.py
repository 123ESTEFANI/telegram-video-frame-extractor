from flask import Flask, request, jsonify
import requests, os, base64, uuid, subprocess
from PIL import Image

app = Flask(__name__)

# Validar existencia del token
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("❌ TELEGRAM_BOT_TOKEN no está definido en las variables de entorno.")

DOWNLOAD_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id="
FILE_URL = f"https://api.telegram.org/file/bot{BOT_TOKEN}/"

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

    try:
        info_res = requests.get(DOWNLOAD_URL + file_id)
        info_res.raise_for_status()
        file_info = info_res.json()

        if not file_info.get("ok") or "result" not in file_info:
            return jsonify({"error": "Invalid response from Telegram"}), 502

        file_path = file_info["result"].get("file_path")
        if not file_path:
            return jsonify({"error": "No file_path found"}), 502

        video_url = FILE_URL + file_path
        video_data = requests.get(video_url)
        video_data.raise_for_status()
    except Exception as e:
        return jsonify({"error": f"Failed to download video: {str(e)}"}), 500

    temp_video = f"/tmp/video_{uuid.uuid4().hex}.mp4"
    with open(temp_video, "wb") as f:
        f.write(video_data.content)

    output_folder = f"/tmp/frames_{uuid.uuid4().hex}"
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
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000))) 
