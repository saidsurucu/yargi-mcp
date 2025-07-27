"""
Web Routes for Yargı MCP Web Interface
"""
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import logging

# Templates setup
templates = Jinja2Templates(directory="templates")

# Router setup
web_router = APIRouter()

logger = logging.getLogger(__name__)

class SearchRequest(BaseModel):
    query: str
    court_type: Optional[str] = None
    date_start: Optional[str] = None
    date_end: Optional[str] = None

class SearchResult(BaseModel):
    id: str
    title: str
    court: str
    date: str
    summary: str
    url: Optional[str] = None

@web_router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Ana sayfa"""
    return templates.TemplateResponse("index.html", {"request": request})

@web_router.post("/api/search")
async def search_api(search_request: SearchRequest):
    """Arama API endpoint'i"""
    try:
        # Import MCP tools here to avoid circular imports
        from yargi_mcp.bedesten_unified_client import search_bedesten_unified
        from yargi_mcp.emsal_client import search_emsal_detailed_decisions
        
        results = []
        
        # Determine which API to call based on court_type
        if not search_request.court_type or search_request.court_type in ["", "yargitay", "danistay"]:
            # Use unified Bedesten API
            try:
                if search_request.court_type == "yargitay":
                    court_types = ["yargitay"]
                elif search_request.court_type == "danistay":
                    court_types = ["danistay"]
                else:
                    court_types = ["yargitay", "danistay", "yerel_hukuk"]
                
                bedesten_results = await search_bedesten_unified(
                    phrase=search_request.query,
                    court_types=court_types,
                    birimAdi="",
                    kararTarihiStart=search_request.date_start,
                    kararTarihiEnd=search_request.date_end,
                    pageSize=10
                )
                
                # Convert bedesten results to our format
                if bedesten_results.get("success") and bedesten_results.get("data"):
                    for item in bedesten_results["data"][:10]:  # Limit to 10 results
                        results.append(SearchResult(
                            id=item.get("documentId", ""),
                            title=item.get("baslik", "Başlık Yok")[:100] + "...",
                            court=get_court_name(item.get("mahkeme", "")),
                            date=format_date(item.get("kararTarihi", "")),
                            summary=item.get("icerik", "")[:200] + "..." if item.get("icerik") else "Özet mevcut değil",
                            url=item.get("url", "")
                        ))
                        
            except Exception as e:
                logger.error(f"Bedesten search error: {e}")
        
        elif search_request.court_type == "emsal":
            # Use Emsal API
            try:
                emsal_results = await search_emsal_detailed_decisions(
                    keyword=search_request.query,
                    pageSize=10
                )
                
                if emsal_results.get("success") and emsal_results.get("data"):
                    for item in emsal_results["data"][:10]:
                        results.append(SearchResult(
                            id=item.get("id", ""),
                            title=item.get("baslik", "Başlık Yok")[:100] + "...",
                            court="Emsal (UYAP)",
                            date=format_date(item.get("tarih", "")),
                            summary=item.get("ozet", "")[:200] + "..." if item.get("ozet") else "Özet mevcut değil",
                            url=item.get("url", "")
                        ))
                        
            except Exception as e:
                logger.error(f"Emsal search error: {e}")
        
        # Convert results to dict for JSON response
        results_dict = [result.dict() for result in results]
        
        return JSONResponse({
            "success": True,
            "results": results_dict,
            "total": len(results_dict),
            "query": search_request.query
        })
        
    except Exception as e:
        logger.error(f"Search API error: {e}")
        return JSONResponse({
            "success": False,
            "error": f"Arama hatası: {str(e)}",
            "results": []
        }, status_code=500)

@web_router.get("/document/{document_id}", response_class=HTMLResponse)
async def view_document(request: Request, document_id: str):
    """Doküman detay sayfası"""
    try:
        # Import document retrieval functions
        from yargi_mcp.bedesten_unified_client import get_bedesten_document_markdown
        
        # Try to get document content
        document_content = await get_bedesten_document_markdown(document_id)
        
        if document_content.get("success"):
            content = document_content.get("content", "İçerik bulunamadı")
            title = document_content.get("title", "Karar Detayı")
        else:
            content = "Doküman içeriği alınamadı."
            title = "Hata"
            
        return templates.TemplateRespon
