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

@web_router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Ana sayfa"""
    return templates.TemplateResponse("index.html", {"request": request})

@web_router.post("/api/search")
async def search_api(search_request: SearchRequest):
    """Arama API endpoint'i"""
    try:
        # Basit mock sonuçlar (şimdilik)
        results = [
            {
                "id": "test-1",
                "title": "Örnek Yargıtay Kararı",
                "court": "Yargıtay 1. Hukuk Dairesi",
                "date": "2024-07-27",
                "summary": f"'{search_request.query}' ile ilgili örnek karar özeti..."
            },
            {
                "id": "test-2", 
                "title": "Örnek Danıştay Kararı",
                "court": "Danıştay 5. Daire",
                "date": "2024-07-26",
                "summary": f"'{search_request.query}' konusunda örnek idari karar..."
            }
        ]
        
        return JSONResponse({
            "success": True,
            "results": results,
            "total": len(results),
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
        # Mock document content
        content = f"""
        # Örnek Karar Metni
        
        **Karar ID:** {document_id}
        
        ## Karar Özeti
        Bu örnek bir karar metnider. Gerçek MCP entegrasyonu sonraki aşamada eklenecektir.
        
        ## Hukuki Gerekçe
        Lorem ipsum dolor sit amet, consectetur adipiscing elit...
        
        ## Sonuç
        Karar bu şekilde verilmiştir.
        """
        
        return templates.TemplateResponse("document.html", {
            "request": request,
            "document_id": document_id,
            "title": f"Karar {document_id}",
            "content": content
        })
        
    except Exception as e:
        logger.error(f"Document view error: {e}")
        raise HTTPException(status_code=404, detail="Doküman bulunamadı")
