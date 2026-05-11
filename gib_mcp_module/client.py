# gib_mcp_module/client.py

import asyncio
import httpx
import io
import logging
import math
from typing import Optional, Any, Dict
from markitdown import MarkItDown

from .models import (
    GibSearchRequest,
    GibOzelgeSummary,
    GibSearchResult,
    GibDocumentMarkdown,
)

logger = logging.getLogger(__name__)
if not logger.hasHandlers():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


class GibApiClient:
    """
    API client for searching and retrieving GİB özelgeler (Turkish Revenue
    Administration tax rulings) via the public gib.gov.tr JSON API.

    The endpoint is a single POST list endpoint; document retrieval is done
    by filtering the same endpoint with an exact `id`.
    """

    BASE_URL = "https://gib.gov.tr/api"
    LIST_PATH = "/gibportal/mevzuat/ozelge/list"
    DOCUMENT_MARKDOWN_CHUNK_SIZE = 5000

    # Fixed filter values required by the backend
    _REQUIRED_STATUS = 2
    _REQUIRED_DELETED = False
    _REQUIRED_KTYPE = 99  # ktype=99 selects özelge
    _SORT_FIELD = "ozelgeTarih"
    _SORT_TYPE = "DESC"

    def __init__(self, request_timeout: float = 60.0):
        self.http_client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers={
                "Accept": "application/json",
                "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.7",
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (compatible; yargi-mcp/1.0; +https://github.com/saidsurucu/yargi-mcp)",
            },
            timeout=request_timeout,
            verify=True,
            follow_redirects=True,
        )

    @staticmethod
    def _normalize_date(value: str, end_of_day: bool = False) -> Optional[str]:
        """
        Accept 'YYYY-MM-DD' or full ISO 8601; always return full ISO 8601.

        GİB backend rejects date-only strings.
        """
        if not value:
            return None
        v = value.strip()
        if not v:
            return None
        # Already ISO with time component
        if "T" in v:
            return v
        # Simple YYYY-MM-DD - expand to start/end of day
        suffix = "T23:59:59.999Z" if end_of_day else "T00:00:00.000Z"
        return f"{v}{suffix}"

    def _build_search_body(self, params: GibSearchRequest) -> Dict[str, Any]:
        body: Dict[str, Any] = {
            "status": self._REQUIRED_STATUS,
            "deleted": self._REQUIRED_DELETED,
            "ktype": self._REQUIRED_KTYPE,
        }

        keywords = params.keywords.strip()
        kanun_no = params.kanunNo.strip()
        # Frontend sets title/kanunNo/description to the SAME value; the backend
        # ORs across them. If the caller supplies both, combine them so kanun_no
        # still biases toward ruling text, while keywords remain primary.
        search_term = keywords or kanun_no
        if keywords and kanun_no and kanun_no not in keywords:
            search_term = f"{keywords} {kanun_no}"
        if search_term:
            body["title"] = search_term
            body["kanunNo"] = search_term
            body["description"] = search_term

        if params.ozelgeNo.strip():
            body["ozelgeNo"] = params.ozelgeNo.strip()

        if params.kanunId and params.kanunId > 0:
            body["kanunIds"] = [params.kanunId]

        start_iso = self._normalize_date(params.ozelgeStartDate, end_of_day=False)
        end_iso = self._normalize_date(params.ozelgeEndDate, end_of_day=True)
        if start_iso:
            body["ozelgeStartDate"] = start_iso
        if end_iso:
            body["ozelgeEndDate"] = end_iso

        return body

    def _build_query_params(self, page_1_indexed: int, page_size: int) -> Dict[str, Any]:
        # API expects 0-indexed page
        zero_indexed = max(0, page_1_indexed - 1)
        return {
            "page": zero_indexed,
            "size": page_size,
            "sortFieldName": self._SORT_FIELD,
            "sortType": self._SORT_TYPE,
        }

    @staticmethod
    def _to_summary(item: Dict[str, Any]) -> Optional[GibOzelgeSummary]:
        if not isinstance(item, dict):
            return None
        raw_id = item.get("id")
        if raw_id is None:
            return None
        try:
            ozelge_id = int(raw_id)
        except (TypeError, ValueError):
            return None
        return GibOzelgeSummary(
            id=ozelge_id,
            ozelgeNo=item.get("ozelgeNo"),
            ozelgeTarih=item.get("ozelgeTarih"),
            title=item.get("title"),
            kanunNo=item.get("kanunNo"),
            kanunTitle=item.get("kanunTitle"),
            siteLink=item.get("siteLink"),
        )

    async def search_ozelge(self, params: GibSearchRequest) -> GibSearchResult:
        """Search GİB özelgeler."""
        body = self._build_search_body(params)
        query = self._build_query_params(params.page, params.pageSize)
        logger.info(
            "GibApiClient: search page=%s size=%s body_keys=%s",
            params.page, params.pageSize, sorted(body.keys()),
        )

        try:
            resp = await self.http_client.post(self.LIST_PATH, params=query, json=body)
            resp.raise_for_status()
            payload = resp.json()
        except httpx.HTTPStatusError as e:
            logger.error("GibApiClient: HTTP %s during search", e.response.status_code)
            return GibSearchResult(
                ozelgeler=[],
                total_results=0,
                total_pages=0,
                current_page=params.page,
                page_size=params.pageSize,
            )
        except Exception as e:
            logger.error("GibApiClient: search request failed: %s", e)
            return GibSearchResult(
                ozelgeler=[],
                total_results=0,
                total_pages=0,
                current_page=params.page,
                page_size=params.pageSize,
            )

        container = (payload or {}).get("resultContainer") or {}
        raw_items = container.get("content") or []

        summaries = []
        for raw in raw_items:
            summary = self._to_summary(raw)
            if summary is not None:
                summaries.append(summary)

        total_results = container.get("totalElements") or 0
        total_pages = container.get("totalPages") or 0
        try:
            total_results = int(total_results)
        except (TypeError, ValueError):
            total_results = 0
        try:
            total_pages = int(total_pages)
        except (TypeError, ValueError):
            total_pages = 0

        return GibSearchResult(
            ozelgeler=summaries,
            total_results=total_results,
            total_pages=total_pages,
            current_page=params.page,
            page_size=params.pageSize,
        )

    def _convert_html_to_markdown(self, html_content: str) -> Optional[str]:
        """Convert HTML content to Markdown using MarkItDown with BytesIO."""
        if not html_content:
            return None
        try:
            html_bytes = html_content.encode("utf-8")
            html_stream = io.BytesIO(html_bytes)
            md_converter = MarkItDown(enable_plugins=False)
            result = md_converter.convert(html_stream)
            return result.text_content
        except Exception as e:
            logger.error("GibApiClient: HTML→Markdown conversion failed: %s", e)
            return None

    @staticmethod
    def _build_header_block(item: Dict[str, Any]) -> str:
        """Build a small Markdown header block summarising the ruling metadata."""
        parts = []
        title = item.get("title")
        if title:
            parts.append(f"# {title}")
        meta_lines = []
        if item.get("ozelgeNo"):
            meta_lines.append(f"**Sayı:** {item['ozelgeNo']}")
        if item.get("ozelgeTarih"):
            meta_lines.append(f"**Tarih:** {item['ozelgeTarih']}")
        if item.get("kanunTitle"):
            kanun_no = item.get("kanunNo")
            if kanun_no:
                meta_lines.append(f"**Kanun:** {item['kanunTitle']} ({kanun_no})")
            else:
                meta_lines.append(f"**Kanun:** {item['kanunTitle']}")
        if item.get("siteLink"):
            meta_lines.append(f"**Kaynak:** {item['siteLink']}")
        if meta_lines:
            parts.append("\n".join(meta_lines))
        return "\n\n".join(parts).strip()

    async def get_ozelge_document(
        self, ozelge_id: int, page_number: int = 1
    ) -> GibDocumentMarkdown:
        """Retrieve a single özelge and return its paginated Markdown form."""
        logger.info(
            "GibApiClient: fetching özelge id=%s page=%s", ozelge_id, page_number
        )

        if not isinstance(ozelge_id, int) or ozelge_id <= 0:
            return GibDocumentMarkdown(
                ozelge_id=ozelge_id if isinstance(ozelge_id, int) else 0,
                current_page=page_number,
                total_pages=0,
                is_paginated=False,
                error_message="ozelge_id must be a positive integer",
            )

        body = {
            "status": self._REQUIRED_STATUS,
            "deleted": self._REQUIRED_DELETED,
            "ktype": self._REQUIRED_KTYPE,
            "id": ozelge_id,
        }
        query = {"page": 0, "size": 1}

        try:
            resp = await self.http_client.post(self.LIST_PATH, params=query, json=body)
            resp.raise_for_status()
            payload = resp.json()
        except httpx.HTTPStatusError as e:
            msg = f"HTTP {e.response.status_code} when fetching özelge {ozelge_id}"
            logger.error("GibApiClient: %s", msg)
            return GibDocumentMarkdown(
                ozelge_id=ozelge_id,
                current_page=page_number,
                total_pages=0,
                is_paginated=False,
                error_message=msg,
            )
        except Exception as e:
            msg = f"Request failed: {e}"
            logger.error("GibApiClient: %s", msg)
            return GibDocumentMarkdown(
                ozelge_id=ozelge_id,
                current_page=page_number,
                total_pages=0,
                is_paginated=False,
                error_message=msg,
            )

        container = (payload or {}).get("resultContainer") or {}
        content = container.get("content") or []
        if not content:
            return GibDocumentMarkdown(
                ozelge_id=ozelge_id,
                current_page=page_number,
                total_pages=0,
                is_paginated=False,
                error_message=f"Özelge {ozelge_id} not found",
            )

        item = content[0] if isinstance(content[0], dict) else {}
        description_html = item.get("description") or ""
        markdown_body = (await asyncio.to_thread(self._convert_html_to_markdown, description_html)) or ""
        header_block = self._build_header_block(item)

        if header_block and markdown_body:
            full_markdown = f"{header_block}\n\n---\n\n{markdown_body}"
        else:
            full_markdown = header_block or markdown_body

        if not full_markdown.strip():
            return GibDocumentMarkdown(
                ozelge_id=ozelge_id,
                ozelge_no=item.get("ozelgeNo"),
                title=item.get("title"),
                ozelge_tarih=item.get("ozelgeTarih"),
                kanun_title=item.get("kanunTitle"),
                kanun_no=item.get("kanunNo"),
                site_link=item.get("siteLink"),
                current_page=page_number,
                total_pages=0,
                is_paginated=False,
                error_message="Document body is empty",
            )

        total_pages = max(
            1, math.ceil(len(full_markdown) / self.DOCUMENT_MARKDOWN_CHUNK_SIZE)
        )
        current_page_clamped = max(1, min(page_number, total_pages))
        start = (current_page_clamped - 1) * self.DOCUMENT_MARKDOWN_CHUNK_SIZE
        end = start + self.DOCUMENT_MARKDOWN_CHUNK_SIZE
        chunk = full_markdown[start:end]

        return GibDocumentMarkdown(
            ozelge_id=ozelge_id,
            ozelge_no=item.get("ozelgeNo"),
            title=item.get("title"),
            ozelge_tarih=item.get("ozelgeTarih"),
            kanun_title=item.get("kanunTitle"),
            kanun_no=item.get("kanunNo"),
            site_link=item.get("siteLink"),
            markdown_chunk=chunk,
            current_page=current_page_clamped,
            total_pages=total_pages,
            is_paginated=total_pages > 1,
            error_message=None,
        )

    async def close_client_session(self):
        if hasattr(self, "http_client") and self.http_client and not self.http_client.is_closed:
            await self.http_client.aclose()
            logger.info("GibApiClient: HTTP client session closed.")
