#!/usr/bin/env bash
# Quick launcher for Vijayavani Newspaper Downloader Web Interface

cd "$(dirname "$0")"

echo "=========================================================="
echo " Starting Vijayavani Newspaper Downloader Web Interface..."
echo "=========================================================="

python3 server.py "$@"
