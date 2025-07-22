# sayistay_mcp_module/client.py

import httpx
import re
from bs4 import BeautifulSoup
from typing import Dict, Any, List, Optional, Tuple
import logging
import html
import io
from urllib.parse import urlencode, urljoin
from markitdown import MarkItDown

from .models import (
    GenelKurulSearchRequest, GenelKurulSearchResponse, GenelKurulDecision,
    TemyizKuruluSearchRequest, TemyizKuruluSearchResponse, TemyizKuruluDecision,
    DaireSearchRequest, DaireSearchResponse, DaireDecision,
    SayistayDocumentMarkdown
)
from .enums import DaireEnum, KamuIdaresiTuruEnum, WebKararKonusuEnum, WEB_KARAR_KONUSU_MAPPING

logger = logging.getLogger(__name__)
if not logger.hasHandlers():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

class SayistayApiClient:
    """
    API Client for Sayıştay (Turkish Court of Accounts) decision search system.
    
    Handles three types of decisions:
    - Genel Kurul (General Assembly): Precedent-setting interpretive decisions
    - Temyiz Kurulu (Appeals Board): Appeals against chamber decisions  
    - Daire (Chamber): First-instance audit findings and sanctions
    
    Features:
    - ASP.NET WebForms session management with CSRF tokens
    - DataTables-based pagination and filtering
    - Automatic session refresh on expiration
    - Document retrieval with Markdown conversion
    """
    
    BASE_URL = "https://www.sayistay.gov.tr"
    
    # Search endpoints for each decision type
    GENEL_KURUL_ENDPOINT = "/KararlarGenelKurul/DataTablesList"
    TEMYIZ_KURULU_ENDPOINT = "/KararlarTemyiz/DataTablesList" 
    DAIRE_ENDPOINT = "/KararlarDaire/DataTablesList"
    
    # Page endpoints for session initialization and document access
    GENEL_KURUL_PAGE = "/KararlarGenelKurul"
    TEMYIZ_KURULU_PAGE = "/KararlarTemyiz"
    DAIRE_PAGE = "/KararlarDaire"
    
    def __init__(self, request_timeout: float = 60.0):
        self.request_timeout = request_timeout
        self.session_cookies: Dict[str, str] = {}
        self.csrf_tokens: Dict[str, str] = {}  # Store tokens for each endpoint
        
        self.http_client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers={
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
                "X-Requested-With": "XMLHttpRequest",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors", 
                "Sec-Fetch-Site": "same-origin"
            },
            timeout=request_timeout,
            follow_redirects=True
        )

    async def _initialize_session_for_endpoint(self, endpoint_type: str) -> bool:
        """
        Initialize session and obtain CSRF token for specific endpoint.
        
        Args:
            endpoint_type: One of 'genel_kurul', 'temyiz_kurulu', 'daire'
            
        Returns:
            True if session initialized successfully, False otherwise
        """
        page_mapping = {
            'genel_kurul': self.GENEL_KURUL_PAGE,
            'temyiz_kurulu': self.TEMYIZ_KURULU_PAGE,
            'daire': self.DAIRE_PAGE
        }
        
        if endpoint_type not in page_mapping:
            logger.error(f"Invalid endpoint type: {endpoint_type}")
            return False
            
        page_url = page_mapping[endpoint_type]
        logger.info(f"Initializing session for {endpoint_type} endpoint: {page_url}")
        
        try:
            response = await self.http_client.get(page_url)
            response.raise_for_status()
            
            # Extract session cookies
            for cookie_name, cookie_value in response.cookies.items():
                self.session_cookies[cookie_name] = cookie_value
                logger.debug(f"Stored session cookie: {cookie_name}")
            
            # Extract CSRF token from form
            soup = BeautifulSoup(response.text, 'html.parser')
            csrf_input = soup.find('input', {'name': '__RequestVerificationToken'})
            
            if csrf_input and csrf_input.get('value'):
                self.csrf_tokens[endpoint_type] = csrf_input['value']
                logger.info(f"Extracted CSRF token for {endpoint_type}")
                return True
            else:
                logger.warning(f"CSRF token not found in {endpoint_type} page")
                return False
                
        except httpx.RequestError as e:
            logger.error(f"HTTP error during session initialization for {endpoint_type}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error initializing session for {endpoint_type}: {e}")
            return False

    def _enum_to_form_value(self, enum_value: str, enum_type: str) -> str:
        """Convert enum values to form values expected by the API."""
        if enum_value == "ALL":
            if enum_type == "daire":
                return "Tüm Daireler"
            elif enum_type == "kamu_idaresi":
                return "Tüm Kurumlar" 
            elif enum_type == "web_karar_konusu":
                return "Tüm Konular"
        
        # Apply web_karar_konusu mapping
        if enum_type == "web_karar_konusu":
            return WEB_KARAR_KONUSU_MAPPING.get(enum_value, enum_value)
        
        return enum_value

    def _build_datatables_params(self, start: int, length: int, draw: int = 1) -> List[Tuple[str, str]]:
        """Build standard DataTables parameters for all endpoints."""
        params = [
            ("draw", str(draw)),
            ("start", str(start)),
            ("length", str(length)),
            ("search[value]", ""),
            ("search[regex]", "false")
        ]
        return params

    def _build_genel_kurul_form_data(self, params: GenelKurulSearchRequest, draw: int = 1) -> List[Tuple[str, str]]:
        """Build form data for Genel Kurul search request."""
        form_data = self._build_datatables_params(params.start, params.length, draw)
        
        # Add DataTables column definitions (from actual request)
        column_defs = [
            ("columns[0][data]", "KARARNO"),
            ("columns[0][name]", ""),
            ("columns[0][searchable]", "true"),
            ("columns[0][orderable]", "false"),
            ("columns[0][search][value]", ""),
            ("columns[0][search][regex]", "false"),
            
            ("columns[1][data]", "KARARNO"),
            ("columns[1][name]", ""),
            ("columns[1][searchable]", "true"),
            ("columns[1][orderable]", "true"),
            ("columns[1][search][value]", ""),
            ("columns[1][search][regex]", "false"),
            
            ("columns[2][data]", "KARARTARIH"),
            ("columns[2][name]", ""),
            ("columns[2][searchable]", "true"),
            ("columns[2][orderable]", "true"),
            ("columns[2][search][value]", ""),
            ("columns[2][search][regex]", "false"),
            
            ("columns[3][data]", "KARAROZETI"),
            ("columns[3][name]", ""),
            ("columns[3][searchable]", "true"),
            ("columns[3][orderable]", "false"),
            ("columns[3][search][value]", ""),
            ("columns[3][search][regex]", "false"),
            
            ("columns[4][data]", ""),
            ("columns[4][name]", ""),
            ("columns[4][searchable]", "true"),
            ("columns[4][orderable]", "false"),
            ("columns[4][search][value]", ""),
            ("columns[4][search][regex]", "false"),
            
            ("order[0][column]", "2"),
            ("order[0][dir]", "desc")
        ]
        form_data.extend(column_defs)
        
        # Add search parameters
        form_data.extend([
            ("KararlarGenelKurulAra.KARARNO", params.karar_no or ""),
            ("__Invariant[]", "KararlarGenelKurulAra.KARARNO"),
            ("__Invariant[]", "KararlarGenelKurulAra.KARAREK"),
            ("KararlarGenelKurulAra.KARAREK", params.karar_ek or ""),
            ("KararlarGenelKurulAra.KARARTARIHBaslangic", params.karar_tarih_baslangic or "Başlangıç Tarihi"),
            ("KararlarGenelKurulAra.KARARTARIHBitis", params.karar_tarih_bitis or "Bitiş Tarihi"), 
            ("KararlarGenelKurulAra.KARARTAMAMI", params.karar_tamami or ""),
            ("__RequestVerificationToken", self.csrf_tokens.get('genel_kurul', ''))
        ])
        
        return form_data

    def _build_temyiz_kurulu_form_data(self, params: TemyizKuruluSearchRequest, draw: int = 1) -> List[Tuple[str, str]]:
        """Build form data for Temyiz Kurulu search request."""
        form_data = self._build_datatables_params(params.start, params.length, draw)
        
        # Add DataTables column definitions (from actual request)
        column_defs = [
            ("columns[0][data]", "TEMYIZTUTANAKTARIHI"),
            ("columns[0][name]", ""),
            ("columns[0][searchable]", "true"),
            ("columns[0][orderable]", "false"),
            ("columns[0][search][value]", ""),
            ("columns[0][search][regex]", "false"),
            
            ("columns[1][data]", "TEMYIZTUTANAKTARIHI"),
            ("columns[1][name]", ""),
            ("columns[1][searchable]", "true"),
            ("columns[1][orderable]", "true"),
            ("columns[1][search][value]", ""),
            ("columns[1][search][regex]", "false"),
            
            ("columns[2][data]", "ILAMDAIRESI"),
            ("columns[2][name]", ""),
            ("columns[2][searchable]", "true"),
            ("columns[2][orderable]", "true"),
            ("columns[2][search][value]", ""),
            ("columns[2][search][regex]", "false"),
            
            ("columns[3][data]", "TEMYIZKARAR"),
            ("columns[3][name]", ""),
            ("columns[3][searchable]", "true"),
            ("columns[3][orderable]", "false"),
            ("columns[3][search][value]", ""),
            ("columns[3][search][regex]", "false"),
            
            ("columns[4][data]", ""),
            ("columns[4][name]", ""),
            ("columns[4][searchable]", "true"),
            ("columns[4][orderable]", "false"),
            ("columns[4][search][value]", ""),
            ("columns[4][search][regex]", "false"),
            
            ("order[0][column]", "1"),
            ("order[0][dir]", "desc")
        ]
        form_data.extend(column_defs)
        
        # Add search parameters
        daire_value = self._enum_to_form_value(params.ilam_dairesi, "daire")
        kamu_idaresi_value = self._enum_to_form_value(params.kamu_idaresi_turu, "kamu_idaresi")
        web_karar_konusu_value = self._enum_to_form_value(params.web_karar_konusu, "web_karar_konusu")
        
        form_data.extend([
            ("KararlarTemyizAra.ILAMDAIRESI", daire_value),
            ("KararlarTemyizAra.YILI", params.yili or ""),
            ("KararlarTemyizAra.KARARTRHBaslangic", params.karar_tarih_baslangic or ""),
            ("KararlarTemyizAra.KARARTRHBitis", params.karar_tarih_bitis or ""),
            ("KararlarTemyizAra.KAMUIDARESITURU", kamu_idaresi_value if kamu_idaresi_value != "Tüm Kurumlar" else ""),
            ("KararlarTemyizAra.ILAMNO", params.ilam_no or ""),
            ("KararlarTemyizAra.DOSYANO", params.dosya_no or ""),
            ("KararlarTemyizAra.TEMYIZTUTANAKNO", params.temyiz_tutanak_no or ""),
            ("__Invariant", "KararlarTemyizAra.TEMYIZTUTANAKNO"),
            ("KararlarTemyizAra.TEMYIZKARAR", params.temyiz_karar or ""),
            ("KararlarTemyizAra.WEBKARARKONUSU", web_karar_konusu_value if web_karar_konusu_value != "Tüm Konular" else ""),
            ("__RequestVerificationToken", self.csrf_tokens.get('temyiz_kurulu', ''))
        ])
        
        return form_data

    def _build_daire_form_data(self, params: DaireSearchRequest, draw: int = 1) -> List[Tuple[str, str]]:
        """Build form data for Daire search request."""
        form_data = self._build_datatables_params(params.start, params.length, draw)
        
        # Add DataTables column definitions (from actual request)
        column_defs = [
            ("columns[0][data]", "YARGILAMADAIRESI"),
            ("columns[0][name]", ""),
            ("columns[0][searchable]", "true"),
            ("columns[0][orderable]", "false"),
            ("columns[0][search][value]", ""),
            ("columns[0][search][regex]", "false"),
            
            ("columns[1][data]", "KARARTRH"),
            ("columns[1][name]", ""),
            ("columns[1][searchable]", "true"),
            ("columns[1][orderable]", "true"),
            ("columns[1][search][value]", ""),
            ("columns[1][search][regex]", "false"),
            
            ("columns[2][data]", "KARARNO"),
            ("columns[2][name]", ""),
            ("columns[2][searchable]", "true"),
            ("columns[2][orderable]", "true"),
            ("columns[2][search][value]", ""),
            ("columns[2][search][regex]", "false"),
            
            ("columns[3][data]", "YARGILAMADAIRESI"),
            ("columns[3][name]", ""),
            ("columns[3][searchable]", "true"),
            ("columns[3][orderable]", "true"),
            ("columns[3][search][value]", ""),
            ("columns[3][search][regex]", "false"),
            
            ("columns[4][data]", "WEBKARARMETNI"),
            ("columns[4][name]", ""),
            ("columns[4][searchable]", "true"),
            ("columns[4][orderable]", "false"),
            ("columns[4][search][value]", ""),
            ("columns[4][search][regex]", "false"),
            
            ("columns[5][data]", ""),
            ("columns[5][name]", ""),
            ("columns[5][searchable]", "true"),
            ("columns[5][orderable]", "false"),
            ("columns[5][search][value]", ""),
            ("columns[5][search][regex]", "false"),
            
            ("order[0][column]", "2"),
            ("order[0][dir]", "desc")
        ]
        form_data.extend(column_defs)
        
        # Add search parameters
        daire_value = self._enum_to_form_value(params.yargilama_dairesi, "daire")
        kamu_idaresi_value = self._enum_to_form_value(params.kamu_idaresi_turu, "kamu_idaresi")
        web_karar_konusu_value = self._enum_to_form_value(params.web_karar_konusu, "web_karar_konusu")
        
        form_data.extend([
            ("KararlarDaireAra.YARGILAMADAIRESI", daire_value),
            ("KararlarDaireAra.KARARTRHBaslangic", params.karar_tarih_baslangic or ""),
            ("KararlarDaireAra.KARARTRHBitis", params.karar_tarih_bitis or ""),
            ("KararlarDaireAra.ILAMNO", params.ilam_no or ""),
            ("KararlarDaireAra.KAMUIDARESITURU", kamu_idaresi_value if kamu_idaresi_value != "Tüm Kurumlar" else ""),
            ("KararlarDaireAra.HESAPYILI", params.hesap_yili or ""),
            ("KararlarDaireAra.WEBKARARKONUSU", web_karar_konusu_value if web_karar_konusu_value != "Tüm Konular" else ""),
            ("KararlarDaireAra.WEBKARARMETNI", params.web_karar_metni or ""),
            ("__RequestVerificationToken", self.csrf_tokens.get('daire', ''))
        ])
        
        return form_data

    async def search_genel_kurul_decisions(self, params: GenelKurulSearchRequest) -> GenelKurulSearchResponse:
        """
        Search Sayıştay Genel Kurul (General Assembly) decisions.
        
        Args:
            params: Search parameters for Genel Kurul decisions
            
        Returns:
            GenelKurulSearchResponse with matching decisions
        """
        # Initialize session if needed
        if 'genel_kurul' not in self.csrf_tokens:
            if not await self._initialize_session_for_endpoint('genel_kurul'):
                raise Exception("Failed to initialize session for Genel Kurul endpoint")
        
        form_data = self._build_genel_kurul_form_data(params)
        encoded_data = urlencode(form_data, encoding='utf-8')
        
        logger.info(f"Searching Genel Kurul decisions with parameters: {params.model_dump(exclude_none=True)}")
        
        try:
            # Update headers with cookies
            headers = self.http_client.headers.copy()
            if self.session_cookies:
                cookie_header = "; ".join([f"{k}={v}" for k, v in self.session_cookies.items()])
                headers["Cookie"] = cookie_header
            
            response = await self.http_client.post(
                self.GENEL_KURUL_ENDPOINT,
                data=encoded_data,
                headers=headers
            )
            response.raise_for_status()
            response_json = response.json()
            
            # Parse response
            decisions = []
            for item in response_json.get('data', []):
                decisions.append(GenelKurulDecision(
                    id=item['Id'],
                    karar_no=item['KARARNO'],
                    karar_tarih=item['KARARTARIH'],
                    karar_ozeti=item['KARAROZETI']
                ))
            
            return GenelKurulSearchResponse(
                decisions=decisions,
                total_records=response_json.get('recordsTotal', 0),
                total_filtered=response_json.get('recordsFiltered', 0),
                draw=response_json.get('draw', 1)
            )
            
        except httpx.RequestError as e:
            logger.error(f"HTTP error during Genel Kurul search: {e}")
            raise
        except Exception as e:
            logger.error(f"Error processing Genel Kurul search: {e}")
            raise

    async def search_temyiz_kurulu_decisions(self, params: TemyizKuruluSearchRequest) -> TemyizKuruluSearchResponse:
        """
        Search Sayıştay Temyiz Kurulu (Appeals Board) decisions.
        
        Args:
            params: Search parameters for Temyiz Kurulu decisions
            
        Returns:
            TemyizKuruluSearchResponse with matching decisions
        """
        # Initialize session if needed
        if 'temyiz_kurulu' not in self.csrf_tokens:
            if not await self._initialize_session_for_endpoint('temyiz_kurulu'):
                raise Exception("Failed to initialize session for Temyiz Kurulu endpoint")
        
        form_data = self._build_temyiz_kurulu_form_data(params)
        encoded_data = urlencode(form_data, encoding='utf-8')
        
        logger.info(f"Searching Temyiz Kurulu decisions with parameters: {params.model_dump(exclude_none=True)}")
        
        try:
            # Update headers with cookies
            headers = self.http_client.headers.copy()
            if self.session_cookies:
                cookie_header = "; ".join([f"{k}={v}" for k, v in self.session_cookies.items()])
                headers["Cookie"] = cookie_header
            
            response = await self.http_client.post(
                self.TEMYIZ_KURULU_ENDPOINT,
                data=encoded_data,
                headers=headers
            )
            response.raise_for_status()
            response_json = response.json()
            
            # Parse response
            decisions = []
            for item in response_json.get('data', []):
                decisions.append(TemyizKuruluDecision(
                    id=item['Id'],
                    temyiz_tutanak_tarihi=item['TEMYIZTUTANAKTARIHI'],
                    ilam_dairesi=item['ILAMDAIRESI'],
                    temyiz_karar=item['TEMYIZKARAR']
                ))
            
            return TemyizKuruluSearchResponse(
                decisions=decisions,
                total_records=response_json.get('recordsTotal', 0),
                total_filtered=response_json.get('recordsFiltered', 0),
                draw=response_json.get('draw', 1)
            )
            
        except httpx.RequestError as e:
            logger.error(f"HTTP error during Temyiz Kurulu search: {e}")
            raise
        except Exception as e:
            logger.error(f"Error processing Temyiz Kurulu search: {e}")
            raise

    async def search_daire_decisions(self, params: DaireSearchRequest) -> DaireSearchResponse:
        """
        Search Sayıştay Daire (Chamber) decisions.
        
        Args:
            params: Search parameters for Daire decisions
            
        Returns:
            DaireSearchResponse with matching decisions
        """
        # Initialize session if needed
        if 'daire' not in self.csrf_tokens:
            if not await self._initialize_session_for_endpoint('daire'):
                raise Exception("Failed to initialize session for Daire endpoint")
        
        form_data = self._build_daire_form_data(params)
        encoded_data = urlencode(form_data, encoding='utf-8')
        
        logger.info(f"Searching Daire decisions with parameters: {params.model_dump(exclude_none=True)}")
        
        try:
            # Update headers with cookies
            headers = self.http_client.headers.copy()
            if self.session_cookies:
                cookie_header = "; ".join([f"{k}={v}" for k, v in self.session_cookies.items()])
                headers["Cookie"] = cookie_header
            
            response = await self.http_client.post(
                self.DAIRE_ENDPOINT,
                data=encoded_data,
                headers=headers
            )
            response.raise_for_status()
            response_json = response.json()
            
            # Parse response
            decisions = []
            for item in response_json.get('data', []):
                decisions.append(DaireDecision(
                    id=item['Id'],
                    yargilama_dairesi=item['YARGILAMADAIRESI'],
                    karar_tarih=item['KARARTRH'],
                    karar_no=item['KARARNO'],
                    ilam_no=item.get('ILAMNO'),  # Use get() to handle None values
                    madde_no=item['MADDENO'],
                    kamu_idaresi_turu=item['KAMUIDARESITURU'],
                    hesap_yili=item['HESAPYILI'],
                    web_karar_konusu=item['WEBKARARKONUSU'],
                    web_karar_metni=item['WEBKARARMETNI']
                ))
            
            return DaireSearchResponse(
                decisions=decisions,
                total_records=response_json.get('recordsTotal', 0),
                total_filtered=response_json.get('recordsFiltered', 0),
                draw=response_json.get('draw', 1)
            )
            
        except httpx.RequestError as e:
            logger.error(f"HTTP error during Daire search: {e}")
            raise
        except Exception as e:
            logger.error(f"Error processing Daire search: {e}")
            raise

    def _convert_html_to_markdown(self, html_content: str) -> Optional[str]:
        """Convert HTML content to Markdown using MarkItDown with BytesIO to avoid filename length issues."""
        if not html_content:
            return None
            
        try:
            # Convert HTML string to bytes and create BytesIO stream
            html_bytes = html_content.encode('utf-8')
            html_stream = io.BytesIO(html_bytes)
            
            # Pass BytesIO stream to MarkItDown to avoid temp file creation
            md_converter = MarkItDown()
            result = md_converter.convert(html_stream)
            markdown_content = result.text_content
            
            logger.info("Successfully converted HTML to Markdown")
            return markdown_content
            
        except Exception as e:
            logger.error(f"Error converting HTML to Markdown: {e}")
            return f"Error converting HTML content: {str(e)}"

    async def get_document_as_markdown(self, decision_id: str, decision_type: str) -> SayistayDocumentMarkdown:
        """
        Retrieve full text of a Sayıştay decision and convert to Markdown.
        
        Args:
            decision_id: Unique decision identifier
            decision_type: Type of decision ('genel_kurul', 'temyiz_kurulu', 'daire')
            
        Returns:
            SayistayDocumentMarkdown with converted content
        """
        logger.info(f"Retrieving document for {decision_type} decision ID: {decision_id}")
        
        # Validate decision_id
        if not decision_id or not decision_id.strip():
            return SayistayDocumentMarkdown(
                decision_id=decision_id,
                decision_type=decision_type,
                source_url="",
                markdown_content=None,
                error_message="Decision ID cannot be empty"
            )
        
        # Map decision type to URL path
        url_path_mapping = {
            'genel_kurul': 'KararlarGenelKurul',
            'temyiz_kurulu': 'KararlarTemyiz',
            'daire': 'KararlarDaire'
        }
        
        if decision_type not in url_path_mapping:
            return SayistayDocumentMarkdown(
                decision_id=decision_id,
                decision_type=decision_type,
                source_url="",
                markdown_content=None,
                error_message=f"Invalid decision type: {decision_type}. Must be one of: {list(url_path_mapping.keys())}"
            )
        
        # Build document URL
        url_path = url_path_mapping[decision_type]
        document_url = f"{self.BASE_URL}/{url_path}/Detay/{decision_id}/"
        
        try:
            # Make HTTP GET request to document URL
            headers = {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "same-origin"
            }
            
            # Include session cookies if available
            if self.session_cookies:
                cookie_header = "; ".join([f"{k}={v}" for k, v in self.session_cookies.items()])
                headers["Cookie"] = cookie_header
            
            response = await self.http_client.get(document_url, headers=headers)
            response.raise_for_status()
            html_content = response.text
            
            if not html_content or not html_content.strip():
                logger.warning(f"Received empty HTML content from {document_url}")
                return SayistayDocumentMarkdown(
                    decision_id=decision_id,
                    decision_type=decision_type,
                    source_url=document_url,
                    markdown_content=None,
                    error_message="Document content is empty"
                )
            
            # Convert HTML to Markdown using existing method
            markdown_content = self._convert_html_to_markdown(html_content)
            
            if markdown_content and "Error converting HTML content" not in markdown_content:
                logger.info(f"Successfully retrieved and converted document {decision_id} to Markdown")
                return SayistayDocumentMarkdown(
                    decision_id=decision_id,
                    decision_type=decision_type,
                    source_url=document_url,
                    markdown_content=markdown_content,
                    retrieval_date=None  # Could add datetime.now().isoformat() if needed
                )
            else:
                return SayistayDocumentMarkdown(
                    decision_id=decision_id,
                    decision_type=decision_type,
                    source_url=document_url,
                    markdown_content=None,
                    error_message=f"Failed to convert HTML to Markdown: {markdown_content}"
                )
                
        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP error {e.response.status_code} when fetching document: {e}"
            logger.error(f"HTTP error fetching document {decision_id}: {error_msg}")
            return SayistayDocumentMarkdown(
                decision_id=decision_id,
                decision_type=decision_type,
                source_url=document_url,
                markdown_content=None,
                error_message=error_msg
            )
        except httpx.RequestError as e:
            error_msg = f"Network error when fetching document: {e}"
            logger.error(f"Network error fetching document {decision_id}: {error_msg}")
            return SayistayDocumentMarkdown(
                decision_id=decision_id,
                decision_type=decision_type,
                source_url=document_url,
                markdown_content=None,
                error_message=error_msg
            )
        except Exception as e:
            error_msg = f"Unexpected error when fetching document: {e}"
            logger.error(f"Unexpected error fetching document {decision_id}: {error_msg}")
            return SayistayDocumentMarkdown(
                decision_id=decision_id,
                decision_type=decision_type,
                source_url=document_url,
                markdown_content=None,
                error_message=error_msg
            )

    async def close_client_session(self):
        """Close HTTP client session."""
        if hasattr(self, 'http_client') and self.http_client and not self.http_client.is_closed:
            await self.http_client.aclose()
            logger.info("SayistayApiClient: HTTP client session closed.")