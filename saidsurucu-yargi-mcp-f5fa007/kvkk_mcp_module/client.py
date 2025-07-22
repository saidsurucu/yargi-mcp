# kvkk_mcp_module/client.py

import httpx
from bs4 import BeautifulSoup
from typing import List, Optional, Dict, Any
import logging
import os
import re
import io
import math
from urllib.parse import urljoin, urlparse, parse_qs
from markitdown import MarkItDown
from pydantic import HttpUrl

from .models import (
    KvkkSearchRequest,
    KvkkDecisionSummary,
    KvkkSearchResult,
    KvkkDocumentMarkdown
)

logger = logging.getLogger(__name__)
if not logger.hasHandlers():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

class KvkkApiClient:
    """
    API client for searching and retrieving KVKK (Personal Data Protection Authority) decisions
    using Brave Search API for discovery and direct HTTP requests for content retrieval.
    """
    
    BRAVE_API_URL = "https://api.search.brave.com/res/v1/web/search"
    KVKK_BASE_URL = "https://www.kvkk.gov.tr"
    DOCUMENT_MARKDOWN_CHUNK_SIZE = 5000  # Character limit per page
    
    def __init__(self, request_timeout: float = 60.0):
        """Initialize the KVKK API client."""
        self.brave_api_token = os.getenv("BRAVE_API_TOKEN")
        if not self.brave_api_token:
            # Fallback to provided free token
            self.brave_api_token = "BSAuaRKB-dvSDSQxIN0ft1p2k6N82Kq"
            logger.info("Using fallback Brave API token (limited free token)")
        else:
            logger.info("Using Brave API token from environment variable")
        
        self.http_client = httpx.AsyncClient(
            headers={
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            },
            timeout=request_timeout,
            verify=True,
            follow_redirects=True
        )
    
    def _construct_search_query(self, keywords: str) -> str:
        """Construct the search query for Brave API."""
        base_query = 'site:kvkk.gov.tr "karar özeti"'
        if keywords.strip():
            return f"{base_query} {keywords.strip()}"
        return base_query
    
    def _extract_decision_id_from_url(self, url: str) -> Optional[str]:
        """Extract decision ID from KVKK decision URL."""
        try:
            # Example URL: https://www.kvkk.gov.tr/Icerik/7288/2021-1303
            parsed_url = urlparse(url)
            path_parts = parsed_url.path.strip('/').split('/')
            
            if len(path_parts) >= 3 and path_parts[0] == 'Icerik':
                # Extract the decision ID from the path
                decision_id = '/'.join(path_parts[1:])  # e.g., "7288/2021-1303"
                return decision_id
            
        except Exception as e:
            logger.debug(f"Could not extract decision ID from URL {url}: {e}")
        
        return None
    
    def _extract_decision_metadata_from_title(self, title: str) -> Dict[str, Optional[str]]:
        """Extract decision metadata from title string."""
        metadata = {
            "decision_date": None,
            "decision_number": None
        }
        
        if not title:
            return metadata
        
        # Extract decision date (DD/MM/YYYY format)
        date_match = re.search(r'(\d{1,2}/\d{1,2}/\d{4})', title)
        if date_match:
            metadata["decision_date"] = date_match.group(1)
        
        # Extract decision number (YYYY/XXXX format)
        number_match = re.search(r'(\d{4}/\d+)', title)
        if number_match:
            metadata["decision_number"] = number_match.group(1)
        
        return metadata
    
    async def search_decisions(self, params: KvkkSearchRequest) -> KvkkSearchResult:
        """Search for KVKK decisions using Brave API."""
        
        search_query = self._construct_search_query(params.keywords)
        logger.info(f"KvkkApiClient: Searching with query: {search_query}")
        
        try:
            # Calculate offset for pagination
            offset = (params.page - 1) * params.pageSize
            
            response = await self.http_client.get(
                self.BRAVE_API_URL,
                headers={
                    "Accept": "application/json",
                    "Accept-Encoding": "gzip",
                    "x-subscription-token": self.brave_api_token
                },
                params={
                    "q": search_query,
                    "country": "TR",
                    "search_lang": "tr",
                    "ui_lang": "tr-TR",
                    "offset": offset,
                    "count": params.pageSize
                }
            )
            
            response.raise_for_status()
            data = response.json()
            
            # Extract search results
            decisions = []
            web_results = data.get("web", {}).get("results", [])
            
            for result in web_results:
                title = result.get("title", "")
                url = result.get("url", "")
                description = result.get("description", "")
                
                # Extract metadata from title
                metadata = self._extract_decision_metadata_from_title(title)
                
                # Extract decision ID from URL
                decision_id = self._extract_decision_id_from_url(url)
                
                decision = KvkkDecisionSummary(
                    title=title,
                    url=HttpUrl(url) if url else None,
                    description=description,
                    decision_id=decision_id,
                    publication_date=metadata.get("decision_date"),
                    decision_number=metadata.get("decision_number")
                )
                decisions.append(decision)
            
            # Get total results if available
            total_results = None
            query_info = data.get("query", {})
            if "total_results" in query_info:
                total_results = query_info["total_results"]
            
            return KvkkSearchResult(
                decisions=decisions,
                total_results=total_results,
                page=params.page,
                pageSize=params.pageSize,
                query=search_query
            )
            
        except httpx.RequestError as e:
            logger.error(f"KvkkApiClient: HTTP request error during search: {e}")
            return KvkkSearchResult(
                decisions=[], 
                total_results=0, 
                page=params.page, 
                pageSize=params.pageSize,
                query=search_query
            )
        except Exception as e:
            logger.error(f"KvkkApiClient: Unexpected error during search: {e}")
            return KvkkSearchResult(
                decisions=[], 
                total_results=0, 
                page=params.page, 
                pageSize=params.pageSize,
                query=search_query
            )
    
    def _extract_decision_content_from_html(self, html: str, url: str) -> Dict[str, Any]:
        """Extract decision content from KVKK decision page HTML."""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extract title
            title = None
            title_element = soup.find('h3', class_='blog-post-title')
            if title_element:
                title = title_element.get_text(strip=True)
            elif soup.title:
                title = soup.title.get_text(strip=True)
            
            # Extract decision content from the main content div
            content_div = soup.find('div', class_='blog-post-inner')
            if not content_div:
                # Fallback to other possible content containers
                content_div = soup.find('div', style='text-align:justify;')
                if not content_div:
                    logger.warning(f"Could not find decision content div in {url}")
                    return {
                        "title": title,
                        "decision_date": None,
                        "decision_number": None,
                        "subject_summary": None,
                        "html_content": None
                    }
            
            # Extract decision metadata from table
            decision_date = None
            decision_number = None
            subject_summary = None
            
            table = content_div.find('table')
            if table:
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) >= 3:
                        field_name = cells[0].get_text(strip=True)
                        field_value = cells[2].get_text(strip=True)
                        
                        if 'Karar Tarihi' in field_name:
                            decision_date = field_value
                        elif 'Karar No' in field_name:
                            decision_number = field_value
                        elif 'Konu Özeti' in field_name:
                            subject_summary = field_value
            
            return {
                "title": title,
                "decision_date": decision_date,
                "decision_number": decision_number,
                "subject_summary": subject_summary,
                "html_content": str(content_div)
            }
            
        except Exception as e:
            logger.error(f"Error extracting content from HTML for {url}: {e}")
            return {
                "title": None,
                "decision_date": None,
                "decision_number": None,
                "subject_summary": None,
                "html_content": None
            }
    
    def _convert_html_to_markdown(self, html_content: str) -> Optional[str]:
        """Convert HTML content to Markdown using MarkItDown with BytesIO to avoid filename length issues."""
        if not html_content:
            return None
        
        try:
            # Convert HTML string to bytes and create BytesIO stream
            html_bytes = html_content.encode('utf-8')
            html_stream = io.BytesIO(html_bytes)
            
            # Pass BytesIO stream to MarkItDown to avoid temp file creation
            md_converter = MarkItDown(enable_plugins=False)
            result = md_converter.convert(html_stream)
            return result.text_content
        except Exception as e:
            logger.error(f"Error converting HTML to Markdown: {e}")
            return None
    
    async def get_decision_document(self, decision_url: str, page_number: int = 1) -> KvkkDocumentMarkdown:
        """Retrieve and convert a KVKK decision document to paginated Markdown."""
        logger.info(f"KvkkApiClient: Getting decision document from: {decision_url}, page: {page_number}")
        
        try:
            # Fetch the decision page
            response = await self.http_client.get(decision_url)
            response.raise_for_status()
            
            # Extract content from HTML
            extracted_data = self._extract_decision_content_from_html(response.text, decision_url)
            
            # Convert HTML content to Markdown
            full_markdown_content = None
            if extracted_data["html_content"]:
                full_markdown_content = self._convert_html_to_markdown(extracted_data["html_content"])
            
            if not full_markdown_content:
                return KvkkDocumentMarkdown(
                    source_url=HttpUrl(decision_url),
                    title=extracted_data["title"],
                    decision_date=extracted_data["decision_date"],
                    decision_number=extracted_data["decision_number"],
                    subject_summary=extracted_data["subject_summary"],
                    markdown_chunk=None,
                    current_page=page_number,
                    total_pages=0,
                    is_paginated=False,
                    error_message="Could not convert document content to Markdown"
                )
            
            # Calculate pagination
            content_length = len(full_markdown_content)
            total_pages = math.ceil(content_length / self.DOCUMENT_MARKDOWN_CHUNK_SIZE)
            if total_pages == 0:
                total_pages = 1
            
            # Clamp page number to valid range
            current_page_clamped = max(1, min(page_number, total_pages))
            
            # Extract the requested chunk
            start_index = (current_page_clamped - 1) * self.DOCUMENT_MARKDOWN_CHUNK_SIZE
            end_index = start_index + self.DOCUMENT_MARKDOWN_CHUNK_SIZE
            markdown_chunk = full_markdown_content[start_index:end_index]
            
            return KvkkDocumentMarkdown(
                source_url=HttpUrl(decision_url),
                title=extracted_data["title"],
                decision_date=extracted_data["decision_date"],
                decision_number=extracted_data["decision_number"],
                subject_summary=extracted_data["subject_summary"],
                markdown_chunk=markdown_chunk,
                current_page=current_page_clamped,
                total_pages=total_pages,
                is_paginated=(total_pages > 1),
                error_message=None
            )
            
        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP error {e.response.status_code} when fetching decision document"
            logger.error(f"KvkkApiClient: {error_msg}")
            return KvkkDocumentMarkdown(
                source_url=HttpUrl(decision_url),
                title=None,
                decision_date=None,
                decision_number=None,
                subject_summary=None,
                markdown_chunk=None,
                current_page=page_number,
                total_pages=0,
                is_paginated=False,
                error_message=error_msg
            )
        except Exception as e:
            error_msg = f"Unexpected error when fetching decision document: {str(e)}"
            logger.error(f"KvkkApiClient: {error_msg}")
            return KvkkDocumentMarkdown(
                source_url=HttpUrl(decision_url),
                title=None,
                decision_date=None,
                decision_number=None,
                subject_summary=None,
                markdown_chunk=None,
                current_page=page_number,
                total_pages=0,
                is_paginated=False,
                error_message=error_msg
            )
    
    async def close_client_session(self):
        """Close the HTTP client session."""
        if hasattr(self, 'http_client') and self.http_client and not self.http_client.is_closed:
            await self.http_client.aclose()
            logger.info("KvkkApiClient: HTTP client session closed.")