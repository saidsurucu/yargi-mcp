# bddk_mcp_module/client.py

import httpx
from typing import List, Optional, Dict, Any
import logging
import os
import re
import io
import math
from urllib.parse import urlparse
from markitdown import MarkItDown

from .models import (
    BddkSearchRequest,
    BddkDecisionSummary,
    BddkSearchResult,
    BddkDocumentMarkdown
)

logger = logging.getLogger(__name__)
if not logger.hasHandlers():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

class BddkApiClient:
    """
    API client for searching and retrieving BDDK (Banking Regulation Authority) decisions
    using Tavily Search API for discovery and direct HTTP requests for content retrieval.
    """
    
    TAVILY_API_URL = "https://api.tavily.com/search"
    BDDK_BASE_URL = "https://www.bddk.org.tr"
    DOCUMENT_URL_TEMPLATE = "https://www.bddk.org.tr/Mevzuat/DokumanGetir/{document_id}"
    DOCUMENT_MARKDOWN_CHUNK_SIZE = 5000  # Character limit per page
    
    def __init__(self, request_timeout: float = 60.0):
        """Initialize the BDDK API client."""
        self.tavily_api_key = os.getenv("TAVILY_API_KEY")
        if not self.tavily_api_key:
            # Fallback to development token
            self.tavily_api_key = "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"
            logger.info("Using fallback Tavily API token (development token)")
        else:
            logger.info("Using Tavily API key from environment variable")
        
        self.http_client = httpx.AsyncClient(
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            },
            timeout=httpx.Timeout(request_timeout)
        )
        self.markitdown = MarkItDown()
    
    async def close_client_session(self):
        """Close the HTTP client session."""
        await self.http_client.aclose()
        logger.info("BddkApiClient: HTTP client session closed.")
    
    def _extract_document_id(self, url: str) -> Optional[str]:
        """Extract document ID from BDDK URL."""
        # Primary pattern: https://www.bddk.org.tr/Mevzuat/DokumanGetir/310
        match = re.search(r'/DokumanGetir/(\d+)', url)
        if match:
            return match.group(1)
        
        # Alternative patterns for different BDDK URL formats
        # Pattern: /Liste/55 -> use as document ID
        match = re.search(r'/Liste/(\d+)', url)
        if match:
            return match.group(1)
        
        # Pattern: /EkGetir/13?ekId=381 -> use ekId as document ID
        match = re.search(r'ekId=(\d+)', url)
        if match:
            return match.group(1)
        
        return None
    
    async def search_decisions(
        self,
        request: BddkSearchRequest
    ) -> BddkSearchResult:
        """
        Search for BDDK decisions using Tavily API.
        
        Args:
            request: Search request parameters
            
        Returns:
            BddkSearchResult with matching decisions
        """
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.tavily_api_key}"
            }
            
            # Tavily API request - enhanced for BDDK decision documents
            query = f"{request.keywords} \"Karar Sayısı\""
            payload = {
                "query": query,
                "country": "turkey",
                "include_domains": ["https://www.bddk.org.tr/Mevzuat/DokumanGetir"],
                "max_results": request.pageSize,
                "search_depth": "advanced"
            }
            
            # Calculate offset for pagination
            if request.page > 1:
                # Tavily doesn't have direct pagination, so we'll need to handle this
                # For now, we'll just return empty for pages > 1
                logger.warning(f"Tavily API doesn't support pagination. Page {request.page} requested.")
            
            response = await self.http_client.post(
                self.TAVILY_API_URL,
                json=payload,
                headers=headers
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Log raw Tavily response for debugging
            logger.info(f"Tavily returned {len(data.get('results', []))} results")
            
            # Convert Tavily results to our format
            decisions = []
            for result in data.get("results", []):
                # Extract document ID from URL
                url = result.get("url", "")
                logger.debug(f"Processing URL: {url}")
                doc_id = self._extract_document_id(url)
                if doc_id:
                    decision = BddkDecisionSummary(
                        title=result.get("title", "").replace("[PDF] ", "").strip(),
                        document_id=doc_id,
                        content=result.get("content", "")[:500]  # Limit content length
                    )
                    decisions.append(decision)
                    logger.debug(f"Added decision: {decision.title} (ID: {doc_id})")
                else:
                    logger.warning(f"Could not extract document ID from URL: {url}")
            
            return BddkSearchResult(
                decisions=decisions,
                total_results=len(data.get("results", [])),
                page=request.page,
                pageSize=request.pageSize
            )
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error searching BDDK decisions: {e}")
            if e.response.status_code == 401:
                raise Exception("Tavily API authentication failed. Check API key.")
            raise Exception(f"Failed to search BDDK decisions: {str(e)}")
        except Exception as e:
            logger.error(f"Error searching BDDK decisions: {e}")
            raise Exception(f"Failed to search BDDK decisions: {str(e)}")
    
    async def get_document_markdown(
        self,
        document_id: str,
        page_number: int = 1
    ) -> BddkDocumentMarkdown:
        """
        Retrieve a BDDK document and convert it to Markdown format.
        
        Args:
            document_id: BDDK document ID (e.g., '310')
            page_number: Page number for paginated content (1-indexed)
            
        Returns:
            BddkDocumentMarkdown with paginated content
        """
        try:
            # Try different URL patterns for BDDK documents
            potential_urls = [
                f"https://www.bddk.org.tr/Mevzuat/DokumanGetir/{document_id}",
                f"https://www.bddk.org.tr/Mevzuat/Liste/{document_id}",
                f"https://www.bddk.org.tr/KurumHakkinda/EkGetir/13?ekId={document_id}",
                f"https://www.bddk.org.tr/KurumHakkinda/EkGetir/5?ekId={document_id}"
            ]
            
            document_url = None
            response = None
            
            # Try each URL pattern until one works
            for url in potential_urls:
                try:
                    logger.info(f"Trying BDDK document URL: {url}")
                    response = await self.http_client.get(
                        url,
                        follow_redirects=True
                    )
                    response.raise_for_status()
                    document_url = url
                    break
                except httpx.HTTPStatusError:
                    continue
            
            if not response or not document_url:
                raise Exception(f"Could not find document with ID {document_id}")
            
            logger.info(f"Successfully fetched BDDK document from: {document_url}")
            
            # Determine content type
            content_type = response.headers.get("content-type", "").lower()
            
            # Convert to Markdown based on content type
            if "pdf" in content_type:
                # Handle PDF documents
                pdf_stream = io.BytesIO(response.content)
                result = self.markitdown.convert_stream(pdf_stream, file_extension=".pdf")
                markdown_content = result.text_content
            else:
                # Handle HTML documents
                html_stream = io.BytesIO(response.content)
                result = self.markitdown.convert_stream(html_stream, file_extension=".html")
                markdown_content = result.text_content
            
            # Clean up the markdown content
            markdown_content = markdown_content.strip()
            
            # Calculate pagination
            total_length = len(markdown_content)
            total_pages = math.ceil(total_length / self.DOCUMENT_MARKDOWN_CHUNK_SIZE)
            
            # Extract the requested page
            start_idx = (page_number - 1) * self.DOCUMENT_MARKDOWN_CHUNK_SIZE
            end_idx = start_idx + self.DOCUMENT_MARKDOWN_CHUNK_SIZE
            page_content = markdown_content[start_idx:end_idx]
            
            return BddkDocumentMarkdown(
                document_id=document_id,
                markdown_content=page_content,
                page_number=page_number,
                total_pages=total_pages
            )
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching BDDK document {document_id}: {e}")
            raise Exception(f"Failed to fetch BDDK document: {str(e)}")
        except Exception as e:
            logger.error(f"Error processing BDDK document {document_id}: {e}")
            raise Exception(f"Failed to process BDDK document: {str(e)}")