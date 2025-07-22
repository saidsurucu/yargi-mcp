# sayistay_mcp_module/unified_client.py
# Unified client for all three Sayıştay decision types

import logging
from typing import Optional, Dict, Any
from urllib.parse import urlparse

from .models import (
    SayistayUnifiedSearchRequest,
    SayistayUnifiedSearchResult,
    SayistayUnifiedDocumentMarkdown,
    GenelKurulSearchRequest,
    TemyizKuruluSearchRequest,
    DaireSearchRequest
)
from .client import SayistayApiClient

logger = logging.getLogger(__name__)

class SayistayUnifiedClient:
    """Unified client that handles all three Sayıştay decision types."""
    
    def __init__(self, request_timeout: float = 60.0):
        self.client = SayistayApiClient(request_timeout)
    
    async def search_unified(self, params: SayistayUnifiedSearchRequest) -> SayistayUnifiedSearchResult:
        """Unified search that routes to appropriate search method based on decision_type."""
        
        if params.decision_type == "genel_kurul":
            # Convert to genel kurul request
            genel_kurul_params = GenelKurulSearchRequest(
                karar_no=params.karar_no,
                karar_ek=params.karar_ek,
                karar_tarih_baslangic=params.karar_tarih_baslangic,
                karar_tarih_bitis=params.karar_tarih_bitis,
                karar_tamami=params.karar_tamami,
                start=params.start,
                length=params.length
            )
            
            result = await self.client.search_genel_kurul_decisions(genel_kurul_params)
            
            # Convert to unified format
            decisions_list = [decision.model_dump() for decision in result.decisions]
            
            return SayistayUnifiedSearchResult(
                decision_type="genel_kurul",
                decisions=decisions_list,
                total_records=result.total_records,
                total_filtered=result.total_filtered,
                draw=result.draw
            )
            
        elif params.decision_type == "temyiz_kurulu":
            # Convert to temyiz kurulu request
            temyiz_params = TemyizKuruluSearchRequest(
                ilam_dairesi=params.ilam_dairesi,
                yili=params.yili,
                karar_tarih_baslangic=params.karar_tarih_baslangic,
                karar_tarih_bitis=params.karar_tarih_bitis,
                kamu_idaresi_turu=params.kamu_idaresi_turu,
                ilam_no=params.ilam_no,
                dosya_no=params.dosya_no,
                temyiz_tutanak_no=params.temyiz_tutanak_no,
                temyiz_karar=params.temyiz_karar,
                web_karar_konusu=params.web_karar_konusu,
                start=params.start,
                length=params.length
            )
            
            result = await self.client.search_temyiz_kurulu_decisions(temyiz_params)
            
            # Convert to unified format
            decisions_list = [decision.model_dump() for decision in result.decisions]
            
            return SayistayUnifiedSearchResult(
                decision_type="temyiz_kurulu",
                decisions=decisions_list,
                total_records=result.total_records,
                total_filtered=result.total_filtered,
                draw=result.draw
            )
            
        elif params.decision_type == "daire":
            # Convert to daire request
            daire_params = DaireSearchRequest(
                yargilama_dairesi=params.yargilama_dairesi,
                karar_tarih_baslangic=params.karar_tarih_baslangic,
                karar_tarih_bitis=params.karar_tarih_bitis,
                ilam_no=params.ilam_no,
                kamu_idaresi_turu=params.kamu_idaresi_turu,
                hesap_yili=params.hesap_yili,
                web_karar_konusu=params.web_karar_konusu,
                web_karar_metni=params.web_karar_metni,
                start=params.start,
                length=params.length
            )
            
            result = await self.client.search_daire_decisions(daire_params)
            
            # Convert to unified format
            decisions_list = [decision.model_dump() for decision in result.decisions]
            
            return SayistayUnifiedSearchResult(
                decision_type="daire",
                decisions=decisions_list,
                total_records=result.total_records,
                total_filtered=result.total_filtered,
                draw=result.draw
            )
        
        else:
            raise ValueError(f"Unsupported decision type: {params.decision_type}")
    
    async def get_document_unified(self, decision_id: str, decision_type: str) -> SayistayUnifiedDocumentMarkdown:
        """Unified document retrieval for all Sayıştay decision types."""
        
        # Use existing client method (decision_type is already a string)
        result = await self.client.get_document_as_markdown(decision_id, decision_type)
        
        return SayistayUnifiedDocumentMarkdown(
            decision_type=decision_type,
            decision_id=result.decision_id,
            source_url=result.source_url,
            document_data=result.model_dump(),
            markdown_content=result.markdown_content,
            error_message=result.error_message
        )
    
    async def close_client_session(self):
        """Close the underlying client session."""
        if hasattr(self.client, 'close_client_session'):
            await self.client.close_client_session()