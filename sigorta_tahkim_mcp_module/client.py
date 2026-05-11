# sigorta_tahkim_mcp_module/client.py

import asyncio
import httpx
from typing import Optional
import logging
import os
import re
import io
import math
from markitdown import MarkItDown

from .models import (
    SigortaTahkimSearchRequest,
    SigortaTahkimDecisionSummary,
    SigortaTahkimSearchResult,
    SigortaTahkimDocumentMarkdown,
    SigortaTahkimSearchWithinMatch,
    SigortaTahkimSearchWithinResult
)

logger = logging.getLogger(__name__)
if not logger.hasHandlers():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


# Turkish-specific lowercase: İ→i, I→ı (Python's str.lower() doesn't handle these)
_TR_UPPER = str.maketrans("İIÇĞÖŞÜ", "iıçğöşü")


def _turkish_lower(text: str) -> str:
    """Lowercase with Turkish İ/I handling."""
    return text.translate(_TR_UPPER).lower()


class SigortaTahkimApiClient:
    """
    API client for searching and retrieving Sigorta Tahkim Komisyonu
    (Insurance Arbitration Commission) decisions using Tavily Search API
    for discovery and direct PDF download for content retrieval.

    The commission publishes quarterly PDF journals ("Hakem Karar Dergisi")
    containing arbitration decisions. There are 64 issues spanning 2010-2025.
    """

    TAVILY_API_URL = "https://api.tavily.com/search"
    BASE_URL = "https://www.sigortatahkim.org"
    PDF_BASE_URL = "https://www.sigortatahkim.org/content/CmsFiles/"
    DOCUMENT_MARKDOWN_CHUNK_SIZE = 5000

    def __init__(self, request_timeout: float = 60.0):
        """Initialize the Sigorta Tahkim API client."""
        self.tavily_api_key = os.getenv("TAVILY_API_KEY")
        if not self.tavily_api_key:
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
        logger.info("SigortaTahkimApiClient: HTTP client session closed.")

    def _get_pdf_filename(self, issue_number: int) -> str:
        """Get the PDF filename for a given journal issue number."""
        if issue_number == 4:
            return "karardergisisayi4.pdf"
        elif 57 <= issue_number <= 61:
            return f"revizekd{issue_number}.pdf"
        else:
            return f"karardrgs{issue_number}.pdf"

    def _extract_issue_number(self, url: str) -> Optional[str]:
        """Extract journal issue number from a sigortatahkim.org URL."""
        # Pattern: karardrgs{N}.pdf
        match = re.search(r'karardrgs(\d+)\.pdf', url, re.IGNORECASE)
        if match:
            return match.group(1)

        # Pattern: revizekd{N}.pdf
        match = re.search(r'revizekd(\d+)\.pdf', url, re.IGNORECASE)
        if match:
            return match.group(1)

        # Pattern: karardergisisayi{N}.pdf
        match = re.search(r'karardergisisayi(\d+)\.pdf', url, re.IGNORECASE)
        if match:
            return match.group(1)

        # Pattern: sayı or sayi in URL path with number
        match = re.search(r'say[ıi]\s*[-:]?\s*(\d+)', url, re.IGNORECASE)
        if match:
            return match.group(1)

        return None

    async def search_decisions(
        self,
        request: SigortaTahkimSearchRequest
    ) -> SigortaTahkimSearchResult:
        """
        Search for Sigorta Tahkim Komisyonu decisions using Tavily API.

        Args:
            request: Search request parameters

        Returns:
            SigortaTahkimSearchResult with matching decisions
        """
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.tavily_api_key}"
            }

            payload = {
                "query": request.keywords,
                "country": "turkey",
                "include_domains": ["sigortatahkim.org"],
                "max_results": request.pageSize,
                "search_depth": "advanced"
            }

            if request.page > 1:
                logger.warning(f"Tavily API doesn't support pagination. Page {request.page} requested.")

            response = await self.http_client.post(
                self.TAVILY_API_URL,
                json=payload,
                headers=headers
            )
            response.raise_for_status()

            data = response.json()
            logger.info(f"Tavily returned {len(data.get('results', []))} results for Sigorta Tahkim")

            decisions = []
            for result in data.get("results", []):
                url = result.get("url", "")
                title = result.get("title", "").strip()
                content = result.get("content", "")[:500]

                issue_num = self._extract_issue_number(url)
                doc_id = issue_num if issue_num else url

                decision = SigortaTahkimDecisionSummary(
                    title=title,
                    document_id=doc_id,
                    content=content,
                    url=url
                )
                decisions.append(decision)

            return SigortaTahkimSearchResult(
                decisions=decisions,
                total_results=len(data.get("results", [])),
                page=request.page,
                pageSize=request.pageSize
            )

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error searching Sigorta Tahkim decisions: {e}")
            if e.response.status_code == 401:
                raise Exception("Tavily API authentication failed. Check API key.")
            raise Exception(f"Failed to search Sigorta Tahkim decisions: {str(e)}")
        except Exception as e:
            logger.error(f"Error searching Sigorta Tahkim decisions: {e}")
            raise Exception(f"Failed to search Sigorta Tahkim decisions: {str(e)}")

    # Regex pattern to split decisions within a journal issue
    DECISION_HEADER_PATTERN = re.compile(
        r'(\d{2}\.\d{2}\.\d{4}\s+Tarih\s+ve\s+K-\d{4}/\d+\s+Sayılı\s+Hakem\s+Kararı)'
    )
    # Minimum body length to distinguish real decisions from TOC entries
    MIN_DECISION_BODY_LENGTH = 1000

    async def _download_and_convert_pdf(self, issue_number: str) -> tuple[str, str]:
        """
        Download a journal issue PDF and convert to markdown.

        Returns:
            Tuple of (markdown_content, pdf_url)
        """
        issue_num = int(issue_number)
        filename = self._get_pdf_filename(issue_num)
        pdf_url = f"{self.PDF_BASE_URL}{filename}"

        logger.info(f"Downloading Sigorta Tahkim PDF: {pdf_url}")

        response = await self.http_client.get(pdf_url, follow_redirects=True)
        response.raise_for_status()

        pdf_stream = io.BytesIO(response.content)
        # markitdown is sync; offload to thread so PDF parsing doesn't block
        # the event-loop / other in-flight MCP requests.
        result = await asyncio.to_thread(
            self.markitdown.convert_stream, pdf_stream, file_extension=".pdf"
        )
        return result.text_content.strip(), pdf_url

    def _split_into_decisions(self, markdown_content: str) -> list[tuple[str, str]]:
        """
        Split markdown content into individual decisions.

        Returns:
            List of (header, body) tuples for decisions with substantial content.
        """
        parts = self.DECISION_HEADER_PATTERN.split(markdown_content)
        decisions = []
        for i in range(1, len(parts) - 1, 2):
            header = parts[i].strip()
            body = parts[i + 1].strip() if i + 1 < len(parts) else ""
            if len(body) >= self.MIN_DECISION_BODY_LENGTH:
                decisions.append((header, body))
        return decisions

    async def get_document_markdown(
        self,
        issue_number: str,
        page_number: int = 1
    ) -> SigortaTahkimDocumentMarkdown:
        """
        Retrieve a Sigorta Tahkim journal issue PDF and convert to Markdown.

        Args:
            issue_number: Journal issue number (e.g., '64')
            page_number: Page number for paginated content (1-indexed)

        Returns:
            SigortaTahkimDocumentMarkdown with paginated content
        """
        try:
            markdown_content, pdf_url = await self._download_and_convert_pdf(issue_number)

            total_length = len(markdown_content)
            total_pages = max(1, math.ceil(total_length / self.DOCUMENT_MARKDOWN_CHUNK_SIZE))

            start_idx = (page_number - 1) * self.DOCUMENT_MARKDOWN_CHUNK_SIZE
            end_idx = start_idx + self.DOCUMENT_MARKDOWN_CHUNK_SIZE
            page_content = markdown_content[start_idx:end_idx]

            return SigortaTahkimDocumentMarkdown(
                document_id=issue_number,
                markdown_content=page_content,
                page_number=page_number,
                total_pages=total_pages,
                source_url=pdf_url
            )

        except ValueError:
            raise Exception(f"Invalid issue number: {issue_number}. Must be a number (e.g., '64').")
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching Sigorta Tahkim issue {issue_number}: {e}")
            raise Exception(f"Failed to fetch journal issue {issue_number}: {str(e)}")
        except Exception as e:
            logger.error(f"Error processing Sigorta Tahkim issue {issue_number}: {e}")
            raise Exception(f"Failed to process journal issue {issue_number}: {str(e)}")

    async def search_within_issue(
        self,
        issue_number: str,
        keyword: str,
        max_results: int = 10
    ) -> SigortaTahkimSearchWithinResult:
        """
        Search for a keyword within a specific journal issue's decisions.

        Downloads the PDF, splits into individual decisions, and returns
        matching decisions sorted by relevance (match count).

        Args:
            issue_number: Journal issue number (e.g., '64')
            keyword: Search keyword or phrase in Turkish
            max_results: Maximum matching decisions to return

        Returns:
            SigortaTahkimSearchWithinResult with matching decisions
        """
        try:
            markdown_content, _ = await self._download_and_convert_pdf(issue_number)
            decisions = self._split_into_decisions(markdown_content)

            logger.info(
                f"Searching '{keyword}' within issue {issue_number}: "
                f"{len(decisions)} decisions found"
            )

            keyword_lower = _turkish_lower(keyword)
            matches = []

            for header, body in decisions:
                body_lower = _turkish_lower(body)
                count = body_lower.count(keyword_lower)
                if count == 0:
                    continue

                # Extract excerpt around the first match
                first_pos = body_lower.find(keyword_lower)
                excerpt_start = max(0, first_pos - 200)
                excerpt_end = min(len(body), first_pos + len(keyword) + 200)
                excerpt = body[excerpt_start:excerpt_end].strip()
                if excerpt_start > 0:
                    excerpt = "..." + excerpt
                if excerpt_end < len(body):
                    excerpt = excerpt + "..."

                matches.append(SigortaTahkimSearchWithinMatch(
                    decision_header=header,
                    relevance_score=count,
                    excerpt=excerpt,
                    body_length=len(body)
                ))

            # Sort by relevance (highest match count first)
            matches.sort(key=lambda m: m.relevance_score, reverse=True)
            matches = matches[:max_results]

            return SigortaTahkimSearchWithinResult(
                issue_number=issue_number,
                keyword=keyword,
                total_decisions=len(decisions),
                matching_decisions=len(matches),
                matches=matches
            )

        except ValueError:
            raise Exception(f"Invalid issue number: {issue_number}. Must be a number (e.g., '64').")
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error in search_within issue {issue_number}: {e}")
            raise Exception(f"Failed to fetch journal issue {issue_number}: {str(e)}")
        except Exception as e:
            logger.error(f"Error in search_within issue {issue_number}: {e}")
            raise Exception(f"Failed to search within issue {issue_number}: {str(e)}")
