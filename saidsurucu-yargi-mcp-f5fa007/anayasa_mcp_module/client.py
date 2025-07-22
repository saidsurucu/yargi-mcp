# anayasa_mcp_module/client.py
# This client is for Norm Denetimi: https://normkararlarbilgibankasi.anayasa.gov.tr

import httpx
from bs4 import BeautifulSoup
from typing import Dict, Any, List, Optional, Tuple
import logging
import html
import re
import io
from urllib.parse import urlencode, urljoin, quote
from markitdown import MarkItDown
import math # For math.ceil for pagination

from .models import (
    AnayasaNormDenetimiSearchRequest,
    AnayasaDecisionSummary,
    AnayasaReviewedNormInfo,
    AnayasaSearchResult,
    AnayasaDocumentMarkdown, # Model for Norm Denetimi document
)

logger = logging.getLogger(__name__)
if not logger.hasHandlers():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

class AnayasaMahkemesiApiClient:
    BASE_URL = "https://normkararlarbilgibankasi.anayasa.gov.tr"
    SEARCH_PATH_SEGMENT = "Ara"
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

    def _build_search_query_params_for_aym(self, params: AnayasaNormDenetimiSearchRequest) -> List[Tuple[str, str]]:
        query_params: List[Tuple[str, str]] = []
        if params.keywords_all:
            for kw in params.keywords_all: query_params.append(("KelimeAra[]", kw))
        if params.keywords_any:
            for kw in params.keywords_any: query_params.append(("HerhangiBirKelimeAra[]", kw))
        if params.keywords_exclude:
            for kw in params.keywords_exclude: query_params.append(("BulunmayanKelimeAra[]", kw))
        if params.period and params.period and params.period != "ALL": query_params.append(("Donemler_id", params.period))
        if params.case_number_esas: query_params.append(("EsasNo", params.case_number_esas))
        if params.decision_number_karar: query_params.append(("KararNo", params.decision_number_karar))
        if params.first_review_date_start: query_params.append(("IlkIncelemeTarihiIlk", params.first_review_date_start))
        if params.first_review_date_end: query_params.append(("IlkIncelemeTarihiSon", params.first_review_date_end))
        if params.decision_date_start: query_params.append(("KararTarihiIlk", params.decision_date_start))
        if params.decision_date_end: query_params.append(("KararTarihiSon", params.decision_date_end))
        if params.application_type and params.application_type and params.application_type != "ALL": query_params.append(("BasvuruTurler_id", params.application_type))
        if params.applicant_general_name: query_params.append(("BasvuranGeneller_id", params.applicant_general_name))
        if params.applicant_specific_name: query_params.append(("BasvuranOzeller_id", params.applicant_specific_name))
        if params.attending_members_names:
            for name in params.attending_members_names: query_params.append(("Uyeler_id[]", name))
        if params.rapporteur_name: query_params.append(("Raportorler_id", params.rapporteur_name))
        if params.norm_type and params.norm_type and params.norm_type != "ALL": query_params.append(("NormunTurler_id", params.norm_type))
        if params.norm_id_or_name: query_params.append(("NormunNumarasiAdlar_id", params.norm_id_or_name))
        if params.norm_article: query_params.append(("NormunMaddeNumarasi", params.norm_article))
        if params.review_outcomes:
            for outcome_val in params.review_outcomes:
                if outcome_val and outcome_val != "ALL": query_params.append(("IncelemeTuruKararSonuclar_id[]", outcome_val))
        if params.reason_for_final_outcome and params.reason_for_final_outcome and params.reason_for_final_outcome != "ALL":
            query_params.append(("KararSonucununGerekcesi", params.reason_for_final_outcome))
        if params.basis_constitution_article_numbers:
            for article_no in params.basis_constitution_article_numbers: query_params.append(("DayanakHukmu[]", article_no))
        if params.official_gazette_date_start: query_params.append(("ResmiGazeteTarihiIlk", params.official_gazette_date_start))
        if params.official_gazette_date_end: query_params.append(("ResmiGazeteTarihiSon", params.official_gazette_date_end))
        if params.official_gazette_number_start: query_params.append(("ResmiGazeteSayisiIlk", params.official_gazette_number_start))
        if params.official_gazette_number_end: query_params.append(("ResmiGazeteSayisiSon", params.official_gazette_number_end))
        if params.has_press_release and params.has_press_release and params.has_press_release != "ALL": query_params.append(("BasinDuyurusu", params.has_press_release))
        if params.has_dissenting_opinion and params.has_dissenting_opinion and params.has_dissenting_opinion != "ALL": query_params.append(("KarsiOy", params.has_dissenting_opinion))
        if params.has_different_reasoning and params.has_different_reasoning and params.has_different_reasoning != "ALL": query_params.append(("FarkliGerekce", params.has_different_reasoning))
        
        # Add pagination and sorting parameters as query params instead of URL path
        if params.results_per_page and params.results_per_page != 10:
            query_params.append(("SatirSayisi", str(params.results_per_page)))
            
        if params.sort_by_criteria and params.sort_by_criteria != "KararTarihi":
            query_params.append(("Siralama", params.sort_by_criteria))
            
        if params.page_to_fetch and params.page_to_fetch > 1:
            query_params.append(("page", str(params.page_to_fetch)))
        return query_params

    async def search_norm_denetimi_decisions(
        self,
        params: AnayasaNormDenetimiSearchRequest
    ) -> AnayasaSearchResult:
        # Use simple /Ara endpoint - the complex path structure seems to cause 404s
        request_path = f"/{self.SEARCH_PATH_SEGMENT}"
        
        final_query_params = self._build_search_query_params_for_aym(params)
        logger.info(f"AnayasaMahkemesiApiClient: Performing Norm Denetimi search. Path: {request_path}, Params: {final_query_params}")

        try:
            response = await self.http_client.get(request_path, params=final_query_params)
            response.raise_for_status()
            html_content = response.text
        except httpx.RequestError as e:
            logger.error(f"AnayasaMahkemesiApiClient: HTTP request error during Norm Denetimi search: {e}")
            raise
        except Exception as e:
            logger.error(f"AnayasaMahkemesiApiClient: Error processing Norm Denetimi search request: {e}")
            raise

        soup = BeautifulSoup(html_content, 'html.parser')

        total_records = None
        bulunan_karar_div = soup.find("div", class_="bulunankararsayisi")
        if not bulunan_karar_div: # Fallback for mobile view
            bulunan_karar_div = soup.find("div", class_="bulunankararsayisiMobil")

        if bulunan_karar_div:
            match_records = re.search(r'(\d+)\s*Karar Bulundu', bulunan_karar_div.get_text(strip=True))
            if match_records:
                total_records = int(match_records.group(1))

        processed_decisions: List[AnayasaDecisionSummary] = []
        decision_divs = soup.find_all("div", class_="birkarar")

        for decision_div in decision_divs:
            link_tag = decision_div.find("a", href=True)
            doc_url_path = link_tag['href'] if link_tag else None
            decision_page_url_str = urljoin(self.BASE_URL, doc_url_path) if doc_url_path else None

            title_div = decision_div.find("div", class_="bkararbaslik")
            ek_no_text_raw = title_div.get_text(strip=True, separator=" ").replace('\xa0', ' ') if title_div else ""
            ek_no_match = re.search(r"(E\.\s*\d+/\d+\s*,\s*K\.\s*\d+/\d+)", ek_no_text_raw)
            ek_no_text = ek_no_match.group(1) if ek_no_match else ek_no_text_raw.split("Sayılı Karar")[0].strip()

            keyword_count_div = title_div.find("div", class_="BulunanKelimeSayisi") if title_div else None
            keyword_count_text = keyword_count_div.get_text(strip=True).replace("Bulunan Kelime Sayısı", "").strip() if keyword_count_div else None
            keyword_count = int(keyword_count_text) if keyword_count_text and keyword_count_text.isdigit() else None

            info_div = decision_div.find("div", class_="kararbilgileri")
            info_parts = [part.strip() for part in info_div.get_text(separator="|").split("|")] if info_div else []
            
            app_type_summary = info_parts[0] if len(info_parts) > 0 else None
            applicant_summary = info_parts[1] if len(info_parts) > 1 else None
            outcome_summary = info_parts[2] if len(info_parts) > 2 else None
            dec_date_raw = info_parts[3] if len(info_parts) > 3 else None
            decision_date_summary = dec_date_raw.replace("Karar Tarihi:", "").strip() if dec_date_raw else None

            reviewed_norms_list: List[AnayasaReviewedNormInfo] = []
            details_table_container = decision_div.find_next_sibling("div", class_=re.compile(r"col-sm-12")) # The details table is in a sibling div
            if details_table_container:
                details_table = details_table_container.find("table", class_="table")
                if details_table and details_table.find("tbody"):
                    for row in details_table.find("tbody").find_all("tr"):
                        cells = row.find_all("td")
                        if len(cells) == 6:
                            reviewed_norms_list.append(AnayasaReviewedNormInfo(
                                norm_name_or_number=cells[0].get_text(strip=True) or None,
                                article_number=cells[1].get_text(strip=True) or None,
                                review_type_and_outcome=cells[2].get_text(strip=True) or None,
                                outcome_reason=cells[3].get_text(strip=True) or None,
                                basis_constitution_articles_cited=[a.strip() for a in cells[4].get_text(strip=True).split(',') if a.strip()] if cells[4].get_text(strip=True) else [],
                                postponement_period=cells[5].get_text(strip=True) or None
                            ))
            
            processed_decisions.append(AnayasaDecisionSummary(
                decision_reference_no=ek_no_text,
                decision_page_url=decision_page_url_str,
                keywords_found_count=keyword_count,
                application_type_summary=app_type_summary,
                applicant_summary=applicant_summary,
                decision_outcome_summary=outcome_summary,
                decision_date_summary=decision_date_summary,
                reviewed_norms=reviewed_norms_list
            ))

        return AnayasaSearchResult(
            decisions=processed_decisions,
            total_records_found=total_records,
            retrieved_page_number=params.page_to_fetch
        )

    def _convert_html_to_markdown_norm_denetimi(self, full_decision_html_content: str) -> Optional[str]:
        """Converts direct HTML content from an Anayasa Mahkemesi Norm Denetimi decision page to Markdown."""
        if not full_decision_html_content:
            return None

        processed_html = html.unescape(full_decision_html_content)
        soup = BeautifulSoup(processed_html, "html.parser")
        html_input_for_markdown = ""

        karar_tab_content = soup.find("div", id="Karar") # "KARAR" tab content
        if karar_tab_content:
            karar_metni_div = karar_tab_content.find("div", class_="KararMetni")
            if karar_metni_div:
                # Remove scripts and styles
                for script_tag in karar_metni_div.find_all("script"): script_tag.decompose()
                for style_tag in karar_metni_div.find_all("style"): style_tag.decompose()
                # Remove "Künye Kopyala" button and other non-content divs
                for item_div in karar_metni_div.find_all("div", class_="item col-sm-12"): item_div.decompose()
                for modal_div in karar_metni_div.find_all("div", class_="modal fade"): modal_div.decompose() # If any modals
                
                word_section = karar_metni_div.find("div", class_="WordSection1")
                html_input_for_markdown = str(word_section) if word_section else str(karar_metni_div)
            else:
                html_input_for_markdown = str(karar_tab_content)
        else:
            # Fallback if specific structure is not found
            word_section_fallback = soup.find("div", class_="WordSection1")
            if word_section_fallback:
                html_input_for_markdown = str(word_section_fallback)
            else:
                # Last resort: use the whole body or the raw HTML
                body_tag = soup.find("body")
                html_input_for_markdown = str(body_tag) if body_tag else processed_html
        
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
            logger.error(f"AnayasaMahkemesiApiClient: MarkItDown conversion error: {e}")
        return markdown_text

    async def get_decision_document_as_markdown(
        self,
        document_url: str,
        page_number: int = 1
    ) -> AnayasaDocumentMarkdown:
        """
        Retrieves a specific Anayasa Mahkemesi (Norm Denetimi) decision,
        converts its content to Markdown, and returns the requested page/chunk.
        """
        full_url = urljoin(self.BASE_URL, document_url) if not document_url.startswith("http") else document_url
        logger.info(f"AnayasaMahkemesiApiClient: Fetching Norm Denetimi document for Markdown (page {page_number}) from URL: {full_url}")

        decision_ek_no_from_page = None
        decision_date_from_page = None
        official_gazette_from_page = None

        try:
            # Use a new client instance for document fetching if headers/timeout needs to be different,
            # or reuse self.http_client if settings are compatible. For now, self.http_client.
            get_response = await self.http_client.get(full_url, headers={"Accept": "text/html"})
            get_response.raise_for_status()
            html_content_from_api = get_response.text

            if not isinstance(html_content_from_api, str) or not html_content_from_api.strip():
                logger.warning(f"AnayasaMahkemesiApiClient: Received empty or non-string HTML from URL {full_url}.")
                return AnayasaDocumentMarkdown(
                    source_url=full_url, markdown_chunk=None, current_page=page_number, total_pages=0, is_paginated=False
                )

            # Extract metadata from the page content (E.K. No, Date, RG)
            soup = BeautifulSoup(html_content_from_api, "html.parser")
            karar_metni_div = soup.find("div", class_="KararMetni") # Usually within div#Karar
            if not karar_metni_div: # Fallback if not in KararMetni
                karar_metni_div = soup.find("div", class_="WordSection1")
            
            # Initialize with empty string defaults
            decision_ek_no_from_page = ""
            decision_date_from_page = ""
            official_gazette_from_page = ""
            
            if karar_metni_div:
                # Attempt to find E.K. No (Esas No, Karar No)
                # Norm Denetimi pages often have this in bold <p> tags directly or in the WordSection1
                # Look for patterns like "Esas No.: YYYY/NN" and "Karar No.: YYYY/NN"
                
                esas_no_tag = karar_metni_div.find(lambda tag: tag.name == "p" and tag.find("b") and "Esas No.:" in tag.find("b").get_text())
                karar_no_tag = karar_metni_div.find(lambda tag: tag.name == "p" and tag.find("b") and "Karar No.:" in tag.find("b").get_text())
                karar_tarihi_tag = karar_metni_div.find(lambda tag: tag.name == "p" and tag.find("b") and "Karar tarihi:" in tag.find("b").get_text()) # Less common on Norm pages
                resmi_gazete_tag = karar_metni_div.find(lambda tag: tag.name == "p" and ("Resmî Gazete tarih ve sayısı:" in tag.get_text() or "Resmi Gazete tarih/sayı:" in tag.get_text()))


                if esas_no_tag and esas_no_tag.find("b") and karar_no_tag and karar_no_tag.find("b"):
                    esas_str = esas_no_tag.find("b").get_text(strip=True).replace('Esas No.:', '').strip()
                    karar_str = karar_no_tag.find("b").get_text(strip=True).replace('Karar No.:', '').strip()
                    decision_ek_no_from_page = f"E.{esas_str}, K.{karar_str}"
                
                if karar_tarihi_tag and karar_tarihi_tag.find("b"):
                     decision_date_from_page = karar_tarihi_tag.find("b").get_text(strip=True).replace("Karar tarihi:", "").strip()
                elif karar_metni_div: # Fallback for Karar Tarihi if not in specific tag
                    date_match = re.search(r"Karar Tarihi\s*:\s*([\d\.]+)", karar_metni_div.get_text()) # Norm pages often use DD.MM.YYYY
                    if date_match: decision_date_from_page = date_match.group(1).strip()


                if resmi_gazete_tag:
                    # Try to get the bold part first if it exists
                    bold_rg_tag = resmi_gazete_tag.find("b")
                    rg_text_content = bold_rg_tag.get_text(strip=True) if bold_rg_tag else resmi_gazete_tag.get_text(strip=True)
                    official_gazette_from_page = rg_text_content.replace("Resmî Gazete tarih ve sayısı:", "").replace("Resmi Gazete tarih/sayı:", "").strip()


            full_markdown_content = self._convert_html_to_markdown_norm_denetimi(html_content_from_api)

            if not full_markdown_content:
                return AnayasaDocumentMarkdown(
                    source_url=full_url,
                    decision_reference_no_from_page=decision_ek_no_from_page,
                    decision_date_from_page=decision_date_from_page,
                    official_gazette_info_from_page=official_gazette_from_page,
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

            return AnayasaDocumentMarkdown(
                source_url=full_url,
                decision_reference_no_from_page=decision_ek_no_from_page,
                decision_date_from_page=decision_date_from_page,
                official_gazette_info_from_page=official_gazette_from_page,
                markdown_chunk=markdown_chunk,
                current_page=current_page_clamped,
                total_pages=total_pages,
                is_paginated=(total_pages > 1)
            )

        except httpx.RequestError as e:
            logger.error(f"AnayasaMahkemesiApiClient: HTTP error fetching Norm Denetimi document from {full_url}: {e}")
            raise
        except Exception as e:
            logger.error(f"AnayasaMahkemesiApiClient: General error processing Norm Denetimi document from {full_url}: {e}")
            raise

    async def close_client_session(self):
        if hasattr(self, 'http_client') and self.http_client and not self.http_client.is_closed:
            await self.http_client.aclose()
            logger.info("AnayasaMahkemesiApiClient (Norm Denetimi): HTTP client session closed.")