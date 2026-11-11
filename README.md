# 4U Ammoootty

A responsive media conversion website. Users upload media they own or are authorized to process and convert it to MP4 or MP3.

## Features
- Responsive dark interface
- Upload by browse or drag-and-drop
- MP4 video and MP3 audio conversion using FFmpeg
- Temporary source/output files
- Flask API and health endpoint
- Docker deployment

## Important scope
This starter does **not** download/extract media from YouTube, Instagram, or other social-platform URLs. Use official platform export/download tools or upload content you own or have permission to process. Do not use this project to bypass DRM, private-account controls, or platform restrictions.

## Run locally
1. Install Python 3.10+ and FFmpeg.
2. Install dependencies: `pip install -r requirements.txt`
3. Run: `python app.py`
4. Open `http://localhost:5000`

## Deploy free (initial launch)
1. Push this folder to a GitHub repository.
2. Create a Render account and choose **New > Blueprint**.
3. Connect the repository; Render detects `render.yaml` and builds the Docker image.
4. Wait for deployment and open the generated `onrender.com` URL.

Free hosting has limits. Render free services may sleep when idle, and ephemeral storage is not persistent. Large uploads/conversions may exceed free-tier request, memory, CPU, or time limits. This is suitable for a demo, not guaranteed unlimited public service.

## Production checklist
- Add rate limiting and abuse protection.
- Add per-IP quotas and stricter upload limits.
- Use a persistent job queue/object storage for larger workloads.
- Configure HTTPS and a custom domain.
- Review platform terms and copyright obligations.
- Do not upload confidential media to a public instance.

## Configuration
- `PORT`: server port (default 5000)
- `FFMPEG_BINARY`: FFmpeg executable path (default `ffmpeg`)
- Upload limit: 200 MB in `app.py`
