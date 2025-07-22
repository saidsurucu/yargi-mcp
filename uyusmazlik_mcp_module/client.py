# uyusmazlik_mcp_module/client.py

import httpx 
from bs4 import BeautifulSoup
from typing import Dict, Any, List, Optional, Union, Tuple 
import logging
import html
import re
import io
from markitdown import MarkItDown
from urllib.parse import urljoin

from .models import (
    UyusmazlikSearchRequest,
    UyusmazlikApiDecisionEntry,
    UyusmazlikSearchResponse,
    UyusmazlikDocumentMarkdown,
    UyusmazlikBolumEnum, 
    UyusmazlikTuruEnum,
    UyusmazlikKararSonucuEnum
)

logger = logging.getLogger(__name__)
if not logger.hasHandlers():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# --- Mappings from user-friendly Enum values to API IDs ---
BOLUM_ENUM_TO_ID_MAP = {
    UyusmazlikBolumEnum.CEZA_BOLUMU: "f6b74320-f2d7-4209-ad6e-c6df180d4e7c",
    UyusmazlikBolumEnum.GENEL_KURUL_KARARLARI: "e4ca658d-a75a-4719-b866-b2d2f1c3b1d9",
    UyusmazlikBolumEnum.HUKUK_BOLUMU: "96b26fc4-ef8e-4a4f-a9cc-a3de89952aa1",
    UyusmazlikBolumEnum.TUMU: "", # Represents "...Seçiniz..." or all - empty string for API
    "ALL": "" # Also map the new "ALL" literal to empty string for backward compatibility
}

UYUSMAZLIK_TURU_ENUM_TO_ID_MAP = {
    UyusmazlikTuruEnum.GOREV_UYUSMAZLIGI: "7b1e2cd3-8f09-418a-921c-bbe501e1740c",
    UyusmazlikTuruEnum.HUKUM_UYUSMAZLIGI: "19b88402-172b-4c1d-8339-595c942a89f5",
    UyusmazlikTuruEnum.TUMU: "", # Represents "...Seçiniz..." or all - empty string for API
    "ALL": "" # Also map the new "ALL" literal to empty string for backward compatibility
}

KARAR_SONUCU_ENUM_TO_ID_MAP = {
    # These IDs are from the form HTML provided by the user
    UyusmazlikKararSonucuEnum.HUKUM_UYUSMAZLIGI_OLMADIGINA_DAIR: "6f47d87f-dcb5-412e-9878-000385dba1d9",
    UyusmazlikKararSonucuEnum.HUKUM_UYUSMAZLIGI_OLDUGUNA_DAIR: "5a01742a-c440-4c4a-ba1f-da20837cffed",
    # Add all other 'Karar Sonucu' enum members and their corresponding GUIDs
    # by inspecting the 'KararSonucuList' checkboxes in the provided form HTML.
}
# --- End Mappings ---

class UyusmazlikApiClient:
    BASE_URL = "https://kararlar.uyusmazlik.gov.tr"
    SEARCH_ENDPOINT = "/Arama/Search" 
    # Individual documents are fetched by their full URLs obtained from search results.

    def __init__(self, request_timeout: float = 30.0):
        self.request_timeout = request_timeout
        # Create shared httpx client for all requests
        self.http_client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers={
                "Accept": "*/*",
                "Accept-Encoding": "gzip, deflate, br, zstd", 
                "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
                "X-Requested-With": "XMLHttpRequest",
                "Origin": self.BASE_URL,
                "Referer": self.BASE_URL + "/",
            },
            timeout=request_timeout,
            verify=False
        )


    async def search_decisions(
        self,
        params: UyusmazlikSearchRequest
    ) -> UyusmazlikSearchResponse:
        
        bolum_id_for_api = BOLUM_ENUM_TO_ID_MAP.get(params.bolum, "")
        uyusmazlik_id_for_api = UYUSMAZLIK_TURU_ENUM_TO_ID_MAP.get(params.uyusmazlik_turu, "")
        
        form_data_list: List[Tuple[str, str]] = []

        def add_to_form_data(key: str, value: Optional[str]):
            # API expects empty strings for omitted optional fields based on user payload example
            form_data_list.append((key, value or ""))

        add_to_form_data("BolumId", bolum_id_for_api)
        add_to_form_data("UyusmazlikId", uyusmazlik_id_for_api)
        
        if params.karar_sonuclari:
            for enum_member in params.karar_sonuclari:
                api_id = KARAR_SONUCU_ENUM_TO_ID_MAP.get(enum_member) 
                if api_id: # Only add if a valid ID is found
                    form_data_list.append(('KararSonucuList', api_id))
        
        add_to_form_data("EsasYil", params.esas_yil)
        add_to_form_data("EsasSayisi", params.esas_sayisi)
        add_to_form_data("KararYil", params.karar_yil)
        add_to_form_data("KararSayisi", params.karar_sayisi)
        add_to_form_data("KanunNo", params.kanun_no)
        add_to_form_data("KararDateBegin", params.karar_date_begin)
        add_to_form_data("KararDateEnd", params.karar_date_end)
        add_to_form_data("ResmiGazeteSayi", params.resmi_gazete_sayi)
        add_to_form_data("ResmiGazeteDate", params.resmi_gazete_date)
        add_to_form_data("Icerik", params.icerik)
        add_to_form_data("Tumce", params.tumce)
        add_to_form_data("WildCard", params.wild_card)
        add_to_form_data("Hepsi", params.hepsi)
        add_to_form_data("Herhangibirisi", params.herhangi_birisi)
        add_to_form_data("NotHepsi", params.not_hepsi)

        # Convert form data to dict for httpx
        form_data_dict = {}
        for key, value in form_data_list:
            if key in form_data_dict:
                # Handle multiple values (like KararSonucuList)
                if not isinstance(form_data_dict[key], list):
                    form_data_dict[key] = [form_data_dict[key]]
                form_data_dict[key].append(value)
            else:
                form_data_dict[key] = value

        logger.info(f"UyusmazlikApiClient (httpx): Performing search to {self.SEARCH_ENDPOINT} with form_data: {form_data_dict}")
        
        try:
            # Use shared httpx client
            response = await self.http_client.post(
                self.SEARCH_ENDPOINT,
                data=form_data_dict,
                headers={"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}
            )
            response.raise_for_status()
            html_content = response.text
            logger.debug("UyusmazlikApiClient (httpx): Received HTML response for search.")
        
        except httpx.HTTPError as e:
            logger.error(f"UyusmazlikApiClient (httpx): HTTP client error during search: {e}")
            raise # Re-raise to be handled by the MCP tool
        except Exception as e:
            logger.error(f"UyusmazlikApiClient (httpx): Error processing search request: {e}")
            raise

        # --- HTML Parsing (remains the same as previous version) ---
        soup = BeautifulSoup(html_content, 'html.parser')
        total_records_text_div = soup.find("div", class_="pull-right label label-important")
        total_records = None
        if total_records_text_div:
            match_records = re.search(r'(\d+)\s*adet kayıt bulundu', total_records_text_div.get_text(strip=True))
            if match_records:
                total_records = int(match_records.group(1))
        
        result_table = soup.find("table", class_="table-hover")
        processed_decisions: List[UyusmazlikApiDecisionEntry] = []
        if result_table:
            rows = result_table.find_all("tr")
            if len(rows) > 1: # Skip header row
                for row in rows[1:]:
                    cols = row.find_all('td')
                    if len(cols) >= 5:
                        try:
                            popover_div = cols[0].find("div", attrs={"data-rel": "popover"})
                            popover_content_raw = popover_div["data-content"] if popover_div and popover_div.has_attr("data-content") else None
                            
                            link_tag = cols[0].find('a')
                            doc_relative_url = link_tag['href'] if link_tag and link_tag.has_attr('href') else None
                            
                            if not doc_relative_url: continue
                            document_url_str = urljoin(self.BASE_URL, doc_relative_url)

                            pdf_link_tag = cols[5].find('a', href=re.compile(r'\.pdf$', re.IGNORECASE)) if len(cols) > 5 else None
                            pdf_url_str = urljoin(self.BASE_URL, pdf_link_tag['href']) if pdf_link_tag and pdf_link_tag.has_attr('href') else None

                            decision_data_parsed = {
                                "karar_sayisi": cols[0].get_text(strip=True),
                                "esas_sayisi": cols[1].get_text(strip=True),
                                "bolum": cols[2].get_text(strip=True),
                                "uyusmazlik_konusu": cols[3].get_text(strip=True),
                                "karar_sonucu": cols[4].get_text(strip=True),
                                "popover_content": html.unescape(popover_content_raw) if popover_content_raw else None,
                                "document_url": document_url_str,
                                "pdf_url": pdf_url_str
                            }
                            decision_model = UyusmazlikApiDecisionEntry(**decision_data_parsed)
                            processed_decisions.append(decision_model)
                        except Exception as e:
                            logger.warning(f"UyusmazlikApiClient: Could not parse decision row. Row content: {row.get_text(strip=True, separator=' | ')}, Error: {e}")
        
        return UyusmazlikSearchResponse(
            decisions=processed_decisions,
            total_records_found=total_records
        )

    def _convert_html_to_markdown_uyusmazlik(self, full_decision_html_content: str) -> Optional[str]:
        """Converts direct HTML content (from an Uyuşmazlık decision page) to Markdown."""
        if not full_decision_html_content: 
            return None
        
        processed_html = html.unescape(full_decision_html_content)
        # As per user request, pass the full (unescaped) HTML to MarkItDown
        html_input_for_markdown = processed_html

        markdown_text = None
        try:
            # Convert HTML string to bytes and create BytesIO stream
            html_bytes = html_input_for_markdown.encode('utf-8')
            html_stream = io.BytesIO(html_bytes)
            
            # Pass BytesIO stream to MarkItDown to avoid temp file creation
            md_converter = MarkItDown()
            conversion_result = md_converter.convert(html_stream)
            markdown_text = conversion_result.text_content
            logger.info("UyusmazlikApiClient: HTML to Markdown conversion successful.")
        except Exception as e:
            logger.error(f"UyusmazlikApiClient: Error during MarkItDown HTML to Markdown conversion: {e}")
        return markdown_text

    async def get_decision_document_as_markdown(self, document_url: str) -> UyusmazlikDocumentMarkdown:
        """
        Retrieves a specific Uyuşmazlık decision from its full URL and returns content as Markdown.
        """
        logger.info(f"UyusmazlikApiClient (httpx for docs): Fetching Uyuşmazlık document for Markdown from URL: {document_url}")
        try:
            # Using a new httpx.AsyncClient instance for this GET request for simplicity
            async with httpx.AsyncClient(verify=False, timeout=self.request_timeout) as doc_fetch_client:
                 get_response = await doc_fetch_client.get(document_url, headers={"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"})
            get_response.raise_for_status()
            html_content_from_api = get_response.text

            if not isinstance(html_content_from_api, str) or not html_content_from_api.strip():
                logger.warning(f"UyusmazlikApiClient: Received empty or non-string HTML from URL {document_url}.")
                return UyusmazlikDocumentMarkdown(source_url=document_url, markdown_content=None)

            markdown_content = self._convert_html_to_markdown_uyusmazlik(html_content_from_api)
            return UyusmazlikDocumentMarkdown(source_url=document_url, markdown_content=markdown_content)
        except httpx.RequestError as e:
            logger.error(f"UyusmazlikApiClient (httpx for docs): HTTP error fetching Uyuşmazlık document from {document_url}: {e}")
            raise
        except Exception as e:
            logger.error(f"UyusmazlikApiClient (httpx for docs): General error processing Uyuşmazlık document from {document_url}: {e}")
            raise

    async def close_client_session(self):
        """Close the shared httpx client session."""
        if hasattr(self, 'http_client') and self.http_client:
            await self.http_client.aclose()
            logger.info("UyusmazlikApiClient: HTTP client session closed.")
        else:
            logger.info("UyusmazlikApiClient: No persistent client session from __init__ to close.")