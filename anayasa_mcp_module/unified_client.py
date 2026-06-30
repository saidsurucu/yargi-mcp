# anayasa_mcp_module/unified_client.py
# Unified client for both Norm Denetimi and Bireysel Başvuru, backed by the new
# KBB JSON API. Routing between the two is by the "decision_type" discriminator
# on search, and by the document URL (?type=...) on document retrieval.

import logging
from typing import Optional, Tuple

from .models import (
    AnayasaUnifiedSearchRequest,
    AnayasaUnifiedSearchResult,
    AnayasaUnifiedDocumentMarkdown,
    AnayasaNormDenetimiSearchRequest,
    AnayasaBireyselReportSearchRequest,
)
from .client import AnayasaMahkemesiApiClient
from .bireysel_client import AnayasaBireyselBasvuruApiClient
from .api_client import (
    KARAR_TIPI_NORM,
    KARAR_TIPI_BIREYSEL,
    parse_document_url,
)

logger = logging.getLogger(__name__)


def normalize_anayasa_document_url(document_url: str) -> Tuple[Optional[str], str]:
    """Detect the AYM decision type from a document URL.

    Returns ``(decision_type, document_url)`` where ``decision_type`` is
    ``"norm_denetimi"``, ``"bireysel_basvuru"``, or ``None`` if it cannot be
    determined. The URL is returned unchanged (kept for backwards compatibility
    with callers that expect a possibly-normalized URL).
    """
    karar_tipi, _ = parse_document_url(document_url)
    if karar_tipi == KARAR_TIPI_NORM:
        return "norm_denetimi", document_url
    if karar_tipi == KARAR_TIPI_BIREYSEL:
        return "bireysel_basvuru", document_url
    return None, document_url


class AnayasaUnifiedClient:
    """Unified client that handles both Norm Denetimi and Bireysel Başvuru searches."""

    def __init__(self, request_timeout: float = 60.0):
        self.norm_client = AnayasaMahkemesiApiClient(request_timeout)
        self.bireysel_client = AnayasaBireyselBasvuruApiClient(request_timeout)

    async def search_unified(self, params: AnayasaUnifiedSearchRequest) -> AnayasaUnifiedSearchResult:
        """Unified search that routes to the appropriate client based on decision_type."""

        if params.decision_type == "norm_denetimi":
            norm_params = AnayasaNormDenetimiSearchRequest(
                keywords_all=params.keywords_all or params.keywords,
                keywords_any=params.keywords_any,
                page_to_fetch=params.page_to_fetch,
                results_per_page=params.results_per_page,
            )
            result = await self.norm_client.search_norm_denetimi_decisions(norm_params)

            return AnayasaUnifiedSearchResult(
                decision_type="norm_denetimi",
                decisions=[d.model_dump() for d in result.decisions],
                total_records_found=result.total_records_found,
                retrieved_page_number=result.retrieved_page_number,
            )

        elif params.decision_type == "bireysel_basvuru":
            bireysel_params = AnayasaBireyselReportSearchRequest(
                keywords=params.keywords or params.keywords_all,
                page_to_fetch=params.page_to_fetch,
                results_per_page=params.results_per_page,
            )
            result = await self.bireysel_client.search_bireysel_basvuru_report(bireysel_params)

            return AnayasaUnifiedSearchResult(
                decision_type="bireysel_basvuru",
                decisions=[d.model_dump() for d in result.decisions],
                total_records_found=result.total_records_found,
                retrieved_page_number=result.retrieved_page_number,
            )

        raise ValueError(f"Unsupported decision type: {params.decision_type}")

    async def get_document_unified(self, document_url: str, page_number: int = 1) -> AnayasaUnifiedDocumentMarkdown:
        """Unified document retrieval that auto-detects the decision type from the URL."""

        decision_type, _ = normalize_anayasa_document_url(document_url)

        if decision_type == "bireysel_basvuru":
            result = await self.bireysel_client.get_decision_document_as_markdown(document_url, page_number)
            return AnayasaUnifiedDocumentMarkdown(
                decision_type="bireysel_basvuru",
                source_url=result.source_url,
                document_data=result.model_dump(mode="json"),
                markdown_chunk=result.markdown_chunk,
                current_page=result.current_page,
                total_pages=result.total_pages,
                is_paginated=result.is_paginated,
            )

        # Default to norm_denetimi (also covers explicit norm_denetimi detection).
        result = await self.norm_client.get_decision_document_as_markdown(document_url, page_number)
        return AnayasaUnifiedDocumentMarkdown(
            decision_type="norm_denetimi",
            source_url=result.source_url,
            document_data=result.model_dump(mode="json"),
            markdown_chunk=result.markdown_chunk,
            current_page=result.current_page,
            total_pages=result.total_pages,
            is_paginated=result.is_paginated,
        )

    async def close_client_session(self):
        """Close both client sessions."""
        await self.norm_client.close_client_session()
        await self.bireysel_client.close_client_session()
