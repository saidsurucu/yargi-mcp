# anayasa_mcp_module/bireysel_client.py
# This client is for Bireysel Başvuru: https://kararlarbilgibankasi.anayasa.gov.tr

import httpx
from bs4 import BeautifulSoup, Tag
from typing import Dict, Any, List, Optional, Tuple
import logging
import html
import re
import io
from urllib.parse import urlencode, urljoin, quote
from markitdown import MarkItDown
import math # For math.ceil for pagination

from .models import (
    AnayasaBireyselReportSearchRequest,
    AnayasaBireyselReportDecisionDetail,
    AnayasaBireyselReportDecisionSummary,
    AnayasaBireyselReportSearchResult,
    AnayasaBireyselBasvuruDocumentMarkdown, # Model for Bireysel Başvuru document
)

logger = logging.getLogger(__name__)
if not logger.hasHandlers():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


class AnayasaBireyselBasvuruApiClient:
    BASE_URL = "https://kararlarbilgibankasi.anayasa.gov.tr"
    SEARCH_PATH = "/Ara"
    DOCUMENT_MARKDOWN_CHUNK_SIZE = 5000 # Character limit per page

    def __init__(self, request_timeout: float = 60.0):
        self.http_client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers={
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            },
            timeout=request_timeout,
            verify=True,
            follow_redirects=True
        )

    def _build_query_params_for_bireysel_report(self, params: AnayasaBireyselReportSearchRequest) -> List[Tuple[str, str]]:
        query_params: List[Tuple[str, str]] = []
        query_params.append(("KararBulteni", "1")) # Specific to this report type

        if params.keywords:
            for kw in params.keywords:
                query_params.append(("KelimeAra[]", kw))
        
        if params.page_to_fetch and params.page_to_fetch > 1:
            query_params.append(("page", str(params.page_to_fetch)))
        
        return query_params

    async def search_bireysel_basvuru_report(
        self,
        params: AnayasaBireyselReportSearchRequest
    ) -> AnayasaBireyselReportSearchResult:
        final_query_params = self._build_query_params_for_bireysel_report(params)
        request_url = self.SEARCH_PATH
        
        logger.info(f"AnayasaBireyselBasvuruApiClient: Performing Bireysel Başvuru Report search. Path: {request_url}, Params: {final_query_params}")

        try:
            response = await self.http_client.get(request_url, params=final_query_params)
            response.raise_for_status()
            html_content = response.text
        except httpx.RequestError as e:
            logger.error(f"AnayasaBireyselBasvuruApiClient: HTTP request error during Bireysel Başvuru Report search: {e}")
            raise
        except Exception as e:
            logger.error(f"AnayasaBireyselBasvuruApiClient: Error processing Bireysel Başvuru Report search request: {e}")
            raise

        soup = BeautifulSoup(html_content, 'html.parser')

        total_records = None
        bulunan_karar_div = soup.find("div", class_="bulunankararsayisi")
        if bulunan_karar_div:
            match_records = re.search(r'(\d+)\s*Karar Bulundu', bulunan_karar_div.get_text(strip=True))
            if match_records:
                total_records = int(match_records.group(1))

        processed_decisions: List[AnayasaBireyselReportDecisionSummary] = []
        
        report_content_area = soup.find("div", class_="HaberBulteni") 
        if not report_content_area:
            logger.warning("HaberBulteni div not found, attempting to parse decision divs from the whole page.")
            report_content_area = soup
            
        decision_divs = report_content_area.find_all("div", class_="KararBulteniBirKarar")
        if not decision_divs:
             logger.warning("No KararBulteniBirKarar divs found.")


        for decision_div in decision_divs:
            title_tag = decision_div.find("h4")
            title_text = title_tag.get_text(strip=True) if title_tag and title_tag.strong else (title_tag.get_text(strip=True) if title_tag else "")


            alti_cizili_div = decision_div.find("div", class_="AltiCizili")
            ref_no, dec_type, body, app_date, dec_date, url_path = "", "", "", "", "", ""
            if alti_cizili_div:
                link_tag = alti_cizili_div.find("a", href=True)
                if link_tag:
                    ref_no = link_tag.get_text(strip=True)
                    url_path = link_tag['href']
                
                parts_text = alti_cizili_div.get_text(separator="|", strip=True)
                parts = [part.strip() for part in parts_text.split("|")]
                
                # Clean ref_no from the first part if it was extracted from link
                if ref_no and parts and parts[0].strip().startswith(ref_no):
                    parts[0] = parts[0].replace(ref_no, "").strip()
                    if not parts[0]: parts.pop(0) # Remove empty string if ref_no was the only content
                
                # Assign parts based on typical order, adjusting for missing ref_no at start
                current_idx = 0
                if not ref_no and len(parts) > current_idx and re.match(r"\d+/\d+", parts[current_idx]): # Check if first part is ref_no
                    ref_no = parts[current_idx]
                    current_idx += 1

                dec_type = parts[current_idx] if len(parts) > current_idx else ""
                current_idx += 1
                body = parts[current_idx] if len(parts) > current_idx else ""
                current_idx += 1
                
                app_date_raw = parts[current_idx] if len(parts) > current_idx else ""
                current_idx += 1
                dec_date_raw = parts[current_idx] if len(parts) > current_idx else ""

                if app_date_raw and "Başvuru Tarihi :" in app_date_raw:
                    app_date = app_date_raw.replace("Başvuru Tarihi :", "").strip()
                elif app_date_raw: # If label is missing but format matches
                    app_date_match = re.search(r'(\d{1,2}/\d{1,2}/\d{4})', app_date_raw)
                    if app_date_match: app_date = app_date_match.group(1)


                if dec_date_raw and "Karar Tarihi :" in dec_date_raw:
                    dec_date = dec_date_raw.replace("Karar Tarihi :", "").strip()
                elif dec_date_raw: # If label is missing but format matches
                    dec_date_match = re.search(r'(\d{1,2}/\d{1,2}/\d{4})', dec_date_raw)
                    if dec_date_match: dec_date = dec_date_match.group(1)

            
            subject_div = decision_div.find(lambda tag: tag.name == 'div' and not tag.has_attr('class') and tag.get_text(strip=True).startswith("BAŞVURU KONUSU :"))
            subject_text = subject_div.get_text(strip=True).replace("BAŞVURU KONUSU :", "").strip() if subject_div else ""
            
            details_list: List[AnayasaBireyselReportDecisionDetail] = []
            karar_detaylari_div = decision_div.find_next_sibling("div", id="KararDetaylari") # Corrected: was KararDetaylari
            if karar_detaylari_div:
                table = karar_detaylari_div.find("table", class_="table")
                if table and table.find("tbody"):
                    for row in table.find("tbody").find_all("tr"):
                        cells = row.find_all("td")
                        if len(cells) == 4: # Hak, Müdahale İddiası, Sonuç, Giderim
                            details_list.append(AnayasaBireyselReportDecisionDetail(
                                hak=cells[0].get_text(strip=True) or "",
                                mudahale_iddiasi=cells[1].get_text(strip=True) or "",
                                sonuc=cells[2].get_text(strip=True) or "",
                                giderim=cells[3].get_text(strip=True) or "",
                            ))
            
            full_decision_page_url = urljoin(self.BASE_URL, url_path) if url_path else ""

            processed_decisions.append(AnayasaBireyselReportDecisionSummary(
                title=title_text,
                decision_reference_no=ref_no,
                decision_page_url=full_decision_page_url,
                decision_type_summary=dec_type,
                decision_making_body=body,
                application_date_summary=app_date,
                decision_date_summary=dec_date,
                application_subject_summary=subject_text,
                details=details_list
            ))

        return AnayasaBireyselReportSearchResult(
            decisions=processed_decisions,
            total_records_found=total_records,
            retrieved_page_number=params.page_to_fetch
        )

    def _convert_html_to_markdown_bireysel(self, full_decision_html_content: str) -> Optional[str]:
        if not full_decision_html_content:
            return None
        
        processed_html = html.unescape(full_decision_html_content)
        soup = BeautifulSoup(processed_html, "html.parser")
        html_input_for_markdown = ""

        karar_tab_content = soup.find("div", id="Karar") 
        if karar_tab_content:
            karar_html_span = karar_tab_content.find("span", class_="kararHtml")
            if karar_html_span:
                word_section = karar_html_span.find("div", class_="WordSection1")
                if word_section:
                    for s in word_section.select('script, style, .item.col-xs-12.col-sm-12, center:has(b)'): 
                        s.decompose()
                    html_input_for_markdown = str(word_section)
                else: 
                    logger.warning("AnayasaBireyselBasvuruApiClient: WordSection1 not found in span.kararHtml. Using span.kararHtml content.")
                    for s in karar_html_span.select('script, style, .item.col-xs-12.col-sm-12, center:has(b)'):
                        s.decompose()
                    html_input_for_markdown = str(karar_html_span)
            else: 
                 logger.warning("AnayasaBireyselBasvuruApiClient: span.kararHtml not found in div#Karar. Using div#Karar content.")
                 for s in karar_tab_content.select('script, style, .item.col-xs-12.col-sm-12, center:has(b)'):
                     s.decompose()
                 html_input_for_markdown = str(karar_tab_content)
        else:
            logger.warning("AnayasaBireyselBasvuruApiClient: div#Karar (KARAR tab) not found. Trying WordSection1 fallback.")
            word_section_fallback = soup.find("div", class_="WordSection1") 
            if word_section_fallback:
                for s in word_section_fallback.select('script, style, .item.col-xs-12.col-sm-12, center:has(b)'):
                    s.decompose()
                html_input_for_markdown = str(word_section_fallback)
            else:
                body_tag = soup.find("body")
                if body_tag:
                    for s in body_tag.select('script, style, .item.col-xs-12.col-sm-12, center:has(b), .banner, .footer, .yazdirmaalani, .filtreler, .menu, .altmenu, .geri, .arabuton, .temizlebutonu, form#KararGetir, .TabBaslik, #KararDetaylari, .share-button-container'): 
                        s.decompose()
                    html_input_for_markdown = str(body_tag)
                else:
                    html_input_for_markdown = processed_html
        
        markdown_text = None
        try:
            # Ensure the content is wrapped in basic HTML structure if it's not already
            if not html_input_for_markdown.strip().lower().startswith(("<html", "<!doctype")):
                html_content = f"<html><head><meta charset=\"UTF-8\"></head><body>{html_input_for_markdown}</body></html>"
            else:
                html_content = html_input_for_markdown
            
            # Convert HTML string to bytes and create BytesIO stream
            html_bytes = html_content.encode('utf-8')
            html_stream = io.BytesIO(html_bytes)
            
            # Pass BytesIO stream to MarkItDown to avoid temp file creation
            md_converter = MarkItDown()
            conversion_result = md_converter.convert(html_stream)
            markdown_text = conversion_result.text_content
        except Exception as e:
            logger.error(f"AnayasaBireyselBasvuruApiClient: MarkItDown conversion error: {e}")
        return markdown_text

    async def get_decision_document_as_markdown(
        self,
        document_url_path: str, # e.g. /BB/2021/20295
        page_number: int = 1
    ) -> AnayasaBireyselBasvuruDocumentMarkdown:
        full_url = urljoin(self.BASE_URL, document_url_path)
        logger.info(f"AnayasaBireyselBasvuruApiClient: Fetching Bireysel Başvuru document for Markdown (page {page_number}) from URL: {full_url}")

        basvuru_no_from_page = None
        karar_tarihi_from_page = None
        basvuru_tarihi_from_page = None
        karari_veren_birim_from_page = None
        karar_turu_from_page = None
        resmi_gazete_info_from_page = None

        try:
            response = await self.http_client.get(full_url)
            response.raise_for_status()
            html_content_from_api = response.text

            if not isinstance(html_content_from_api, str) or not html_content_from_api.strip():
                logger.warning(f"AnayasaBireyselBasvuruApiClient: Received empty HTML from {full_url}.")
                return AnayasaBireyselBasvuruDocumentMarkdown(
                    source_url=full_url, markdown_chunk=None, current_page=page_number, total_pages=0, is_paginated=False
                )

            soup = BeautifulSoup(html_content_from_api, 'html.parser')

            meta_desc_tag = soup.find("meta", attrs={"name": "description"})
            if meta_desc_tag and meta_desc_tag.get("content"):
                content = meta_desc_tag["content"]
                bn_match = re.search(r"B\.\s*No:\s*([\d\/]+)", content)
                if bn_match: basvuru_no_from_page = bn_match.group(1).strip()
                
                date_match = re.search(r"(\d{1,2}\/\d{1,2}\/\d{4}),\s*§", content)
                if date_match: karar_tarihi_from_page = date_match.group(1).strip()

            karar_detaylari_tab = soup.find("div", id="KararDetaylari")
            if karar_detaylari_tab:
                table = karar_detaylari_tab.find("table", class_="table")
                if table:
                    rows = table.find_all("tr")
                    for row in rows:
                        cells = row.find_all("td")
                        if len(cells) == 2:
                            key = cells[0].get_text(strip=True)
                            value = cells[1].get_text(strip=True)
                            if "Kararı Veren Birim" in key: karari_veren_birim_from_page = value
                            elif "Karar Türü (Başvuru Sonucu)" in key: karar_turu_from_page = value
                            elif "Başvuru No" in key and not basvuru_no_from_page: basvuru_no_from_page = value
                            elif "Başvuru Tarihi" in key: basvuru_tarihi_from_page = value
                            elif "Karar Tarihi" in key and not karar_tarihi_from_page: karar_tarihi_from_page = value
                            elif "Resmi Gazete Tarih / Sayı" in key: resmi_gazete_info_from_page = value
            
            full_markdown_content = self._convert_html_to_markdown_bireysel(html_content_from_api)

            if not full_markdown_content:
                return AnayasaBireyselBasvuruDocumentMarkdown(
                    source_url=full_url,
                    basvuru_no_from_page=basvuru_no_from_page,
                    karar_tarihi_from_page=karar_tarihi_from_page,
                    basvuru_tarihi_from_page=basvuru_tarihi_from_page,
                    karari_veren_birim_from_page=karari_veren_birim_from_page,
                    karar_turu_from_page=karar_turu_from_page,
                    resmi_gazete_info_from_page=resmi_gazete_info_from_page,
                    markdown_chunk=None,
                    current_page=page_number,
                    total_pages=0,
                    is_paginated=False
                )

            content_length = len(full_markdown_content)
            total_pages = math.ceil(content_length / self.DOCUMENT_MARKDOWN_CHUNK_SIZE)
            if total_pages == 0: total_pages = 1

            current_page_clamped = max(1, min(page_number, total_pages))
            start_index = (current_page_clamped - 1) * self.DOCUMENT_MARKDOWN_CHUNK_SIZE
            end_index = start_index + self.DOCUMENT_MARKDOWN_CHUNK_SIZE
            markdown_chunk = full_markdown_content[start_index:end_index]

            return AnayasaBireyselBasvuruDocumentMarkdown(
                source_url=full_url,
                basvuru_no_from_page=basvuru_no_from_page,
                karar_tarihi_from_page=karar_tarihi_from_page,
                basvuru_tarihi_from_page=basvuru_tarihi_from_page,
                karari_veren_birim_from_page=karari_veren_birim_from_page,
                karar_turu_from_page=karar_turu_from_page,
                resmi_gazete_info_from_page=resmi_gazete_info_from_page,
                markdown_chunk=markdown_chunk,
                current_page=current_page_clamped,
                total_pages=total_pages,
                is_paginated=(total_pages > 1)
            )

        except httpx.RequestError as e:
            logger.error(f"AnayasaBireyselBasvuruApiClient: HTTP error fetching Bireysel Başvuru document from {full_url}: {e}")
            raise
        except Exception as e:
            logger.error(f"AnayasaBireyselBasvuruApiClient: General error processing Bireysel Başvuru document from {full_url}: {e}")
            raise

    async def close_client_session(self):
        if hasattr(self, 'http_client') and self.http_client and not self.http_client.is_closed:
            await self.http_client.aclose()
            logger.info("AnayasaBireyselBasvuruApiClient: HTTP client session closed.")