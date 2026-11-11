import os
import re
import shutil
import threading
import uuid
from pathlib import Path

import yt_dlp
from flask import Flask, Response, jsonify, request, send_file, render_template

BASE_DIR = Path(__file__).parent.resolve()
DOWNLOAD_DIR = BASE_DIR / "downloads"
DOWNLOAD_DIR.mkdir(exist_ok=True)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024
jobs = {}
jobs_lock = threading.Lock()

# This service intentionally does not accept browser cookies or credentials.
# Only download content that you own or are authorized to save.
ALLOWED_AUDIO = {"mp3", "m4a", "wav", "opus", "flac"}
ALLOWED_QUALITY = {"best", "1080", "720", "480", "360"}

def base_opts():
    opts = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "retries": 3,
        "socket_timeout": 25,
        "ignoreerrors": False,
    }
    # yt-dlp YouTube support may need a JS runtime for supported public media.
    if shutil.which("deno"):
        opts["js_runtimes"] = {"deno": {}}
    elif shutil.which("node"):
        opts["js_runtimes"] = {"node": {}}
    return opts

def valid_url(url):
    if not isinstance(url, str) or len(url) > 2048:
        return False
    return url.strip().lower().startswith(("http://", "https://"))

def set_job(job_id, **values):
    with jobs_lock:
        if job_id in jobs:
            jobs[job_id].update(values)

def run_download(job_id, url, mode, quality, audio_fmt):
    out_dir = DOWNLOAD_DIR / job_id
    out_dir.mkdir(parents=True, exist_ok=True)

    def hook(data):
        if data.get("status") == "downloading":
            total = data.get("total_bytes") or data.get("total_bytes_estimate") or 0
            done = data.get("downloaded_bytes") or 0
            percent = round(done * 100 / total, 1) if total else 0
            set_job(job_id, state="downloading", percent=percent,
                    speed=(data.get("_speed_str") or "").strip())
        elif data.get("status") == "finished":
            set_job(job_id, state="processing", percent=100)

    opts = base_opts()
    opts.update({
        "outtmpl": str(out_dir / "%(title).80s [%(id)s].%(ext)s"),
        "progress_hooks": [hook],
        "restrictfilenames": True,
        "windowsfilenames": True,
        "max_filesize": 500 * 1024 * 1024,
    })

    if mode == "audio":
        codec = audio_fmt if audio_fmt in ALLOWED_AUDIO else "mp3"
        opts["format"] = "bestaudio/best"
        opts["postprocessors"] = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": codec,
            "preferredquality": "192",
        }]
    else:
        if quality == "best":
            opts["format"] = "bestvideo*+bestaudio/best"
        else:
            h = int(quality)
            opts["format"] = f"bestvideo*[height<={h}]+bestaudio/best[height<={h}]/best"
        opts["merge_output_format"] = "mp4"

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
        if not info:
            raise RuntimeError("No downloadable media was returned by the source.")
        # Avoid playlist downloads; keep metadata for the selected item.
        set_job(job_id, title=info.get("title") or "Your media")
        files = [p for p in out_dir.iterdir() if p.is_file() and not p.name.endswith((".part", ".ytdl"))]
        if not files:
            raise RuntimeError("The download completed but no output file was created.")
        final_file = max(files, key=lambda p: p.stat().st_size)
        set_job(job_id, state="done", percent=100, file=str(final_file),
                filename=final_file.name, size=final_file.stat().st_size)
    except Exception as exc:
        message = str(exc)
        if "ffmpeg" in message.lower() or "ffprobe" in message.lower():
            message += " Install FFmpeg in the hosting container."
        set_job(job_id, state="error", error=message[:1200])

@app.get("/")
def index():
    return render_template("index.html")

@app.get("/api/health")
def health():
    return jsonify(service="4U Ammoootty", status="ok", version="4.0",
                   yt_dlp=yt_dlp.version.__version__)

@app.post("/api/info")
def api_info():
    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()
    if not valid_url(url):
        return jsonify(error="Paste a valid public http(s) media link."), 400
    try:
        opts = base_opts()
        opts["skip_download"] = True
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
        if not info:
            raise RuntimeError("No media information was returned.")
        if info.get("_type") in ("playlist", "multi_video"):
            return jsonify(error="Playlist links are not supported. Paste a link to one video."), 400
        heights = sorted({int(f["height"]) for f in info.get("formats", [])
                          if f.get("height") and f.get("vcodec") != "none"}, reverse=True)
        return jsonify(
            title=info.get("title") or "Media",
            uploader=info.get("uploader") or info.get("channel") or "",
            duration=info.get("duration"),
            thumbnail=info.get("thumbnail"),
            platform=info.get("extractor_key") or info.get("extractor") or "Media source",
            heights=heights[:12],
        )
    except Exception as exc:
        return jsonify(error=str(exc)[:1000]), 422

@app.post("/api/download")
def api_download():
    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()
    if not valid_url(url):
        return jsonify(error="Paste a valid public http(s) media link."), 400
    mode = "audio" if data.get("mode") == "audio" else "video"
    quality = str(data.get("quality") or "best")
    audio_fmt = str(data.get("audio_fmt") or "mp3").lower()
    if quality not in ALLOWED_QUALITY:
        quality = "best"
    if audio_fmt not in ALLOWED_AUDIO:
        audio_fmt = "mp3"

    job_id = uuid.uuid4().hex[:12]
    with jobs_lock:
        jobs[job_id] = {
            "state": "queued", "percent": 0, "file": None,
            "error": None, "title": "", "speed": "", "filename": "",
        }
    worker = threading.Thread(
        target=run_download,
        args=(job_id, url, mode, quality, audio_fmt),
        daemon=True,
    )
    worker.start()
    return jsonify(job_id=job_id)

@app.get("/api/status/<job_id>")
def api_status(job_id):
    with jobs_lock:
        job = jobs.get(job_id)
        if not job:
            return jsonify(error="Unknown or expired job."), 404
        result = {k: v for k, v in job.items() if k != "file"}
        result["ready"] = bool(job.get("file"))
    return jsonify(result)

@app.get("/api/file/<job_id>")
def api_file(job_id):
    with jobs_lock:
        job = jobs.get(job_id)
        file_path = job.get("file") if job else None
    if not file_path or not Path(file_path).is_file():
        return jsonify(error="The file is not ready or has expired."), 404
    return send_file(file_path, as_attachment=True,
                     download_name=Path(file_path).name)

@app.post("/api/clear")
def api_clear():
    shutil.rmtree(DOWNLOAD_DIR, ignore_errors=True)
    DOWNLOAD_DIR.mkdir(exist_ok=True)
    with jobs_lock:
        jobs.clear()
    return jsonify(ok=True)

@app.errorhandler(413)
def too_large(_):
    return jsonify(error="Request is too large."), 413

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=False)
