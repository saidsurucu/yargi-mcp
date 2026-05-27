# anayasa_mcp_module/unified_client.py
# Unified client for both Norm Denetimi and Bireysel Başvuru

import logging
from typing import Optional, Tuple
from urllib.parse import urlparse, urlunparse

from .models import (
    AnayasaUnifiedSearchRequest,
    AnayasaUnifiedSearchResult, 
    AnayasaUnifiedDocumentMarkdown,
    # Removed AnayasaDecisionTypeEnum - now using string literals
    AnayasaNormDenetimiSearchRequest,
    AnayasaBireyselReportSearchRequest
)
from .client import AnayasaMahkemesiApiClient
from .bireysel_client import AnayasaBireyselBasvuruApiClient

logger = logging.getLogger(__name__)

# Canonical hosts per decision type. Norm Denetimi (/ND/) documents live on the
# "norm" subdomain; Bireysel Başvuru (/BB/) documents on the plain subdomain.
# Callers (or upstream search links) sometimes supply the wrong host for a given
# path, which makes the AYM server return 404. We re-key the host off the path.
_NORM_HOST = "normkararlarbilgibankasi.anayasa.gov.tr"
_BIREYSEL_HOST = "kararlarbilgibankasi.anayasa.gov.tr"


def normalize_anayasa_document_url(document_url: str) -> Tuple[Optional[str], str]:
    """Detect the AYM decision type from the URL path and force the correct host.

    Detection is path-based (``/ND/`` vs ``/BB/``) because the path is
    unambiguous, whereas the supplied host may be wrong. Query params and
    fragment are preserved (they are harmless for document fetches).

    Returns ``(decision_type, normalized_url)`` where ``decision_type`` is
    ``"norm_denetimi"``, ``"bireysel_basvuru"``, or ``None`` if it cannot be
    determined (URL returned unchanged in that case).
    """
    parsed = urlparse(document_url)
    path = parsed.path or ""

    if "/ND/" in path:
        decision_type, host = "norm_denetimi", _NORM_HOST
    elif "/BB/" in path:
        decision_type, host = "bireysel_basvuru", _BIREYSEL_HOST
    else:
        # Fall back to host-based detection when the path is uninformative.
        if "normkararlarbilgibankasi" in parsed.netloc:
            return "norm_denetimi", document_url
        if "kararlarbilgibankasi" in parsed.netloc:
            return "bireysel_basvuru", document_url
        return None, document_url

    normalized = urlunparse((
        parsed.scheme or "https",
        host,
        parsed.path,
        parsed.params,
        parsed.query,
        parsed.fragment,
    ))
    return decision_type, normalized


class AnayasaUnifiedClient:
    """Unified client that handles both Norm Denetimi and Bireysel Başvuru searches."""
    
    def __init__(self, request_timeout: float = 60.0):
        self.norm_client = AnayasaMahkemesiApiClient(request_timeout)
        self.bireysel_client = AnayasaBireyselBasvuruApiClient(request_timeout)
    
    async def search_unified(self, params: AnayasaUnifiedSearchRequest) -> AnayasaUnifiedSearchResult:
        """Unified search that routes to appropriate client based on decision_type."""
        
        if params.decision_type == "norm_denetimi":
            # Convert to norm denetimi request
            norm_params = AnayasaNormDenetimiSearchRequest(
                keywords_all=params.keywords_all or params.keywords,
                keywords_any=params.keywords_any,
                application_type=params.decision_type_norm,
                page_to_fetch=params.page_to_fetch,
                results_per_page=params.results_per_page
            )
            
            result = await self.norm_client.search_norm_denetimi_decisions(norm_params)
            
            # Convert to unified format
            decisions_list = [decision.model_dump() for decision in result.decisions]
            
            return AnayasaUnifiedSearchResult(
                decision_type="norm_denetimi",
                decisions=decisions_list,
                total_records_found=result.total_records_found,
                retrieved_page_number=result.retrieved_page_number
            )
            
        elif params.decision_type == "bireysel_basvuru":
            # Convert to bireysel başvuru request
            bireysel_params = AnayasaBireyselReportSearchRequest(
                keywords=params.keywords,
                decision_start_date=params.decision_start_date,
                decision_end_date=params.decision_end_date,
                norm_type=params.norm_type,
                subject_category=params.subject_category,
                page_to_fetch=params.page_to_fetch,
                results_per_page=params.results_per_page
            )
            
            result = await self.bireysel_client.search_bireysel_basvuru_report(bireysel_params)
            
            # Convert to unified format
            decisions_list = [decision.model_dump() for decision in result.decisions]
            
            return AnayasaUnifiedSearchResult(
                decision_type="bireysel_basvuru",
                decisions=decisions_list,
                total_records_found=result.total_records_found,
                retrieved_page_number=result.retrieved_page_number
            )
        
        else:
            raise ValueError(f"Unsupported decision type: {params.decision_type}")
    
    async def get_document_unified(self, document_url: str, page_number: int = 1) -> AnayasaUnifiedDocumentMarkdown:
        """Unified document retrieval that auto-detects the appropriate client."""
        
        # Auto-detect decision type from the path and force the correct host.
        # This repairs malformed URLs (e.g. a /ND/ path on the bireysel host),
        # which otherwise 404 against the AYM server.
        decision_type, normalized_url = normalize_anayasa_document_url(document_url)
        if normalized_url != document_url:
            logger.info(
                f"AnayasaUnifiedClient: Normalized document URL "
                f"'{document_url}' -> '{normalized_url}'"
            )

        if decision_type == "norm_denetimi":
            result = await self.norm_client.get_decision_document_as_markdown(normalized_url, page_number)

            return AnayasaUnifiedDocumentMarkdown(
                decision_type="norm_denetimi",
                source_url=result.source_url,
                document_data=result.model_dump(),
                markdown_chunk=result.markdown_chunk,
                current_page=result.current_page,
                total_pages=result.total_pages,
                is_paginated=result.is_paginated
            )

        elif decision_type == "bireysel_basvuru":
            result = await self.bireysel_client.get_decision_document_as_markdown(normalized_url, page_number)

            return AnayasaUnifiedDocumentMarkdown(
                decision_type="bireysel_basvuru",
                source_url=result.source_url,
                document_data=result.model_dump(),
                markdown_chunk=result.markdown_chunk,
                current_page=result.current_page,
                total_pages=result.total_pages,
                is_paginated=result.is_paginated
            )

        else:
            raise ValueError(f"Cannot determine document type from URL: {document_url}")
    
    async def close_client_session(self):
        """Close both client sessions."""
        if hasattr(self.norm_client, 'close_client_session'):
            await self.norm_client.close_client_session()
        if hasattr(self.bireysel_client, 'close_client_session'):
            await self.bireysel_client.close_client_session()