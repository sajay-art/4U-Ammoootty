# 4U Ammoootty v3

## What works
- Direct public audio/video file URL fetching (100 MB limit) and MP4/MP3 conversion.
- Upload local audio/video files (200 MB limit) and convert to MP4/MP3.
- Temporary files are deleted after processing/delivery.
- SSRF protections: public HTTP(S) hosts only, DNS/IP checks, redirect revalidation, no local/private network targets.

## Social platform links
YouTube, Instagram, Facebook, TikTok, X and Vimeo post URLs are not direct media-file URLs. This app does not extract arbitrary social posts or bypass DRM, login/private-account controls, or platform restrictions. Use platform-authorized export/download options for media you own or are authorized to process, then upload the file here.

## Deploy update to existing Render service
1. Extract this ZIP on your phone.
2. In the existing GitHub repository, replace files with these versions while preserving paths.
3. Commit to `main`.
4. Render should auto-deploy. If not, service > Manual Deploy > Deploy latest commit.
5. Check `/api/health`.

## Local
Install Python 3.10+, FFmpeg, then `pip install -r requirements.txt` and `python app.py`.

## Limits
Free Render instances can sleep and have limited CPU, RAM, request duration and bandwidth. This is a starter, not unlimited production hosting.
