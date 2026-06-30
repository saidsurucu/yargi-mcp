# anayasa_mcp_module/client.py
# Norm Denetimi client backed by the new KBB JSON API (see api_client.py).
#
# The Anayasa Mahkemesi sites were rebuilt as a single-page app; the old
# HTML-scraping endpoints on normkararlarbilgibankasi.anayasa.gov.tr/Ara now
# return HTTP 404. This client maps the rich legacy request model onto the new
# free-text "query" search and rebuilds the legacy response models from the JSON
# payload so existing tooling keeps working.

import logging
import math
from typing import List, Optional

from .api_client import (
    AnayasaApiClient,
    KARAR_TIPI_NORM,
    DOCUMENT_MARKDOWN_CHUNK_SIZE,
    build_document_url,
    parse_document_url,
    convert_icerik_to_markdown,
    strip_html_text,
)
from .models import (
    AnayasaNormDenetimiSearchRequest,
    AnayasaDecisionSummary,
    AnayasaSearchResult,
    AnayasaDocumentMarkdown,
)

logger = logging.getLogger(__name__)
if not logger.hasHandlers():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


def _build_query(params: AnayasaNormDenetimiSearchRequest) -> str:
    """Derive the free-text query string the new API expects from the legacy model.

    The new endpoint only supports a single full-text "query" field, so the
    keyword lists are flattened. Esas/Karar numbers are appended when no keyword
    is provided so number-based lookups still return results.
    """
    terms: List[str] = []
    for bucket in (params.keywords_all, params.keywords_any):
        if bucket:
            terms.extend(t for t in bucket if t)
    if not terms:
        for value in (params.case_number_esas, params.decision_number_karar):
            if value:
                terms.append(value)
    return " ".join(terms).strip()


class AnayasaMahkemesiApiClient:
    """Norm Denetimi search/document client over the KBB JSON API."""

    def __init__(self, request_timeout: float = 60.0):
        self.api = AnayasaApiClient(request_timeout)

    async def search_norm_denetimi_decisions(
        self,
        params: AnayasaNormDenetimiSearchRequest,
    ) -> AnayasaSearchResult:
        query = _build_query(params)
        payload = await self.api.search(
            karar_tipi=KARAR_TIPI_NORM,
            query=query,
            page=params.page_to_fetch,
            size=params.results_per_page,
        )

        total_records = int(payload.get("total") or 0)
        decisions: List[AnayasaDecisionSummary] = []
        for item in payload.get("data") or []:
            esas_no = item.get("esasNo") or ""
            karar_no = item.get("kararNo") or ""
            if esas_no and karar_no:
                reference = f"E.{esas_no}, K.{karar_no}"
            else:
                reference = esas_no or karar_no or ""
            decisions.append(AnayasaDecisionSummary(
                decision_reference_no=reference,
                decision_page_url=build_document_url(KARAR_TIPI_NORM, item.get("id", "")),
                keywords_found_count=item.get("highlightCount") or 0,
                application_type_summary=item.get("basvuruTuruLabel") or "",
                applicant_summary=item.get("basvuranGenelLabel") or "",
                decision_outcome_summary=strip_html_text(item.get("kararKonusu")),
                decision_date_summary=item.get("kararTarihi") or "",
                reviewed_norms=[],
            ))

        return AnayasaSearchResult(
            decisions=decisions,
            total_records_found=total_records,
            retrieved_page_number=params.page_to_fetch,
        )

    async def get_decision_document_as_markdown(
        self,
        document_url: str,
        page_number: int = 1,
    ) -> AnayasaDocumentMarkdown:
        karar_tipi, uuid = parse_document_url(document_url)
        if karar_tipi is None:
            karar_tipi = KARAR_TIPI_NORM

        record = await self.api.get_decision(karar_tipi, uuid) if uuid else None

        if not record:
            logger.warning("AnayasaMahkemesiApiClient: No record for document_url %s", document_url)
            return AnayasaDocumentMarkdown(
                source_url=document_url, markdown_chunk=None,
                current_page=page_number, total_pages=0, is_paginated=False,
            )

        esas_no = record.get("esasNo") or ""
        karar_no = record.get("kararNo") or ""
        reference = f"E.{esas_no}, K.{karar_no}" if (esas_no and karar_no) else (esas_no or karar_no or "")
        rg_tarihi = record.get("resmiGazeteTarihi") or ""
        rg_sayisi = record.get("resmiGazeteSayisi")
        official_gazette = f"{rg_tarihi} / {rg_sayisi}".strip(" /") if (rg_tarihi or rg_sayisi) else ""

        full_markdown = convert_icerik_to_markdown(record.get("icerik"))
        if not full_markdown:
            return AnayasaDocumentMarkdown(
                source_url=document_url,
                decision_reference_no_from_page=reference,
                decision_date_from_page=record.get("kararTarihi") or "",
                official_gazette_info_from_page=official_gazette,
                markdown_chunk=None, current_page=page_number, total_pages=0, is_paginated=False,
            )

        total_pages = max(1, math.ceil(len(full_markdown) / DOCUMENT_MARKDOWN_CHUNK_SIZE))
        current_page = max(1, min(page_number, total_pages))
        start = (current_page - 1) * DOCUMENT_MARKDOWN_CHUNK_SIZE
        chunk = full_markdown[start:start + DOCUMENT_MARKDOWN_CHUNK_SIZE]

        return AnayasaDocumentMarkdown(
            source_url=document_url,
            decision_reference_no_from_page=reference,
            decision_date_from_page=record.get("kararTarihi") or "",
            official_gazette_info_from_page=official_gazette,
            markdown_chunk=chunk,
            current_page=current_page,
            total_pages=total_pages,
            is_paginated=(total_pages > 1),
        )

    async def close_client_session(self):
        await self.api.close()
        logger.info("AnayasaMahkemesiApiClient (Norm Denetimi): HTTP client session closed.")
