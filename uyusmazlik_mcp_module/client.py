# uyusmazlik_mcp_module/client.py
#
# Client for the rebuilt Uyuşmazlık Mahkemesi search site
# (https://kararlar.uyusmazlik.gov.tr). The site is an ASP.NET WebForms app:
# searching is a form postback against "/" that returns an HTML page with a
# GridView of results, and each decision is a PDF served from /Uploads/.
#
# The previous AJAX endpoint (/Arama/Search) was retired and now returns 404.

import asyncio
import io
import logging
import re
from typing import Dict, List, Optional
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup
from markitdown import MarkItDown

from .models import (
    UyusmazlikSearchRequest,
    UyusmazlikApiDecisionEntry,
    UyusmazlikSearchResponse,
    UyusmazlikDocumentMarkdown,
)

logger = logging.getLogger(__name__)
if not logger.hasHandlers():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# ASP.NET hidden fields that must be round-tripped on every postback.
_HIDDEN_FIELDS = ("__VIEWSTATE", "__VIEWSTATEGENERATOR", "__EVENTVALIDATION")


class UyusmazlikApiClient:
    BASE_URL = "https://kararlar.uyusmazlik.gov.tr"
    SEARCH_PATH = "/"

    def __init__(self, request_timeout: float = 30.0):
        self.request_timeout = request_timeout
        # A persistent cookie-aware client so ASP.NET session/viewstate are kept.
        self.http_client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers={
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                              "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Origin": self.BASE_URL,
                "Referer": self.BASE_URL + "/",
            },
            timeout=request_timeout,
            verify=False,
            follow_redirects=True,
        )

    @staticmethod
    def _extract_hidden_fields(html_content: str) -> Dict[str, str]:
        soup = BeautifulSoup(html_content, "html.parser")
        fields: Dict[str, str] = {}
        for name in _HIDDEN_FIELDS:
            tag = soup.find("input", attrs={"name": name})
            fields[name] = tag["value"] if tag and tag.has_attr("value") else ""
        return fields

    @staticmethod
    def _parse_results(html_content: str, base_url: str) -> UyusmazlikSearchResponse:
        soup = BeautifulSoup(html_content, "html.parser")

        decisions: List[UyusmazlikApiDecisionEntry] = []
        grid = soup.find("table", id="GridView1")
        if grid:
            rows = grid.find_all("tr")
            for row in rows[1:]:  # skip header row
                cells = row.find_all("td")
                if len(cells) < 4:
                    continue
                # The İşlemler cell holds the PDF "Görüntüle" link. Pager rows also
                # contain <a> tags (javascript:__doPostBack ...), so require a real
                # document link and skip everything else.
                link_tag = cells[3].find(
                    "a", href=lambda h: h and not h.strip().lower().startswith("javascript:")
                )
                if not link_tag:
                    continue
                href = link_tag["href"].strip()
                if "uploads" not in href.lower() and not href.lower().endswith(".pdf"):
                    continue
                document_url = urljoin(base_url + "/", href)
                decisions.append(UyusmazlikApiDecisionEntry(
                    esas_sayisi=cells[0].get_text(strip=True) or None,
                    karar_sayisi=cells[1].get_text(strip=True) or None,
                    karar_tarihi=cells[2].get_text(strip=True) or None,
                    document_url=document_url,
                ))

        # Try to read a "N kayıt/sonuç/karar bulundu" style count if present.
        total_records: Optional[int] = None
        count_match = re.search(r'(\d+)\s*(?:adet\s*)?(?:kayıt|sonuç|karar)\b', html_content, re.IGNORECASE)
        if count_match:
            total_records = int(count_match.group(1))

        return UyusmazlikSearchResponse(decisions=decisions, total_records_found=total_records)

    async def search_decisions(self, params: UyusmazlikSearchRequest) -> UyusmazlikSearchResponse:
        # 1. Load the landing page to obtain a fresh viewstate + session cookie.
        landing = await self.http_client.get(self.SEARCH_PATH)
        landing.raise_for_status()
        form_data = self._extract_hidden_fields(landing.text)

        # 2. Submit the search form.
        form_data.update({
            "txtSearch": params.icerik or "",
            "rblSearchScope": params.search_scope,
            "btnSearch": "Ara",
        })
        if params.case_sensitive:
            form_data["chkCaseSensitive"] = "on"

        logger.info("UyusmazlikApiClient: search icerik=%r scope=%s page=%s",
                    params.icerik, params.search_scope, params.page_number)
        response = await self.http_client.post(
            self.SEARCH_PATH,
            data=form_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        response.raise_for_status()
        html_content = response.text

        # 3. Navigate the GridView pager if a later page is requested.
        if params.page_number > 1:
            page_fields = self._extract_hidden_fields(html_content)
            page_fields.update({
                "txtSearch": params.icerik or "",
                "rblSearchScope": params.search_scope,
                "__EVENTTARGET": "GridView1",
                "__EVENTARGUMENT": f"Page${params.page_number}",
            })
            if params.case_sensitive:
                page_fields["chkCaseSensitive"] = "on"
            page_response = await self.http_client.post(
                self.SEARCH_PATH,
                data=page_fields,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            page_response.raise_for_status()
            html_content = page_response.text

        return self._parse_results(html_content, self.BASE_URL)

    def _convert_pdf_to_markdown(self, pdf_bytes: bytes) -> Optional[str]:
        try:
            pdf_stream = io.BytesIO(pdf_bytes)
            conversion_result = MarkItDown().convert(pdf_stream, file_extension=".pdf")
            return conversion_result.text_content
        except Exception as e:
            logger.error("UyusmazlikApiClient: PDF to Markdown conversion error: %s", e)
            return None

    async def get_decision_document_as_markdown(self, document_url: str) -> UyusmazlikDocumentMarkdown:
        """Fetch an Uyuşmazlık decision PDF and return its content as Markdown."""
        logger.info("UyusmazlikApiClient: Fetching document PDF from %s", document_url)
        try:
            response = await self.http_client.get(
                document_url,
                headers={"Accept": "application/pdf,*/*"},
            )
            response.raise_for_status()
            markdown_content = await asyncio.to_thread(self._convert_pdf_to_markdown, response.content)
            return UyusmazlikDocumentMarkdown(source_url=document_url, markdown_content=markdown_content)
        except httpx.HTTPError as e:
            logger.error("UyusmazlikApiClient: HTTP error fetching document from %s: %s", document_url, e)
            raise

    async def close_client_session(self):
        if hasattr(self, "http_client") and self.http_client and not self.http_client.is_closed:
            await self.http_client.aclose()
            logger.info("UyusmazlikApiClient: HTTP client session closed.")
