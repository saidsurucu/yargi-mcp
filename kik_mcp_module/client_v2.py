# kik_mcp_module/client_v2.py

import httpx
import logging
import uuid
import ssl
import os
from typing import Optional
from datetime import datetime

# Cryptography imports for AES-256-CBC encryption of document IDs
try:
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.backends import default_backend
    HAS_CRYPTOGRAPHY = True
except ImportError:
    HAS_CRYPTOGRAPHY = False

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

    # AES-256-CBC encryption key for document ID encryption (reverse engineered from ekapv2.kik.gov.tr Angular app)
    # This key is used to encrypt numeric gundemMaddesiId values to 64-character hex hashes for document URLs
    DOCUMENT_ID_ENCRYPTION_KEY = bytes([
        236, 193, 164, 43, 12, 135, 121, 170, 4, 244, 123, 219, 82, 158, 124, 174,
        174, 228, 219, 174, 208, 104, 174, 120, 32, 76, 250, 4, 143, 159, 211, 176
    ])

    @staticmethod
    def encrypt_document_id(numeric_id: str) -> str:
        """
        Encrypt a numeric KİK gundemMaddesiId to the 64-character hex hash
        used in document URLs.

        Algorithm: AES-256-CBC with PKCS7 padding
        Output format: IV (16 bytes hex) + Ciphertext (16 bytes hex) = 64 chars

        Args:
            numeric_id: The numeric document ID from search results (e.g., "177280")

        Returns:
            64-character hex string for use in document URL KararId parameter
        """
        if not HAS_CRYPTOGRAPHY:
            raise ImportError("cryptography library required for document ID encryption")

        # Generate random IV (16 bytes)
        iv = os.urandom(16)

        # Create AES-CBC cipher with the encryption key
        cipher = Cipher(
            algorithms.AES(KikV2ApiClient.DOCUMENT_ID_ENCRYPTION_KEY),
            modes.CBC(iv),
            backend=default_backend()
        )
        encryptor = cipher.encryptor()

        # Encode plaintext and apply PKCS7 padding
        plaintext = numeric_id.encode('utf-8')
        block_size = 16
        padding_len = block_size - (len(plaintext) % block_size)
        padded_plaintext = plaintext + bytes([padding_len] * padding_len)

        # Encrypt
        ciphertext = encryptor.update(padded_plaintext) + encryptor.finalize()

        # Return IV + ciphertext as lowercase hex (64 characters total)
        return iv.hex() + ciphertext.hex()

    def __init__(self, request_timeout: float = 60.0):
        # Create SSL context with legacy server support
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        # Enable legacy server connect option for older SSL implementations (Python 3.12+)
        if hasattr(ssl, 'OP_LEGACY_SERVER_CONNECT'):
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
        2. Use httpx to fetch the document content
        
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
            
            # If document_id is numeric, encrypt it to get the KararId hash
            # The web interface uses AES-256-CBC encrypted hashes for document URLs
            karar_id = document_id
            if document_id.isdigit():
                try:
                    karar_id = self.encrypt_document_id(document_id)
                    logger.info(f"KikV2ApiClient: Encrypted numeric ID {document_id} to hash: {karar_id}")
                except Exception as enc_error:
                    logger.warning(f"KikV2ApiClient: Could not encrypt document ID, using as-is: {enc_error}")

            # Construct full document URL with the encrypted KararId
            document_url = f"{base_document_url}?KararId={karar_id}"
            logger.info(f"KikV2ApiClient: Step 2 - Retrieved document URL: {document_url}")

        except Exception as e:
            logger.error(f"KikV2ApiClient: Error getting document URL for ID {document_id}: {str(e)}")
            # Fallback to old method if GetSorgulamaUrl fails
            # Also encrypt numeric IDs in fallback path
            karar_id = document_id
            if document_id.isdigit():
                try:
                    karar_id = self.encrypt_document_id(document_id)
                    logger.info(f"KikV2ApiClient: Encrypted numeric ID in fallback: {karar_id}")
                except Exception as enc_error:
                    logger.warning(f"KikV2ApiClient: Could not encrypt in fallback: {enc_error}")
            document_url = f"https://ekap.kik.gov.tr/EKAP/Vatandas/KurulKararGoster.aspx?KararId={karar_id}"
            logger.info(f"KikV2ApiClient: Falling back to direct URL: {document_url}")
        
        try:
            # Step 2: Use httpx to get the document content
            logger.info(f"KikV2ApiClient: Step 2 - Using httpx to retrieve document from: {document_url}")

            # Create a separate httpx client for document retrieval with HTML headers
            doc_ssl_context = ssl.create_default_context()
            doc_ssl_context.check_hostname = False
            doc_ssl_context.verify_mode = ssl.CERT_NONE
            if hasattr(ssl, 'OP_LEGACY_SERVER_CONNECT'):
                doc_ssl_context.options |= ssl.OP_LEGACY_SERVER_CONNECT
            doc_ssl_context.set_ciphers('ALL:!aNULL:!eNULL:!EXPORT:!DES:!RC4:!MD5:!PSK:!SRP:!CAMELLIA')

            async with httpx.AsyncClient(
                verify=doc_ssl_context,
                headers={
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "tr,en-US;q=0.5",
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"
                },
                timeout=60.0,
                follow_redirects=True
            ) as doc_client:
                response = await doc_client.get(document_url)
                response.raise_for_status()
                html_content = response.text
                logger.info(f"KikV2ApiClient: Retrieved content via httpx, length: {len(html_content)}")
            
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