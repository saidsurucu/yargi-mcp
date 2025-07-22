# rekabet_mcp_module/client.py

import httpx
from bs4 import BeautifulSoup
from typing import List, Optional, Tuple, Dict, Any
import logging
import html
import re
import io # For io.BytesIO
from urllib.parse import urlencode, urljoin, quote, parse_qs, urlparse
from markitdown import MarkItDown
import math

# pypdf for PDF processing (lighter alternative to PyMuPDF)
from pypdf import PdfReader, PdfWriter # PyPDF2'nin devamı niteliğindeki pypdf

from .models import (
    RekabetKurumuSearchRequest,
    RekabetDecisionSummary,
    RekabetSearchResult,
    RekabetDocument,
    RekabetKararTuruGuidEnum
)
from pydantic import HttpUrl # Ensure HttpUrl is imported from pydantic

logger = logging.getLogger(__name__)
if not logger.hasHandlers(): # Pragma: no cover
    logging.basicConfig(
        level=logging.INFO,  # Varsayılan log seviyesi
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    # Debug betiğinde daha detaylı loglama için seviye ayrıca ayarlanabilir.

class RekabetKurumuApiClient:
    BASE_URL = "https://www.rekabet.gov.tr"
    SEARCH_PATH = "/tr/Kararlar"
    DECISION_LANDING_PATH_TEMPLATE = "/Karar"
    # PDF sayfa bazlı Markdown döndürüldüğü için bu sabit artık doğrudan kullanılmıyor.
    # DOCUMENT_MARKDOWN_CHUNK_SIZE = 5000 

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

    def _build_search_query_params(self, params: RekabetKurumuSearchRequest) -> List[Tuple[str, str]]:
        query_params: List[Tuple[str, str]] = []
        query_params.append(("sayfaAdi", params.sayfaAdi if params.sayfaAdi is not None else ""))
        query_params.append(("YayinlanmaTarihi", params.YayinlanmaTarihi if params.YayinlanmaTarihi is not None else ""))
        query_params.append(("PdfText", params.PdfText if params.PdfText is not None else ""))
        
        karar_turu_id_value = ""
        if params.KararTuruID is not None: 
            karar_turu_id_value = params.KararTuruID.value if params.KararTuruID.value != "ALL" else "" 
        query_params.append(("KararTuruID", karar_turu_id_value))
            
        query_params.append(("KararSayisi", params.KararSayisi if params.KararSayisi is not None else ""))
        query_params.append(("KararTarihi", params.KararTarihi if params.KararTarihi is not None else ""))
        
        if params.page and params.page > 1:
            query_params.append(("page", str(params.page)))
            
        return query_params

    async def search_decisions(self, params: RekabetKurumuSearchRequest) -> RekabetSearchResult:
        request_path = self.SEARCH_PATH
        final_query_params = self._build_search_query_params(params)
        logger.info(f"RekabetKurumuApiClient: Performing search. Path: {request_path}, Parameters: {final_query_params}")
        
        try:
            response = await self.http_client.get(request_path, params=final_query_params)
            response.raise_for_status()
            html_content = response.text
        except httpx.RequestError as e:
            logger.error(f"RekabetKurumuApiClient: HTTP request error during search: {e}")
            raise
        
        soup = BeautifulSoup(html_content, 'html.parser')
        processed_decisions: List[RekabetDecisionSummary] = []
        total_records: Optional[int] = None
        total_pages: Optional[int] = None
        
        pagination_div = soup.find("div", class_="yazi01")
        if pagination_div:
            text_content = pagination_div.get_text(separator=" ", strip=True)
            total_match = re.search(r"Toplam\s*:\s*(\d+)", text_content)
            if total_match:
                try:
                    total_records = int(total_match.group(1))
                    logger.debug(f"Total records found from pagination: {total_records}")
                except ValueError:
                    logger.warning(f"Could not convert 'Toplam' value to int: {total_match.group(1)}")
            else:
                logger.warning("'Toplam :' string not found in pagination section.")
            
            results_per_page_assumed = 10 
            if total_records is not None:
                calculated_total_pages = math.ceil(total_records / results_per_page_assumed)
                total_pages = calculated_total_pages if calculated_total_pages > 0 else (1 if total_records > 0 else 0)
                logger.debug(f"Calculated total pages: {total_pages}")
            
            if total_pages is None: # Fallback if total_records couldn't be parsed
                last_page_link = pagination_div.select_one("li.PagedList-skipToLast a")
                if last_page_link and last_page_link.has_attr('href'):
                    qs = parse_qs(urlparse(last_page_link['href']).query)
                    if 'page' in qs and qs['page']:
                        try:
                            total_pages = int(qs['page'][0])
                            logger.debug(f"Total pages found from 'Last >>' link: {total_pages}")
                        except ValueError:
                            logger.warning(f"Could not convert page value from 'Last >>' link to int: {qs['page'][0]}")
                elif total_records == 0 : total_pages = 0 # If no records, 0 pages
                elif total_records is not None and total_records > 0 : total_pages = 1 # If records exist but no last page link (e.g. single page)
                else: logger.warning("'Last >>' link not found in pagination section.")
        
        decision_tables_container = soup.find("div", id="kararList")
        if not decision_tables_container:
            logger.warning("`div#kararList` (decision list container) not found. HTML structure might have changed or no decisions on this page.")
        else:
            decision_tables = decision_tables_container.find_all("table", class_="equalDivide")
            logger.info(f"Found {len(decision_tables)} 'table' elements with class='equalDivide' for parsing.")
            
            if not decision_tables and total_records is not None and total_records > 0 :
                 logger.warning(f"Page indicates {total_records} records but no decision tables found with class='equalDivide'.")

            for idx, table in enumerate(decision_tables):
                logger.debug(f"Processing table {idx + 1}...")
                try:
                    rows = table.find_all("tr")
                    if len(rows) != 3: 
                        logger.warning(f"Table {idx + 1} has an unexpected number of rows ({len(rows)} instead of 3). Skipping. HTML snippet:\n{table.prettify()[:500]}")
                        continue

                    # Row 1: Publication Date, Decision Number, Related Cases Link
                    td_elements_r1 = rows[0].find_all("td")
                    pub_date = td_elements_r1[0].get_text(strip=True) if len(td_elements_r1) > 0 else None
                    dec_num = td_elements_r1[1].get_text(strip=True) if len(td_elements_r1) > 1 else None
                    
                    related_cases_link_tag = td_elements_r1[2].find("a", href=True) if len(td_elements_r1) > 2 else None
                    related_cases_url_str: Optional[str] = None
                    karar_id_from_related: Optional[str] = None
                    if related_cases_link_tag and related_cases_link_tag.has_attr('href'):
                        related_cases_url_str = urljoin(self.BASE_URL, related_cases_link_tag['href'])
                        qs_related = parse_qs(urlparse(related_cases_link_tag['href']).query)
                        if 'kararId' in qs_related and qs_related['kararId']:
                            karar_id_from_related = qs_related['kararId'][0]
                    
                    # Row 2: Decision Date, Decision Type
                    td_elements_r2 = rows[1].find_all("td")
                    dec_date = td_elements_r2[0].get_text(strip=True) if len(td_elements_r2) > 0 else None
                    dec_type_text = td_elements_r2[1].get_text(strip=True) if len(td_elements_r2) > 1 else None

                    # Row 3: Title and Main Decision Link
                    title_cell = rows[2].find("td", colspan="5")
                    decision_link_tag = title_cell.find("a", href=True) if title_cell else None
                    
                    title_text: Optional[str] = None
                    decision_landing_url_str: Optional[str] = None 
                    karar_id_from_main_link: Optional[str] = None

                    if decision_link_tag and decision_link_tag.has_attr('href'):
                        title_text = decision_link_tag.get_text(strip=True)
                        href_val = decision_link_tag['href']
                        if href_val.startswith(self.DECISION_LANDING_PATH_TEMPLATE + "?kararId="): # Ensure it's a decision link
                            decision_landing_url_str = urljoin(self.BASE_URL, href_val)
                            qs_main = parse_qs(urlparse(href_val).query)
                            if 'kararId' in qs_main and qs_main['kararId']:
                                karar_id_from_main_link = qs_main['kararId'][0]
                        else:
                            logger.warning(f"Table {idx+1} decision link has unexpected format: {href_val}")
                    else:
                        logger.warning(f"Table {idx+1} could not find title/decision link tag.")
                    
                    current_karar_id = karar_id_from_main_link or karar_id_from_related

                    if not current_karar_id: 
                        logger.warning(f"Table {idx+1} Karar ID not found. Skipping. Title (if any): {title_text}")
                        continue
                    
                    # Convert string URLs to HttpUrl for the model
                    final_decision_url = HttpUrl(decision_landing_url_str) if decision_landing_url_str else None
                    final_related_cases_url = HttpUrl(related_cases_url_str) if related_cases_url_str else None

                    processed_decisions.append(RekabetDecisionSummary(
                        publication_date=pub_date, decision_number=dec_num, decision_date=dec_date,
                        decision_type_text=dec_type_text, title=title_text, 
                        decision_url=final_decision_url, 
                        karar_id=current_karar_id, 
                        related_cases_url=final_related_cases_url
                    ))
                    logger.debug(f"Table {idx+1} parsed successfully: Karar ID '{current_karar_id}', Title '{title_text[:50] if title_text else 'N/A'}...'")

                except Exception as e:
                    logger.warning(f"RekabetKurumuApiClient: Error parsing decision summary {idx+1}: {e}. Problematic Table HTML:\n{table.prettify()}", exc_info=True)
                    continue
        
        return RekabetSearchResult(
            decisions=processed_decisions, total_records_found=total_records, 
            retrieved_page_number=params.page, total_pages=total_pages if total_pages is not None else 0
        )

    async def _extract_pdf_url_and_landing_page_metadata(self, karar_id: str, landing_page_html: str, landing_page_url: str) -> Dict[str, Any]:
        soup = BeautifulSoup(landing_page_html, 'html.parser')
        data: Dict[str, Any] = {
            "pdf_url": None,
            "title_on_landing_page": soup.title.string.strip() if soup.title and soup.title.string else f"Rekabet Kurumu Kararı {karar_id}",
        }
        # This part needs to be robust and specific to Rekabet Kurumu's landing page structure.
        # Look for common patterns: direct links, download buttons, embedded viewers.
        pdf_anchor = soup.find("a", href=re.compile(r"\.pdf(\?|$)", re.IGNORECASE)) # Basic PDF link
        if not pdf_anchor: # Try other common patterns if the basic one fails
            # Example: Look for links with specific text or class
            pdf_anchor = soup.find("a", string=re.compile(r"karar metni|pdf indir", re.IGNORECASE))
        
        if pdf_anchor and pdf_anchor.has_attr('href'):
            pdf_path = pdf_anchor['href']
            data["pdf_url"] = urljoin(landing_page_url, pdf_path)
            logger.info(f"PDF link found on landing page (<a>): {data['pdf_url']}")
        else:
            iframe_pdf = soup.find("iframe", src=re.compile(r"\.pdf(\?|$)", re.IGNORECASE))
            if iframe_pdf and iframe_pdf.has_attr('src'):
                pdf_path = iframe_pdf['src']
                data["pdf_url"] = urljoin(landing_page_url, pdf_path)
                logger.info(f"PDF link found on landing page (<iframe>): {data['pdf_url']}")
            else:
                embed_pdf = soup.find("embed", src=re.compile(r"\.pdf(\?|$)", re.IGNORECASE), type="application/pdf")
                if embed_pdf and embed_pdf.has_attr('src'):
                    pdf_path = embed_pdf['src']
                    data["pdf_url"] = urljoin(landing_page_url, pdf_path)
                    logger.info(f"PDF link found on landing page (<embed>): {data['pdf_url']}")
                else:
                    logger.warning(f"No PDF link found on landing page {landing_page_url} for kararId {karar_id} using common selectors.")
        return data

    async def _download_pdf_bytes(self, pdf_url: str) -> Optional[bytes]:
        try:
            url_to_fetch = pdf_url if pdf_url.startswith(('http://', 'https://')) else urljoin(self.BASE_URL, pdf_url)
            logger.info(f"Downloading PDF from: {url_to_fetch}")
            response = await self.http_client.get(url_to_fetch)
            response.raise_for_status()
            pdf_bytes = await response.aread()
            logger.info(f"PDF content downloaded ({len(pdf_bytes)} bytes) from: {url_to_fetch}")
            return pdf_bytes
        except httpx.RequestError as e:
            logger.error(f"HTTP error downloading PDF from {pdf_url}: {e}")
        except Exception as e:
            logger.error(f"General error downloading PDF from {pdf_url}: {e}")
        return None

    def _extract_single_pdf_page_as_pdf_bytes(self, original_pdf_bytes: bytes, page_number_to_extract: int) -> Tuple[Optional[bytes], int]:
        total_pages_in_original_pdf = 0
        single_page_pdf_bytes: Optional[bytes] = None
        
        if not original_pdf_bytes:
            logger.warning("No original PDF bytes provided for page extraction.")
            return None, 0

        try:
            pdf_stream = io.BytesIO(original_pdf_bytes)
            reader = PdfReader(pdf_stream)
            total_pages_in_original_pdf = len(reader.pages)
            
            if not (0 < page_number_to_extract <= total_pages_in_original_pdf):
                logger.warning(f"Requested page number ({page_number_to_extract}) is out of PDF page range (1-{total_pages_in_original_pdf}).")
                return None, total_pages_in_original_pdf

            writer = PdfWriter()
            writer.add_page(reader.pages[page_number_to_extract - 1]) # pypdf is 0-indexed
            
            output_pdf_stream = io.BytesIO()
            writer.write(output_pdf_stream)
            single_page_pdf_bytes = output_pdf_stream.getvalue()
            
            logger.debug(f"Page {page_number_to_extract} of original PDF (total {total_pages_in_original_pdf} pages) extracted as new PDF using pypdf.")
            
        except Exception as e:
            logger.error(f"Error extracting PDF page using pypdf: {e}", exc_info=True)
            return None, total_pages_in_original_pdf 
        return single_page_pdf_bytes, total_pages_in_original_pdf

    def _convert_pdf_bytes_to_markdown(self, pdf_bytes: bytes, source_url_for_logging: str) -> Optional[str]:
        if not pdf_bytes:
            logger.warning(f"No PDF bytes provided for Markdown conversion (source: {source_url_for_logging}).")
            return None
        
        pdf_stream = io.BytesIO(pdf_bytes)
        try:
            md_converter = MarkItDown(enable_plugins=False) 
            conversion_result = md_converter.convert(pdf_stream) 
            markdown_text = conversion_result.text_content
            
            if not markdown_text:
                 logger.warning(f"MarkItDown returned empty content from PDF byte stream (source: {source_url_for_logging}). PDF page might be image-based or MarkItDown could not process the PDF stream.")
            return markdown_text
        except Exception as e:
            logger.error(f"MarkItDown conversion error for PDF byte stream (source: {source_url_for_logging}): {e}", exc_info=True)
            return None

    async def get_decision_document(self, karar_id: str, page_number: int = 1) -> RekabetDocument:
        if not karar_id:
             return RekabetDocument(
                source_landing_page_url=HttpUrl(f"{self.BASE_URL}"), 
                karar_id=karar_id or "UNKNOWN_KARAR_ID",
                error_message="karar_id is required.",
                current_page=1, total_pages=0, is_paginated=False )

        decision_url_path = f"{self.DECISION_LANDING_PATH_TEMPLATE}?kararId={karar_id}"
        full_landing_page_url = urljoin(self.BASE_URL, decision_url_path)
        
        logger.info(f"RekabetKurumuApiClient: Getting decision document: {full_landing_page_url}, Requested PDF Page: {page_number}")

        pdf_url_to_report: Optional[HttpUrl] = None
        title_to_report: Optional[str] = f"Rekabet Kurumu Kararı {karar_id}" # Default
        error_message: Optional[str] = None
        markdown_for_requested_page: Optional[str] = None
        total_pdf_pages: int = 0
        
        try:
            async with self.http_client.stream("GET", full_landing_page_url) as response:
                response.raise_for_status()
                content_type = response.headers.get("content-type", "").lower()
                final_url_of_response = HttpUrl(str(response.url))
                original_pdf_bytes: Optional[bytes] = None

                if "application/pdf" in content_type:
                    logger.info(f"URL {final_url_of_response} is a direct PDF. Processing content.")
                    pdf_url_to_report = final_url_of_response
                    original_pdf_bytes = await response.aread()
                elif "text/html" in content_type:
                    logger.info(f"URL {final_url_of_response} is an HTML landing page. Looking for PDF link.")
                    landing_page_html_bytes = await response.aread()
                    detected_charset = response.charset_encoding or 'utf-8'
                    try: landing_page_html = landing_page_html_bytes.decode(detected_charset)
                    except UnicodeDecodeError: landing_page_html = landing_page_html_bytes.decode('utf-8', errors='replace')

                    if landing_page_html.strip():
                        landing_page_data = self._extract_pdf_url_and_landing_page_metadata(karar_id, landing_page_html, str(final_url_of_response))
                        pdf_url_str_from_html = landing_page_data.get("pdf_url")
                        if landing_page_data.get("title_on_landing_page"): title_to_report = landing_page_data.get("title_on_landing_page")
                        if pdf_url_str_from_html:
                            pdf_url_to_report = HttpUrl(pdf_url_str_from_html)
                            original_pdf_bytes = await self._download_pdf_bytes(str(pdf_url_to_report))
                        else: error_message = (error_message or "") + " PDF URL not found on HTML landing page."
                    else: error_message = "Decision landing page content is empty."
                else: error_message = f"Unexpected content type ({content_type}) for URL: {final_url_of_response}"

                if original_pdf_bytes:
                    single_page_pdf_bytes, total_pdf_pages_from_extraction = self._extract_single_pdf_page_as_pdf_bytes(original_pdf_bytes, page_number)
                    total_pdf_pages = total_pdf_pages_from_extraction 

                    if single_page_pdf_bytes:
                        markdown_for_requested_page = self._convert_pdf_bytes_to_markdown(single_page_pdf_bytes, str(pdf_url_to_report or full_landing_page_url))
                        if not markdown_for_requested_page:
                            error_message = (error_message or "") + f"; Could not convert page {page_number} of PDF to Markdown."
                    elif total_pdf_pages > 0 : 
                        error_message = (error_message or "") + f"; Could not extract page {page_number} from PDF (page may be out of range or extraction failed)."
                    else: 
                         error_message = (error_message or "") + "; PDF could not be processed or page count was zero (original PDF might be invalid)."
                elif not error_message: 
                    error_message = "PDF content could not be downloaded or identified."
            
            is_paginated = total_pdf_pages > 1
            current_page_final = page_number
            if total_pdf_pages > 0: 
                current_page_final = max(1, min(page_number, total_pdf_pages))
            elif markdown_for_requested_page is None: 
                current_page_final = 1 
            
            # If markdown is None but there was no specific error for markdown conversion (e.g. PDF not found first)
            # make sure error_message reflects that.
            if markdown_for_requested_page is None and pdf_url_to_report and not error_message:
                 error_message = (error_message or "") + "; Failed to produce Markdown from PDF page."


            return RekabetDocument(
                source_landing_page_url=full_landing_page_url, karar_id=karar_id,
                title_on_landing_page=title_to_report, pdf_url=pdf_url_to_report,
                markdown_chunk=markdown_for_requested_page, current_page=current_page_final,
                total_pages=total_pdf_pages, is_paginated=is_paginated,
                error_message=error_message.strip("; ") if error_message else None )

        except httpx.HTTPStatusError as e: error_msg_detail = f"HTTP Status error {e.response.status_code} while processing decision page."
        except httpx.RequestError as e: error_msg_detail = f"HTTP Request error while processing decision page: {str(e)}"
        except Exception as e: error_msg_detail = f"General error while processing decision: {str(e)}"
        
        exc_info_flag = not isinstance(e, (httpx.HTTPStatusError, httpx.RequestError)) if 'e' in locals() else True
        logger.error(f"RekabetKurumuApiClient: Error processing decision {karar_id} from {full_landing_page_url}: {error_msg_detail}", exc_info=exc_info_flag)
        error_message = (error_message + "; " if error_message else "") + error_msg_detail
        
        return RekabetDocument(
            source_landing_page_url=full_landing_page_url, karar_id=karar_id,
            title_on_landing_page=title_to_report, pdf_url=pdf_url_to_report,
            markdown_chunk=None, current_page=page_number, total_pages=0, is_paginated=False,
            error_message=error_message.strip("; ") if error_message else "An unexpected error occurred." )

    async def close_client_session(self): # Pragma: no cover
        if hasattr(self, 'http_client') and self.http_client and not self.http_client.is_closed:
            await self.http_client.aclose()
            logger.info("RekabetKurumuApiClient: HTTP client session closed.")