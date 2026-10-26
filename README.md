# Vijayavani Newspaper Image Scraper 🗞️📸

A powerful, production-ready Python CLI scraper to fetch high-resolution images from Karnataka's leading Kannada daily newspaper **Vijayavani** (ವಿಜಯವಾಣಿ).

Supports both:
1. **Vijayavani News Portal (`vijayavani.net`)**: High-resolution article images, breaking news photos, categories, along with Kannada headlines and metadata.
2. **Vijayavani Digital E-Paper (`epaper.vijayavani.net`)**: Scanned print newspaper pages and edition front covers directly from the CDN (`images.enewspapr.com`).

---

## 🚀 Features

- **Dual Mode Scraping**:
  - **News Website**: Fetches latest stories, breaking news, or specific sections (State, National, Sports, Cinevani, District, Lifestyle, etc.).
  - **E-Paper**: Scrapes print newspaper editions (Bengaluru, Hubballi, Namaste Bengaluru, Cinema, Vijayapura, etc.).
- **Zero Required External Dependencies**:
  - Built using Python 3 standard library (`urllib`, `json`, `argparse`, `concurrent.futures`, `ssl`).
  - Seamless fallback to macOS system `curl` to handle TLS 1.3 / Cloudflare CDN protocol negotiations smoothly.
- **Multithreaded Concurrent Downloads**: Rapidly downloads multiple images in parallel.
- **Full Metadata Export**: Saves Kannada headlines, publish dates, captions, and article URLs in both `metadata.json` and `metadata.csv`.
- **Interactive Terminal Menu & CLI Flags**: Run with interactive prompts or automate via command line arguments.

---

## 📁 Project Structure

```
web-sceper/
├── vijayavani_scraper.py   # Main CLI scraper script
├── requirements.txt        # Optional dependencies
├── README.md               # Documentation & usage guide
└── downloads/              # Default image output directory (auto-created)
    ├── news/               # Downloaded news article images & metadata
    │   └── {section}/
    │       ├── 01_article_image.jpg
    │       ├── metadata.json
    │       └── metadata.csv
    └── epaper/             # Downloaded e-paper newspaper page images
        └── frontpages_{date}/
            ├── BEN_Bengaluru_frontpage.jpg
            └── NAM_Namaste_Bengaluru_frontpage.jpg
```

---

## 🛠️ Quick Start

### 1. Interactive Mode
Run the script without any arguments to open the interactive terminal wizard:
```bash
python3 vijayavani_scraper.py
```
You will be prompted to select:
1. Fetch latest news images
2. Fetch news images by category
3. Fetch breaking news images
4. Fetch today's e-paper front pages
5. Fetch all (News + E-Paper)

---

### 2. Command Line Usage

#### A. Fetch Latest News Article Images
```bash
# Fetch 15 latest news images
python3 vijayavani_scraper.py --news

# Fetch 30 latest news images
python3 vijayavani_scraper.py --news --limit 30
```

#### B. Fetch News by Specific Category
Available categories: `state`, `national`, `international`, `sports`, `cinevani`, `district`, `lifestyle`, `rajakeeya`, `trending`
```bash
# Fetch Sports images
python3 vijayavani_scraper.py --news --section sports --limit 20

# Fetch State news (ಕರ್ನಾಟಕ ಸುದ್ದಿ)
python3 vijayavani_scraper.py --news --section state --limit 20

# Fetch Cinema (ಸಿನಿವಾಣಿ)
python3 vijayavani_scraper.py --news --section cinevani --limit 15
```

#### C. Fetch Breaking News Images
```bash
python3 vijayavani_scraper.py --breaking
```

#### D. Fetch E-Paper Pages
```bash
# Download front pages of today's editions (Bengaluru, Hubballi, etc.)
python3 vijayavani_scraper.py --epaper

# Download e-paper for a specific edition (BEN, NAM, HUB, etc.)
python3 vijayavani_scraper.py --epaper --edition BEN

# Download all pages of an edition (Page 1 to 16), not just the front page
python3 vijayavani_scraper.py --epaper --edition BEN --all-pages

# Download e-paper directly from Vijayavani reader URL
python3 vijayavani_scraper.py --url "https://epaper.vijayavani.net/edition/Bengaluru/VVAANINEW_BEN/VVAANINEW_BEN_20260916/date/2026-09-16/page/1"

# Download e-paper for a specific publication date (YYYY-MM-DD)
python3 vijayavani_scraper.py --epaper --date 2026-10-10
```

#### E. Fetch Both (All News & E-Paper Images)
```bash
python3 vijayavani_scraper.py --all
```

---

## ⚙️ CLI Options & Flags

| Flag | Type | Description | Default |
|------|------|-------------|---------|
| `--url` | String | Direct e-paper URL (auto-parses edition & date) | `None` |
| `--news` | Flag | Scrape news portal article images | `False` |
| `--epaper` | Flag | Scrape e-paper edition page images | `False` |
| `--breaking` | Flag | Scrape breaking news images | `False` |
| `--all` | Flag | Scrape both news and e-paper images | `False` |
| `--all-pages` | Flag | Download all pages of the edition (not just front page) | `False` |
| `--edition` | String | E-paper edition code or name (`BEN`, `NAM`, `HUB`, `CIN`, etc.) | All main |
| `--section` | String | Specific news section (e.g. `sports`, `state`, `cinevani`) | `None` (All) |
| `--limit` | Integer | Maximum number of stories to fetch | `15` |
| `--date` | String | Date for e-paper (`YYYY-MM-DD`) | Today |
| `--output` | String | Target directory to save images | `downloads` |
| `--threads` | Integer | Concurrent download threads | `4` |

---

## 📊 Metadata Format

When scraping news articles, a `metadata.json` and `metadata.csv` file is automatically saved in the corresponding directory containing:
- `headline`: Article title in Kannada
- `published_at`: Publication ISO timestamp
- `sections`: Categories / tags
- `caption`: Image caption / alt text
- `image_url`: Full-resolution source image URL on CDN
- `local_file`: Local filename of the downloaded image
- `article_url`: Direct link to the story on Vijayavani website
