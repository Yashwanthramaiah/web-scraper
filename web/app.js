/**
 * Vijayavani Newspaper & E-Paper Suite - Client Application
 * Handles E-Paper scraping, live download tracking, interactive reader lightbox,
 * ZIP generation, and archive browsing.
 */

// Application State
const state = {
    selectedDate: '',
    selectedEdition: 'BEN',
    pageScope: 'all',
    editions: [],
    activeJobId: null,
    pollInterval: null,
    currentPages: [],
    currentArchiveFolder: '',
    reader: {
        isOpen: false,
        currentIndex: 0,
        zoom: 1,
        panX: 0,
        panY: 0,
        isDragging: false,
        startX: 0,
        startY: 0
    }
};

// DOM Elements
const elements = {
    dateInput: document.getElementById('scrape-date'),
    datePresets: document.getElementById('date-presets'),
    editionsContainer: document.getElementById('editions-container'),
    btnStartScrape: document.getElementById('btn-start-scrape'),
    btnPreviewPages: document.getElementById('btn-preview-pages'),
    
    // Progress
    progressPanel: document.getElementById('progress-panel'),
    progressTitle: document.getElementById('progress-title'),
    progressSubtitle: document.getElementById('progress-subtitle'),
    progressPercent: document.getElementById('progress-percent'),
    progressBarFill: document.getElementById('progress-bar-fill'),
    liveStreamGrid: document.getElementById('live-stream-grid'),
    liveStreamCount: document.getElementById('live-stream-count'),
    consoleLogs: document.getElementById('console-logs'),
    
    // Results
    resultsSection: document.getElementById('results-section'),
    resultsTitle: document.getElementById('results-title'),
    resultsSubtitle: document.getElementById('results-subtitle'),
    pagesGrid: document.getElementById('pages-grid'),
    btnDownloadAllZip: document.getElementById('btn-download-all-zip'),
    btnOpenReaderFirst: document.getElementById('btn-open-reader-first'),
    
    // Tabs & Navigation
    navTabs: document.querySelectorAll('.nav-tab'),
    tabPanes: document.querySelectorAll('.tab-pane'),
    archivesCountBadge: document.getElementById('archives-count-badge'),
    serverStatus: document.getElementById('server-status'),
    
    // Archives
    archivesGrid: document.getElementById('archives-grid'),
    archivesEmpty: document.getElementById('archives-empty'),
    archiveSearch: document.getElementById('archive-search'),
    btnRefreshArchives: document.getElementById('btn-refresh-archives'),
    btnGoToEpaper: document.getElementById('btn-go-to-epaper'),
    
    // Reader Lightbox
    readerModal: document.getElementById('reader-modal'),
    readerBackdrop: document.getElementById('reader-backdrop'),
    readerViewport: document.getElementById('reader-viewport'),
    readerImageWrapper: document.getElementById('reader-image-wrapper'),
    readerImage: document.getElementById('reader-image'),
    readerTitle: document.getElementById('reader-title'),
    readerPageBadge: document.getElementById('reader-page-badge'),
    readerFilmstrip: document.getElementById('reader-filmstrip'),
    readerPrev: document.getElementById('reader-prev'),
    readerNext: document.getElementById('reader-next'),
    toolZoomIn: document.getElementById('tool-zoom-in'),
    toolZoomOut: document.getElementById('tool-zoom-out'),
    toolZoomReset: document.getElementById('tool-zoom-reset'),
    toolFit: document.getElementById('tool-fit'),
    toolDownload: document.getElementById('tool-download'),
    toolClose: document.getElementById('tool-close'),
    
    // News Portal
    newsCategoriesContainer: document.getElementById('news-categories-container'),
    newsLimitInput: document.getElementById('news-limit-input'),
    newsLimitVal: document.getElementById('news-limit-val'),
    btnScrapeNews: document.getElementById('btn-scrape-news'),
    newsResultsGrid: document.getElementById('news-results-grid'),
    
    // Toast
    toastContainer: document.getElementById('toast-container')
};

// ==============================================================================
// INITIALIZATION
// ==============================================================================

document.addEventListener('DOMContentLoaded', () => {
    initDate();
    initTabs();
    initEditions();
    initScopeSelector();
    initEventListeners();
    initReaderEvents();
    loadArchives();
    initNewsCategories();
});

// Setup default date to today
function initDate() {
    const today = new Date();
    const yyyy = today.getFullYear();
    const mm = String(today.getMonth() + 1).padStart(2, '0');
    const dd = String(today.getDate()).padStart(2, '0');
    const todayStr = `${yyyy}-${mm}-${dd}`;
    
    state.selectedDate = todayStr;
    elements.dateInput.value = todayStr;
    // Set max date to today
    elements.dateInput.max = todayStr;
}

// Format Date Helper
function formatDateString(date) {
    const yyyy = date.getFullYear();
    const mm = String(date.getMonth() + 1).padStart(2, '0');
    const dd = String(date.getDate()).padStart(2, '0');
    return `${yyyy}-${mm}-${dd}`;
}

// Navigation Tabs
function initTabs() {
    elements.navTabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const tabName = tab.dataset.tab;
            
            elements.navTabs.forEach(t => t.classList.remove('active'));
            elements.tabPanes.forEach(p => p.classList.remove('active'));
            
            tab.classList.add('active');
            const targetPane = document.getElementById(`pane-${tabName}`);
            if (targetPane) targetPane.classList.add('active');
            
            if (tabName === 'archives') {
                loadArchives();
            }
        });
    });

    if (elements.btnGoToEpaper) {
        elements.btnGoToEpaper.addEventListener('click', () => {
            document.getElementById('tab-epaper').click();
        });
    }
}

// Scope Option Selector
function initScopeSelector() {
    const scopeCards = document.querySelectorAll('.scope-card');
    scopeCards.forEach(card => {
        const radio = card.querySelector('input[type="radio"]');
        card.addEventListener('click', () => {
            scopeCards.forEach(c => c.classList.remove('selected'));
            card.classList.add('selected');
            radio.checked = true;
            state.pageScope = radio.value;
        });
    });
}

// Date Presets Handler
function handleDatePreset(presetKey) {
    const today = new Date();
    let target = new Date();

    if (presetKey === 'today') {
        target = today;
    } else if (presetKey === 'yesterday') {
        target.setDate(today.getDate() - 1);
    } else if (presetKey === '2days') {
        target.setDate(today.getDate() - 2);
    } else if (presetKey === 'sunday') {
        const day = today.getDay(); // 0 is Sunday
        const diff = day === 0 ? 7 : day;
        target.setDate(today.getDate() - diff);
    }

    const dateStr = formatDateString(target);
    state.selectedDate = dateStr;
    elements.dateInput.value = dateStr;

    // Update active pill
    document.querySelectorAll('.preset-pill').forEach(pill => {
        pill.classList.toggle('active', pill.dataset.preset === presetKey);
    });

    showToast(`ದಿನಾಂಕ ಆಯ್ಕೆಮಾಡಲಾಗಿದೆ: ${dateStr}`, 'info');
}

// ==============================================================================
// EDITIONS DATA & RENDERING
// ==============================================================================

async function initEditions() {
    try {
        const res = await fetch('/api/editions');
        if (res.ok) {
            state.editions = await res.json();
            renderEditions();
        } else {
            fallbackEditions();
        }
    } catch (err) {
        fallbackEditions();
    }
}

function fallbackEditions() {
    state.editions = [
        { code: "BEN", name: "Bengaluru", name_kn: "ಬೆಂಗಳೂರು", tag: "ರಾಜಧಾನಿ" },
        { code: "NAM", name: "Namaste Bengaluru", name_kn: "ನಮಸ್ತೆ ಬೆಂಗಳೂರು", tag: "ಸಿಟಿ ವಿಶೇಷ" },
        { code: "HUB", name: "Hubballi", name_kn: "ಹುಬ್ಬಳ್ಳಿ", tag: "ಉತ್ತರ ಕರ್ನಾಟಕ" },
        { code: "MYS", name: "Mysuru", name_kn: "ಮೈಸೂರು", tag: "ದಕ್ಷಿಣ ಕರ್ನಾಟಕ" },
        { code: "MNG", name: "Mangaluru", name_kn: "ಮಂಗಳೂರು", tag: "ಕರಾವಳಿ" },
        { code: "BEL", name: "Belagavi", name_kn: "ಬೆಳಗಾವಿ", tag: "ಗಡಿ ನಾಡು" },
        { code: "VIJ", name: "Vijayapura", name_kn: "ವಿಜಯಪುರ", tag: "ವಿಜಯಪುರ" },
        { code: "KAL", name: "Kalaburagi", name_kn: "ಕಲಬುರಗಿ", tag: "ಕಲ್ಯಾಣ ಕರ್ನಾಟಕ" },
        { code: "SHI", name: "Shivamogga", name_kn: "ಶಿವಮೊಗ್ಗ", tag: "ಮಲೆನಾಡು" },
        { code: "CIN", name: "Cinema / Special", name_kn: "ಸಿನಿಮಾ / ವಿಶೇಷ", tag: "ಸಿನಿವಾಣಿ" }
    ];
    renderEditions();
}

function renderEditions() {
    elements.editionsContainer.innerHTML = '';
    
    state.editions.forEach(ed => {
        const card = document.createElement('div');
        card.className = `edition-card ${ed.code === state.selectedEdition ? 'selected' : ''}`;
        card.dataset.code = ed.code;
        
        card.innerHTML = `
            <div class="edition-header">
                <span class="edition-code">${ed.code}</span>
                <span style="font-size: 11px; color: var(--brand-saffron); font-weight: 600;">${ed.tag || ''}</span>
            </div>
            <div class="edition-name-kn">${ed.name_kn || ed.name}</div>
            <div class="edition-name-en">${ed.name}</div>
        `;
        
        card.addEventListener('click', () => {
            document.querySelectorAll('.edition-card').forEach(c => c.classList.remove('selected'));
            card.classList.add('selected');
            state.selectedEdition = ed.code;
        });
        
        elements.editionsContainer.appendChild(card);
    });
}

// ==============================================================================
// EVENT LISTENERS
// ==============================================================================

function initEventListeners() {
    // Date input change
    elements.dateInput.addEventListener('change', (e) => {
        state.selectedDate = e.target.value;
        document.querySelectorAll('.preset-pill').forEach(pill => pill.classList.remove('active'));
    });

    // Preset pills click
    elements.datePresets.addEventListener('click', (e) => {
        const pill = e.target.closest('.preset-pill');
        if (pill) {
            handleDatePreset(pill.dataset.preset);
        }
    });

    // Start Scrape Button
    elements.btnStartScrape.addEventListener('click', () => {
        startScraping();
    });

    // Preview Pages Button
    elements.btnPreviewPages.addEventListener('click', () => {
        previewPages();
    });

    // Download All ZIP Button
    elements.btnDownloadAllZip.addEventListener('click', () => {
        downloadZipCurrent();
    });

    // Open Reader First Button
    elements.btnOpenReaderFirst.addEventListener('click', () => {
        if (state.currentPages.length > 0) {
            openReader(0);
        }
    });

    // Archives Search
    elements.archiveSearch.addEventListener('input', (e) => {
        filterArchives(e.target.value);
    });

    // Refresh Archives Button
    elements.btnRefreshArchives.addEventListener('click', () => {
        loadArchives();
        showToast('ಆರ್ಕೈವ್ಸ್ ರಿಫ್ರೆಶ್ ಮಾಡಲಾಗಿದೆ', 'info');
    });
}

// ==============================================================================
// SCRAPING & LIVE DOWNLOAD LOGIC
// ==============================================================================

async function startScraping() {
    const dateVal = elements.dateInput.value.trim();
    if (!dateVal) {
        showToast('ದಯವಿಟ್ಟು ಮಾನ್ಯವಾದ ದಿನಾಂಕವನ್ನು ನಮೂದಿಸಿ (Please select date)', 'warning');
        return;
    }

    const ed = state.editions.find(e => e.code === state.selectedEdition) || { name: state.selectedEdition, name_kn: state.selectedEdition };
    const isAllPages = state.pageScope === 'all';

    // Show Progress Panel & Reset Tracker
    elements.progressPanel.style.display = 'block';
    elements.resultsSection.style.display = 'none';
    elements.progressTitle.textContent = `ಡೌನ್‌ಲೋಡ್ ಆಗುತ್ತಿದೆ: ${ed.name_kn || ed.name} (${dateVal})`;
    elements.progressSubtitle.textContent = isAllPages ? 'ಇಡೀ ಪತ್ರಿಕೆಯ ಎಲ್ಲಾ ಪುಟಗಳನ್ನು ಸಂಪರ್ಕಿಸಲಾಗುತ್ತಿದೆ...' : 'ಮೊದಲ ಪುಟವನ್ನು ಪಡೆಯಲಾಗುತ್ತಿದೆ...';
    elements.progressPercent.textContent = '0%';
    elements.progressBarFill.style.width = '0%';
    elements.liveStreamGrid.innerHTML = '';
    elements.liveStreamCount.textContent = '0 Pages';
    elements.consoleLogs.innerHTML = '';
    appendLog(`[Start] Initializing download for ${ed.name} (${state.selectedEdition}) on ${dateVal} [All Pages: ${isAllPages}]`, 'info');

    // Smooth Scroll to Progress
    elements.progressPanel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

    // Disable start button during execution
    elements.btnStartScrape.disabled = true;
    elements.btnPreviewPages.disabled = true;

    try {
        const response = await fetch('/api/epaper/scrape', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                date: dateVal,
                edition: state.selectedEdition,
                all_pages: isAllPages
            })
        });

        const data = await response.json();
        if (!response.ok || !data.job_id) {
            throw new Error(data.error || 'Failed to initialize download job');
        }

        state.activeJobId = data.job_id;
        appendLog(`[Job Created] Job ID: ${data.job_id}. Starting page stream...`, 'info');
        
        // Start Polling
        startJobPolling(data.job_id);

    } catch (err) {
        appendLog(`[Error] ${err.message}`, 'error');
        showToast(`ದೋಷ: ${err.message}`, 'error');
        elements.btnStartScrape.disabled = false;
        elements.btnPreviewPages.disabled = false;
        elements.progressSubtitle.textContent = `Failed: ${err.message}`;
    }
}

function startJobPolling(jobId) {
    if (state.pollInterval) clearInterval(state.pollInterval);

    let seenPagesCount = 0;

    state.pollInterval = setInterval(async () => {
        try {
            const res = await fetch(`/api/epaper/job/${jobId}`);
            if (!res.ok) return;

            const job = await res.json();
            
            // Update percentage and text
            const pct = job.percent || 0;
            elements.progressPercent.textContent = `${pct}%`;
            elements.progressBarFill.style.width = `${pct}%`;
            elements.progressSubtitle.textContent = job.message || 'Downloading pages...';

            // Logs
            if (job.logs && job.logs.length > 0) {
                elements.consoleLogs.innerHTML = job.logs.map(l => `<div class="log-line info">${escapeHtml(l)}</div>`).join('');
                elements.consoleLogs.scrollTop = elements.consoleLogs.scrollHeight;
            }

            // Update live page feed thumbnails
            const downloadedPages = job.pages_downloaded || [];
            if (downloadedPages.length > seenPagesCount) {
                for (let i = seenPagesCount; i < downloadedPages.length; i++) {
                    const p = downloadedPages[i];
                    addStreamThumbnail(p);
                }
                seenPagesCount = downloadedPages.length;
                elements.liveStreamCount.textContent = `${seenPagesCount} / ${job.total_pages || '?'} Pages`;
            }

            // Check completion or error
            if (job.status === 'completed') {
                clearInterval(state.pollInterval);
                state.pollInterval = null;
                elements.btnStartScrape.disabled = false;
                elements.btnPreviewPages.disabled = false;
                
                showToast(`🎉 ಎಲ್ಲಾ ${job.pages_downloaded.length} ಪುಟಗಳು ಯಶಸ್ವಿಯಾಗಿ ಡೌನ್‌ಲೋಡ್ ಆಗಿವೆ!`, 'success');
                appendLog(`[Completed] Successfully downloaded ${job.pages_downloaded.length} pages!`, 'success');
                
                state.currentPages = job.pages_downloaded;
                state.currentArchiveFolder = job.folder_name;
                displayResults(job);
                loadArchives(); // refresh count
            } else if (job.status === 'error') {
                clearInterval(state.pollInterval);
                state.pollInterval = null;
                elements.btnStartScrape.disabled = false;
                elements.btnPreviewPages.disabled = false;
                showToast(`ವಿಫಲವಾಗಿದೆ: ${job.error}`, 'error');
                appendLog(`[Failed] ${job.error}`, 'error');
            }
        } catch (err) {
            console.error('Job polling error:', err);
        }
    }, 800);
}

function addStreamThumbnail(pageInfo) {
    const thumb = document.createElement('div');
    thumb.className = 'stream-thumb';
    thumb.innerHTML = `
        <img src="${pageInfo.thumb_url || pageInfo.full_url || pageInfo.local_url}" alt="Page ${pageInfo.page_num}" loading="lazy">
        <span class="page-tag">ಪುಟ ${pageInfo.page_num}</span>
    `;
    elements.liveStreamGrid.appendChild(thumb);
    thumb.scrollIntoView({ behavior: 'smooth', inline: 'end' });
}

function appendLog(text, type = 'info') {
    const line = document.createElement('div');
    line.className = `log-line ${type}`;
    line.textContent = `[${new Date().toLocaleTimeString()}] ${text}`;
    elements.consoleLogs.appendChild(line);
    elements.consoleLogs.scrollTop = elements.consoleLogs.scrollHeight;
}

// ==============================================================================
// PREVIEW PAGES (FAST PRE-FLIGHT CHECK WITHOUT DOWNLOADING)
// ==============================================================================

async function previewPages() {
    const dateVal = elements.dateInput.value.trim();
    if (!dateVal) {
        showToast('ದಯವಿಟ್ಟು ದಿನಾಂಕ ಆಯ್ಕೆಮಾಡಿ', 'warning');
        return;
    }

    elements.btnPreviewPages.disabled = true;
    showToast('ಪುಟಗಳ ಪಟ್ಟಿಯನ್ನು ಸರ್ವರ್‌ನಿಂದ ಪಡೆಯಲಾಗುತ್ತಿದೆ...', 'info');

    try {
        const res = await fetch('/api/epaper/preview', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                date: dateVal,
                edition: state.selectedEdition
            })
        });

        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Failed to fetch page preview');

        if (!data.pages || data.pages.length === 0) {
            showToast(`ಆಯ್ಕೆಮಾಡಿದ ದಿನಾಂಕಕ್ಕೆ (${dateVal}) ಪುಟಗಳು ಲಭ್ಯವಿಲ್ಲ`, 'warning');
            return;
        }

        state.currentPages = data.pages;
        state.currentArchiveFolder = '';

        elements.resultsSection.style.display = 'block';
        elements.resultsTitle.textContent = `${data.edition_name || state.selectedEdition} - ${dateVal}`;
        elements.resultsSubtitle.textContent = `ಪೂರ್ವವೀಕ್ಷಣೆ: ಒಟ್ಟು ${data.pages.length} ಪುಟಗಳು ಲಭ್ಯವಿವೆ (Preview Mode - Ready to download)`;
        
        elements.btnDownloadAllZip.style.display = 'none'; // preview only
        renderPagesGrid(data.pages, true);

        elements.resultsSection.scrollIntoView({ behavior: 'smooth' });
        showToast(`ಒಟ್ಟು ${data.pages.length} ಪುಟಗಳು ಪತ್ತೆಯಾಗಿವೆ! 'ಸಂಪೂರ್ಣ ಪತ್ರಿಕೆ ಡೌನ್‌ಲೋಡ್' ಕ್ಲಿಕ್ ಮಾಡಿ.`, 'success');

    } catch (err) {
        showToast(`ದೋಷ: ${err.message}`, 'error');
    } finally {
        elements.btnPreviewPages.disabled = false;
    }
}

// ==============================================================================
// DISPLAY RESULTS & NEWSPAPER GALLERY
// ==============================================================================

function displayResults(job) {
    elements.resultsSection.style.display = 'block';
    elements.resultsTitle.textContent = `${job.edition_name || state.selectedEdition} (${job.date})`;
    elements.resultsSubtitle.textContent = `ಒಟ್ಟು ${job.pages_downloaded.length} ಪುಟಗಳು ಡೌನ್‌ಲೋಡ್ ಆಗಿವೆ (Ready to view and download ZIP)`;
    
    elements.btnDownloadAllZip.style.display = 'inline-flex';
    elements.btnDownloadAllZip.onclick = () => {
        downloadZip(job.folder_name);
    };

    renderPagesGrid(job.pages_downloaded, false);
    elements.resultsSection.scrollIntoView({ behavior: 'smooth' });
}

function renderPagesGrid(pages, isPreview = false) {
    elements.pagesGrid.innerHTML = '';

    pages.forEach((page, index) => {
        const card = document.createElement('div');
        card.className = 'page-card';

        const imgSrc = page.local_url || page.thumb_url || page.full_url;
        const pageNum = page.page_num || (index + 1);
        const padNum = String(pageNum).padStart(2, '0');
        const sizeText = page.file_size ? `${(page.file_size / 1024).toFixed(1)} KB` : (isPreview ? 'High Resolution' : 'Saved');

        card.innerHTML = `
            <div class="page-card-image" data-index="${index}">
                <img src="${imgSrc}" alt="Page ${pageNum}" loading="lazy">
                <div class="page-card-badge">ಪುಟ ${padNum}</div>
                <div class="page-overlay">
                    <button class="overlay-btn read-btn" title="Fullscreen Reader">🔍</button>
                </div>
            </div>
            <div class="page-card-body">
                <div class="page-info">
                    <span class="page-name">ಪುಟ ${padNum} (Page ${padNum})</span>
                    <span class="page-size">${sizeText}</span>
                </div>
                ${!isPreview ? `
                    <a href="${page.local_url || page.full_url}" download="Vijayavani_Page_${padNum}.jpg" class="page-download-btn" title="Download Page Image">
                        ⬇️
                    </a>
                ` : `
                    <button class="page-download-btn view-only" title="Preview Only">👁️</button>
                `}
            </div>
        `;

        card.querySelector('.page-card-image').addEventListener('click', () => {
            openReader(index);
        });

        elements.pagesGrid.appendChild(card);
    });
}

// Download Zip
function downloadZipCurrent() {
    if (state.currentArchiveFolder) {
        downloadZip(state.currentArchiveFolder);
    } else {
        showToast('ದಯವಿಟ್ಟು ಮೊದಲು ಪತ್ರಿಕೆಯನ್ನು ಡೌನ್‌ಲೋಡ್ ಮಾಡಿ', 'warning');
    }
}

function downloadZip(folderName) {
    if (!folderName) return;
    showToast('ಜಿಪ್ ಫೈಲ್ ರಚಿಸಲಾಗುತ್ತಿದೆ...', 'info');
    window.location.href = `/api/download-zip?folder=${encodeURIComponent(folderName)}`;
}

// ==============================================================================
// ARCHIVES BROWSER
// ==============================================================================

async function loadArchives() {
    try {
        const res = await fetch('/api/archives');
        if (!res.ok) return;

        const archives = await res.json();
        elements.archivesCountBadge.textContent = archives.length;

        if (archives.length === 0) {
            elements.archivesGrid.innerHTML = '';
            elements.archivesEmpty.style.display = 'block';
            return;
        }

        elements.archivesEmpty.style.display = 'none';
        renderArchives(archives);

    } catch (err) {
        console.error('Failed to load archives:', err);
    }
}

function renderArchives(archives) {
    elements.archivesGrid.innerHTML = '';

    archives.forEach(arch => {
        const card = document.createElement('div');
        card.className = 'archive-card';

        const coverSrc = arch.cover_url || '/downloads/placeholder.jpg';
        const totalMb = (arch.total_size_bytes / (1024 * 1024)).toFixed(1);

        card.innerHTML = `
            <div class="archive-cover">
                <img src="${coverSrc}" alt="${arch.edition_name}" loading="lazy">
            </div>
            <div class="archive-details">
                <div>
                    <h3 class="archive-title">${arch.edition_name || arch.edition_code}</h3>
                    <div class="archive-date">📅 ${arch.date}</div>
                    <div class="archive-meta">📖 ${arch.page_count} Pages &nbsp;|&nbsp; 💾 ${totalMb} MB</div>
                </div>
                <div class="archive-actions">
                    <button class="btn btn-primary btn-sm btn-open-archive" data-folder="${arch.folder}">
                        <span>📖 ಓದಿ (Read)</span>
                    </button>
                    <button class="btn btn-outline btn-sm btn-zip-archive" data-folder="${arch.folder}">
                        <span>📦 ZIP</span>
                    </button>
                </div>
            </div>
        `;

        card.querySelector('.btn-open-archive').addEventListener('click', () => {
            openArchiveInViewer(arch.folder);
        });

        card.querySelector('.btn-zip-archive').addEventListener('click', () => {
            downloadZip(arch.folder);
        });

        elements.archivesGrid.appendChild(card);
    });
}

async function openArchiveInViewer(folderName) {
    try {
        showToast('ಆರ್ಕೈವ್ ಲೋಡ್ ಮಾಡಲಾಗುತ್ತಿದೆ...', 'info');
        const res = await fetch(`/api/archives/${encodeURIComponent(folderName)}`);
        if (!res.ok) throw new Error('Archive not found');

        const data = await res.json();
        state.currentPages = data.pages || [];
        state.currentArchiveFolder = folderName;

        // Switch to E-Paper tab and show results
        document.getElementById('tab-epaper').click();
        elements.resultsSection.style.display = 'block';
        elements.progressPanel.style.display = 'none';
        elements.resultsTitle.textContent = `${data.edition_name || data.edition_code} (${data.date})`;
        elements.resultsSubtitle.textContent = `ಸ್ಥಳೀಯ ಆರ್ಕೈವ್: ಒಟ್ಟು ${data.pages.length} ಪುಟಗಳು (Saved on your computer)`;
        
        elements.btnDownloadAllZip.style.display = 'inline-flex';
        elements.btnDownloadAllZip.onclick = () => downloadZip(folderName);

        renderPagesGrid(data.pages, false);
        elements.resultsSection.scrollIntoView({ behavior: 'smooth' });

    } catch (err) {
        showToast(`ದೋಷ: ${err.message}`, 'error');
    }
}

function filterArchives(query) {
    const q = query.toLowerCase().trim();
    const cards = elements.archivesGrid.querySelectorAll('.archive-card');
    cards.forEach(card => {
        const text = card.textContent.toLowerCase();
        card.style.display = text.includes(q) ? 'flex' : 'none';
    });
}

// ==============================================================================
// FULLSCREEN ZOOMABLE NEWSPAPER VIEWER (LIGHTBOX)
// ==============================================================================

function initReaderEvents() {
    // Navigation
    elements.readerPrev.addEventListener('click', () => changeReaderPage(-1));
    elements.readerNext.addEventListener('click', () => changeReaderPage(1));
    elements.toolClose.addEventListener('click', closeReader);
    elements.readerBackdrop.addEventListener('click', closeReader);

    // Zoom Controls
    elements.toolZoomIn.addEventListener('click', () => setReaderZoom(state.reader.zoom + 0.3));
    elements.toolZoomOut.addEventListener('click', () => setReaderZoom(state.reader.zoom - 0.3));
    elements.toolZoomReset.addEventListener('click', () => resetReaderZoom());
    elements.toolFit.addEventListener('click', () => resetReaderZoom());

    // Mouse Wheel Zoom
    elements.readerViewport.addEventListener('wheel', (e) => {
        e.preventDefault();
        const delta = e.deltaY < 0 ? 0.2 : -0.2;
        setReaderZoom(state.reader.zoom + delta);
    }, { passive: false });

    // Drag to Pan when zoomed
    elements.readerViewport.addEventListener('mousedown', (e) => {
        if (state.reader.zoom > 1) {
            state.reader.isDragging = true;
            state.reader.startX = e.clientX - state.reader.panX;
            state.reader.startY = e.clientY - state.reader.panY;
            elements.readerViewport.classList.add('dragging');
        }
    });

    window.addEventListener('mousemove', (e) => {
        if (state.reader.isDragging && state.reader.zoom > 1) {
            state.reader.panX = e.clientX - state.reader.startX;
            state.reader.panY = e.clientY - state.reader.startY;
            applyReaderTransform();
        }
    });

    window.addEventListener('mouseup', () => {
        state.reader.isDragging = false;
        elements.readerViewport.classList.remove('dragging');
    });

    // Keyboard Shortcuts
    window.addEventListener('keydown', (e) => {
        if (!state.reader.isOpen) return;

        if (e.key === 'Escape') {
            closeReader();
        } else if (e.key === 'ArrowLeft') {
            changeReaderPage(-1);
        } else if (e.key === 'ArrowRight') {
            changeReaderPage(1);
        } else if (e.key === '+' || e.key === '=') {
            setReaderZoom(state.reader.zoom + 0.3);
        } else if (e.key === '-' || e.key === '_') {
            setReaderZoom(state.reader.zoom - 0.3);
        } else if (e.key === '0') {
            resetReaderZoom();
        }
    });
}

function openReader(index) {
    if (!state.currentPages || state.currentPages.length === 0) return;

    state.reader.isOpen = true;
    state.reader.currentIndex = Math.max(0, Math.min(index, state.currentPages.length - 1));
    elements.readerModal.style.display = 'flex';
    document.body.style.overflow = 'hidden';

    renderFilmstrip();
    updateReaderContent();
}

function closeReader() {
    state.reader.isOpen = false;
    elements.readerModal.style.display = 'none';
    document.body.style.overflow = 'auto';
    resetReaderZoom();
}

function changeReaderPage(delta) {
    const nextIdx = state.reader.currentIndex + delta;
    if (nextIdx >= 0 && nextIdx < state.currentPages.length) {
        state.reader.currentIndex = nextIdx;
        resetReaderZoom();
        updateReaderContent();
    }
}

function updateReaderContent() {
    const page = state.currentPages[state.reader.currentIndex];
    if (!page) return;

    const pageNum = page.page_num || (state.reader.currentIndex + 1);
    const totalPages = state.currentPages.length;
    const highResUrl = page.full_url || page.local_url || page.thumb_url;

    elements.readerImage.src = highResUrl;
    elements.readerPageBadge.textContent = `ಪುಟ ${pageNum} / ${totalPages}`;
    elements.readerTitle.textContent = `ವಿಜಯವಾಣಿ ದಿನಪತ್ರಿಕೆ (Page ${pageNum})`;
    
    elements.toolDownload.href = highResUrl;
    elements.toolDownload.setAttribute('download', `Vijayavani_Page_${String(pageNum).padStart(2, '0')}.jpg`);

    // Prev / Next button states
    elements.readerPrev.style.display = state.reader.currentIndex > 0 ? 'flex' : 'none';
    elements.readerNext.style.display = state.reader.currentIndex < totalPages - 1 ? 'flex' : 'none';

    // Update active filmstrip item
    const stripItems = elements.readerFilmstrip.querySelectorAll('.strip-item');
    stripItems.forEach((item, idx) => {
        item.classList.toggle('active', idx === state.reader.currentIndex);
        if (idx === state.reader.currentIndex) {
            item.scrollIntoView({ behavior: 'smooth', inline: 'center', block: 'nearest' });
        }
    });
}

function renderFilmstrip() {
    elements.readerFilmstrip.innerHTML = '';
    state.currentPages.forEach((page, idx) => {
        const item = document.createElement('div');
        item.className = `strip-item ${idx === state.reader.currentIndex ? 'active' : ''}`;
        const thumbUrl = page.thumb_url || page.local_url || page.full_url;
        item.innerHTML = `<img src="${thumbUrl}" alt="Page ${idx + 1}" loading="lazy">`;
        
        item.addEventListener('click', () => {
            state.reader.currentIndex = idx;
            resetReaderZoom();
            updateReaderContent();
        });
        
        elements.readerFilmstrip.appendChild(item);
    });
}

function setReaderZoom(newZoom) {
    state.reader.zoom = Math.max(1, Math.min(newZoom, 4.0));
    if (state.reader.zoom === 1) {
        state.reader.panX = 0;
        state.reader.panY = 0;
    }
    applyReaderTransform();
}

function resetReaderZoom() {
    state.reader.zoom = 1;
    state.reader.panX = 0;
    state.reader.panY = 0;
    applyReaderTransform();
}

function applyReaderTransform() {
    elements.readerImageWrapper.style.transform = `translate(${state.reader.panX}px, ${state.reader.panY}px) scale(${state.reader.zoom})`;
}

// ==============================================================================
// NEWS PORTAL ARTICLES TAB
// ==============================================================================

function initNewsCategories() {
    const categories = [
        { slug: "state", name: "ರಾಜ್ಯ (State News)" },
        { slug: "national", name: "ದೇಶ (National)" },
        { slug: "sports", name: "ಕ್ರೀಡೆ (Sports)" },
        { slug: "cinevani", name: "ಸಿನಿವಾಣಿ (Cinema)" },
        { slug: "rajakeeya", name: "ರಾಜಕೀಯ (Politics)" },
        { slug: "lifestyle", name: "ಲೈಫ್‌ಸ್ಟೈಲ್ (Lifestyle)" },
        { slug: "breaking", name: "ಬ್ರೇಕಿಂಗ್ ನ್ಯೂಸ್ (Breaking News)" }
    ];

    let selectedCat = 'state';

    categories.forEach(cat => {
        const pill = document.createElement('button');
        pill.type = 'button';
        pill.className = `category-pill ${cat.slug === selectedCat ? 'selected' : ''}`;
        pill.textContent = cat.name;
        
        pill.addEventListener('click', () => {
            document.querySelectorAll('.category-pill').forEach(p => p.classList.remove('selected'));
            pill.classList.add('selected');
            selectedCat = cat.slug;
        });

        elements.newsCategoriesContainer.appendChild(pill);
    });

    elements.newsLimitInput.addEventListener('input', (e) => {
        elements.newsLimitVal.textContent = e.target.value;
    });

    elements.btnScrapeNews.addEventListener('click', async () => {
        const limit = parseInt(elements.newsLimitInput.value) || 15;
        elements.btnScrapeNews.disabled = true;
        showToast('ಸುದ್ದಿಗಳನ್ನು ಲೋಡ್ ಮಾಡಲಾಗುತ್ತಿದೆ...', 'info');

        try {
            const res = await fetch('/api/news/scrape', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    section: selectedCat === 'breaking' ? null : selectedCat,
                    breaking_only: selectedCat === 'breaking',
                    limit: limit
                })
            });

            const data = await res.json();
            if (!res.ok) throw new Error(data.error || 'Failed to fetch stories');

            renderNewsGrid(data.stories || []);
            showToast(`${data.stories.length} ಸುದ್ದಿ ಲೇಖನಗಳು ದೊರೆತಿವೆ!`, 'success');

        } catch (err) {
            showToast(`ದೋಷ: ${err.message}`, 'error');
        } finally {
            elements.btnScrapeNews.disabled = false;
        }
    });
}

function renderNewsGrid(stories) {
    elements.newsResultsGrid.innerHTML = '';
    if (stories.length === 0) {
        elements.newsResultsGrid.innerHTML = '<p style="text-align:center; color:var(--text-muted);">ಯಾವುದೇ ಸುದ್ದಿಗಳು ಕಂಡುಬಂದಿಲ್ಲ (No stories found).</p>';
        return;
    }

    stories.forEach(story => {
        const item = document.createElement('div');
        item.className = 'news-card-item';
        
        const photoUrl = story.image_url || '/downloads/placeholder.jpg';
        const dateStr = story.published_at ? new Date(story.published_at).toLocaleDateString() : '';

        item.innerHTML = `
            <div class="news-thumb">
                <img src="${photoUrl}" alt="${escapeHtml(story.headline)}" loading="lazy">
            </div>
            <div class="news-content">
                <h4 class="news-headline">${escapeHtml(story.headline)}</h4>
                <div class="news-footer">
                    <span>${story.sections || 'ಸುದ್ದಿ'}</span>
                    <span>${dateStr}</span>
                </div>
            </div>
        `;

        elements.newsResultsGrid.appendChild(item);
    });
}

// ==============================================================================
// TOAST NOTIFICATIONS & UTILS
// ==============================================================================

function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    let icon = 'ℹ️';
    if (type === 'success') icon = '✅';
    if (type === 'warning') icon = '⚠️';
    if (type === 'error') icon = '❌';

    toast.innerHTML = `<span>${icon}</span> <span>${escapeHtml(message)}</span>`;
    elements.toastContainer.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(10px)';
        setTimeout(() => toast.remove(), 300);
    }, 4500);
}

function escapeHtml(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}
