#!/usr/bin/env python3
"""
Vijayavani Newspaper Downloader - Web Application Server
=========================================================
A self-contained Python HTTP server providing a modern Web UI and REST API
to scrape, view, zoom, and download entire Vijayavani newspaper editions for any date.

Zero external dependencies required (Pure Python 3 standard library).
"""

import os
import sys
import json
import time
import uuid
import shutil
import zipfile
import mimetypes
import threading
import webbrowser
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, unquote
from datetime import datetime

# Import scraping engine
try:
    from vijayavani_scraper import EpaperScraper, NewsScraper, EPAPER_EDITIONS, download_file, sanitize_filename
except ImportError:
    # Allow running if scraper is in the same directory
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from vijayavani_scraper import EpaperScraper, NewsScraper, EPAPER_EDITIONS, download_file, sanitize_filename

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEB_DIR = os.path.join(BASE_DIR, "web")
DOWNLOADS_DIR = os.path.join(BASE_DIR, "downloads")
EPAPER_DIR = os.path.join(DOWNLOADS_DIR, "epaper")
NEWS_DIR = os.path.join(DOWNLOADS_DIR, "news")

os.makedirs(EPAPER_DIR, exist_ok=True)
os.makedirs(NEWS_DIR, exist_ok=True)

# Rich Kannada Edition Metadata
EDITIONS_LIST = [
    {"code": "BEN", "name": "Bengaluru", "name_kn": "ಬೆಂಗಳೂರು", "tag": "ರಾಜಧಾನಿ (Capital)", "sub_path": "BENG"},
    {"code": "HUB", "name": "Hubballi", "name_kn": "ಹುಬ್ಬಳ್ಳಿ", "tag": "ಉತ್ತರ ಕರ್ನಾಟಕ", "sub_path": "HUB"},
    {"code": "NAM", "name": "Namaste Bengaluru", "name_kn": "ನಮಸ್ತೆ ಬೆಂಗಳೂರು", "tag": "ನಗರ ವಿಶೇಷ", "sub_path": "NAM"},
    {"code": "MYS", "name": "Mysuru", "name_kn": "ಮೈಸೂರು", "tag": "ದಕ್ಷಿಣ ಕರ್ನಾಟಕ", "sub_path": "MYS"},
    {"code": "MNG", "name": "Mangaluru", "name_kn": "ಮಂಗಳೂರು", "tag": "ಕರಾವಳಿ ಕರ್ನಾಟಕ", "sub_path": "MNG"},
    {"code": "BEL", "name": "Belagavi", "name_kn": "ಬೆಳಗಾವಿ", "tag": "ಗಡಿ ನಾಡು", "sub_path": "BEL"},
    {"code": "VIJ", "name": "Vijayapura", "name_kn": "ವಿಜಯಪುರ", "tag": "ವಿಜಯಪುರ", "sub_path": "VIJ"},
    {"code": "KAL", "name": "Kalaburagi", "name_kn": "ಕಲಬುರಗಿ", "tag": "ಕಲ್ಯಾಣ ಕರ್ನಾಟಕ", "sub_path": "KAL"},
    {"code": "SHI", "name": "Shivamogga", "name_kn": "ಶಿವಮೊಗ್ಗ", "tag": "ಮಲೆನಾಡು", "sub_path": "SHI"},
    {"code": "CIN", "name": "Cinema / Special", "name_kn": "ಸಿನಿಮಾ / ವಿಶೇಷ", "tag": "ಸಿನಿವಾಣಿ", "sub_path": "CIN"},
]

# Thread-safe in-memory job store
jobs_lock = threading.Lock()
ACTIVE_JOBS = {}

def get_job(job_id):
    with jobs_lock:
        return ACTIVE_JOBS.get(job_id)

def set_job(job_id, data):
    with jobs_lock:
        ACTIVE_JOBS[job_id] = data

def update_job(job_id, **kwargs):
    with jobs_lock:
        if job_id in ACTIVE_JOBS:
            ACTIVE_JOBS[job_id].update(kwargs)

def append_job_log(job_id, message):
    with jobs_lock:
        if job_id in ACTIVE_JOBS:
            ACTIVE_JOBS[job_id].setdefault("logs", []).append(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

# ==============================================================================
# BACKGROUND SCRAPER WORKER
# ==============================================================================

def execute_epaper_download(job_id, date_str, ed_code, all_pages=True):
    """Worker thread that fetches and saves all pages for an edition & date."""
    ed_info = next((e for e in EDITIONS_LIST if e["code"] == ed_code), {"name": ed_code, "name_kn": ed_code})
    ed_name = ed_info["name"]
    ed_name_kn = ed_info.get("name_kn", ed_name)
    
    update_job(job_id,
        status="fetching_pages",
        percent=5,
        message=f"Fetching page catalog for {ed_name} ({date_str})..."
    )
    append_job_log(job_id, f"Connecting to Vijayavani ePaper servers for {ed_name} on {date_str}...")

    scraper = EpaperScraper(output_dir=EPAPER_DIR)
    pages = scraper.fetch_edition_pages(ed_code, date_str)

    if not pages:
        update_job(job_id,
            status="error",
            percent=100,
            error=f"No pages found for {ed_name} on {date_str}. Please verify that a newspaper was published on this date."
        )
        append_job_log(job_id, f"No pages found for {ed_name} on {date_str}")
        return

    total_pages = len(pages) if all_pages else min(1, len(pages))
    target_pages = pages if all_pages else [pages[0]]

    folder_name = f"{ed_code}_{date_str}"
    target_dir = os.path.join(EPAPER_DIR, folder_name)
    os.makedirs(target_dir, exist_ok=True)

    update_job(job_id,
        status="downloading",
        total_pages=total_pages,
        folder_name=folder_name,
        target_dir=target_dir,
        percent=10,
        message=f"Found {len(pages)} pages. Downloading {total_pages} page(s)..."
    )
    append_job_log(job_id, f"Found {len(pages)} pages. Starting download of {total_pages} page(s) to '{folder_name}'...")

    downloaded = []
    metadata_pages = []

    for idx, p in enumerate(target_pages, start=1):
        p_num = p["page_num"]
        pad = f"{p_num:02d}"
        file_name = f"Page_{pad}.jpg"
        save_path = os.path.join(target_dir, file_name)

        pct = int(10 + (idx / total_pages) * 85)
        update_job(job_id,
            current_page=p_num,
            percent=pct,
            message=f"Downloading Page {idx} of {total_pages} (పుಟ {p_num})..."
        )
        append_job_log(job_id, f"Downloading Page {p_num:02d} ({p.get('img_id', '')})...")

        # Try full resolution first, fallback to thumbnail
        ok = download_file(p["full_url"], save_path)
        if not ok:
            ok = download_file(p["thumb_url"], save_path)

        if ok and os.path.exists(save_path):
            file_size = os.path.getsize(save_path)
            page_record = {
                "page_num": p_num,
                "file_name": file_name,
                "file_size": file_size,
                "local_url": f"/downloads/epaper/{folder_name}/{file_name}",
                "full_url": p["full_url"],
                "thumb_url": p["thumb_url"]
            }
            downloaded.append(page_record)
            metadata_pages.append(page_record)
            update_job(job_id, pages_downloaded=list(downloaded))
            append_job_log(job_id, f"✔ Page {p_num:02d} saved ({file_size:,} bytes)")
        else:
            append_job_log(job_id, f"✘ Page {p_num:02d} download failed")

    # Save issue metadata JSON
    issue_meta = {
        "edition_code": ed_code,
        "edition_name": ed_name,
        "edition_name_kn": ed_name_kn,
        "date": date_str,
        "folder": folder_name,
        "page_count": len(downloaded),
        "created_at": datetime.now().isoformat(),
        "pages": metadata_pages
    }
    with open(os.path.join(target_dir, "issue_metadata.json"), "w", encoding="utf-8") as f:
        json.dump(issue_meta, f, ensure_ascii=False, indent=2)

    update_job(job_id,
        status="completed",
        percent=100,
        message=f"Successfully downloaded all {len(downloaded)} pages of {ed_name}!",
        pages_downloaded=downloaded
    )
    append_job_log(job_id, f"Download complete! Saved {len(downloaded)} pages in downloads/epaper/{folder_name}")

# ==============================================================================
# HTTP REQUEST HANDLER
# ==============================================================================

class AppHandler(SimpleHTTPRequestHandler):
    """Custom request handler for Vijayavani Web Interface & REST APIs."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BASE_DIR, **kwargs)

    def send_json(self, data, status=200):
        """Helper to send JSON HTTP response."""
        content = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.end_headers()
        self.wfile.write(content)

    def do_OPTIONS(self):
        """Handle CORS pre-flight."""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        """Handle HTTP GET requests."""
        parsed = urlparse(self.path)
        path = parsed.path
        qs = parse_qs(parsed.query)

        # 1. API: List Editions
        if path == "/api/editions":
            self.send_json(EDITIONS_LIST)
            return

        # 2. API: Server Status
        if path == "/api/status":
            archive_count = len([d for d in os.listdir(EPAPER_DIR) if os.path.isdir(os.path.join(EPAPER_DIR, d))]) if os.path.exists(EPAPER_DIR) else 0
            self.send_json({
                "status": "online",
                "time": datetime.now().isoformat(),
                "archives_count": archive_count,
                "epaper_dir": EPAPER_DIR
            })
            return

        # 3. API: Job Status Polling
        if path.startswith("/api/epaper/job/"):
            job_id = path.replace("/api/epaper/job/", "").strip()
            job = get_job(job_id)
            if job:
                self.send_json(job)
            else:
                self.send_json({"error": "Job not found"}, 404)
            return

        # 4. API: List Downloaded Archives
        if path == "/api/archives":
            archives = []
            if os.path.exists(EPAPER_DIR):
                for folder in os.listdir(EPAPER_DIR):
                    folder_path = os.path.join(EPAPER_DIR, folder)
                    if os.path.isdir(folder_path):
                        meta_file = os.path.join(folder_path, "issue_metadata.json")
                        images = [f for f in os.listdir(folder_path) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
                        images.sort()

                        if os.path.exists(meta_file):
                            try:
                                with open(meta_file, 'r', encoding='utf-8') as f:
                                    meta = json.load(f)
                                total_size = sum(os.path.getsize(os.path.join(folder_path, img)) for img in images)
                                cover = f"/downloads/epaper/{folder}/{images[0]}" if images else None
                                archives.append({
                                    "folder": folder,
                                    "edition_code": meta.get("edition_code", folder.split("_")[0]),
                                    "edition_name": meta.get("edition_name", folder),
                                    "date": meta.get("date", ""),
                                    "page_count": len(images),
                                    "total_size_bytes": total_size,
                                    "cover_url": cover,
                                    "created_at": meta.get("created_at", "")
                                })
                                continue
                            except Exception:
                                pass

                        # Fallback parsing from folder name
                        total_size = sum(os.path.getsize(os.path.join(folder_path, img)) for img in images)
                        cover = f"/downloads/epaper/{folder}/{images[0]}" if images else None
                        archives.append({
                            "folder": folder,
                            "edition_code": folder.split("_")[0] if "_" in folder else folder,
                            "edition_name": folder,
                            "date": folder.split("_")[1] if "_" in folder else "",
                            "page_count": len(images),
                            "total_size_bytes": total_size,
                            "cover_url": cover,
                            "created_at": datetime.fromtimestamp(os.path.getmtime(folder_path)).isoformat()
                        })

            archives.sort(key=lambda x: x.get("date") or x.get("folder"), reverse=True)
            self.send_json(archives)
            return

        # 5. API: Archive Folder Details
        if path.startswith("/api/archives/"):
            folder_name = unquote(path.replace("/api/archives/", "").strip())
            folder_path = os.path.join(EPAPER_DIR, folder_name)
            if not os.path.isdir(folder_path):
                self.send_json({"error": "Archive not found"}, 404)
                return

            images = [f for f in os.listdir(folder_path) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
            images.sort()
            pages = []
            for idx, img in enumerate(images, start=1):
                img_path = os.path.join(folder_path, img)
                pages.append({
                    "page_num": idx,
                    "file_name": img,
                    "file_size": os.path.getsize(img_path),
                    "local_url": f"/downloads/epaper/{folder_name}/{img}",
                    "full_url": f"/downloads/epaper/{folder_name}/{img}"
                })

            meta_file = os.path.join(folder_path, "issue_metadata.json")
            ed_name = folder_name
            date_str = ""
            if os.path.exists(meta_file):
                try:
                    with open(meta_file, 'r', encoding='utf-8') as f:
                        meta = json.load(f)
                        ed_name = meta.get("edition_name", folder_name)
                        date_str = meta.get("date", "")
                except Exception:
                    pass

            self.send_json({
                "folder": folder_name,
                "edition_name": ed_name,
                "date": date_str,
                "pages": pages
            })
            return

        # 6. API: Download All Pages as ZIP
        if path == "/api/download-zip":
            folder_name = qs.get("folder", [""])[0]
            if not folder_name:
                self.send_json({"error": "Missing folder parameter"}, 400)
                return

            folder_path = os.path.join(EPAPER_DIR, folder_name)
            if not os.path.isdir(folder_path):
                self.send_json({"error": "Archive folder not found"}, 404)
                return

            zip_filename = f"Vijayavani_{folder_name}.zip"
            images = [f for f in os.listdir(folder_path) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
            images.sort()

            # Stream zip directly
            self.send_response(200)
            self.send_header("Content-Type", "application/zip")
            self.send_header("Content-Disposition", f'attachment; filename="{zip_filename}"')
            self.end_headers()

            with zipfile.ZipFile(self.wfile, "w", zipfile.ZIP_DEFLATED) as zip_out:
                for img in images:
                    full_p = os.path.join(folder_path, img)
                    zip_out.write(full_p, arcname=img)
                # Also include metadata if exists
                meta_file = os.path.join(folder_path, "issue_metadata.json")
                if os.path.exists(meta_file):
                    zip_out.write(meta_file, arcname="issue_metadata.json")
            return

        # 7. Serve Static Files from /web
        if path == "/" or path == "/index.html":
            self.serve_file(os.path.join(WEB_DIR, "index.html"), "text/html; charset=utf-8")
            return

        if path in ["/style.css", "/app.js"]:
            mime = "text/css" if path.endswith(".css") else "application/javascript"
            self.serve_file(os.path.join(WEB_DIR, path.lstrip("/")), mime)
            return

        # 8. Serve Downloaded Image Files
        if path.startswith("/downloads/"):
            rel_path = unquote(path.replace("/downloads/", ""))
            full_path = os.path.join(DOWNLOADS_DIR, rel_path)
            # Security check: prevent directory traversal
            if os.path.commonpath([DOWNLOADS_DIR, os.path.abspath(full_path)]) == DOWNLOADS_DIR and os.path.isfile(full_path):
                mime, _ = mimetypes.guess_type(full_path)
                self.serve_file(full_path, mime or "application/octet-stream")
                return
            else:
                self.send_error(404, "File not found")
                return

        self.send_error(404, "Page not found")

    def do_POST(self):
        """Handle HTTP POST requests."""
        parsed = urlparse(self.path)
        path = parsed.path

        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length)
        try:
            body = json.loads(post_data.decode("utf-8")) if post_data else {}
        except Exception:
            body = {}

        # 1. API: Preview Pages (Fast check without downloading)
        if path == "/api/epaper/preview":
            date_str = body.get("date")
            ed_code = body.get("edition", "BEN")
            if not date_str:
                self.send_json({"error": "Publication date is required"}, 400)
                return

            scraper = EpaperScraper(output_dir=EPAPER_DIR)
            pages = scraper.fetch_edition_pages(ed_code, date_str)
            ed_info = next((e for e in EDITIONS_LIST if e["code"] == ed_code), {"name": ed_code})
            
            self.send_json({
                "date": date_str,
                "edition_code": ed_code,
                "edition_name": ed_info["name"],
                "edition_name_kn": ed_info.get("name_kn", ed_info["name"]),
                "pages": pages,
                "total_pages": len(pages)
            })
            return

        # 2. API: Start Scraping Job
        if path == "/api/epaper/scrape":
            date_str = body.get("date")
            ed_code = body.get("edition", "BEN")
            all_pages = body.get("all_pages", True)

            if not date_str:
                self.send_json({"error": "Publication date is required"}, 400)
                return

            job_id = f"job_{int(time.time())}_{uuid.uuid4().hex[:6]}"
            job_record = {
                "job_id": job_id,
                "date": date_str,
                "edition": ed_code,
                "edition_name": next((e["name"] for e in EDITIONS_LIST if e["code"] == ed_code), ed_code),
                "all_pages": all_pages,
                "status": "pending",
                "percent": 0,
                "message": "Initializing...",
                "pages_downloaded": [],
                "logs": [],
                "created_at": datetime.now().isoformat()
            }
            set_job(job_id, job_record)

            # Spawn worker thread
            thread = threading.Thread(
                target=execute_epaper_download,
                args=(job_id, date_str, ed_code, all_pages),
                daemon=True
            )
            thread.start()

            self.send_json({"job_id": job_id, "status": "started"})
            return

        # 3. API: News Portal Stories Scrape
        if path == "/api/news/scrape":
            section = body.get("section")
            limit = int(body.get("limit", 15))
            breaking_only = bool(body.get("breaking_only", False))

            news_scraper = NewsScraper(output_dir=NEWS_DIR)
            if breaking_only:
                stories = news_scraper.get_breaking_news()
            else:
                stories = news_scraper.get_latest_stories(limit=limit, section=section)

            results = []
            for s in stories:
                s3_key = s.get("hero-image-s3-key")
                image_url = f"{NewsScraper.IMAGE_CDN}/{s3_key}?format=jpg&q=80" if s3_key else None
                results.append({
                    "id": s.get("id"),
                    "headline": s.get("headline"),
                    "slug": s.get("slug"),
                    "published_at": s.get("published-at"),
                    "sections": ", ".join([sec.get("name", "") for sec in s.get("sections", [])]),
                    "image_url": image_url
                })

            self.send_json({"stories": results})
            return

        # 4. API: Delete Archive
        if path == "/api/archives/delete":
            folder_name = body.get("folder")
            if not folder_name:
                self.send_json({"error": "Folder name required"}, 400)
                return

            folder_path = os.path.join(EPAPER_DIR, folder_name)
            if os.path.isdir(folder_path):
                shutil.rmtree(folder_path, ignore_errors=True)
                self.send_json({"status": "deleted", "folder": folder_name})
            else:
                self.send_json({"error": "Archive not found"}, 404)
            return

        self.send_error(404, "Endpoint not found")

    def serve_file(self, file_path, content_type):
        """Serve a local file with the specified MIME type."""
        try:
            with open(file_path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self.send_error(500, f"Error reading file: {e}")

# ==============================================================================
# SERVER LAUNCHER
# ==============================================================================

def find_available_port(start_port=8080, max_tries=20):
    """Find an available TCP port starting from start_port."""
    import socket
    for port in range(start_port, start_port + max_tries):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("0.0.0.0", port))
                return port
            except OSError:
                continue
    return start_port

def start_server(port=None, open_browser=True):
    port = port or find_available_port(start_port=8080)
    server_address = ("0.0.0.0", port)
    
    httpd = ThreadingHTTPServer(server_address, AppHandler)
    url = f"http://localhost:{port}"

    print("\n" + "=" * 70)
    print("  🗞️  VIJAYAVANI NEWSPAPER DOWNLOADER - WEB INTERFACE RUNNING")
    print("=" * 70)
    print(f"  Local Web UI URL : \033[92m\033[1m{url}\033[0m")
    print(f"  Storage Directory: {DOWNLOADS_DIR}")
    print("=" * 70)
    print("  Press Ctrl+C to stop the server.\n")

    if open_browser:
        def _open():
            time.sleep(0.8)
            webbrowser.open(url)
        threading.Thread(target=_open, daemon=True).start()

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[!] Server shutting down.")
        httpd.server_close()
        sys.exit(0)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Vijayavani Newspaper Downloader Web Server")
    parser.add_argument("--port", type=int, default=None, help="Port to bind (default: 8080)")
    parser.add_argument("--no-browser", action="store_true", help="Do not automatically open browser")
    args = parser.parse_args()

    start_server(port=args.port, open_browser=not args.no_browser)
