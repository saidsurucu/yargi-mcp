# kik_mcp_module/client.py
import asyncio
from playwright.async_api import (
    async_playwright, 
    Page, 
    BrowserContext, 
    Browser, 
    Error as PlaywrightError, 
    TimeoutError as PlaywrightTimeoutError
)
from bs4 import BeautifulSoup
import logging
from typing import Dict, Any, List, Optional
import urllib.parse 
import base64 # Base64 için
import re
import html as html_parser 
from markitdown import MarkItDown 
import os
import math 
import io
import random

from .models import (
    KikSearchRequest,
    KikDecisionEntry,
    KikSearchResult,
    KikDocumentMarkdown,
    KikKararTipi
)

logger = logging.getLogger(__name__)

class KikApiClient:
    BASE_URL = "https://ekap.kik.gov.tr"
    SEARCH_PAGE_PATH = "/EKAP/Vatandas/kurulkararsorgu.aspx"
    FIELD_LOCATORS = {
        "karar_tipi_radio_group": "input[name='ctl00$ContentPlaceHolder1$kurulKararTip']",
        "karar_no": "input[name='ctl00$ContentPlaceHolder1$txtKararNo']",
        "karar_tarihi_baslangic": "input[name='ctl00$ContentPlaceHolder1$etKararTarihBaslangic$EkapTakvimTextBox_etKararTarihBaslangic']",
        "karar_tarihi_bitis": "input[name='ctl00$ContentPlaceHolder1$etKararTarihBitis$EkapTakvimTextBox_etKararTarihBitis']",
        "resmi_gazete_sayisi": "input[name='ctl00$ContentPlaceHolder1$txtResmiGazeteSayisi']",
        "resmi_gazete_tarihi": "input[name='ctl00$ContentPlaceHolder1$etResmiGazeteTarihi$EkapTakvimTextBox_etResmiGazeteTarihi']",
        "basvuru_konusu_ihale": "input[name='ctl00$ContentPlaceHolder1$txtBasvuruKonusuIhale']",
        "basvuru_sahibi": "input[name='ctl00$ContentPlaceHolder1$txtSikayetci']",
        "ihaleyi_yapan_idare": "input[name='ctl00$ContentPlaceHolder1$txtIhaleyiYapanIdare']",
        "yil": "select[name='ctl00$ContentPlaceHolder1$ddlYil']",
        "karar_metni": "input[name='ctl00$ContentPlaceHolder1$txtKararMetni']",
        "search_button_id": "ctl00_ContentPlaceHolder1_btnAra" 
    }
    RESULTS_TABLE_ID = "grdKurulKararSorguSonuc"
    NO_RESULTS_MESSAGE_SELECTOR = "div#ctl00_MessageContent1" 
    VALIDATION_SUMMARY_SELECTOR = "div#ctl00_ValidationSummary1"
    MODAL_CLOSE_BUTTON_SELECTOR = "div#detayPopUp.in a#btnKapatPencere_0.close"
    DOCUMENT_MARKDOWN_CHUNK_SIZE = 5000 

    def __init__(self, request_timeout: float = 60000): 
        self.playwright_instance: Optional[async_playwright] = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.request_timeout = request_timeout 
        self._lock = asyncio.Lock()

    async def _ensure_playwright_ready(self, force_new_page: bool = False):
        async with self._lock:
            browser_recreated = False
            context_recreated = False
            if not self.playwright_instance:
                self.playwright_instance = await async_playwright().start()
            if not self.browser or not self.browser.is_connected():
                if self.browser: await self.browser.close()
                # Ultra stealth browser configuration
                self.browser = await self.playwright_instance.chromium.launch(
                    headless=True,
                    args=[
                        # Disable automation indicators
                        '--no-first-run',
                        '--no-default-browser-check',
                        '--disable-dev-shm-usage',
                        '--disable-extensions',
                        '--disable-gpu',
                        '--disable-default-apps',
                        '--disable-translate',
                        '--disable-blink-features=AutomationControlled',
                        '--disable-ipc-flooding-protection',
                        '--disable-renderer-backgrounding',
                        '--disable-backgrounding-occluded-windows',
                        '--disable-client-side-phishing-detection',
                        '--disable-sync',
                        '--disable-features=TranslateUI,BlinkGenPropertyTrees',
                        '--disable-component-extensions-with-background-pages',
                        '--no-sandbox',  # Sometimes needed for headless
                        '--disable-web-security',
                        '--disable-features=VizDisplayCompositor',
                        # Language and locale
                        '--lang=tr-TR',
                        '--accept-lang=tr-TR,tr;q=0.9,en;q=0.8',
                        # Performance optimizations
                        '--memory-pressure-off',
                        '--max_old_space_size=4096',
                    ]
                ) 
                browser_recreated = True 
            if not self.context or browser_recreated:
                if self.context: await self.context.close()
                if not self.browser: raise PlaywrightError("Browser not initialized.")
                # Ultra realistic context configuration
                self.context = await self.browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                    viewport={'width': 1920, 'height': 1080},
                    screen={'width': 1920, 'height': 1080},
                    device_scale_factor=1.0,
                    is_mobile=False,
                    has_touch=False,
                    # Localization
                    locale='tr-TR',
                    timezone_id='Europe/Istanbul',
                    # Realistic browser features
                    java_script_enabled=True,
                    accept_downloads=True,
                    ignore_https_errors=True,
                    # Color scheme and media
                    color_scheme='light',
                    reduced_motion='no-preference',
                    forced_colors='none',
                    # Additional headers for realism
                    extra_http_headers={
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                        'Accept-Encoding': 'gzip, deflate, br',
                        'Accept-Language': 'tr-TR,tr;q=0.9,en;q=0.8',
                        'Cache-Control': 'max-age=0',
                        'DNT': '1',
                        'Upgrade-Insecure-Requests': '1',
                        'Sec-Ch-Ua': '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
                        'Sec-Ch-Ua-Mobile': '?0',
                        'Sec-Ch-Ua-Platform': '"Windows"',
                        'Sec-Fetch-Dest': 'document',
                        'Sec-Fetch-Mode': 'navigate',
                        'Sec-Fetch-Site': 'none',
                        'Sec-Fetch-User': '?1',
                    },
                    # Permissions to appear realistic
                    permissions=['geolocation'],
                    geolocation={'latitude': 41.0082, 'longitude': 28.9784},  # Istanbul
                )
                context_recreated = True 
            if not self.page or self.page.is_closed() or force_new_page or context_recreated or browser_recreated:
                if self.page and not self.page.is_closed(): await self.page.close()
                if not self.context: raise PlaywrightError("Context is None.")
                self.page = await self.context.new_page()
                if not self.page: raise PlaywrightError("Failed to create new page.")
                self.page.set_default_navigation_timeout(self.request_timeout)
                self.page.set_default_timeout(self.request_timeout)
                
                # CRITICAL: Anti-detection JavaScript injection
                await self._inject_stealth_scripts()
            if not self.page or self.page.is_closed(): 
                raise PlaywrightError("Playwright page initialization failed.")
            logger.debug("_ensure_playwright_ready completed.")

    async def close_client_session(self):
        async with self._lock:
            # ... (öncekiyle aynı)
            if self.page and not self.page.is_closed(): await self.page.close(); self.page = None
            if self.context: await self.context.close(); self.context = None
            if self.browser: await self.browser.close(); self.browser = None
            if self.playwright_instance: await self.playwright_instance.stop(); self.playwright_instance = None
            logger.info("KikApiClient (Playwright): Resources closed.")

    async def _inject_stealth_scripts(self):
        """
        Inject comprehensive stealth JavaScript to evade bot detection.
        Overrides navigator properties and other fingerprinting vectors.
        """
        if not self.page:
            logger.warning("Cannot inject stealth scripts: page is None")
            return
            
        logger.debug("Injecting comprehensive stealth scripts...")
        
        stealth_script = '''
        // Override navigator.webdriver
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined,
            configurable: true
        });
        
        // Override navigator properties to appear more human
        Object.defineProperty(navigator, 'languages', {
            get: () => ['tr-TR', 'tr', 'en-US', 'en'],
            configurable: true
        });
        
        Object.defineProperty(navigator, 'platform', {
            get: () => 'Win32',
            configurable: true
        });
        
        Object.defineProperty(navigator, 'vendor', {
            get: () => 'Google Inc.',
            configurable: true
        });
        
        Object.defineProperty(navigator, 'deviceMemory', {
            get: () => 8,
            configurable: true
        });
        
        Object.defineProperty(navigator, 'hardwareConcurrency', {
            get: () => 8,
            configurable: true
        });
        
        Object.defineProperty(navigator, 'maxTouchPoints', {
            get: () => 0,
            configurable: true
        });
        
        // Override plugins to appear realistic
        Object.defineProperty(navigator, 'plugins', {
            get: () => {
                return [
                    {
                        0: {type: "application/x-google-chrome-pdf", suffixes: "pdf", description: "Portable Document Format", enabledPlugin: Plugin},
                        description: "Portable Document Format",
                        filename: "internal-pdf-viewer",
                        length: 1,
                        name: "Chrome PDF Plugin"
                    },
                    {
                        0: {type: "application/pdf", suffixes: "pdf", description: "", enabledPlugin: Plugin},
                        description: "",
                        filename: "mhjfbmdgcfjbbpaeojofohoefgiehjai",
                        length: 1,
                        name: "Chrome PDF Viewer"
                    }
                ];
            },
            configurable: true
        });
        
        // Override permissions
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters)
        );
        
        // Override WebGL rendering context
        const getParameter = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(parameter) {
            if (parameter === 37445) { // UNMASKED_VENDOR_WEBGL
                return 'Intel Inc.';
            }
            if (parameter === 37446) { // UNMASKED_RENDERER_WEBGL
                return 'Intel(R) Iris(R) Plus Graphics 640';
            }
            return getParameter(parameter);
        };
        
        // Override canvas fingerprinting
        const toBlob = HTMLCanvasElement.prototype.toBlob;
        const toDataURL = HTMLCanvasElement.prototype.toDataURL;
        const getImageData = CanvasRenderingContext2D.prototype.getImageData;
        
        const noisify = (canvas, context) => {
            const imageData = context.getImageData(0, 0, canvas.width, canvas.height);
            for (let i = 0; i < imageData.data.length; i += 4) {
                imageData.data[i] += Math.floor(Math.random() * 10) - 5;
                imageData.data[i + 1] += Math.floor(Math.random() * 10) - 5;
                imageData.data[i + 2] += Math.floor(Math.random() * 10) - 5;
            }
            context.putImageData(imageData, 0, 0);
        };
        
        Object.defineProperty(HTMLCanvasElement.prototype, 'toBlob', {
            value: function(callback, type, encoderOptions) {
                noisify(this, this.getContext('2d'));
                return toBlob.apply(this, arguments);
            }
        });
        
        Object.defineProperty(HTMLCanvasElement.prototype, 'toDataURL', {
            value: function(type, encoderOptions) {
                noisify(this, this.getContext('2d'));
                return toDataURL.apply(this, arguments);
            }
        });
        
        // Override AudioContext for audio fingerprinting
        const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        const originalAnalyser = audioCtx.createAnalyser;
        audioCtx.createAnalyser = function() {
            const analyser = originalAnalyser.apply(this, arguments);
            const getFloatFrequencyData = analyser.getFloatFrequencyData;
            analyser.getFloatFrequencyData = function(array) {
                getFloatFrequencyData.apply(this, arguments);
                for (let i = 0; i < array.length; i++) {
                    array[i] += Math.random() * 0.0001;
                }
            };
            return analyser;
        };
        
        // Override screen properties
        Object.defineProperty(window.screen, 'colorDepth', {
            get: () => 24,
            configurable: true
        });
        
        Object.defineProperty(window.screen, 'pixelDepth', {
            get: () => 24,
            configurable: true
        });
        
        // Override timezone
        Date.prototype.getTimezoneOffset = function() {
            return -180; // UTC+3 (Istanbul)
        };
        
        // Override document.cookie to prevent tracking
        const originalCookieDescriptor = Object.getOwnPropertyDescriptor(Document.prototype, 'cookie') || 
                                       Object.getOwnPropertyDescriptor(HTMLDocument.prototype, 'cookie');
        if (originalCookieDescriptor && originalCookieDescriptor.configurable) {
            Object.defineProperty(document, 'cookie', {
                get: function() {
                    return originalCookieDescriptor.get.call(this);
                },
                set: function(val) {
                    console.log('Cookie set blocked:', val);
                    return originalCookieDescriptor.set.call(this, val);
                },
                configurable: true
            });
        }
        
        // Remove automation traces
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_JSON;
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Object;
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Proxy;
        
        // Add realistic performance timing
        if (window.performance && window.performance.timing) {
            const timing = window.performance.timing;
            const now = Date.now();
            Object.defineProperty(timing, 'navigationStart', { value: now - Math.floor(Math.random() * 1000) + 1000, configurable: false });
            Object.defineProperty(timing, 'loadEventEnd', { value: now - Math.floor(Math.random() * 100) + 100, configurable: false });
        }
        
        console.log('✓ Stealth scripts injected successfully');
        '''
        
        try:
            await self.page.add_init_script(stealth_script)
            logger.debug("✅ Stealth scripts injected successfully")
        except Exception as e:
            logger.warning(f"⚠️ Failed to inject stealth scripts: {e}")

    async def _simulate_human_behavior(self, fast_mode: bool = True):
        """
        Simulate realistic human behavior patterns to avoid detection.
        Includes mouse movements, typing patterns, and natural delays.
        
        Args:
            fast_mode: If True, use minimal timing for speed optimization
        """
        if not self.page:
            logger.warning("Cannot simulate human behavior: page is None")
            return
            
        logger.debug("🤖 Simulating human behavior patterns...")
        
        try:
            if fast_mode:
                # ULTRA-FAST MODE: Minimal human behavior
                viewport_size = self.page.viewport_size
                if viewport_size and random.random() < 0.7:  # 70% chance to do movement
                    width, height = viewport_size['width'], viewport_size['height']
                    
                    # Single quick mouse movement
                    x = random.randint(200, width - 200)
                    y = random.randint(200, height - 200)
                    await self.page.mouse.move(x, y)
                    
                    # Brief scroll (50% chance)
                    if random.random() < 0.5:
                        await self.page.mouse.wheel(0, random.randint(50, 100))
                
                # Ultra-minimal delay
                await asyncio.sleep(random.uniform(0.05, 0.15))  # Reduced from 0.1-0.3
                
            else:
                # FULL MODE: Original comprehensive behavior
                viewport_size = self.page.viewport_size
                if viewport_size:
                    width, height = viewport_size['width'], viewport_size['height']
                    
                    # Generate 3-5 random mouse movements
                    movements = random.randint(3, 5)
                    logger.debug(f"  🖱️ Performing {movements} random mouse movements")
                    
                    for i in range(movements):
                        x = random.randint(100, width - 100)
                        y = random.randint(100, height - 100)
                        
                        # Move mouse with realistic speed (not instant)
                        await self.page.mouse.move(x, y)
                        await asyncio.sleep(random.uniform(0.1, 0.3))
                    
                    # 2. Scroll simulation
                    logger.debug("  📜 Simulating scroll behavior")
                    scroll_amount = random.randint(100, 300)
                    await self.page.mouse.wheel(0, scroll_amount)
                    await asyncio.sleep(random.uniform(0.2, 0.5))
                    
                    # Scroll back up
                    await self.page.mouse.wheel(0, -scroll_amount)
                    await asyncio.sleep(random.uniform(0.2, 0.4))
                
                # 3. Random page interaction delays
                await asyncio.sleep(random.uniform(0.5, 1.5))
            
            logger.debug("✅ Human behavior simulation completed")
            
        except Exception as e:
            logger.warning(f"⚠️ Human behavior simulation failed: {e}")

    async def _human_type(self, selector: str, text: str, clear_first: bool = True, fast_mode: bool = True):
        """
        Type text with human-like patterns and delays.
        
        Args:
            selector: CSS selector for the input element
            text: Text to type
            clear_first: Whether to clear the field first
            fast_mode: If True, use minimal delays for speed optimization
        """
        if not self.page:
            logger.warning("Cannot perform human typing: page is None")
            return
            
        try:
            if fast_mode:
                # FAST MODE: Direct fill for speed
                await self.page.fill(selector, text)
                await asyncio.sleep(random.uniform(0.02, 0.05))  # Reduced from 0.05-0.1
            else:
                # FULL MODE: Character-by-character human typing
                # Focus on the element first
                await self.page.focus(selector)
                await asyncio.sleep(random.uniform(0.1, 0.3))
                
                # Clear field if requested
                if clear_first:
                    await self.page.keyboard.press('Control+a')
                    await asyncio.sleep(random.uniform(0.05, 0.15))
                    await self.page.keyboard.press('Delete')
                    await asyncio.sleep(random.uniform(0.05, 0.15))
                
                # Type each character with human-like delays
                for char in text:
                    await self.page.keyboard.type(char)
                    # Human typing speed: 50-150ms between characters
                    delay = random.uniform(0.05, 0.15)
                    
                    # Occasional longer pauses (thinking)
                    if random.random() < 0.1:  # 10% chance
                        delay += random.uniform(0.2, 0.8)
                    
                    await asyncio.sleep(delay)
                
                # Brief pause after typing
                await asyncio.sleep(random.uniform(0.2, 0.6))
            
            logger.debug(f"✅ Human-typed '{text}' into {selector}")
            
        except Exception as e:
            logger.warning(f"⚠️ Human typing failed: {e}")

    async def _human_click(self, selector: str, wait_before: bool = True, wait_after: bool = True, fast_mode: bool = True):
        """
        Perform a human-like click with realistic delays and mouse movement.
        
        Args:
            selector: CSS selector or element to click
            wait_before: Whether to wait before clicking
            wait_after: Whether to wait after clicking
            fast_mode: If True, use minimal delays for speed optimization
        """
        if not self.page:
            logger.warning("Cannot perform human click: page is None")
            return
            
        try:
            if fast_mode:
                # FAST MODE: Direct click with minimal delay
                if wait_before:
                    await asyncio.sleep(random.uniform(0.02, 0.08))  # Reduced from 0.05-0.15
                
                await self.page.click(selector)
                
                if wait_after:
                    await asyncio.sleep(random.uniform(0.02, 0.08))  # Reduced from 0.05-0.15
                    
            else:
                # FULL MODE: Realistic mouse movement and timing
                # Wait before clicking (thinking time)
                if wait_before:
                    await asyncio.sleep(random.uniform(0.3, 0.8))
                
                # Get element bounds for realistic mouse movement
                element = await self.page.query_selector(selector)
                if element:
                    box = await element.bounding_box()
                    if box:
                        # Move to element with slight randomness
                        center_x = box['x'] + box['width'] / 2
                        center_y = box['y'] + box['height'] / 2
                        
                        # Add small random offset
                        offset_x = random.uniform(-10, 10)
                        offset_y = random.uniform(-5, 5)
                        
                        await self.page.mouse.move(center_x + offset_x, center_y + offset_y)
                        await asyncio.sleep(random.uniform(0.1, 0.3))
                        
                        # Perform click
                        await self.page.mouse.click(center_x + offset_x, center_y + offset_y)
                        
                        logger.debug(f"✅ Human-clicked {selector}")
                    else:
                        # Fallback to regular click
                        await self.page.click(selector)
                        logger.debug(f"✅ Fallback-clicked {selector}")
                else:
                    logger.warning(f"⚠️ Element not found for human click: {selector}")
                    return
                
                # Wait after clicking (processing time)
                if wait_after:
                    await asyncio.sleep(random.uniform(0.2, 0.6))
            
            logger.debug(f"✅ Human-clicked {selector}")
                
        except Exception as e:
            logger.warning(f"⚠️ Human click failed: {e}")

    async def _simulate_page_exploration(self, fast_mode: bool = True):
        """
        Simulate natural page exploration before performing the main task.
        This helps establish a more human-like session.
        
        Args:
            fast_mode: If True, use minimal exploration for speed optimization
        """
        if not self.page:
            return
            
        logger.debug("🕵️ Simulating page exploration...")
        
        try:
            if fast_mode:
                # ULTRA-FAST MODE: Minimal exploration
                await asyncio.sleep(random.uniform(0.05, 0.1))  # Reduced from 0.1-0.3
                
                # Single mouse movement (optional)
                try:
                    elements = await self.page.query_selector_all("input, button")
                    if elements and random.random() < 0.5:  # 50% chance to skip
                        element = random.choice(elements)
                        box = await element.bounding_box()
                        if box:
                            center_x = box['x'] + box['width'] / 2
                            center_y = box['y'] + box['height'] / 2
                            await self.page.mouse.move(center_x, center_y)
                except:
                    pass
                
                await asyncio.sleep(random.uniform(0.02, 0.05))  # Reduced from 0.05-0.15
                
            else:
                # FULL MODE: Comprehensive exploration
                # 1. Brief pause to "read" the page
                await asyncio.sleep(random.uniform(1.0, 2.5))
                
                # 2. Move mouse to various UI elements (like a human would explore)
                explore_selectors = [
                    "h1", "h2", ".navbar", "#header", ".logo", 
                    "input", "button", "a", ".form-group"
                ]
                
                explored = 0
                for selector in explore_selectors:
                    elements = await self.page.query_selector_all(selector)
                    if elements and explored < 3:  # Explore max 3 elements
                        element = random.choice(elements)
                        box = await element.bounding_box()
                        if box:
                            center_x = box['x'] + box['width'] / 2
                            center_y = box['y'] + box['height'] / 2
                            
                            await self.page.mouse.move(center_x, center_y)
                            await asyncio.sleep(random.uniform(0.3, 0.8))
                            explored += 1
                
                # 3. Small scroll to simulate reading
                await self.page.mouse.wheel(0, random.randint(50, 150))
                await asyncio.sleep(random.uniform(0.5, 1.2))
            
            logger.debug("✅ Page exploration completed")
            
        except Exception as e:
            logger.debug(f"⚠️ Page exploration failed: {e}")

    def _parse_decision_entries_from_soup(self, soup: BeautifulSoup, search_karar_tipi: KikKararTipi) -> List[KikDecisionEntry]:
        entries: List[KikDecisionEntry] = []
        table = soup.find("table", {"id": self.RESULTS_TABLE_ID})
        
        logger.debug(f"Looking for table with ID: {self.RESULTS_TABLE_ID}")
        if not table: 
            logger.warning(f"Table with ID '{self.RESULTS_TABLE_ID}' not found in HTML")
            # Log available tables for debugging
            all_tables = soup.find_all("table")
            logger.debug(f"Found {len(all_tables)} tables in HTML")
            for idx, tbl in enumerate(all_tables):
                table_id = tbl.get('id', 'no-id')
                table_class = tbl.get('class', 'no-class')
                rows = tbl.find_all('tr')
                logger.debug(f"Table {idx}: id='{table_id}', class='{table_class}', rows={len(rows)}")
                
                # If this looks like a results table, try to use it
                if (table_id and ('grd' in table_id.lower() or 'kurul' in table_id.lower() or 'sonuc' in table_id.lower())) or \
                   (isinstance(table_class, list) and any('grid' in cls.lower() or 'result' in cls.lower() for cls in table_class)) or \
                   len(rows) > 3:  # Table with multiple rows might be results
                    logger.info(f"Trying to parse table {idx} as potential results table: id='{table_id}'")
                    table = tbl
                    break
            
            if not table:
                logger.error("No suitable results table found")
                return entries
            
        rows = table.find_all("tr")
        logger.info(f"Found {len(rows)} rows in results table")
        
        # Debug: Log first few rows structure
        for i, row in enumerate(rows[:3]):
            cells = row.find_all(["td", "th"])
            cell_texts = [cell.get_text(strip=True)[:30] for cell in cells]
            logger.info(f"Row {i} structure: {len(cells)} cells: {cell_texts}")
        
        for row_idx, row in enumerate(rows):
            # Skip first row (search bar with colspan=7) and second row (header with 6 cells)
            if row_idx < 2: 
                logger.debug(f"Skipping header row {row_idx}")
                continue
                
            cells = row.find_all("td")
            logger.debug(f"Row {row_idx}: Found {len(cells)} cells")
            
            # Log cell contents for debugging
            if cells and row_idx < 5:  # Log first few data rows
                for cell_idx, cell in enumerate(cells):
                    cell_text = cell.get_text(strip=True)[:50]  # First 50 chars
                    logger.debug(f"  Cell {cell_idx}: '{cell_text}...'")
            
            # Be more flexible with cell count - try 6 cells first, then adapt
            if len(cells) >= 5:  # At least 5 cells for minimum required data
                try:
                    # Try to find preview button in first cell or any cell with a link
                    preview_button_tag = None
                    event_target = ""
                    
                    # Look for preview button in first few cells
                    for cell_idx in range(min(3, len(cells))):
                        cell = cells[cell_idx]
                        # Try multiple patterns for preview button (based on actual HTML structure)
                        preview_candidates = [
                            cell.find("a", id="btnOnizle"),  # Exact match
                            cell.find("a", id=re.compile(r"btnOnizle$")),
                            cell.find("a", id=re.compile(r"btn.*Onizle")),
                            cell.find("a", id=re.compile(r".*Onizle.*")),
                            cell.find("a", href=re.compile(r"__doPostBack"))
                        ]
                        
                        for candidate in preview_candidates:
                            if candidate and candidate.has_attr('href'):
                                match = re.search(r"__doPostBack\('([^']*)','([^']*)'\)", candidate['href'])
                                if match:
                                    event_target = match.group(1)
                                    preview_button_tag = candidate
                                    logger.debug(f"Row {row_idx}: Found event_target '{event_target}' in cell {cell_idx}")
                                    break
                        
                        if preview_button_tag:
                            break
                    
                    if not preview_button_tag:
                        logger.debug(f"Row {row_idx}: No preview button found in any cell")
                        # Log what links we found
                        for cell_idx, cell in enumerate(cells[:3]):
                            links_in_cell = cell.find_all("a")
                            logger.debug(f"  Cell {cell_idx}: {len(links_in_cell)} links")
                            for link in links_in_cell[:2]:
                                logger.debug(f"    Link id='{link.get('id')}', href='{link.get('href', '')[:50]}...'")
                    
                    # Try to find decision data spans with more flexible patterns
                    karar_no_span = None
                    karar_tarihi_span = None
                    idare_span = None
                    basvuru_sahibi_span = None
                    ihale_span = None
                    
                    # Try different span patterns for karar no (usually in cell 1)
                    for cell_idx in range(min(4, len(cells))):
                        if not karar_no_span:
                            cell = cells[cell_idx]
                            candidates = [
                                cell.find("span", id="lblKno"),  # Exact match based on actual HTML
                                cell.find("span", id=re.compile(r"lblKno$")),
                                cell.find("span", id=re.compile(r".*Kno.*")),
                                cell.find("span", id=re.compile(r".*KararNo.*")),
                                cell.find("span", id=re.compile(r".*No.*"))
                            ]
                            for candidate in candidates:
                                if candidate and candidate.get_text(strip=True):
                                    karar_no_span = candidate
                                    logger.debug(f"Row {row_idx}: Found karar_no in cell {cell_idx}")
                                    break
                    
                    # Try different patterns for karar tarihi (usually in cell 2)
                    for cell_idx in range(min(4, len(cells))):
                        if not karar_tarihi_span:
                            cell = cells[cell_idx]
                            candidates = [
                                cell.find("span", id="lblKtar"),  # Exact match based on actual HTML
                                cell.find("span", id=re.compile(r"lblKtar$")),
                                cell.find("span", id=re.compile(r".*Ktar.*")),
                                cell.find("span", id=re.compile(r".*Tarih.*")),
                                cell.find("span", id=re.compile(r".*Date.*"))
                            ]
                            for candidate in candidates:
                                if candidate and candidate.get_text(strip=True):
                                    # Check if it looks like a date
                                    text = candidate.get_text(strip=True)
                                    if re.match(r'\d{1,2}[./]\d{1,2}[./]\d{4}', text):
                                        karar_tarihi_span = candidate
                                        logger.debug(f"Row {row_idx}: Found karar_tarihi in cell {cell_idx}")
                                        break
                    
                    # Find other spans in remaining cells (if we have 6 cells) - using exact IDs
                    if len(cells) >= 6:
                        idare_span = cells[3].find("span", id="lblIdare") or cells[3].find("span")
                        basvuru_sahibi_span = cells[4].find("span", id="lblSikayetci") or cells[4].find("span")
                        ihale_span = cells[5].find("span", id="lblIhale") or cells[5].find("span")
                    elif len(cells) == 5:
                        # Adjust for 5-cell layout
                        idare_span = cells[2].find("span") if cells[2] != cells[1] else None
                        basvuru_sahibi_span = cells[3].find("span") if len(cells) > 3 else None
                        ihale_span = cells[4].find("span") if len(cells) > 4 else None
                    
                    # Log what we found
                    logger.debug(f"Row {row_idx}: karar_no_span={karar_no_span is not None}, "
                               f"karar_tarihi_span={karar_tarihi_span is not None}, "
                               f"event_target={bool(event_target)}")
                    
                    # For KIK, we need at least karar_no and karar_tarihi, event_target is helpful but not critical
                    if not (karar_no_span and karar_tarihi_span):
                        logger.debug(f"Row {row_idx}: Missing required fields (karar_no or karar_tarihi), skipping")
                        # Log what spans we found in cells
                        for i, cell in enumerate(cells):
                            spans = cell.find_all("span")
                            if spans:
                                span_info = []
                                for s in spans:
                                    span_id = s.get('id', 'no-id')
                                    span_text = s.get_text(strip=True)[:20]
                                    span_info.append(f"{span_id}:'{span_text}...'")
                                logger.debug(f"  Cell {i} spans: {span_info}")
                        continue
                    
                    # If we don't have event_target, we can still create an entry but mark it specially
                    if not event_target:
                        logger.warning(f"Row {row_idx}: No event_target found, document retrieval won't work")
                        event_target = f"missing_target_row_{row_idx}"  # Placeholder
                    
                    # Karar tipini arama parametresinden alıyoruz, çünkü HTML'de direkt olarak bulunmuyor.
                    try:
                        entry = KikDecisionEntry(
                            preview_event_target=event_target,
                            kararNo=karar_no_span.get_text(strip=True), 
                            karar_tipi=search_karar_tipi, # Arama yapılan karar tipini ekle
                            kararTarihi=karar_tarihi_span.get_text(strip=True),
                            idare=idare_span.get_text(strip=True) if idare_span else None,
                            basvuruSahibi=basvuru_sahibi_span.get_text(strip=True) if basvuru_sahibi_span else None,
                            ihaleKonusu=ihale_span.get_text(strip=True) if ihale_span else None,
                        )
                        entries.append(entry)
                        logger.info(f"Row {row_idx}: Successfully parsed decision: {entry.karar_no_str}")
                    except Exception as e:
                        logger.error(f"Row {row_idx}: Error creating KikDecisionEntry: {e}")
                        continue
                    
                except Exception as e:
                    logger.error(f"Error parsing row {row_idx}: {e}", exc_info=True)
            else:
                logger.warning(f"Row {row_idx}: Expected at least 5 cells but found {len(cells)}, skipping")
                if len(cells) > 0:
                    cell_texts = [cell.get_text(strip=True)[:50] for cell in cells[:3]]
                    logger.debug(f"Row {row_idx} cells preview: {cell_texts}")
                
        logger.info(f"Parsed {len(entries)} decision entries from {len(rows)} rows")
        return entries
        
    def _parse_total_records_from_soup(self, soup: BeautifulSoup) -> int:
        # ... (öncekiyle aynı) ...
        try:
            pager_div = soup.find("div", class_="gridToplamSayi")
            if pager_div:
                match = re.search(r"Toplam Kayıt Sayısı:(\d+)", pager_div.get_text(strip=True))
                if match: return int(match.group(1))
        except: pass 
        return 0
        
    def _parse_current_page_from_soup(self, soup: BeautifulSoup) -> int:
        # ... (öncekiyle aynı) ...
        try:
            pager_div = soup.find("div", class_="sayfalama")
            if pager_div:
                active_page_span = pager_div.find("span", class_="active")
                if active_page_span: return int(active_page_span.get_text(strip=True))
        except: pass
        return 1

    async def search_decisions(self, search_params: KikSearchRequest) -> KikSearchResult:
        await self._ensure_playwright_ready()
        page = self.page 
        search_url = f"{self.BASE_URL}{self.SEARCH_PAGE_PATH}"
        try:
            if page.url != search_url:
                await page.goto(search_url, wait_until="networkidle", timeout=self.request_timeout)
                
            # Simulate natural page exploration after navigation (FAST MODE)
            await self._simulate_page_exploration(fast_mode=True)
            
            search_button_selector = f"a[id='{self.FIELD_LOCATORS['search_button_id']}']"
            await page.wait_for_selector(search_button_selector, state="visible", timeout=self.request_timeout)

            current_karar_tipi_value = search_params.karar_tipi.value
            radio_locator_selector = f"{self.FIELD_LOCATORS['karar_tipi_radio_group']}[value='{current_karar_tipi_value}']"
            if not await page.locator(radio_locator_selector).is_checked():
                 js_target_radio = f"ctl00$ContentPlaceHolder1${current_karar_tipi_value}"
                 logger.info(f"Selecting radio button: {js_target_radio}")
                 async with page.expect_navigation(wait_until="networkidle", timeout=self.request_timeout):
                     await page.evaluate(f"javascript:__doPostBack('{js_target_radio}','')")
                 # Ultra-fast wait for page to stabilize after radio button change
                 await page.wait_for_timeout(300)  # Reduced from 1000ms
                 logger.info("Radio button selection completed") 

            # Helper function for human-like form filling (FAST MODE)
            async def human_fill_if_value(selector_key: str, value: Optional[str]):
                if value is not None:
                    selector = self.FIELD_LOCATORS[selector_key]
                    await self._human_type(selector, value, fast_mode=True)
            
            # Karar No'yu KİK sitesine göndermeden önce '_' -> '/' dönüşümü yap
            karar_no_for_kik_form = None
            if search_params.karar_no: # search_params.karar_no Claude'dan '_' ile gelmiş olabilir
                karar_no_for_kik_form = search_params.karar_no.replace('_', '/')
                logger.info(f"Using karar_no '{karar_no_for_kik_form}' (transformed from '{search_params.karar_no}') for KIK form.")
            
            # Fill form fields with FAST human-like behavior
            logger.info("Filling form fields with fast mode...")
            
            # Start with FAST mouse behavior simulation
            await self._simulate_human_behavior(fast_mode=True)
            
            await human_fill_if_value('karar_metni', search_params.karar_metni)
            await human_fill_if_value('karar_no', karar_no_for_kik_form) # Dönüştürülmüş halini kullan
            await human_fill_if_value('karar_tarihi_baslangic', search_params.karar_tarihi_baslangic)
            await human_fill_if_value('karar_tarihi_bitis', search_params.karar_tarihi_bitis)
            await human_fill_if_value('resmi_gazete_sayisi', search_params.resmi_gazete_sayisi)
            await human_fill_if_value('resmi_gazete_tarihi', search_params.resmi_gazete_tarihi)
            await human_fill_if_value('basvuru_konusu_ihale', search_params.basvuru_konusu_ihale)
            await human_fill_if_value('basvuru_sahibi', search_params.basvuru_sahibi)
            await human_fill_if_value('ihaleyi_yapan_idare', search_params.ihaleyi_yapan_idare)

            if search_params.yil:
                await page.select_option(self.FIELD_LOCATORS['yil'], value=search_params.yil)
                await page.wait_for_timeout(50)  # Reduced from 100ms
            
            logger.info("Form filling completed, preparing for search...")
            
            # Additional FAST human behavior before search
            await self._simulate_human_behavior(fast_mode=True)

            action_is_search_button_click = (search_params.page == 1)
            event_target_for_submit: str
            
            try:
                if action_is_search_button_click:
                    event_target_for_submit = self.FIELD_LOCATORS['search_button_id']
                    # Use human-like clicking for search button
                    search_button_selector = f"a[id='{event_target_for_submit}']"
                    logger.info(f"Performing human-like search button click...")
                    
                    try:
                        # Hide datepicker first to prevent interference
                        await page.evaluate("$('#ui-datepicker-div').hide()")
                        
                        # FAST Human-like click on search button
                        await self._human_click(search_button_selector, wait_before=True, wait_after=False, fast_mode=True)
                        
                        # Wait for navigation
                        await page.wait_for_load_state("networkidle", timeout=self.request_timeout)
                        logger.info("Search navigation completed successfully")
                    except Exception as e:
                        logger.warning(f"Human click failed, falling back to JavaScript: {e}")
                        # Hide datepicker and use JavaScript fallback
                        await page.evaluate("$('#ui-datepicker-div').hide()")
                        async with page.expect_navigation(wait_until="networkidle", timeout=self.request_timeout):
                            await page.evaluate(f"javascript:__doPostBack('{event_target_for_submit}','')")
                        logger.info("Search navigation completed via fallback")
                else: 
                    # Pagination - use original method for consistency
                    page_link_ctl_number = search_params.page + 2 
                    event_target_for_submit = f"ctl00$ContentPlaceHolder1$grdKurulKararSorguSonuc$ctl14$ctl{page_link_ctl_number:02d}"
                    logger.info(f"Executing pagination with event target: {event_target_for_submit}")
                    
                    async with page.expect_navigation(wait_until="networkidle", timeout=self.request_timeout):
                        await page.evaluate(f"javascript:__doPostBack('{event_target_for_submit}','')")
                    logger.info("Pagination navigation completed successfully")
            except PlaywrightTimeoutError:
                logger.warning("Search navigation timed out, but continuing...")
                await page.wait_for_timeout(5000)  # Longer wait if navigation fails
            
            # Ultra-fast wait time for results to load
            logger.info("Waiting for search results to load...")
            await page.wait_for_timeout(500)  # Reduced from 1000ms 
            
            results_table_dom_selector = f"table#{self.RESULTS_TABLE_ID}"
            try:
                # First wait for any tables to appear (more general check)
                logger.info("Waiting for any tables to appear...")
                await page.wait_for_function("""
                    () => document.querySelectorAll('table').length > 0
                """, timeout=4000)  # Reduced from 8000ms
                logger.info("At least one table appeared")
                
                # Then wait for our specific table
                await page.wait_for_selector(results_table_dom_selector, timeout=4000, state="attached")  # Reduced from 8000ms
                logger.debug("Results table attached to DOM")
                
                # Wait for table to have some content (more than just headers)
                await page.wait_for_function(f"""
                    () => {{
                        const table = document.querySelector('{results_table_dom_selector}');
                        return table && table.querySelectorAll('tr').length > 2;
                    }}
                """, timeout=4000)  # Reduced from 20000ms
                logger.debug("Results table populated with data")
                
                # Ultra-fast additional wait for any remaining JavaScript
                await page.wait_for_timeout(500)  # Reduced from 3000ms 
                
            except PlaywrightTimeoutError:
                logger.warning(f"Timeout waiting for results table '{results_table_dom_selector}'.")
                # Try one more wait for content placeholder
                try:
                    await page.wait_for_selector("#ctl00_ContentPlaceHolder1", timeout=10000)
                    logger.info("ContentPlaceHolder1 found, checking for tables...")
                    await page.wait_for_timeout(5000)
                except PlaywrightTimeoutError:
                    logger.warning("ContentPlaceHolder1 also not found - content may not have loaded")
            
            html_content = await page.content()
            soup = BeautifulSoup(html_content, "html.parser")
            # ... (hata ve sonuç yok mesajı kontrolü aynı) ...
            validation_summary_tag = soup.find("div", id=self.VALIDATION_SUMMARY_SELECTOR.split('[')[0].split(':')[0])
            if validation_summary_tag and validation_summary_tag.get_text(strip=True) and \
               ("display: none" not in validation_summary_tag.get("style", "").lower() if validation_summary_tag.has_attr("style") else True) and \
               validation_summary_tag.get_text(strip=True) != "":
                return KikSearchResult(decisions=[], total_records=0, current_page=search_params.page)
            message_content_div = soup.find("div", id=self.NO_RESULTS_MESSAGE_SELECTOR.split(':')[0])
            if message_content_div and "kayıt bulunamamıştır" in message_content_div.get_text(strip=True).lower():
                return KikSearchResult(decisions=[], total_records=0, current_page=1)

            # _parse_decision_entries_from_soup'a arama yapılan karar_tipi'ni gönder
            decisions = self._parse_decision_entries_from_soup(soup, search_params.karar_tipi)
            total_records = self._parse_total_records_from_soup(soup)
            current_page_from_html = self._parse_current_page_from_soup(soup)
            return KikSearchResult(decisions=decisions, total_records=total_records, current_page=current_page_from_html)
        except Exception as e: 
            logger.error(f"Error during KIK decision search: {e}", exc_info=True)
            return KikSearchResult(decisions=[], current_page=search_params.page)

    def _clean_html_for_markdown(self, html_content: str) -> str:
        # ... (öncekiyle aynı) ...
        if not html_content: return ""
        return html_parser.unescape(html_content)

    def _convert_html_to_markdown_internal(self, html_fragment: str) -> Optional[str]:
        # ... (öncekiyle aynı) ...
        if not html_fragment: return None
        cleaned_html = self._clean_html_for_markdown(html_fragment)
        markdown_output = None
        try:
            # Convert HTML string to bytes and create BytesIO stream
            html_bytes = cleaned_html.encode('utf-8')
            html_stream = io.BytesIO(html_bytes)
            
            # Pass BytesIO stream to MarkItDown to avoid temp file creation
            md_converter = MarkItDown(enable_plugins=True, remove_alt_whitespace=True, keep_underline=True)
            markdown_output = md_converter.convert(html_stream).text_content
            if markdown_output: markdown_output = re.sub(r'\n{3,}', '\n\n', markdown_output).strip()
        except Exception as e: logger.error(f"MarkItDown conversion error: {e}", exc_info=True)
        return markdown_output


    async def get_decision_document_as_markdown(
            self, 
            karar_id_b64: str, 
            page_number: int = 1 
        ) -> KikDocumentMarkdown:
        await self._ensure_playwright_ready()
        # Bu metodun kendi içinde yeni bir 'page' nesnesi ('doc_page_for_content') kullanacağını unutmayın,
        # ana 'self.page' arama sonuçları sayfasında kalır.
        current_main_page = self.page # Ana arama sonuçları sayfasını referans alalım

        try:
            decoded_key = base64.b64decode(karar_id_b64.encode('utf-8')).decode('utf-8')
            karar_tipi_value, karar_no_for_search = decoded_key.split('|', 1)
            original_karar_tipi = KikKararTipi(karar_tipi_value)
            logger.info(f"KIK Get Detail: Decoded karar_id '{karar_id_b64}' to Karar Tipi: {original_karar_tipi.value}, Karar No: {karar_no_for_search}. Requested Markdown Page: {page_number}")
        except Exception as e_decode:
            logger.error(f"Invalid karar_id format. Could not decode Base64 or split: {karar_id_b64}. Error: {e_decode}")
            return KikDocumentMarkdown(retrieved_with_karar_id=karar_id_b64, error_message="Invalid karar_id format.", current_page=page_number)

        default_error_response_data = {
            "retrieved_with_karar_id": karar_id_b64,
            "retrieved_karar_no": karar_no_for_search,
            "retrieved_karar_tipi": original_karar_tipi,
            "error_message": "An unspecified error occurred.",
            "current_page": page_number, "total_pages": 1, "is_paginated": False
        }
        
        # Ana arama sayfasında olduğumuzdan emin olalım
        if self.SEARCH_PAGE_PATH not in current_main_page.url:
            logger.info(f"Not on search page ({current_main_page.url}). Navigating to {self.SEARCH_PAGE_PATH} before targeted search for document.")
            await current_main_page.goto(f"{self.BASE_URL}{self.SEARCH_PAGE_PATH}", wait_until="networkidle", timeout=self.request_timeout)
            await current_main_page.wait_for_selector(f"a[id='{self.FIELD_LOCATORS['search_button_id']}']", state="visible", timeout=self.request_timeout)

        targeted_search_params = KikSearchRequest(
            karar_no=karar_no_for_search, 
            karar_tipi=original_karar_tipi,
            page=1 
        )
        logger.info(f"Performing targeted search for Karar No: {karar_no_for_search}")
        # search_decisions kendi içinde _ensure_playwright_ready çağırır ve self.page'i kullanır.
        # Bu, current_main_page ile aynı olmalı.
        search_results = await self.search_decisions(targeted_search_params)

        if not search_results.decisions:
            default_error_response_data["error_message"] = f"Decision with Karar No '{karar_no_for_search}' (Tipi: {original_karar_tipi.value}) not found by internal search."
            return KikDocumentMarkdown(**default_error_response_data)

        decision_to_fetch = None
        for dec_entry in search_results.decisions:
            if dec_entry.karar_no_str == karar_no_for_search and dec_entry.karar_tipi == original_karar_tipi:
                decision_to_fetch = dec_entry
                break
        
        if not decision_to_fetch:
            default_error_response_data["error_message"] = f"Karar No '{karar_no_for_search}' (Tipi: {original_karar_tipi.value}) not present with an exact match in first page of targeted search results."
            return KikDocumentMarkdown(**default_error_response_data)

        decision_preview_event_target = decision_to_fetch.preview_event_target
        logger.info(f"Found target decision. Using preview_event_target: {decision_preview_event_target} for Karar No: {decision_to_fetch.karar_no_str}")
        
        iframe_document_url_str = None
        karar_id_param_from_url_on_doc_page = None
        document_html_content = ""

        try:
            logger.info(f"Evaluating __doPostBack on main page to show modal for: {decision_preview_event_target}")
            # Bu evaluate, self.page (yani current_main_page) üzerinde çalışır
            await current_main_page.evaluate(f"javascript:__doPostBack('{decision_preview_event_target}','')")
            await current_main_page.wait_for_timeout(1000) 
            logger.info(f"Executed __doPostBack for {decision_preview_event_target} on main page.")
            
            iframe_selector = "iframe#iframe_detayPopUp"
            modal_visible_selector = "div#detayPopUp.in" 

            try:
                logger.info(f"Waiting for modal '{modal_visible_selector}' to be visible and iframe '{iframe_selector}' src to be populated on main page...")
                await current_main_page.wait_for_function(
                    f"""
                    () => {{
                        const modal = document.querySelector('{modal_visible_selector}');
                        const iframe = document.querySelector('{iframe_selector}');
                        const modalIsTrulyVisible = modal && (window.getComputedStyle(modal).display !== 'none');
                        return modalIsTrulyVisible && 
                               iframe && iframe.getAttribute('src') && 
                               iframe.getAttribute('src').includes('KurulKararGoster.aspx');
                    }}
                    """,
                    timeout=self.request_timeout / 2 
                )
                iframe_src_value = await current_main_page.locator(iframe_selector).get_attribute("src")
                logger.info(f"Iframe src populated: {iframe_src_value}")

            except PlaywrightTimeoutError:
                 logger.warning(f"Timeout waiting for KIK iframe src for {decision_preview_event_target}. Trying to parse from static content after presumed update.")
                 html_after_postback = await current_main_page.content()
                 # ... (fallback parsing öncekiyle aynı, default_error_response_data set edilir ve return edilir) ...
                 soup_after_postback = BeautifulSoup(html_after_postback, "html.parser")
                 detay_popup_div = soup_after_postback.find("div", {"id": "detayPopUp", "class": re.compile(r"\bin\b")})
                 if not detay_popup_div: detay_popup_div = soup_after_postback.find("div", {"id": "detayPopUp", "style": re.compile(r"display:\s*block", re.I)})
                 iframe_tag = detay_popup_div.find("iframe", {"id": "iframe_detayPopUp"}) if detay_popup_div else None
                 if iframe_tag and iframe_tag.has_attr("src") and iframe_tag["src"]: iframe_src_value = iframe_tag["src"]
                 else:
                    default_error_response_data["error_message"]="Timeout or failure finding decision content iframe URL after postback."
                    return KikDocumentMarkdown(**default_error_response_data)
            
            if not iframe_src_value or not iframe_src_value.strip():
                default_error_response_data["error_message"]="Extracted iframe URL for decision content is empty."
                return KikDocumentMarkdown(**default_error_response_data)

            # iframe_src_value göreceli bir URL ise, ana sayfanın URL'si ile birleştir
            iframe_document_url_str = urllib.parse.urljoin(current_main_page.url, iframe_src_value)
            logger.info(f"Constructed absolute iframe_document_url_str for goto: {iframe_document_url_str}") # Log this absolute URL
            default_error_response_data["source_url"] = iframe_document_url_str
            
            parsed_url = urllib.parse.urlparse(iframe_document_url_str)
            query_params = urllib.parse.parse_qs(parsed_url.query)
            karar_id_param_from_url_on_doc_page = query_params.get("KararId", [None])[0] 
            default_error_response_data["karar_id_param_from_url"] = karar_id_param_from_url_on_doc_page
            if not karar_id_param_from_url_on_doc_page:
                 default_error_response_data["error_message"]="KararId (KIK internal ID) not found in extracted iframe URL."
                 return KikDocumentMarkdown(**default_error_response_data)

            logger.info(f"Fetching KIK decision content from iframe URL using a new Playwright page: {iframe_document_url_str}")
            
            doc_page_for_content = await self.context.new_page() 
            try:
                # `goto` metoduna MUTLAK URL verilmeli. Loglanan URL'nin mutlak olduğundan emin olalım.
                await doc_page_for_content.goto(iframe_document_url_str, wait_until="domcontentloaded", timeout=self.request_timeout)
                document_html_content = await doc_page_for_content.content()
            except Exception as e_doc_page:
                logger.error(f"Error navigating or getting content from doc_page ({iframe_document_url_str}): {e_doc_page}")
                if doc_page_for_content and not doc_page_for_content.is_closed(): await doc_page_for_content.close()
                default_error_response_data["error_message"]=f"Failed to load decision detail page: {e_doc_page}"
                return KikDocumentMarkdown(**default_error_response_data)
            finally:
                if doc_page_for_content and not doc_page_for_content.is_closed(): 
                    await doc_page_for_content.close() 

            soup_decision_detail = BeautifulSoup(document_html_content, "html.parser")
            karar_content_span = soup_decision_detail.find("span", {"id": "ctl00_ContentPlaceHolder1_lblKarar"})
            actual_decision_html = karar_content_span.decode_contents() if karar_content_span else document_html_content
            full_markdown_content = self._convert_html_to_markdown_internal(actual_decision_html)

            if not full_markdown_content:
                 default_error_response_data["error_message"]="Markdown conversion failed or returned empty content."
                 try: 
                    if await current_main_page.locator(self.MODAL_CLOSE_BUTTON_SELECTOR).is_visible(timeout=1000):
                        await current_main_page.locator(self.MODAL_CLOSE_BUTTON_SELECTOR).click()
                 except: pass
                 return KikDocumentMarkdown(**default_error_response_data)

            content_length = len(full_markdown_content); total_pages = math.ceil(content_length / self.DOCUMENT_MARKDOWN_CHUNK_SIZE) or 1
            current_page_clamped = max(1, min(page_number, total_pages))
            start_index = (current_page_clamped - 1) * self.DOCUMENT_MARKDOWN_CHUNK_SIZE
            markdown_chunk = full_markdown_content[start_index : start_index + self.DOCUMENT_MARKDOWN_CHUNK_SIZE]
            
            try: 
                if await current_main_page.locator(self.MODAL_CLOSE_BUTTON_SELECTOR).is_visible(timeout=2000): 
                    await current_main_page.locator(self.MODAL_CLOSE_BUTTON_SELECTOR).click()
                    await current_main_page.wait_for_selector(f"div#detayPopUp:not(.in)", timeout=5000) 
            except: pass

            return KikDocumentMarkdown(
                retrieved_with_karar_id=karar_id_b64,
                retrieved_karar_no=karar_no_for_search,
                retrieved_karar_tipi=original_karar_tipi,
                kararIdParam=karar_id_param_from_url_on_doc_page, 
                markdown_chunk=markdown_chunk, source_url=iframe_document_url_str,
                current_page=current_page_clamped, total_pages=total_pages,
                is_paginated=(total_pages > 1), full_content_char_count=content_length
            )
        except Exception as e: 
            logger.error(f"Error in get_decision_document_as_markdown for Karar ID {karar_id_b64}: {e}", exc_info=True)
            default_error_response_data["error_message"] = f"General error: {str(e)}"
            return KikDocumentMarkdown(**default_error_response_data)
