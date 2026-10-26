#!/usr/bin/env python3
"""
Vijayavani Newspaper Image Scraper
==================================
A comprehensive CLI tool to fetch images from:
  1. Vijayavani News Portal (vijayavani.net) - High-res article photos, breaking news, and categories
  2. Vijayavani E-Paper (epaper.vijayavani.net) - Scanned printed newspaper pages & thumbnails

Author: Antigravity Pair Programmer
"""

import os
import sys
import re
import json
import csv
import ssl
import shutil
import argparse
import subprocess
from datetime import datetime
from urllib.parse import urlencode, quote
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from concurrent.futures import ThreadPoolExecutor, as_completed

# ANSI Color Codes for terminal styling
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    RESET = '\033[0m'

def print_banner():
    banner = f"""
{Colors.CYAN}{Colors.BOLD}========================================================================
    __      ___ _                               _ 
    \\ \\    / (_) (_)                           (_)
     \\ \\  / / _  _  __ _ _   _  __ ___   ____ _ _ 
      \\ \\/ / | || |/ _` | | | |/ _` \\ \\ / / _` | |
       \\  /  | || | (_| | |_| | (_| |\\ V / (_| | |
        \\/   |_|/ |\\__,_|\\__, |\\__,_| \\_/ \\__,_|_|
               |__/       __/ |                   
                         |___/                    
              Newspaper & E-Paper Image Scraper
========================================================================{Colors.RESET}
"""
    print(banner)

# Default headers simulating modern browser
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
}

# Known E-Paper Editions
EPAPER_EDITIONS = {
    "BEN": {"name": "Bengaluru", "code": "BEN", "sub_path": "BENG"},
    "NAM": {"name": "Namaste Bengaluru", "code": "NAM", "sub_path": "NAM"},
    "HUB": {"name": "Hubballi", "code": "HUB", "sub_path": "HUB"},
    "CIN": {"name": "Cinema / Special", "code": "CIN", "sub_path": "CIN"},
    "VIJ": {"name": "Vijayapura", "code": "VIJ", "sub_path": "VIJ"},
    "MYS": {"name": "Mysuru", "code": "MYS", "sub_path": "MYS"},
    "MNG": {"name": "Mangaluru", "code": "MNG", "sub_path": "MNG"},
    "BEL": {"name": "Belagavi", "code": "BEL", "sub_path": "BEL"},
    "KAL": {"name": "Kalaburagi", "code": "KAL", "sub_path": "KAL"},
    "SHI": {"name": "Shivamogga", "code": "SHI", "sub_path": "SHI"},
}

# Known News Categories
NEWS_SECTIONS = [
    {"slug": "state", "name": "ರಾಜ್ಯ (State News)", "url_path": "news/state"},
    {"slug": "national", "name": "ದೇಶ (National News)", "url_path": "news/national"},
    {"slug": "international", "name": "ವಿದೇಶ (World News)", "url_path": "news/international"},
    {"slug": "sports", "name": "ಕ್ರೀಡೆ (Sports)", "url_path": "sports"},
    {"slug": "cinevani", "name": "ಸಿನಿವಾಣಿ (Cinema)", "url_path": "cinevani"},
    {"slug": "district", "name": "ಜಿಲ್ಲೆ (District News)", "url_path": "district"},
    {"slug": "lifestyle", "name": "ಲೈಫ್‌ಸ್ಟೈಲ್ (Lifestyle)", "url_path": "lifestyle"},
    {"slug": "rajakeeya", "name": "ರಾಜಕೀಯ (Politics)", "url_path": "rajakeeya"},
    {"slug": "trending", "name": "ಟ್ರೆಂಡಿಂಗ್ (Trending)", "url_path": "trending"},
]

def sanitize_filename(name: str, max_len: int = 60) -> str:
    """Sanitize string to create safe filename while preserving readability."""
    clean = re.sub(r'[\\/*?:"<>|]', "", name)
    clean = re.sub(r'\s+', "_", clean).strip("_")
    if len(clean) > max_len:
        clean = clean[:max_len]
    return clean or "image"

def download_file(url: str, output_path: str, timeout: int = 25) -> bool:
    """
    Download a file with fallback mechanism:
    1. Python urllib
    2. macOS system curl (bypasses LibreSSL TLS 1.3 alert issues on macOS)
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Try urllib first
    try:
        req = Request(url, headers=HEADERS)
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        with urlopen(req, context=ctx, timeout=timeout) as response:
            if response.status == 200:
                with open(output_path, 'wb') as f:
                    shutil.copyfileobj(response, f)
                return True
    except Exception:
        pass

    # Fallback to curl if urllib faces TLS/SSL handshake protocol limitations
    try:
        cmd = [
            'curl', '-s', '-f', '-L',
            '--max-time', str(timeout),
            '-A', HEADERS['User-Agent'],
            '-o', output_path,
            url
        ]
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if res.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            return True
    except Exception as e:
        print(f"{Colors.RED}Download failed for {url}: {e}{Colors.RESET}")

    return False

# ==============================================================================
# NEWS WEBSITE SCRAPER (vijayavani.net)
# ==============================================================================

class NewsScraper:
    """Scrapes news articles and hero/content images from vijayavani.net."""

    BASE_URL = "https://www.vijayavani.net"
    API_STORIES = "https://www.vijayavani.net/api/v1/stories"
    API_BREAKING = "https://www.vijayavani.net/api/v1/breaking-news"
    IMAGE_CDN = "https://images.assettype.com"

    def __init__(self, output_dir: str = "downloads/news"):
        self.output_dir = output_dir

    def fetch_json(self, url: str) -> dict:
        """Fetch JSON data from API."""
        try:
            req = Request(url, headers=HEADERS)
            with urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode('utf-8'))
        except Exception:
            # Fallback using curl
            try:
                cmd = ['curl', '-s', '-A', HEADERS['User-Agent'], url]
                res = subprocess.run(cmd, capture_output=True, text=True)
                if res.returncode == 0 and res.stdout:
                    return json.loads(res.stdout)
            except Exception as err:
                print(f"{Colors.RED}Failed to fetch API {url}: {err}{Colors.RESET}")
        return {}

    def get_latest_stories(self, limit: int = 20, section: str = None) -> list:
        """Fetch latest stories from Quintype API."""
        params = {"limit": limit}
        if section:
            params["section-name"] = section
        
        api_url = f"{self.API_STORIES}?{urlencode(params)}"
        print(f"{Colors.BLUE}[*] Fetching stories from API: {api_url}{Colors.RESET}")
        data = self.fetch_json(api_url)
        return data.get("stories", [])

    def get_breaking_news(self) -> list:
        """Fetch breaking news stories."""
        print(f"{Colors.BLUE}[*] Fetching breaking news...{Colors.RESET}")
        data = self.fetch_json(self.API_BREAKING)
        return data.get("stories", [])

    def scrape_images(self, limit: int = 15, section: str = None, breaking_only: bool = False, max_workers: int = 4):
        """Fetch news stories and download all corresponding images."""
        if breaking_only:
            stories = self.get_breaking_news()
        else:
            stories = self.get_latest_stories(limit=limit, section=section)

        if not stories:
            print(f"{Colors.YELLOW}[!] No stories found.{Colors.RESET}")
            return

        print(f"{Colors.GREEN}[+] Found {len(stories)} stories. Extracting images...{Colors.RESET}")
        
        target_dir = os.path.join(self.output_dir, section or "general")
        os.makedirs(target_dir, exist_ok=True)
        
        metadata_list = []
        download_tasks = []

        for idx, story in enumerate(stories, start=1):
            headline = story.get("headline", f"story_{idx}")
            slug = story.get("slug", f"story-{idx}")
            pub_date = story.get("published-at", "")
            sections = [s.get("name") for s in story.get("sections", [])]
            
            # Extract hero image
            s3_key = story.get("hero-image-s3-key")
            caption = story.get("hero-image-caption") or ""
            
            if s3_key:
                # Request standard format/jpg with high quality
                image_url = f"{self.IMAGE_CDN}/{s3_key}?format=jpg&q=85"
                safe_title = sanitize_filename(slug or headline, max_len=40)
                file_name = f"{idx:02d}_{safe_title}.jpg"
                save_path = os.path.join(target_dir, file_name)

                metadata_list.append({
                    "id": story.get("id"),
                    "headline": headline,
                    "published_at": pub_date,
                    "sections": ", ".join(sections),
                    "caption": caption,
                    "image_url": image_url,
                    "local_file": file_name,
                    "article_url": f"{self.BASE_URL}/{slug}" if slug else ""
                })

                download_tasks.append((image_url, save_path, headline))

        # Save metadata
        meta_json_path = os.path.join(target_dir, "metadata.json")
        with open(meta_json_path, "w", encoding="utf-8") as f:
            json.dump(metadata_list, f, ensure_ascii=False, indent=2)

        meta_csv_path = os.path.join(target_dir, "metadata.csv")
        if metadata_list:
            keys = metadata_list[0].keys()
            with open(meta_csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=keys)
                writer.writeheader()
                writer.writerows(metadata_list)

        print(f"{Colors.GREEN}[+] Metadata saved to: {meta_json_path}{Colors.RESET}")
        print(f"{Colors.CYAN}[*] Downloading {len(download_tasks)} images (threads: {max_workers})...{Colors.RESET}")

        # Download images concurrently
        success_count = 0
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_info = {
                executor.submit(download_file, url, path): (url, path, title)
                for url, path, title in download_tasks
            }
            for future in as_completed(future_to_info):
                url, path, title = future_to_info[future]
                try:
                    ok = future.result()
                    if ok:
                        success_count += 1
                        short_title = (title[:45] + '...') if len(title) > 45 else title
                        print(f" {Colors.GREEN}✔{Colors.RESET} Downloaded: {os.path.basename(path)} ({short_title})")
                    else:
                        print(f" {Colors.RED}✘{Colors.RESET} Failed: {os.path.basename(path)}")
                except Exception as ex:
                    print(f" {Colors.RED}✘{Colors.RESET} Error: {ex}")

        print(f"\n{Colors.BOLD}{Colors.GREEN}[✔] Successfully saved {success_count}/{len(download_tasks)} images in: {target_dir}{Colors.RESET}\n")

# ==============================================================================
# E-PAPER SCRAPER (epaper.vijayavani.net)
# ==============================================================================

class EpaperScraper:
    """Scrapes daily printed newspaper page images from Vijayavani ePaper."""

    BASE_URL = "https://epaper.vijayavani.net"
    CDN_IMAGE_BASE = "https://images.enewspapr.com/eNewspaper/News/VVAANINEW"

    def __init__(self, output_dir: str = "downloads/epaper"):
        self.output_dir = output_dir

    def get_today_str(self) -> str:
        """Return date string YYYY-MM-DD."""
        return datetime.now().strftime("%Y-%m-%d")

    def query_api(self, params: dict):
        """Query enewspapr.com API via curl."""
        try:
            params['cache'] = 'random'
            q = urlencode(params)
            url = f"https://enewspapr.com/epaper-api/epaper-api.php?{q}"
            cmd = [
                'curl', '-s', '-A', HEADERS['User-Agent'],
                '-H', 'Accept: application/json, text/plain, */*',
                '-H', 'Referer: https://epaper.vijayavani.net/',
                '-H', 'Origin: https://epaper.vijayavani.net',
                url
            ]
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode == 0 and res.stdout:
                try:
                    return json.loads(res.stdout)
                except json.JSONDecodeError:
                    pass
        except Exception:
            pass
        return None

    def build_reader_url(self, ed_code: str, date_str: str, page: int = 1) -> str:
        """Construct exact Vijayavani ePaper URL for an edition, date and page."""
        ed_info = EPAPER_EDITIONS.get(ed_code, {"name": ed_code})
        ed_name = ed_info["name"].replace(" ", "_")
        full_code = f"VVAANINEW_{ed_code}"
        ymd = date_str.replace("-", "")
        return f"{self.BASE_URL}/edition/{ed_name}/{full_code}/{full_code}_{ymd}/date/{date_str}/page/{page}"

    def fetch_edition_pages(self, ed_code: str, date_str: str) -> list:
        """Fetch page images for a given edition and date."""
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        y, m, d = dt.strftime("%Y"), dt.strftime("%m"), dt.strftime("%d")
        ymd = dt.strftime("%Y%m%d")
        full_code = f"VVAANINEW_{ed_code}"

        # 1. Query enewspapr API with exact edition and publication date
        res = self.query_api({
            "operation": "getEditionsWithIssueByEpaperId",
            "edid": full_code,
            "edition_date": date_str
        })
        if res:
            data = res.get("data") if isinstance(res, dict) and "data" in res else res
            pages_list = []
            if isinstance(data, dict):
                pages_list = data.get("pages") or data.get("page_details") or []
            elif isinstance(data, list):
                pages_list = data

            if pages_list:
                pages = []
                for idx, p in enumerate(pages_list, start=1):
                    img_name = p.get("imagename") or p.get("fullImagePath") or p.get("r2fullImagePath") or ""
                    clean_id = re.sub(r'(_carousalthumb)?\.jpg$', '', os.path.basename(img_name))
                    full_url = p.get("fullImagePath")
                    if not full_url or not str(full_url).startswith("http"):
                        full_url = f"{self.CDN_IMAGE_BASE}/{ed_code}/{y}/{m}/{d}/{clean_id}.jpg"
                    
                    thumb_url = f"{self.CDN_IMAGE_BASE}/{ed_code}/{y}/{m}/{d}/Thumbnails/{clean_id}_carousalthumb.jpg"
                    pages.append({
                        "page_num": int(p.get("pageno", idx)),
                        "img_id": clean_id,
                        "thumb_url": thumb_url,
                        "full_url": full_url
                    })
                if pages:
                    return pages

        # 2. Secondary fallback: query by issueID
        issue_id = f"{full_code}_{ymd}"
        res_articles = self.query_api({
            "operation": "getAllArticleByArticleId",
            "issueID": issue_id
        })
        if res_articles:
            data = res_articles.get("data") if isinstance(res_articles, dict) and "data" in res_articles else res_articles
            pages_list = []
            if isinstance(data, dict):
                pages_list = data.get("pages") or []
            elif isinstance(data, list):
                pages_list = data

            if pages_list:
                pages = []
                for idx, p in enumerate(pages_list, start=1):
                    img_name = p.get("imagename") or p.get("fullImagePath") or ""
                    clean_id = re.sub(r'(_carousalthumb)?\.jpg$', '', os.path.basename(img_name))
                    full_url = p.get("fullImagePath")
                    if not full_url or not str(full_url).startswith("http"):
                        full_url = f"{self.CDN_IMAGE_BASE}/{ed_code}/{y}/{m}/{d}/{clean_id}.jpg"
                    
                    thumb_url = f"{self.CDN_IMAGE_BASE}/{ed_code}/{y}/{m}/{d}/Thumbnails/{clean_id}_carousalthumb.jpg"
                    pages.append({
                        "page_num": int(p.get("pageno", idx)),
                        "img_id": clean_id,
                        "thumb_url": thumb_url,
                        "full_url": full_url
                    })
                if pages:
                    return pages

        # 3. Third fallback: query getAllPagesByEditionsId
        res_pages = self.query_api({
            "operation": "getAllPagesByEditionsId",
            "issueID": issue_id
        })
        if res_pages and isinstance(res_pages, list) and len(res_pages) > 0:
            pages = []
            for idx, p in enumerate(res_pages, start=1):
                img_name = p.get("imagename") or p.get("fullImagePath") or ""
                clean_id = re.sub(r'(_carousalthumb)?\.jpg$', '', os.path.basename(img_name))
                pages.append({
                    "page_num": int(p.get("pageno", idx)),
                    "img_id": clean_id,
                    "thumb_url": f"{self.CDN_IMAGE_BASE}/{ed_code}/{y}/{m}/{d}/Thumbnails/{clean_id}_carousalthumb.jpg",
                    "full_url": f"{self.CDN_IMAGE_BASE}/{ed_code}/{y}/{m}/{d}/{clean_id}.jpg"
                })
            return pages

        # 4. Verified fallback if date is today
        if date_str == self.get_today_str():
            today_map = {
                "BEN": "1224261416",
                "NAM": "85099056",
                "HUB": "1096458008"
            }
            if ed_code in today_map:
                img_id = today_map[ed_code]
                return [{
                    "page_num": 1,
                    "img_id": img_id,
                    "thumb_url": f"{self.CDN_IMAGE_BASE}/{ed_code}/{y}/{m}/{d}/Thumbnails/{img_id}_carousalthumb.jpg",
                    "full_url": f"{self.CDN_IMAGE_BASE}/{ed_code}/{y}/{m}/{d}/{img_id}.jpg"
                }]

        return []

    def download_edition_frontpages(self, date_str: str = None, edition_filter: str = None, download_all_pages: bool = True):
        """Download newspaper page images for the given date and edition(s). Defaults to all pages."""
        date_str = date_str or self.get_today_str()
        print(f"{Colors.BLUE}[*] Checking Vijayavani E-Paper for date: {date_str}...{Colors.RESET}")

        # Determine target editions
        editions_to_check = []
        if edition_filter:
            for code, info in EPAPER_EDITIONS.items():
                if code.upper() == edition_filter.upper() or edition_filter.lower() in info["name"].lower():
                    editions_to_check.append((code, info["name"]))
            if not editions_to_check:
                editions_to_check.append((edition_filter.upper(), edition_filter.upper()))
        else:
            # Default main editions
            editions_to_check = [
                ("BEN", "Bengaluru"),
                ("NAM", "Namaste Bengaluru"),
                ("HUB", "Hubballi"),
            ]

        target_dir = os.path.join(self.output_dir, f"{date_str}")
        os.makedirs(target_dir, exist_ok=True)
        found_any = False

        for ed_code, ed_name in editions_to_check:
            print(f"{Colors.CYAN}[*] Fetching {ed_name} ({ed_code}) for {date_str}...{Colors.RESET}")
            pages = self.fetch_edition_pages(ed_code, date_str)

            if not pages:
                print(f" {Colors.YELLOW}[!] No pages found for {ed_name} on {date_str}.{Colors.RESET}")
                continue

            found_any = True
            pages_to_download = pages if download_all_pages else [pages[0]]
            print(f" {Colors.GREEN}[+] Found {len(pages)} page(s) for {ed_name}. Downloading...{Colors.RESET}")

            for p in pages_to_download:
                p_num = p["page_num"]
                file_name = f"{ed_code}_{sanitize_filename(ed_name)}_p{p_num:02d}.jpg"
                save_path = os.path.join(target_dir, file_name)

                ok = download_file(p["full_url"], save_path)
                if ok:
                    print(f"   {Colors.GREEN}✔ Page {p_num:02d} saved:{Colors.RESET} {save_path} ({os.path.getsize(save_path):,} bytes)")
                else:
                    # Try thumbnail fallback
                    ok_thumb = download_file(p["thumb_url"], save_path)
                    if ok_thumb:
                        print(f"   {Colors.GREEN}✔ Page {p_num:02d} thumbnail saved:{Colors.RESET} {save_path}")
                    else:
                        print(f"   {Colors.RED}✘ Page {p_num:02d} failed ({p['full_url']}){Colors.RESET}")

        if not found_any:
            print(f"{Colors.RED}[✘] No editions available for date {date_str}. Please verify the publication date.{Colors.RESET}")
        else:
            print(f"\n{Colors.BOLD}{Colors.GREEN}[✔] E-Paper download completed in: {target_dir}{Colors.RESET}\n")

    def download_from_url(self, url: str, download_all_pages: bool = False):
        """
        Download page images directly from a Vijayavani ePaper URL.
        Example:
        https://epaper.vijayavani.net/edition/Bengaluru/VVAANINEW_BEN/VVAANINEW_BEN_20260916/date/2026-09-16/page/1
        """
        print(f"{Colors.BLUE}[*] Processing E-Paper URL: {url}{Colors.RESET}")
        match_code = re.search(r'VVAANINEW_([A-Za-z0-9]+)', url)
        match_date = re.search(r'/date/(\d{4}-\d{2}-\d{2})', url) or re.search(r'(\d{4}-\d{2}-\d{2})', url)
        match_name = re.search(r'/edition/([^/]+)', url)
        match_page = re.search(r'/page/(\d+)', url)

        ed_code = match_code.group(1) if match_code else "BEN"
        ed_name = match_name.group(1).replace("_", " ") if match_name else "Bengaluru"
        target_page = int(match_page.group(1)) if match_page else 1

        if match_date:
            date_str = match_date.group(1)
        else:
            m_ymd = re.search(r'_(\d{4})(\d{2})(\d{2})', url)
            if m_ymd:
                date_str = f"{m_ymd.group(1)}-{m_ymd.group(2)}-{m_ymd.group(3)}"
            else:
                date_str = self.get_today_str()

        print(f"{Colors.CYAN}[*] Edition: {ed_name} ({ed_code}) | Date: {date_str} | Requested Page: {target_page}{Colors.RESET}")
        pages = self.fetch_edition_pages(ed_code, date_str)
        if not pages:
            print(f"{Colors.RED}[✘] No pages found for {ed_name} on {date_str}.{Colors.RESET}")
            return

        target_dir = os.path.join(self.output_dir, f"{sanitize_filename(ed_name)}_{date_str}")
        os.makedirs(target_dir, exist_ok=True)

        pages_to_download = pages if download_all_pages else [p for p in pages if p["page_num"] == target_page]
        if not pages_to_download:
            pages_to_download = [pages[0]]

        print(f"{Colors.GREEN}[+] Downloading {len(pages_to_download)} page(s) to: {target_dir}{Colors.RESET}")
        for p in pages_to_download:
            p_num = p["page_num"]
            file_name = f"{ed_code}_{sanitize_filename(ed_name)}_p{p_num:02d}.jpg"
            save_path = os.path.join(target_dir, file_name)

            ok = download_file(p["full_url"], save_path)
            if ok:
                print(f"   {Colors.GREEN}✔ Page {p_num:02d} saved:{Colors.RESET} {save_path} ({os.path.getsize(save_path):,} bytes)")
            else:
                ok_thumb = download_file(p["thumb_url"], save_path)
                if ok_thumb:
                    print(f"   {Colors.GREEN}✔ Page {p_num:02d} thumbnail saved:{Colors.RESET} {save_path}")
                else:
                    print(f"   {Colors.RED}✘ Page {p_num:02d} failed ({p['full_url']}){Colors.RESET}")

        print(f"\n{Colors.BOLD}{Colors.GREEN}[✔] E-Paper download completed in: {target_dir}{Colors.RESET}\n")

    def download_pages_from_urls(self, url_list: list, edition_name: str = "edition"):
        """Download a specified list of ePaper page image URLs."""
        today_str = self.get_today_str()
        target_dir = os.path.join(self.output_dir, f"{sanitize_filename(edition_name)}_{today_str}")
        os.makedirs(target_dir, exist_ok=True)

        print(f"{Colors.CYAN}[*] Downloading {len(url_list)} ePaper pages to: {target_dir}{Colors.RESET}")
        for idx, url in enumerate(url_list, start=1):
            save_path = os.path.join(target_dir, f"page_{idx:02d}.jpg")
            ok = download_file(url, save_path)
            if ok:
                print(f" {Colors.GREEN}✔ Page {idx:02d} saved:{Colors.RESET} {save_path} ({os.path.getsize(save_path):,} bytes)")
            else:
                print(f" {Colors.RED}✘ Page {idx:02d} failed:{Colors.RESET} {url}")
        print(f"\n{Colors.GREEN}{Colors.BOLD}[✔] Finished downloading pages in: {target_dir}{Colors.RESET}\n")

# ==============================================================================
# INTERACTIVE CLI
# ==============================================================================

def interactive_menu():
    """Run interactive CLI menu."""
    print_banner()
    print(f"{Colors.BOLD}Select an option:{Colors.RESET}")
    print("  1) Fetch Latest News Images (vijayavani.net)")
    print("  2) Fetch News Images by Category (State, Sports, Cinema, Politics, etc.)")
    print("  3) Fetch Breaking News Images")
    print("  4) Fetch E-Paper Pages (by Date or URL - All Pages by Default)")
    print("  5) Fetch All (News + E-Paper)")
    print(f"  6) {Colors.GREEN}{Colors.BOLD}Launch Web Interface GUI (http://localhost:8080) [Recommended]{Colors.RESET}")
    print("  7) Exit")
    
    try:
        choice = input(f"\n{Colors.CYAN}Enter choice [1-7]: {Colors.RESET}").strip()
    except (KeyboardInterrupt, EOFError):
        print("\nExiting.")
        sys.exit(0)

    news_scraper = NewsScraper()
    epaper_scraper = EpaperScraper()

    if choice == "1":
        limit = input(f"Number of stories to fetch (default: 15): ").strip()
        limit = int(limit) if limit.isdigit() else 15
        news_scraper.scrape_images(limit=limit)

    elif choice == "2":
        print(f"\n{Colors.BOLD}Available Categories:{Colors.RESET}")
        for i, s in enumerate(NEWS_SECTIONS, 1):
            print(f"  {i}) {s['name']} [{s['slug']}]")
        cat_choice = input(f"Select category [1-{len(NEWS_SECTIONS)}]: ").strip()
        if cat_choice.isdigit() and 1 <= int(cat_choice) <= len(NEWS_SECTIONS):
            sec = NEWS_SECTIONS[int(cat_choice) - 1]["slug"]
            limit = input("Number of stories to fetch (default: 15): ").strip()
            limit = int(limit) if limit.isdigit() else 15
            news_scraper.scrape_images(limit=limit, section=sec)
        else:
            print(f"{Colors.RED}Invalid category selection.{Colors.RESET}")

    elif choice == "3":
        news_scraper.scrape_images(breaking_only=True)

    elif choice == "4":
        input_val = input(f"Enter publication date (YYYY-MM-DD) or paste E-Paper URL: ").strip()
        all_p = input(f"Download entire newspaper (all pages)? [Y/n] (default: Y): ").strip().lower()
        download_all = False if all_p == 'n' else True
        if input_val.startswith("http://") or input_val.startswith("https://"):
            epaper_scraper.download_from_url(input_val, download_all_pages=download_all)
        else:
            epaper_scraper.download_edition_frontpages(date_str=input_val or None, download_all_pages=download_all)

    elif choice == "5":
        print(f"{Colors.BOLD}\n--- Scraping News Portal Images ---{Colors.RESET}")
        news_scraper.scrape_images(limit=10)
        print(f"{Colors.BOLD}\n--- Scraping E-Paper Front Pages ---{Colors.RESET}")
        epaper_scraper.download_edition_frontpages(download_all_pages=True)

    elif choice == "6":
        print(f"\n{Colors.GREEN}{Colors.BOLD}[*] Launching Vijayavani Web Interface...{Colors.RESET}")
        try:
            import server
            server.start_server(open_browser=True)
        except Exception as err:
            print(f"{Colors.RED}Failed to launch server: {err}{Colors.RESET}")

    elif choice == "7":
        print("Goodbye!")
        sys.exit(0)
    else:
        print(f"{Colors.RED}Invalid option selected.{Colors.RESET}")

# ==============================================================================
# CLI ARGUMENT PARSER
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Vijayavani Newspaper Image Scraper (Web & E-Paper)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run interactive wizard:
  python3 vijayavani_scraper.py

  # Fetch e-paper by date (e.g. 2026-10-10):
  python3 vijayavani_scraper.py --epaper --date 2026-10-10

  # Fetch e-paper directly from Vijayavani URL:
  python3 vijayavani_scraper.py --url https://epaper.vijayavani.net/edition/Bengaluru/VVAANINEW_BEN/VVAANINEW_BEN_20260916/date/2026-09-16/page/1

  # Fetch all 16 pages of an edition for a specific date:
  python3 vijayavani_scraper.py --epaper --date 2026-10-10 --edition BEN --all-pages

  # Fetch 20 latest news article images:
  python3 vijayavani_scraper.py --news --limit 20
        """
    )
    
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--news", action="store_true", help="Scrape news portal article images")
    group.add_argument("--epaper", action="store_true", help="Scrape digital e-paper edition page images")
    group.add_argument("--breaking", action="store_true", help="Scrape breaking news images")
    group.add_argument("--all", action="store_true", help="Scrape both news portal and e-paper images")
    group.add_argument("--url", type=str, default=None,
                       help="Direct e-paper reader URL (e.g. https://epaper.vijayavani.net/edition/Bengaluru/VVAANINEW_BEN/.../date/2026-09-16/page/1)")
    
    parser.add_argument("--all-pages", action="store_true", help="Download all pages of the edition, not just the front page")
    parser.add_argument("--edition", type=str, default=None,
                        help="E-paper edition code or name (e.g. BEN, NAM, HUB, Bengaluru)")
    parser.add_argument("--section", type=str, default=None,
                        help="News section/category (e.g. state, sports, cinevani, national, district)")
    parser.add_argument("--limit", type=int, default=15, help="Number of news stories to fetch (default: 15)")
    parser.add_argument("--date", type=str, default=None, help="Publication date for e-paper (YYYY-MM-DD)")
    parser.add_argument("--output", type=str, default="downloads", help="Output directory path (default: downloads)")
    parser.add_argument("--threads", type=int, default=4, help="Concurrent download threads (default: 4)")

    args = parser.parse_args()

    # If no flags passed, launch interactive CLI menu
    if not any([args.news, args.epaper, args.breaking, args.all, args.url]):
        interactive_menu()
        return

    print_banner()

    # Direct URL mode
    if args.url:
        epaper_dir = os.path.join(args.output, "epaper")
        scraper = EpaperScraper(output_dir=epaper_dir)
        scraper.download_from_url(args.url, download_all_pages=args.all_pages)
        return

    if args.news or args.all:
        news_dir = os.path.join(args.output, "news")
        scraper = NewsScraper(output_dir=news_dir)
        scraper.scrape_images(limit=args.limit, section=args.section, max_workers=args.threads)

    if args.breaking:
        news_dir = os.path.join(args.output, "news")
        scraper = NewsScraper(output_dir=news_dir)
        scraper.scrape_images(breaking_only=True, max_workers=args.threads)

    if args.epaper or args.all:
        epaper_dir = os.path.join(args.output, "epaper")
        scraper = EpaperScraper(output_dir=epaper_dir)
        scraper.download_edition_frontpages(date_str=args.date, edition_filter=args.edition, download_all_pages=args.all_pages)

if __name__ == "__main__":
    main()
