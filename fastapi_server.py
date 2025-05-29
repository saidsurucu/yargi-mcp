import logging
import os
from fastapi import FastAPI, HTTPException, Query
from pydantic import HttpUrl
from typing import Optional, List

from yargitay_mcp_module.client import YargitayOfficialApiClient
from yargitay_mcp_module.models import (
    YargitayDetailedSearchRequest,
    YargitayDocumentMarkdown,
    CompactYargitaySearchResult,
)
from danistay_mcp_module.client import DanistayApiClient
from danistay_mcp_module.models import (
    DanistayKeywordSearchRequest,
    DanistayDetailedSearchRequest,
    DanistayDocumentMarkdown,
    CompactDanistaySearchResult,
)
from emsal_mcp_module.client import EmsalApiClient
from emsal_mcp_module.models import (
    EmsalSearchRequest,
    EmsalDocumentMarkdown,
    CompactEmsalSearchResult,
)
from uyusmazlik_mcp_module.client import UyusmazlikApiClient
from uyusmazlik_mcp_module.models import (
    UyusmazlikSearchRequest,
    UyusmazlikSearchResponse,
    UyusmazlikDocumentMarkdown,
)
from anayasa_mcp_module.client import AnayasaMahkemesiApiClient
from anayasa_mcp_module.bireysel_client import AnayasaBireyselBasvuruApiClient
from anayasa_mcp_module.models import (
    AnayasaNormDenetimiSearchRequest,
    AnayasaSearchResult,
    AnayasaDocumentMarkdown,
    AnayasaBireyselReportSearchRequest,
    AnayasaBireyselReportSearchResult,
    AnayasaBireyselBasvuruDocumentMarkdown,
)
from kik_mcp_module.client import KikApiClient
from kik_mcp_module.models import (
    KikSearchRequest,
    KikSearchResult,
    KikDocumentMarkdown,
)

# --- Logging Configuration Start ---
LOG_DIRECTORY = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(LOG_DIRECTORY, exist_ok=True)
LOG_FILE_PATH = os.path.join(LOG_DIRECTORY, "fastapi_server.log")

root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(threadName)s - %(message)s"
)

file_handler = logging.FileHandler(LOG_FILE_PATH, mode="a", encoding="utf-8")
file_handler.setFormatter(formatter)
file_handler.setLevel(logging.DEBUG)
root_logger.addHandler(file_handler)

console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
console_handler.setLevel(logging.INFO)
root_logger.addHandler(console_handler)

logger = logging.getLogger(__name__)
# --- Logging Configuration End ---

app = FastAPI(title="YargiMCP API")

# Clients will be created on startup
clients = {}

@app.on_event("startup")
async def startup_event():
    clients["yargitay"] = YargitayOfficialApiClient()
    clients["danistay"] = DanistayApiClient()
    clients["emsal"] = EmsalApiClient()
    clients["uyusmazlik"] = UyusmazlikApiClient()
    clients["anayasa_norm"] = AnayasaMahkemesiApiClient()
    clients["anayasa_bireysel"] = AnayasaBireyselBasvuruApiClient()
    clients["kik"] = KikApiClient()
    logger.info("API clients initialized")

@app.on_event("shutdown")
async def shutdown_event():
    for c in clients.values():
        if hasattr(c, "close_client_session"):
            try:
                await c.close_client_session()
            except Exception as exc:  # pragma: no cover
                logger.error(f"Error closing client {c}: {exc}")

# --- Yargitay Endpoints ---
@app.post("/yargitay/search/detailed", response_model=CompactYargitaySearchResult)
async def search_yargitay_detailed(request: YargitayDetailedSearchRequest):
    try:
        api_response = await clients["yargitay"].search_detailed_decisions(request)
        if api_response.data:
            return CompactYargitaySearchResult(
                decisions=api_response.data.data,
                total_records=api_response.data.recordsTotal,
                requested_page=request.pageNumber,
                page_size=request.pageSize,
            )
        return CompactYargitaySearchResult(decisions=[], total_records=0, requested_page=request.pageNumber, page_size=request.pageSize)
    except Exception as e:
        logger.exception("Yargitay search failed")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/yargitay/document/{id}", response_model=YargitayDocumentMarkdown)
async def get_yargitay_document(id: str):
    if not id.strip():
        raise HTTPException(status_code=400, detail="id parametresi gerekli")
    try:
        return await clients["yargitay"].get_decision_document_as_markdown(id)
    except Exception as e:
        logger.exception("Yargitay document fetch failed")
        raise HTTPException(status_code=500, detail=str(e))

# --- Danistay Endpoints ---
@app.post("/danistay/search/keyword", response_model=CompactDanistaySearchResult)
async def search_danistay_keyword(request: DanistayKeywordSearchRequest):
    try:
        api_response = await clients["danistay"].search_keyword_decisions(request)
        if api_response.data:
            return CompactDanistaySearchResult(
                decisions=api_response.data.data,
                total_records=api_response.data.recordsTotal,
                requested_page=request.pageNumber,
                page_size=request.pageSize,
            )
        return CompactDanistaySearchResult(decisions=[], total_records=0, requested_page=request.pageNumber, page_size=request.pageSize)
    except Exception as e:
        logger.exception("Danistay keyword search failed")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/danistay/search/detailed", response_model=CompactDanistaySearchResult)
async def search_danistay_detailed(request: DanistayDetailedSearchRequest):
    try:
        api_response = await clients["danistay"].search_detailed_decisions(request)
        if api_response.data:
            return CompactDanistaySearchResult(
                decisions=api_response.data.data,
                total_records=api_response.data.recordsTotal,
                requested_page=request.pageNumber,
                page_size=request.pageSize,
            )
        return CompactDanistaySearchResult(decisions=[], total_records=0, requested_page=request.pageNumber, page_size=request.pageSize)
    except Exception as e:
        logger.exception("Danistay detailed search failed")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/danistay/document/{id}", response_model=DanistayDocumentMarkdown)
async def get_danistay_document(id: str):
    if not id.strip():
        raise HTTPException(status_code=400, detail="id parametresi gerekli")
    try:
        return await clients["danistay"].get_decision_document_as_markdown(id)
    except Exception as e:
        logger.exception("Danistay document fetch failed")
        raise HTTPException(status_code=500, detail=str(e))

# --- Emsal Endpoints ---
@app.post("/emsal/search", response_model=CompactEmsalSearchResult)
async def search_emsal(request: EmsalSearchRequest):
    try:
        api_response = await clients["emsal"].search_detailed_decisions(request)
        if api_response.data:
            return CompactEmsalSearchResult(
                decisions=api_response.data.data,
                total_records=api_response.data.totalRecords or 0,
                requested_page=request.page_number,
                page_size=request.page_size,
            )
        return CompactEmsalSearchResult(decisions=[], total_records=0, requested_page=request.page_number, page_size=request.page_size)
    except Exception as e:
        logger.exception("Emsal search failed")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/emsal/document/{id}", response_model=EmsalDocumentMarkdown)
async def get_emsal_document(id: str):
    if not id.strip():
        raise HTTPException(status_code=400, detail="id parametresi gerekli")
    try:
        return await clients["emsal"].get_decision_document_as_markdown(id)
    except Exception as e:
        logger.exception("Emsal document fetch failed")
        raise HTTPException(status_code=500, detail=str(e))

# --- Uyusmazlik Endpoints ---
@app.post("/uyusmazlik/search", response_model=UyusmazlikSearchResponse)
async def search_uyusmazlik(request: UyusmazlikSearchRequest):
    try:
        return await clients["uyusmazlik"].search_decisions(request)
    except Exception as e:
        logger.exception("Uyusmazlik search failed")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/uyusmazlik/document", response_model=UyusmazlikDocumentMarkdown)
async def get_uyusmazlik_document(url: HttpUrl = Query(..., alias="url")):
    try:
        return await clients["uyusmazlik"].get_decision_document_as_markdown(str(url))
    except Exception as e:
        logger.exception("Uyusmazlik document fetch failed")
        raise HTTPException(status_code=500, detail=str(e))

# --- Anayasa Norm Denetimi Endpoints ---
@app.post("/anayasa/norm/search", response_model=AnayasaSearchResult)
async def search_anayasa_norm(request: AnayasaNormDenetimiSearchRequest):
    try:
        return await clients["anayasa_norm"].search_norm_denetimi_decisions(request)
    except Exception as e:
        logger.exception("Anayasa norm search failed")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/anayasa/norm/document", response_model=AnayasaDocumentMarkdown)
async def get_anayasa_norm_document(
    url: str = Query(..., alias="url"),
    page_number: Optional[int] = Query(1, ge=1),
):
    if not url.strip():
        raise HTTPException(status_code=400, detail="url parametresi gerekli")
    try:
        return await clients["anayasa_norm"].get_decision_document_as_markdown(url, page_number=page_number)
    except Exception as e:
        logger.exception("Anayasa norm document fetch failed")
        raise HTTPException(status_code=500, detail=str(e))

# --- Anayasa Bireysel Basvuru Endpoints ---
@app.post("/anayasa/bireysel/report", response_model=AnayasaBireyselReportSearchResult)
async def search_anayasa_bireysel_report(request: AnayasaBireyselReportSearchRequest):
    try:
        return await clients["anayasa_bireysel"].search_bireysel_basvuru_report(request)
    except Exception as e:
        logger.exception("Anayasa bireysel report search failed")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/anayasa/bireysel/document", response_model=AnayasaBireyselBasvuruDocumentMarkdown)
async def get_anayasa_bireysel_document(
    url_path: str = Query(..., alias="url_path"),
    page_number: Optional[int] = Query(1, ge=1),
):
    if not url_path.strip() or not url_path.startswith("/BB/"):
        raise HTTPException(status_code=400, detail="url_path parametresi gerekli ve /BB/ ile başlamalı")
    try:
        return await clients["anayasa_bireysel"].get_decision_document_as_markdown(url_path, page_number=page_number)
    except Exception as e:
        logger.exception("Anayasa bireysel document fetch failed")
        raise HTTPException(status_code=500, detail=str(e))

# --- KIK Endpoints ---
@app.post("/kik/search", response_model=KikSearchResult)
async def search_kik(request: KikSearchRequest):
    try:
        return await clients["kik"].search_decisions(request)
    except Exception as e:
        logger.exception("KIK search failed")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/kik/document/{karar_id}", response_model=KikDocumentMarkdown)
async def get_kik_document(karar_id: str, page_number: Optional[int] = Query(1, ge=1)):
    if not karar_id.strip():
        raise HTTPException(status_code=400, detail="karar_id parametresi gerekli")
    try:
        return await clients["kik"].get_decision_document_as_markdown(karar_id_b64=karar_id, page_number=page_number)
    except Exception as e:
        logger.exception("KIK document fetch failed")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
