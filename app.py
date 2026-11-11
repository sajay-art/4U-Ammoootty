import os, uuid, subprocess, shutil
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file, after_this_request
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024
ROOT = Path(__file__).parent
UPLOAD = ROOT / "uploads"
OUTPUT = ROOT / "outputs"
UPLOAD.mkdir(exist_ok=True); OUTPUT.mkdir(exist_ok=True)
ALLOWED = {".mp4",".mov",".mkv",".webm",".mp3",".wav",".m4a",".aac",".ogg"}
FFMPEG = os.getenv("FFMPEG_BINARY", "ffmpeg")

@app.get("/")
def home():
    return render_template("index.html")

@app.get("/api/health")
def health():
    return jsonify({"status":"ok","service":"4U Ammoootty"})

@app.post("/api/convert")
def convert():
    if shutil.which(FFMPEG) is None:
        return jsonify(error="FFmpeg is not installed on this server. Use the Docker deployment or install FFmpeg."), 503
    f = request.files.get("media")
    fmt = request.form.get("format", "mp4").lower()
    if not f or not f.filename:
        return jsonify(error="Choose a media file first."), 400
    if fmt not in {"mp4","mp3"}:
        return jsonify(error="Choose MP4 or MP3."), 400
    ext = Path(secure_filename(f.filename)).suffix.lower()
    if ext not in ALLOWED:
        return jsonify(error="Unsupported file type. Upload a common video or audio file."), 400
    token = uuid.uuid4().hex
    source = UPLOAD / f"{token}{ext}"
    target = OUTPUT / f"4u-ammoootty-{token}.{fmt}"
    f.save(source)
    try:
        cmd = [FFMPEG, "-y", "-i", str(source)]
        if fmt == "mp4":
            cmd += ["-map", "0:v:0", "-map", "0:a?", "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-c:a", "aac", "-movflags", "+faststart"]
        else:
            cmd += ["-vn", "-codec:a", "libmp3lame", "-q:a", "2"]
        cmd.append(str(target))
        run = subprocess.run(cmd, capture_output=True, text=True, timeout=240)
        if run.returncode != 0 or not target.exists():
            return jsonify(error="Could not convert this file. Try another supported media file."), 422
    except subprocess.TimeoutExpired:
        return jsonify(error="Conversion took too long. Try a smaller file."), 408
    finally:
        source.unlink(missing_ok=True)
    @after_this_request
    def cleanup(response):
        target.unlink(missing_ok=True)
        return response
    return send_file(target, as_attachment=True, download_name=f"4U-Ammoootty.{fmt}", mimetype="video/mp4" if fmt=="mp4" else "audio/mpeg")

@app.errorhandler(413)
def too_large(_):
    return jsonify(error="File is too large. Maximum upload size is 200 MB."), 413

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=False)
