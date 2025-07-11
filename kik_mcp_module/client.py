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
                self.browser = await self.playwright_instance.chromium.launch(headless=True) 
                browser_recreated = True 
            if not self.context or browser_recreated:
                if self.context: await self.context.close()
                if not self.browser: raise PlaywrightError("Browser not initialized.")
                self.context = await self.browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.0.0 Safari/537.36",
                    java_script_enabled=True,
                )
                context_recreated = True 
            if not self.page or self.page.is_closed() or force_new_page or context_recreated or browser_recreated:
                if self.page and not self.page.is_closed(): await self.page.close()
                if not self.context: raise PlaywrightError("Context is None.")
                self.page = await self.context.new_page()
                if not self.page: raise PlaywrightError("Failed to create new page.")
                self.page.set_default_navigation_timeout(self.request_timeout)
                self.page.set_default_timeout(self.request_timeout)
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

    def _parse_decision_entries_from_soup(self, soup: BeautifulSoup, search_karar_tipi: KikKararTipi) -> List[KikDecisionEntry]:
        entries: List[KikDecisionEntry] = []
        table = soup.find("table", {"id": self.RESULTS_TABLE_ID})
        if not table: return entries
        rows = table.find_all("tr")
        for row_idx, row in enumerate(rows):
            if row_idx < 2: continue             
            cells = row.find_all("td")
            if len(cells) == 6:
                try:
                    preview_button_tag = cells[0].find("a", id=re.compile(r"btnOnizle$"))
                    event_target = ""
                    if preview_button_tag and preview_button_tag.has_attr('href'):
                        match = re.search(r"__doPostBack\('([^']*)','([^']*)'\)", preview_button_tag['href'])
                        if match: event_target = match.group(1)                    
                    karar_no_span = cells[1].find("span", id=re.compile(r"lblKno$"))
                    karar_tarihi_span = cells[2].find("span", id=re.compile(r"lblKtar$"))
                    idare_span = cells[3].find("span", id=re.compile(r"lblIdare$"))
                    basvuru_sahibi_span = cells[4].find("span", id=re.compile(r"lblSikayetci$"))
                    ihale_span = cells[5].find("span", id=re.compile(r"lblIhale$"))
                    if not (event_target and karar_no_span and karar_tarihi_span): continue
                    
                    # Karar tipini arama parametresinden alıyoruz, çünkü HTML'de direkt olarak bulunmuyor.
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
                except Exception as e:
                    logger.error(f"Error parsing a KIK decision entry row: {e}", exc_info=True)
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
            search_button_selector = f"a[id='{self.FIELD_LOCATORS['search_button_id']}']"
            await page.wait_for_selector(search_button_selector, state="visible", timeout=self.request_timeout)

            current_karar_tipi_value = search_params.karar_tipi.value
            radio_locator_selector = f"{self.FIELD_LOCATORS['karar_tipi_radio_group']}[value='{current_karar_tipi_value}']"
            if not await page.locator(radio_locator_selector).is_checked():
                 js_target_radio = f"ctl00$ContentPlaceHolder1${current_karar_tipi_value}"
                 async with page.expect_navigation(wait_until="networkidle", timeout=self.request_timeout):
                     await page.evaluate(f"javascript:__doPostBack('{js_target_radio}','')")
                 await page.wait_for_timeout(1000) 

            async def fill_if_value(selector_key: str, value: Optional[str]):
                if value is not None: await page.fill(self.FIELD_LOCATORS[selector_key], value)
            
            # Karar No'yu KİK sitesine göndermeden önce '_' -> '/' dönüşümü yap
            karar_no_for_kik_form = None
            if search_params.karar_no: # search_params.karar_no Claude'dan '_' ile gelmiş olabilir
                karar_no_for_kik_form = search_params.karar_no.replace('_', '/')
                logger.info(f"Using karar_no '{karar_no_for_kik_form}' (transformed from '{search_params.karar_no}') for KIK form.")
            
            await fill_if_value('karar_metni', search_params.karar_metni)
            await fill_if_value('karar_no', karar_no_for_kik_form) # Dönüştürülmüş halini kullan
            # ... (diğer fill_if_value çağrıları aynı) ...
            await fill_if_value('karar_tarihi_baslangic', search_params.karar_tarihi_baslangic)
            await fill_if_value('karar_tarihi_bitis', search_params.karar_tarihi_bitis)
            await fill_if_value('resmi_gazete_sayisi', search_params.resmi_gazete_sayisi)
            await fill_if_value('resmi_gazete_tarihi', search_params.resmi_gazete_tarihi)
            await fill_if_value('basvuru_konusu_ihale', search_params.basvuru_konusu_ihale)
            await fill_if_value('basvuru_sahibi', search_params.basvuru_sahibi)
            await fill_if_value('ihaleyi_yapan_idare', search_params.ihaleyi_yapan_idare)

            if search_params.yil:
                await page.select_option(self.FIELD_LOCATORS['yil'], value=search_params.yil)

            action_is_search_button_click = (search_params.page == 1)
            event_target_for_submit: str
            if action_is_search_button_click:
                event_target_for_submit = self.FIELD_LOCATORS['search_button_id']
            else: # Pagination
                page_link_ctl_number = search_params.page + 2 
                event_target_for_submit = f"ctl00$ContentPlaceHolder1$grdKurulKararSorguSonuc$ctl14$ctl{page_link_ctl_number:02d}"
            
            try:
                async with page.expect_navigation(wait_until="networkidle", timeout=self.request_timeout):
                    # Use __doPostBack for both search and pagination for consistency
                    await page.evaluate(f"javascript:__doPostBack('{event_target_for_submit}','')")
            except PlaywrightTimeoutError:
                await page.wait_for_timeout(2000) 
            
            results_table_dom_selector = f"table#{self.RESULTS_TABLE_ID}"
            try:
                await page.wait_for_selector(results_table_dom_selector, timeout=30000, state="attached")
                await page.wait_for_timeout(2000) 
            except PlaywrightTimeoutError:
                logger.warning(f"Timeout waiting for results table '{results_table_dom_selector}'.")
            
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
