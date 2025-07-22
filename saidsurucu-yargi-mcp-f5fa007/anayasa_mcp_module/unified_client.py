# anayasa_mcp_module/unified_client.py
# Unified client for both Norm Denetimi and Bireysel Başvuru

import logging
from typing import Optional
from urllib.parse import urlparse

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
        
        # Auto-detect decision type based on URL
        parsed_url = urlparse(document_url)
        
        if "normkararlarbilgibankasi" in parsed_url.netloc or "/ND/" in document_url:
            # Norm Denetimi document
            result = await self.norm_client.get_decision_document_as_markdown(document_url, page_number)
            
            return AnayasaUnifiedDocumentMarkdown(
                decision_type="norm_denetimi",
                source_url=result.source_url,
                document_data=result.model_dump(),
                markdown_chunk=result.markdown_chunk,
                current_page=result.current_page,
                total_pages=result.total_pages,
                is_paginated=result.is_paginated
            )
            
        elif "kararlarbilgibankasi" in parsed_url.netloc or "/BB/" in document_url:
            # Bireysel Başvuru document
            result = await self.bireysel_client.get_decision_document_as_markdown(document_url, page_number)
            
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