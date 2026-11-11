# 4U Ammoootty v4

A Flask + yt-dlp media downloader interface with preview, MP4 quality selection, audio extraction, background jobs and progress.

## Important use restrictions
Only download media you own or are authorized to save, or media that is lawfully available for download. Respect platform terms and copyright. This hosted build intentionally does not accept browser cookies, account credentials, or support private/age-restricted/DRM-protected content. Website support depends on yt-dlp and can change.

## Deploy to the existing Render service
1. Extract this ZIP.
2. Replace the files in your existing GitHub repository `sajay-art/4U-Ammoootty`, preserving folder paths.
3. Commit to `main`.
4. Render should deploy the new commit. If not, choose Manual Deploy > Deploy latest commit.
5. Test `https://fouru-ammoootty.onrender.com/api/health` and look for version `4.0`.

## Runtime
Docker installs FFmpeg and Deno. yt-dlp is installed from its current default extra dependency set. Render free instances have limited CPU, memory, disk, request time and bandwidth and may sleep. Large media jobs may fail. The local downloads folder is ephemeral on free hosting and can be cleared on restart/redeploy.

## Local test
Install Docker and run `docker build -t 4u-ammoootty .` then `docker run -p 10000:10000 4u-ammoootty`.
