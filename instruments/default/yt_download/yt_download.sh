#!/bin/bash

# YouTube Video Downloader using yt-dlp
# Usage: bash yt_download.sh <url>

if [ -z "$1" ]; then
    echo "Error: Please provide a YouTube URL"
    echo "Usage: bash yt_download.sh <url>"
    exit 1
fi

# Install yt-dlp and ffmpeg
sudo apt-get update && sudo apt-get install -y yt-dlp ffmpeg

# Install yt-dlp using pip
pip install --upgrade yt-dlp

# Call the Python script to download the video
python3 /maho/instruments/default/yt_download/download_video.py "$1"
