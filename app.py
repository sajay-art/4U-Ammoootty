import os, uuid, shutil, socket, ipaddress, subprocess, mimetypes
from pathlib import Path
from urllib.parse import urlparse, urljoin
import requests
from flask import Flask, render_template, request, jsonify, send_file, after_this_request
from werkzeug.utils import secure_filename

app = Flask(__name__)
MAX_BYTES = 100 * 1024 * 1024
app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024
ROOT = Path(__file__).parent
UPLOAD, OUTPUT = ROOT/"uploads", ROOT/"outputs"
UPLOAD.mkdir(exist_ok=True); OUTPUT.mkdir(exist_ok=True)
FFMPEG = os.getenv("FFMPEG_BINARY", "ffmpeg")
ALLOWED_EXT = {".mp4",".mov",".mkv",".webm",".mp3",".wav",".m4a",".aac",".ogg",".m4v"}
MEDIA_TYPES = ("video/", "audio/")

PLATFORMS = [
    ("YouTube", ("youtube.com", "youtu.be")),
    ("Instagram", ("instagram.com",)),
    ("Facebook", ("facebook.com", "fb.watch")),
    ("TikTok", ("tiktok.com",)),
    ("X / Twitter", ("x.com", "twitter.com")),
    ("Vimeo", ("vimeo.com",)),
]

def platform_for(raw):
    try:
        p = urlparse(raw.strip())
        host = (p.hostname or "").lower()
        if p.scheme not in ("http", "https") or not host:
            return None
        for label, domains in PLATFORMS:
            if any(host == d or host.endswith("." + d) for d in domains):
                return label
        return "Direct media URL / other website"
    except Exception:
        return None

def validate_public_url(url):
    p = urlparse(url)
    if p.scheme not in ("http", "https") or not p.hostname or p.username or p.password:
        raise ValueError("Enter a valid public http:// or https:// media URL.")
    host = p.hostname.lower()
    if host in ("localhost",) or host.endswith((".localhost", ".local")):
        raise ValueError("Local network URLs are not allowed.")
    try:
        infos = socket.getaddrinfo(host, p.port or (443 if p.scheme=="https" else 80), type=socket.SOCK_STREAM)
        addresses = {info[4][0] for info in infos}
    except socket.gaierror:
        raise ValueError("Could not resolve that website.")
    for addr in addresses:
        ip = ipaddress.ip_address(addr)
        if not ip.is_global:
            raise ValueError("Private or local network addresses are not allowed.")
    return url

def fetch_direct_media(url, destination):
    session = requests.Session()
    current = validate_public_url(url)
    headers = {"User-Agent": "4U-Ammoootty/3.0 (authorized media fetch)", "Accept": "video/*,audio/*,application/octet-stream;q=0.9,*/*;q=0.1"}
    for _ in range(4):
        validate_public_url(current)
        with session.get(current, headers=headers, stream=True, timeout=(8, 25), allow_redirects=False) as r:
            if r.is_redirect or r.is_permanent_redirect:
                loc = r.headers.get("Location")
                if not loc: raise ValueError("The media URL returned an invalid redirect.")
                current = urljoin(current, loc)
                continue
            r.raise_for_status()
            ctype = r.headers.get("Content-Type", "").split(";")[0].lower()
            if not (ctype.startswith(MEDIA_TYPES) or ctype in ("application/octet-stream", "binary/octet-stream")):
                raise ValueError("That link does not appear to point directly to an audio or video file. Social post pages are not direct media URLs.")
            length = r.headers.get("Content-Length")
            if length and int(length) > MAX_BYTES:
                raise ValueError("Media URL exceeds the 100 MB download limit.")
            total = 0
            with open(destination, "wb") as out:
                for chunk in r.iter_content(1024*256):
                    if not chunk: continue
                    total += len(chunk)
                    if total > MAX_BYTES:
                        raise ValueError("Media URL exceeds the 100 MB download limit.")
                    out.write(chunk)
            return ctype
    raise ValueError("Too many redirects.")

@app.get("/")
def home():
    return render_template("index.html")

@app.get("/api/health")
def health():
    return jsonify(status="ok", service="4U Ammoootty", version="3.0")

@app.post("/api/inspect")
def inspect():
    data = request.get_json(silent=True) or {}
    raw = (data.get("url") or "").strip()
    if len(raw) > 2048:
        return jsonify(error="URL is too long."), 400
    label = platform_for(raw)
    if not label:
        return jsonify(error="Paste a complete http:// or https:// URL."), 400
    is_social = label in ("YouTube", "Instagram", "Facebook", "TikTok", "X / Twitter", "Vimeo")
    return jsonify(platform=label, direct=not is_social,
        message=("This looks like a social-platform page. 4U Ammoootty cannot extract arbitrary posts from it. Use the platform's official download/export feature for media you own or are authorized to use, then upload the file below."
                 if is_social else
                 "This looks like a direct media link. If it points to a publicly accessible audio/video file and you have permission to download it, choose your output format and continue."))

def convert_file(source, fmt, output):
    if shutil.which(FFMPEG) is None:
        raise RuntimeError("FFmpeg is not installed on the server.")
    cmd = [FFMPEG, "-nostdin", "-y", "-i", str(source)]
    if fmt == "mp4":
        cmd += ["-map", "0:v:0", "-map", "0:a?", "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-c:a", "aac", "-movflags", "+faststart"]
    else:
        cmd += ["-vn", "-codec:a", "libmp3lame", "-q:a", "2"]
    cmd.append(str(output))
    run = subprocess.run(cmd, capture_output=True, text=True, timeout=240)
    if run.returncode != 0 or not output.exists():
        raise ValueError("Could not convert this media. It may be unsupported or damaged.")

def process_source(source, fmt):
    token = uuid.uuid4().hex
    output = OUTPUT/f"4u-ammoootty-{token}.{fmt}"
    try:
        convert_file(source, fmt, output)
    except Exception:
        output.unlink(missing_ok=True)
        raise
    return output

def send_temp_file(output, fmt):
    @after_this_request
    def cleanup(response):
        output.unlink(missing_ok=True)
        return response
    return send_file(output, as_attachment=True, download_name=f"4U-Ammoootty.{fmt}",
                     mimetype="video/mp4" if fmt=="mp4" else "audio/mpeg")

@app.post("/api/download-direct")
def download_direct():
    raw = (request.form.get("url") or "").strip()
    fmt = (request.form.get("format") or "mp4").lower()
    if fmt not in ("mp4", "mp3"):
        return jsonify(error="Choose MP4 or MP3."), 400
    label = platform_for(raw)
    if not raw or not label:
        return jsonify(error="Enter a valid media URL."), 400
    if label in ("YouTube", "Instagram", "Facebook", "TikTok", "X / Twitter", "Vimeo"):
        return jsonify(error="This is a social-platform page, not a direct media file. Arbitrary post extraction is not supported. Use an official download/export for media you own or are authorized to use, then upload it below."), 400
    token = uuid.uuid4().hex
    source = UPLOAD/f"{token}.media"
    try:
        fetch_direct_media(raw, source)
        output = process_source(source, fmt)
    except requests.RequestException:
        return jsonify(error="Could not fetch that media URL. It may require sign-in, block automated requests, or be unavailable."), 422
    except (ValueError, RuntimeError) as e:
        return jsonify(error=str(e)), 422
    finally:
        source.unlink(missing_ok=True)
    return send_temp_file(output, fmt)

@app.post("/api/convert")
def convert_upload():
    f = request.files.get("media")
    fmt = (request.form.get("format") or "mp4").lower()
    if not f or not f.filename:
        return jsonify(error="Choose a media file first."), 400
    if fmt not in ("mp4", "mp3"):
        return jsonify(error="Choose MP4 or MP3."), 400
    ext = Path(secure_filename(f.filename)).suffix.lower()
    if ext not in ALLOWED_EXT:
        return jsonify(error="Unsupported file type. Upload a common video or audio file."), 400
    token = uuid.uuid4().hex
    source = UPLOAD/f"{token}{ext}"
    f.save(source)
    try:
        output = process_source(source, fmt)
    except (ValueError, RuntimeError) as e:
        return jsonify(error=str(e)), 422
    except subprocess.TimeoutExpired:
        return jsonify(error="Conversion took too long. Try a smaller file."), 408
    finally:
        source.unlink(missing_ok=True)
    return send_temp_file(output, fmt)

@app.errorhandler(413)
def too_large(_):
    return jsonify(error="Upload too large. Maximum upload size is 200 MB."), 413

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=False)
