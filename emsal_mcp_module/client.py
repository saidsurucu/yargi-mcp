# emsal_mcp_module/client.py

import httpx
# from bs4 import BeautifulSoup # Uncomment if needed for advanced HTML pre-processing
from typing import Dict, Any, List, Optional
import logging
import html
import re
import io
from markitdown import MarkItDown

from .models import (
    EmsalSearchRequest,
    EmsalDetailedSearchRequestData, 
    EmsalApiResponse,
    EmsalDocumentMarkdown
)

logger = logging.getLogger(__name__)
if not logger.hasHandlers():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

class EmsalApiClient:
    """API Client for Emsal (UYAP Precedent Decision) search system."""
    BASE_URL = "https://emsal.uyap.gov.tr"
    DETAILED_SEARCH_ENDPOINT = "/aramadetaylist" 
    DOCUMENT_ENDPOINT = "/getDokuman"

    def __init__(self, request_timeout: float = 30.0):
        self.http_client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers={
                "Content-Type": "application/json; charset=UTF-8",
                "Accept": "application/json, text/plain, */*",
                "X-Requested-With": "XMLHttpRequest",
            },
            timeout=request_timeout,
            verify=False # As per user's original FastAPI code
        )

    async def search_detailed_decisions(
        self,
        params: EmsalSearchRequest
    ) -> EmsalApiResponse:
        """Performs a detailed search for Emsal decisions."""
        
        data_for_api_payload = EmsalDetailedSearchRequestData(
            arananKelime=params.keyword or "",
            Bam_Hukuk_Mahkemeleri=params.selected_bam_civil_court, # Uses alias "Bam Hukuk Mahkemeleri"
            Hukuk_Mahkemeleri=params.selected_civil_court,         # Uses alias "Hukuk Mahkemeleri"
            birimHukukMah="+".join(params.selected_regional_civil_chambers) if params.selected_regional_civil_chambers else "",
            esasYil=params.case_year_esas or "",
            esasIlkSiraNo=params.case_start_seq_esas or "",
            esasSonSiraNo=params.case_end_seq_esas or "",
            kararYil=params.decision_year_karar or "",
            kararIlkSiraNo=params.decision_start_seq_karar or "",
            kararSonSiraNo=params.decision_end_seq_karar or "",
            baslangicTarihi=params.start_date or "",
            bitisTarihi=params.end_date or "",
            siralama=params.sort_criteria,
            siralamaDirection=params.sort_direction,
            pageSize=params.page_size,
            pageNumber=params.page_number
        )
        
        # Create request dict and remove empty string fields to avoid API issues
        payload_dict = data_for_api_payload.model_dump(by_alias=True, exclude_none=True)
        # Remove empty string fields that might cause API issues
        cleaned_payload = {k: v for k, v in payload_dict.items() if v != ""}
        final_payload = {"data": cleaned_payload} 
        
        logger.info(f"EmsalApiClient: Performing DETAILED search with payload: {final_payload}")
        return await self._execute_api_search(self.DETAILED_SEARCH_ENDPOINT, final_payload)

    async def _execute_api_search(self, endpoint: str, payload: Dict) -> EmsalApiResponse:
        """Helper method to execute search POST request and process response for Emsal."""
        try:
            response = await self.http_client.post(endpoint, json=payload)
            response.raise_for_status()
            response_json_data = response.json()
            logger.debug(f"EmsalApiClient: Raw API response from {endpoint}: {response_json_data}")
            
            api_response_parsed = EmsalApiResponse(**response_json_data)

            if api_response_parsed.data and api_response_parsed.data.data:
                for decision_item in api_response_parsed.data.data:
                    if decision_item.id:
                        decision_item.document_url = f"{self.BASE_URL}{self.DOCUMENT_ENDPOINT}?id={decision_item.id}"
            
            return api_response_parsed
        except httpx.RequestError as e:
            logger.error(f"EmsalApiClient: HTTP request error during Emsal search to {endpoint}: {e}")
            raise
        except Exception as e:
            logger.error(f"EmsalApiClient: Error processing or validating Emsal search response from {endpoint}: {e}")
            raise

    def _clean_html_and_convert_to_markdown_emsal(self, html_content_from_api_data_field: str) -> Optional[str]:
        """
        Cleans HTML (from Emsal API 'data' field containing HTML string)
        and converts it to Markdown using MarkItDown.
        This assumes Emsal /getDokuman response is JSON with HTML in "data" field,
        similar to Yargitay and the last Emsal /getDokuman example.
        """
        if not html_content_from_api_data_field:
            return None

        # Basic HTML unescaping and fixing common escaped characters
        # Based on user's original fix_html_content in app/routers/emsal.py
        content = html.unescape(html_content_from_api_data_field)
        content = content.replace('\\"', '"')
        content = content.replace('\\r\\n', '\n')
        content = content.replace('\\n', '\n')
        content = content.replace('\\t', '\t')
        
        # The HTML string from "data" field starts with "<html><head>..."
        html_input_for_markdown = content 

        markdown_text = None
        try:
            # Convert HTML string to bytes and create BytesIO stream
            html_bytes = html_input_for_markdown.encode('utf-8')
            html_stream = io.BytesIO(html_bytes)
            
            # Pass BytesIO stream to MarkItDown to avoid temp file creation
            md_converter = MarkItDown()
            conversion_result = md_converter.convert(html_stream)
            markdown_text = conversion_result.text_content
            logger.info("EmsalApiClient: HTML to Markdown conversion successful.")
        except Exception as e:
            logger.error(f"EmsalApiClient: Error during MarkItDown HTML to Markdown conversion for Emsal: {e}")
        
        return markdown_text

    async def get_decision_document_as_markdown(self, id: str) -> EmsalDocumentMarkdown:
        """
        Retrieves a specific Emsal decision by ID and returns its content as Markdown.
        Assumes Emsal /getDokuman endpoint returns JSON with HTML content in the 'data' field.
        """
        document_api_url = f"{self.DOCUMENT_ENDPOINT}?id={id}"
        source_url = f"{self.BASE_URL}{document_api_url}"
        logger.info(f"EmsalApiClient: Fetching Emsal document for Markdown (ID: {id}) from {source_url}")

        try:
            response = await self.http_client.get(document_api_url)
            response.raise_for_status()
            
            # Emsal /getDokuman returns JSON with HTML in 'data' field (confirmed by user example)
            response_json = response.json()
            html_content_from_api = response_json.get("data")

            if not isinstance(html_content_from_api, str) or not html_content_from_api.strip():
                logger.warning(f"EmsalApiClient: Received empty or non-string HTML in 'data' field for Emsal ID {id}.")
                return EmsalDocumentMarkdown(id=id, markdown_content=None, source_url=source_url)

            markdown_content = self._clean_html_and_convert_to_markdown_emsal(html_content_from_api)

            return EmsalDocumentMarkdown(
                id=id,
                markdown_content=markdown_content,
                source_url=source_url
            )
        except httpx.RequestError as e:
            logger.error(f"EmsalApiClient: HTTP error fetching Emsal document (ID: {id}): {e}")
            raise
        except ValueError as e: 
            logger.error(f"EmsalApiClient: ValueError processing Emsal document response (ID: {id}): {e}")
            raise
        except Exception as e:
            logger.error(f"EmsalApiClient: General error processing Emsal document (ID: {id}): {e}")
            raise

    async def close_client_session(self):
        """Closes the HTTPX client session."""
        if self.http_client and not self.http_client.is_closed:
            await self.http_client.aclose()
        logger.info("EmsalApiClient: HTTP client session closed.")