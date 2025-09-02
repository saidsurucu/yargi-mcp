# kik_mcp_module/client_v2.py

import httpx
import requests
import logging
import uuid
import base64
import ssl
from typing import Optional
from datetime import datetime

from .models_v2 import (
    KikV2DecisionType, KikV2SearchPayload, KikV2SearchPayloadDk, KikV2SearchPayloadMk,
    KikV2RequestData, KikV2QueryRequest, KikV2KeyValuePair, 
    KikV2SearchResponse, KikV2SearchResponseDk, KikV2SearchResponseMk,
    KikV2SearchResult, KikV2CompactDecision, KikV2DocumentMarkdown
)

logger = logging.getLogger(__name__)

class KikV2ApiClient:
    """
    New KIK v2 API Client for https://ekapv2.kik.gov.tr
    
    This client uses the modern JSON-based API endpoint that provides
    better structured data compared to the legacy form-based API.
    """
    
    BASE_URL = "https://ekapv2.kik.gov.tr"
    
    # Endpoint mappings for different decision types
    ENDPOINTS = {
        KikV2DecisionType.UYUSMAZLIK: "/b_ihalearaclari/api/KurulKararlari/GetKurulKararlari",
        KikV2DecisionType.DUZENLEYICI: "/b_ihalearaclari/api/KurulKararlari/GetKurulKararlariDk", 
        KikV2DecisionType.MAHKEME: "/b_ihalearaclari/api/KurulKararlari/GetKurulKararlariMk"
    }
    
    def __init__(self, request_timeout: float = 60.0):
        # Create SSL context with legacy server support
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        # Enable legacy server connect option for older SSL implementations
        ssl_context.options |= ssl.OP_LEGACY_SERVER_CONNECT
        
        # Set broader cipher suite support including legacy ciphers
        ssl_context.set_ciphers('ALL:!aNULL:!eNULL:!EXPORT:!DES:!RC4:!MD5:!PSK:!SRP:!CAMELLIA')
        
        self.http_client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            verify=ssl_context,
            headers={
                "Accept": "application/json",
                "Accept-Language": "tr",
                "Content-Type": "application/json",
                "Origin": self.BASE_URL,
                "Referer": f"{self.BASE_URL}/sorgulamalar/kurul-kararlari",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors", 
                "Sec-Fetch-Site": "same-origin",
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36",
                "api-version": "v1",
                "sec-ch-ua": '"Not;A=Brand";v="99", "Google Chrome";v="139", "Chromium";v="139"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"macOS"'
            },
            timeout=request_timeout
        )
        
        # Generate security headers (these might need to be updated based on API requirements)
        self.security_headers = self._generate_security_headers()
    
    def _generate_security_headers(self) -> dict:
        """
        Generate the custom security headers required by KIK v2 API.
        These headers appear to be for request validation/encryption.
        """
        # Generate a random GUID for each session
        request_guid = str(uuid.uuid4())
        
        # These are example values - in a real implementation, these might need
        # to be calculated based on the request content or session
        return {
            "X-Custom-Request-Guid": request_guid,
            "X-Custom-Request-R8id": "hwnOjsN8qdgtDw70x3sKkxab0rj2bQ8Uph4+C+oU+9AMmQqRN3eMOEEeet748DOf",
            "X-Custom-Request-Siv": "p2IQRTitF8z7I39nBjdAqA==",
            "X-Custom-Request-Ts": "1vB3Wwrt8YQ5U6t3XAzZ+Q=="
        }
    
    def _build_search_payload(self, 
                             decision_type: KikV2DecisionType,
                             karar_metni: str = "",
                             karar_no: str = "",
                             basvuran: str = "",
                             idare_adi: str = "",
                             baslangic_tarihi: str = "",
                             bitis_tarihi: str = ""):
        """Build the search payload for KIK v2 API."""
        
        key_value_pairs = []
        
        # Add non-empty search criteria
        if karar_metni:
            key_value_pairs.append(KikV2KeyValuePair(key="KararMetni", value=karar_metni))
        
        if karar_no:
            key_value_pairs.append(KikV2KeyValuePair(key="KararNo", value=karar_no))
            
        if basvuran:
            key_value_pairs.append(KikV2KeyValuePair(key="BasvuranAdi", value=basvuran))
            
        if idare_adi:
            key_value_pairs.append(KikV2KeyValuePair(key="IdareAdi", value=idare_adi))
            
        if baslangic_tarihi:
            key_value_pairs.append(KikV2KeyValuePair(key="BaslangicTarihi", value=baslangic_tarihi))
            
        if bitis_tarihi:
            key_value_pairs.append(KikV2KeyValuePair(key="BitisTarihi", value=bitis_tarihi))
        
        # If no search criteria provided, use a generic search
        if not key_value_pairs:
            key_value_pairs.append(KikV2KeyValuePair(key="KararMetni", value=""))
        
        query_request = KikV2QueryRequest(keyValueOfstringanyType=key_value_pairs)
        request_data = KikV2RequestData(keyValuePairs=query_request)
        
        # Return appropriate payload based on decision type
        if decision_type == KikV2DecisionType.UYUSMAZLIK:
            return KikV2SearchPayload(sorgulaKurulKararlari=request_data)
        elif decision_type == KikV2DecisionType.DUZENLEYICI:
            return KikV2SearchPayloadDk(sorgulaKurulKararlariDk=request_data)
        elif decision_type == KikV2DecisionType.MAHKEME:
            return KikV2SearchPayloadMk(sorgulaKurulKararlariMk=request_data)
        else:
            raise ValueError(f"Unsupported decision type: {decision_type}")
    
    async def search_decisions(self,
                              decision_type: KikV2DecisionType = KikV2DecisionType.UYUSMAZLIK,
                              karar_metni: str = "",
                              karar_no: str = "",
                              basvuran: str = "",
                              idare_adi: str = "",
                              baslangic_tarihi: str = "",
                              bitis_tarihi: str = "") -> KikV2SearchResult:
        """
        Search KIK decisions using the v2 API.
        
        Args:
            decision_type: Type of decision to search (uyusmazlik/duzenleyici/mahkeme)
            karar_metni: Decision text search
            karar_no: Decision number (e.g., "2025/UH.II-1801")
            basvuran: Applicant name
            idare_adi: Administration name
            baslangic_tarihi: Start date (YYYY-MM-DD format)
            bitis_tarihi: End date (YYYY-MM-DD format)
            
        Returns:
            KikV2SearchResult with compact decision list
        """
        
        logger.info(f"KikV2ApiClient: Searching {decision_type.value} decisions with criteria - karar_metni: '{karar_metni}', karar_no: '{karar_no}', basvuran: '{basvuran}'")
        
        try:
            # Build request payload
            payload = self._build_search_payload(
                decision_type=decision_type,
                karar_metni=karar_metni,
                karar_no=karar_no,
                basvuran=basvuran,
                idare_adi=idare_adi,
                baslangic_tarihi=baslangic_tarihi,
                bitis_tarihi=bitis_tarihi
            )
            
            # Update security headers for this request
            headers = {**self.http_client.headers, **self._generate_security_headers()}
            
            # Get the appropriate endpoint for this decision type
            endpoint = self.ENDPOINTS[decision_type]
            
            # Make API request
            response = await self.http_client.post(
                endpoint,
                json=payload.model_dump(),
                headers=headers
            )
            
            response.raise_for_status()
            response_data = response.json()
            
            logger.debug(f"KikV2ApiClient: Raw API response structure: {type(response_data)}")
            
            # Parse the API response based on decision type
            if decision_type == KikV2DecisionType.UYUSMAZLIK:
                api_response = KikV2SearchResponse(**response_data)
                result_data = api_response.SorgulaKurulKararlariResponse.SorgulaKurulKararlariResult
            elif decision_type == KikV2DecisionType.DUZENLEYICI:
                api_response = KikV2SearchResponseDk(**response_data)
                result_data = api_response.SorgulaKurulKararlariDkResponse.SorgulaKurulKararlariDkResult
            elif decision_type == KikV2DecisionType.MAHKEME:
                api_response = KikV2SearchResponseMk(**response_data)
                result_data = api_response.SorgulaKurulKararlariMkResponse.SorgulaKurulKararlariMkResult
            else:
                raise ValueError(f"Unsupported decision type: {decision_type}")
                
            # Check for API errors
            if result_data.hataKodu and result_data.hataKodu != "0":
                logger.warning(f"KikV2ApiClient: API returned error - Code: {result_data.hataKodu}, Message: {result_data.hataMesaji}")
                return KikV2SearchResult(
                    decisions=[],
                    total_records=0,
                    page=1,
                    error_code=result_data.hataKodu,
                    error_message=result_data.hataMesaji
                )
            
            # Convert to compact format
            compact_decisions = []
            total_count = 0
            
            for decision_group in result_data.KurulKararTutanakDetayListesi:
                for decision_detail in decision_group.KurulKararTutanakDetayi:
                    compact_decision = KikV2CompactDecision(
                        kararNo=decision_detail.kararNo,
                        kararTarihi=decision_detail.kararTarihi,
                        basvuran=decision_detail.basvuran,
                        idareAdi=decision_detail.idareAdi,
                        basvuruKonusu=decision_detail.basvuruKonusu,
                        gundemMaddesiId=decision_detail.gundemMaddesiId,
                        decision_type=decision_type.value
                    )
                    compact_decisions.append(compact_decision)
                    total_count += 1
            
            logger.info(f"KikV2ApiClient: Found {total_count} decisions")
            
            return KikV2SearchResult(
                decisions=compact_decisions,
                total_records=total_count,
                page=1,
                error_code="0",
                error_message=""
            )
            
        except httpx.HTTPStatusError as e:
            logger.error(f"KikV2ApiClient: HTTP error during search: {e.response.status_code} - {e.response.text}")
            return KikV2SearchResult(
                decisions=[],
                total_records=0, 
                page=1,
                error_code="HTTP_ERROR",
                error_message=f"HTTP {e.response.status_code}: {e.response.text}"
            )
        except Exception as e:
            logger.error(f"KikV2ApiClient: Unexpected error during search: {str(e)}")
            return KikV2SearchResult(
                decisions=[],
                total_records=0,
                page=1, 
                error_code="UNEXPECTED_ERROR",
                error_message=str(e)
            )
    
    async def get_document_markdown(self, document_id: str) -> KikV2DocumentMarkdown:
        """
        Get KİK decision document content in Markdown format.
        
        This method uses a two-step process:
        1. Call GetSorgulamaUrl endpoint to get the actual document URL
        2. Use Playwright to navigate to that URL and extract content
        
        Args:
            document_id: The gundemMaddesiId from search results
            
        Returns:
            KikV2DocumentMarkdown with document content converted to Markdown
        """
        
        logger.info(f"KikV2ApiClient: Getting document for ID: {document_id}")
        
        if not document_id or not document_id.strip():
            return KikV2DocumentMarkdown(
                document_id=document_id,
                kararNo="",
                markdown_content="",
                source_url="",
                error_message="Document ID is required"
            )
        
        try:
            # Step 1: Get the actual document URL using GetSorgulamaUrl endpoint
            logger.info(f"KikV2ApiClient: Step 1 - Getting document URL for ID: {document_id}")
            
            # Update security headers for this request
            headers = {**self.http_client.headers, **self._generate_security_headers()}
            
            # Call GetSorgulamaUrl to get the real document URL
            url_payload = {"sorguSayfaTipi": 2}  # As shown in curl example
            
            url_response = await self.http_client.post(
                "/b_ihalearaclari/api/KurulKararlari/GetSorgulamaUrl",
                json=url_payload,
                headers=headers
            )
            
            url_response.raise_for_status()
            url_data = url_response.json()
            
            # Get the base document URL from API response
            base_document_url = url_data.get("sorgulamaUrl", "")
            if not base_document_url:
                return KikV2DocumentMarkdown(
                    document_id=document_id,
                    kararNo="",
                    markdown_content="",
                    source_url="",
                    error_message="Could not get document URL from GetSorgulamaUrl API"
                )
            
            # Construct full document URL with the actual document ID
            document_url = f"{base_document_url}?KararId={document_id}"
            logger.info(f"KikV2ApiClient: Step 2 - Retrieved document URL: {document_url}")
            
        except Exception as e:
            logger.error(f"KikV2ApiClient: Error getting document URL for ID {document_id}: {str(e)}")
            # Fallback to old method if GetSorgulamaUrl fails
            document_url = f"https://ekap.kik.gov.tr/EKAP/Vatandas/KurulKararGoster.aspx?KararId={document_id}"
            logger.info(f"KikV2ApiClient: Falling back to direct URL: {document_url}")
        
        try:
            # Step 2: Use Playwright to get the actual document content
            logger.info(f"KikV2ApiClient: Step 2 - Using Playwright to retrieve document from: {document_url}")
            
            try:
                from playwright.async_api import async_playwright
                
                async with async_playwright() as p:
                    # Launch browser
                    browser = await p.chromium.launch(
                        headless=True,
                        args=['--no-sandbox', '--disable-dev-shm-usage']
                    )
                    
                    page = await browser.new_page(
                        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"
                    )
                    
                    # Navigate to document page with longer timeout for JS loading
                    await page.goto(document_url, wait_until="networkidle", timeout=15000)
                    
                    # Wait for the document content to load (KİK pages might need more time for JS execution)
                    await page.wait_for_timeout(3000)
                    
                    # Wait for Angular/Zone.js to finish loading and document to be ready
                    try:
                        # Wait for Angular zone to be available (this JavaScript code you showed)
                        await page.wait_for_function(
                            "typeof Zone !== 'undefined' && Zone.current", 
                            timeout=10000
                        )
                        
                        # Wait for network to be idle after Angular bootstrap
                        await page.wait_for_load_state("networkidle", timeout=10000)
                        
                        # Wait for specific document content to appear
                        await page.wait_for_function(
                            """
                            document.body.textContent.length > 5000 && 
                            (document.body.textContent.includes('Karar') || 
                             document.body.textContent.includes('KURUL') ||
                             document.body.textContent.includes('Gündem') ||
                             document.body.textContent.includes('Toplantı'))
                            """,
                            timeout=15000
                        )
                        
                        logger.info("KikV2ApiClient: Angular document content loaded successfully")
                        
                    except Exception as e:
                        logger.warning(f"KikV2ApiClient: Angular content loading timed out, proceeding anyway: {str(e)}")
                        # Give a bit more time for any remaining content to load
                        await page.wait_for_timeout(5000)
                    
                    # Get page content
                    html_content = await page.content()
                    
                    await browser.close()
                    
                    logger.info(f"KikV2ApiClient: Retrieved content via Playwright, length: {len(html_content)}")
                    
            except ImportError:
                logger.info("KikV2ApiClient: Playwright not available, falling back to httpx")
                # Fallback to httpx
                response = await self.http_client.get(
                    document_url,
                    headers={
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                        "Accept-Language": "tr,en-US;q=0.5",
                        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36",
                        "Referer": "https://ekap.kik.gov.tr/",
                        "Cache-Control": "no-cache"
                    }
                )
                response.raise_for_status()
                html_content = response.text
            
            # Convert HTML to Markdown using MarkItDown with BytesIO
            try:
                from markitdown import MarkItDown
                from io import BytesIO
                
                md = MarkItDown()
                html_bytes = html_content.encode('utf-8')
                html_stream = BytesIO(html_bytes)
                
                result = md.convert_stream(html_stream, file_extension=".html")
                markdown_content = result.text_content
                
                return KikV2DocumentMarkdown(
                    document_id=document_id,
                    kararNo="",
                    markdown_content=markdown_content,
                    source_url=document_url,
                    error_message=""
                )
                
            except ImportError:
                return KikV2DocumentMarkdown(
                    document_id=document_id,
                    kararNo="",
                    markdown_content="MarkItDown library not available",
                    source_url=document_url,
                    error_message="MarkItDown library not installed"
                )
                
        except Exception as e:
            logger.error(f"KikV2ApiClient: Error retrieving document {document_id}: {str(e)}")
            return KikV2DocumentMarkdown(
                document_id=document_id,
                kararNo="",
                markdown_content="",
                source_url=document_url,
                error_message=str(e)
            )
    
    async def close_client_session(self):
        """Close HTTP client session."""
        await self.http_client.aclose()
        logger.info("KikV2ApiClient: HTTP client session closed.")