import os
import glob
import uuid
import shutil
import threading
from flask import Flask, request, jsonify, send_file, render_template_string, after_this_request
import yt_dlp

app = Flask(__name__)
BASE_DOWNLOAD_DIR = "/tmp/downloads"
os.makedirs(BASE_DOWNLOAD_DIR, exist_ok=True)

# Render automatically mounts Secret Files at /etc/secrets/<filename>
COOKIE_FILE = "/etc/secrets/cookies.txt"

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Media Downloader</title>
    <style>
        * { box-sizing: border-box; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
        body { background: #0b0e14; color: #f1f5f9; margin: 0; padding: 20px; display: flex; justify-content: center; align-items: center; min-height: 100vh; }
        .container { background: #131822; border: 1px solid #1e293b; border-radius: 20px; padding: 24px; width: 100%; max-width: 440px; box-shadow: 0 20px 40px rgba(0,0,0,0.6); }
        .header { text-align: center; margin-bottom: 24px; }
        .badge { font-size: 11px; letter-spacing: 1.5px; color: #94a3b8; text-transform: uppercase; font-weight: 700; }
        h1 { font-size: 24px; margin: 8px 0; color: #ffffff; }
        .subtitle { font-size: 13px; color: #94a3b8; margin: 0; }
        label { display: block; font-size: 11px; letter-spacing: 1px; color: #94a3b8; text-transform: uppercase; font-weight: 700; margin-bottom: 8px; margin-top: 16px; }
        input[type="url"] { width: 100%; padding: 14px; border-radius: 12px; border: 1px solid #334155; background: #ffffff; color: #0f172a; font-size: 15px; outline: none; }
        .btn-check { width: 100%; padding: 14px; margin-top: 12px; border-radius: 12px; border: 1px solid #3b2d54; background: #231934; color: #e2e8f0; font-size: 15px; font-weight: 600; cursor: pointer; transition: 0.2s; }
        .btn-check:hover { background: #2e2144; }
        .error-box { display: none; margin-top: 14px; padding: 12px; border-radius: 12px; background: #1c141d; border: 1px solid #7f1d1d; color: #fca5a5; font-size: 12px; line-height: 1.5; word-break: break-word; }
        .preview-box { display: none; margin-top: 16px; padding: 12px; border-radius: 12px; background: #0f172a; border: 1px solid #1e293b; align-items: center; gap: 12px; }
        .preview-box img { width: 72px; height: 54px; object-fit: cover; border-radius: 8px; }
        .preview-title { font-size: 13px; font-weight: 600; color: #f8fafc; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
        .format-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 8px; }
        .format-btn { padding: 14px; border-radius: 12px; border: 1px solid #1e293b; background: #0f172a; color: #94a3b8; font-size: 14px; font-weight: 600; cursor: pointer; text-align: center; transition: 0.2s; }
        .format-btn.active { background: #231934; border-color: #6d28d9; color: #ffffff; }
        select { width: 100%; padding: 14px; border-radius: 12px; border: 1px solid #1e293b; background: #0f172a; color: #f8fafc; font-size: 14px; outline: none; }
        .btn-download { width: 100%; padding: 16px; margin-top: 20px; border-radius: 12px; border: none; background: linear-gradient(135deg, #6366f1, #8b5cf6); color: #ffffff; font-size: 16px; font-weight: 700; cursor: pointer; }
        .btn-download:disabled { opacity: 0.6; cursor: not-allowed; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="badge">Link to Download</div>
            <h1>Paste your media link.</h1>
            <p class="subtitle">Preview the media, select a format and start your download.</p>
        </div>

        <form id="dlForm" action="/download" method="POST">
            <label>Media URL</label>
            <input type="url" id="urlInput" name="url" placeholder="https://youtu.be/... or Instagram link" required>
            
            <button type="button" class="btn-check" id="checkBtn" onclick="checkLink()">Check link</button>
            
            <div id="errorBox" class="error-box"></div>
            
            <div id="previewBox" class="preview-box">
                <img id="thumbImg" src="" alt="">
                <div class="preview-title" id="videoTitle"></div>
            </div>

            <label>Format</label>
            <input type="hidden" name="format" id="formatInput" value="mp4">
            <div class="format-grid">
                <div class="format-btn active" id="btnMp4" onclick="setFormat('mp4')">🎬 Video MP4</div>
                <div class="format-btn" id="btnMp3" onclick="setFormat('mp3')">🎵 Audio MP3</div>
            </div>

            <div id="qualitySection">
                <label>Video Quality</label>
                <select name="quality">
                    <option value="best">Best Available (Up to 1080p)</option>
                    <option value="720">720p HD</option>
                    <option value="480">480p Data Saver</option>
                </select>
            </div>

            <button type="submit" class="btn-download" id="downloadBtn">Download File</button>
        </form>
    </div>

    <script>
        function setFormat(fmt) {
            document.getElementById('formatInput').value = fmt;
            document.getElementById('btnMp4').classList.toggle('active', fmt === 'mp4');
            document.getElementById('btnMp3').classList.toggle('active', fmt === 'mp3');
            document.getElementById('qualitySection').style.display = fmt === 'mp4' ? 'block' : 'none';
        }

        async function checkLink() {
            const url = document.getElementById('urlInput').value.trim();
            const errorBox = document.getElementById('errorBox');
            const previewBox = document.getElementById('previewBox');
            const checkBtn = document.getElementById('checkBtn');

            if (!url) return;
            errorBox.style.display = 'none';
            previewBox.style.display = 'none';
            checkBtn.innerText = 'Checking...';
            checkBtn.disabled = true;

            try {
                const res = await fetch('/info', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ url })
                });
                const data = await res.json();
                if (!res.ok) {
                    errorBox.innerText = data.error || 'Failed to fetch media info.';
                    errorBox.style.display = 'block';
                } else {
                    document.getElementById('videoTitle').innerText = data.title || 'Media Ready';
                    if (data.thumbnail) {
                        document.getElementById('thumbImg').src = data.thumbnail;
                        document.getElementById('thumbImg').style.display = 'block';
                    } else {
                        document.getElementById('thumbImg').style.display = 'none';
                    }
                    previewBox.style.display = 'flex';
                }
            } catch (err) {
                errorBox.innerText = 'Network error while checking link.';
                errorBox.style.display = 'block';
            } finally {
                checkBtn.innerText = 'Check link';
                checkBtn.disabled = false;
            }
        }
    </script>
</body>
</html>
"""

def get_base_opts():
    opts = {
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
    }
    # Automatically attach cookies if uploaded to Render Secret Files
    if os.path.exists(COOKIE_FILE) and os.path.getsize(COOKIE_FILE) > 0:
        opts['cookiefile'] = COOKIE_FILE
    return opts

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/info', methods=['POST'])
def info():
    data = request.get_json(silent=True) or {}
    url = data.get('url', '').strip()
    if not url:
        return jsonify({'error': 'Please paste a valid URL.'}), 400

    ydl_opts = get_base_opts()
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            meta = ydl.extract_info(url, download=False)
            return jsonify({
                'title': meta.get('title', 'Media File'),
                'thumbnail': meta.get('thumbnail', '')
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/download', methods=['POST'])
def download():
    url = request.form.get('url', '').strip()
    fmt = request.form.get('format', 'mp4')
    quality = request.form.get('quality', 'best')

    if not url:
        return "No URL provided", 400

    # Create a unique folder per request so concurrent users don't overwrite files
    job_id = str(uuid.uuid4())
    job_dir = os.path.join(BASE_DOWNLOAD_DIR, job_id)
    os.makedirs(job_dir, exist_ok=True)

    ydl_opts = get_base_opts()
    ydl_opts['outtmpl'] = os.path.join(job_dir, '%(title).80s.%(ext)s')

    if fmt == 'mp3':
        ydl_opts.update({
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        })
    else:
        if quality == '720':
            fmt_str = 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best'
        elif quality == '480':
            fmt_str = 'bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480][ext=mp4]/best'
        else:
            fmt_str = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'

        ydl_opts.update({
            'format': fmt_str,
            'merge_output_format': 'mp4',
        })

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        downloaded_files = glob.glob(os.path.join(job_dir, '*'))
        if not downloaded_files:
            shutil.rmtree(job_dir, ignore_errors=True)
            return "Download failed: Output file not found.", 500

        filepath = downloaded_files[0]

        @after_this_request
        def cleanup(response):
            def remove_dir():
                shutil.rmtree(job_dir, ignore_errors=True)
            threading.Timer(10.0, remove_dir).start()
            return response

        return send_file(filepath, as_attachment=True)

    except Exception as e:
        shutil.rmtree(job_dir, ignore_errors=True)
        return f"Download Error: {str(e)}", 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
    
