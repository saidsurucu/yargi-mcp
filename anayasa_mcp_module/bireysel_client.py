# anayasa_mcp_module/bireysel_client.py
# Bireysel Başvuru client backed by the new KBB JSON API (see api_client.py).
#
# Same backend as Norm Denetimi, distinguished by kararTipi="BireyselBasvuru".
# The legacy /Ara report-scraping endpoint was retired and now returns HTTP 404.

import logging
import math
from typing import List, Optional

from .api_client import (
    AnayasaApiClient,
    KARAR_TIPI_BIREYSEL,
    DOCUMENT_MARKDOWN_CHUNK_SIZE,
    build_document_url,
    parse_document_url,
    convert_icerik_to_markdown,
    strip_html_text,
)
from .models import (
    AnayasaBireyselReportSearchRequest,
    AnayasaBireyselReportDecisionSummary,
    AnayasaBireyselReportSearchResult,
    AnayasaBireyselBasvuruDocumentMarkdown,
)

logger = logging.getLogger(__name__)
if not logger.hasHandlers():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


class AnayasaBireyselBasvuruApiClient:
    """Bireysel Başvuru search/document client over the KBB JSON API."""

    def __init__(self, request_timeout: float = 60.0):
        self.api = AnayasaApiClient(request_timeout)

    async def search_bireysel_basvuru_report(
        self,
        params: AnayasaBireyselReportSearchRequest,
    ) -> AnayasaBireyselReportSearchResult:
        query = " ".join(t for t in (params.keywords or []) if t).strip()
        payload = await self.api.search(
            karar_tipi=KARAR_TIPI_BIREYSEL,
            query=query,
            page=params.page_to_fetch,
            size=getattr(params, "results_per_page", 10),
        )

        total_records = int(payload.get("total") or 0)
        decisions: List[AnayasaBireyselReportDecisionSummary] = []
        for item in payload.get("data") or []:
            decisions.append(AnayasaBireyselReportDecisionSummary(
                title=item.get("basvuruAdi") or "",
                decision_reference_no=item.get("basvuruNo") or "",
                decision_page_url=build_document_url(KARAR_TIPI_BIREYSEL, item.get("id", "")),
                decision_type_summary=item.get("kararTuruBasvuruSonucuLabel") or "",
                decision_making_body=item.get("kararVerenBirimLabel") or "",
                application_date_summary=item.get("basvuruTarihi") or "",
                decision_date_summary=item.get("kararTarihi") or "",
                application_subject_summary=strip_html_text(item.get("kararKonusu")),
                details=[],
            ))

        return AnayasaBireyselReportSearchResult(
            decisions=decisions,
            total_records_found=total_records,
            retrieved_page_number=params.page_to_fetch,
        )

    async def get_decision_document_as_markdown(
        self,
        document_url_path: str,
        page_number: int = 1,
    ) -> AnayasaBireyselBasvuruDocumentMarkdown:
        karar_tipi, uuid = parse_document_url(document_url_path)
        if karar_tipi is None:
            karar_tipi = KARAR_TIPI_BIREYSEL

        record = await self.api.get_decision(karar_tipi, uuid) if uuid else None

        if not record:
            logger.warning("AnayasaBireyselBasvuruApiClient: No record for %s", document_url_path)
            return AnayasaBireyselBasvuruDocumentMarkdown(
                source_url=document_url_path, markdown_chunk=None,
                current_page=page_number, total_pages=0, is_paginated=False,
            )

        rg_tarihi = record.get("resmiGazeteTarihi") or ""
        rg_sayisi = record.get("resmiGazeteSayisi")
        official_gazette = f"{rg_tarihi} / {rg_sayisi}".strip(" /") if (rg_tarihi or rg_sayisi) else None

        full_markdown = convert_icerik_to_markdown(record.get("icerik"))
        common = dict(
            source_url=document_url_path,
            basvuru_no_from_page=record.get("basvuruNo"),
            karar_tarihi_from_page=record.get("kararTarihi"),
            basvuru_tarihi_from_page=record.get("basvuruTarihi"),
            karari_veren_birim_from_page=record.get("kararVerenBirimLabel"),
            karar_turu_from_page=record.get("kararTuruBasvuruSonucuLabel"),
            resmi_gazete_info_from_page=official_gazette,
        )

        if not full_markdown:
            return AnayasaBireyselBasvuruDocumentMarkdown(
                **common, markdown_chunk=None, current_page=page_number,
                total_pages=0, is_paginated=False,
            )

        total_pages = max(1, math.ceil(len(full_markdown) / DOCUMENT_MARKDOWN_CHUNK_SIZE))
        current_page = max(1, min(page_number, total_pages))
        start = (current_page - 1) * DOCUMENT_MARKDOWN_CHUNK_SIZE
        chunk = full_markdown[start:start + DOCUMENT_MARKDOWN_CHUNK_SIZE]

        return AnayasaBireyselBasvuruDocumentMarkdown(
            **common, markdown_chunk=chunk, current_page=current_page,
            total_pages=total_pages, is_paginated=(total_pages > 1),
        )

    async def close_client_session(self):
        await self.api.close()
        logger.info("AnayasaBireyselBasvuruApiClient: HTTP client session closed.")
