# 4U Ammoootty v2

Mobile-friendly Flask media link detector and authorized media converter.

## Features
- Detects YouTube, Instagram, Facebook, TikTok, X/Twitter, Vimeo and other URLs.
- Converts user-uploaded authorized video/audio files to MP4 or MP3 with FFmpeg.
- Temporary input/output files; upload limit 200 MB.
- Docker + Render Blueprint deployment.

## Important
This project detects platform URLs but does not extract arbitrary social-platform videos. A detected URL is not proof that third-party downloading is allowed. Use official platform download/export tools or upload media you own or are authorized to process. It does not bypass DRM, private-account restrictions, or platform controls.

## Deploy update
1. Replace the corresponding files in your existing GitHub repository with these files.
2. Commit the changes to `main`.
3. Render should automatically deploy the new commit. If not, open the service and choose Manual Deploy > Deploy latest commit.
4. Test `/api/health`, link detection and MP4/MP3 conversion.

## Local run
Install FFmpeg and Python 3.10+, then `pip install -r requirements.txt` and `python app.py`.
