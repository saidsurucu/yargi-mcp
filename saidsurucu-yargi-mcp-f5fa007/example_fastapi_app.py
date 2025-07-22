"""
FastAPI Comprehensive Endpoints with Complete MCP Documentation
This is the complete version with all descriptions and docstrings from MCP server.
"""

import os
from typing import List, Dict, Any, Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException, Query, Depends, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import json

# Import the main MCP app
from mcp_server_main import app as mcp_server

# Create MCP ASGI app
mcp_asgi_app = mcp_server.http_app(path="/mcp")

# Create FastAPI app with MCP lifespan
app = FastAPI(
    title="Yargı MCP API - Turkish Legal Database REST API",
    description="""
    Comprehensive REST API for Turkish Legal Databases with complete MCP tool coverage.
    
    This API provides access to 8 major Turkish legal institutions including:
    • Yargıtay (Court of Cassation) - Supreme civil/criminal court
    • Danıştay (Council of State) - Supreme administrative court  
    • Constitutional Court - Constitutional review and individual applications
    • Competition Authority - Antitrust and merger decisions
    • Public Procurement Authority - Government contracting disputes
    • Court of Accounts - Public audit and accountability
    • Emsal (UYAP Precedents) - Cross-court precedent database
    • Local and Appellate Courts - First and second instance decisions
    
    Features complete coverage of 33 MCP tools with enhanced documentation,
    typed request models, and comprehensive legal context.
    
    Tool Properties (from MCP annotations):
    • Read-only: All tools are read-only and do not modify system state
    • Idempotent: Same inputs produce same outputs for reliable research
    • Open-world search: Search tools explore comprehensive legal databases
    • Deterministic document retrieval: Document tools return consistent content
    """,
    version="1.0.0",
    lifespan=mcp_asgi_app.lifespan
)

# Add CORS middleware
cors_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount MCP server
app.mount("/mcp-server", mcp_asgi_app)

# Response models (keeping from original)
class ToolInfo(BaseModel):
    name: str
    description: str
    parameters: Dict[str, Any]

class ServerInfo(BaseModel):
    name: str
    version: str
    description: str
    tools_count: int
    databases: List[str]
    mcp_endpoint: str
    api_docs: str

class HealthCheck(BaseModel):
    status: str
    timestamp: datetime
    uptime_seconds: Optional[float] = None
    tools_operational: bool

# Track server start time
SERVER_START_TIME = datetime.now()

# MCP tool caller helper
async def call_mcp_tool(tool_name: str, arguments: Dict[str, Any]):
    """Call an MCP tool with given arguments"""
    try:
        tool = mcp_server._tool_manager._tools.get(tool_name)
        if not tool:
            raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")
        result = await tool.fn(**arguments)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tool execution failed: {str(e)}")

# ============================================================================
# COMPREHENSIVE REQUEST MODELS WITH FULL MCP DOCUMENTATION
# ============================================================================

class YargitaySearchRequest(BaseModel):
    """
    Search request for Court of Cassation (Yargıtay) decisions using primary official API.
    
    The Court of Cassation is Turkey's highest court for civil and criminal matters,
    equivalent to a Supreme Court. Provides access to comprehensive supreme court precedents.
    """
    arananKelime: str = Field(
        ..., 
        description="""Keyword to search for with advanced operators:
        • Space between words = OR logic (arsa payı → "arsa" OR "payı")
        • "exact phrase" = Exact match ("arsa payı" → exact phrase)
        • word1+word2 = AND logic (arsa+payı → both words required)
        • word* = Wildcard (bozma* → bozma, bozması, bozmanın, etc.)
        • +"phrase1" +"phrase2" = Multiple required phrases
        • +"required" -"excluded" = Include and exclude
        
        Turkish Examples:
        • Simple OR: arsa payı (~523K results)
        • Exact phrase: "arsa payı" (~22K results)
        • Multiple AND: +"arsa payı" +"bozma sebebi" (~234 results)
        • Wildcard: bozma* (bozma, bozması, bozmanın, etc.)
        • Exclude: +"arsa payı" -"kira sözleşmesi"
        """,
        example='+"mülkiyet hakkı" +"iptal"'
    )
    birimYrgKurulDaire: Optional[str] = Field(
        "", 
        description="""Chamber/board selection (52 options):
        Civil Chambers: 1-23. Hukuk Dairesi
        Criminal Chambers: 1-23. Ceza Dairesi
        General Assemblies: Hukuk Genel Kurulu, Ceza Genel Kurulu
        Special Boards: Hukuk/Ceza Daireleri Başkanlar Kurulu, Büyük Genel Kurulu
        
        Use "" for ALL chambers or specify exact chamber name.
        """,
        example="1. Hukuk Dairesi"
    )
    baslangicTarihi: Optional[str] = Field(None, description="Start date (DD.MM.YYYY)", example="01.01.2020")
    bitisTarihi: Optional[str] = Field(None, description="End date (DD.MM.YYYY)", example="31.12.2024")
    pageSize: int = Field(20, description="Results per page (1-100)", ge=1, le=100, example=20)

class YargitayBedestenSearchRequest(BaseModel):
    """
    Search request for Court of Cassation using Bedesten API (alternative source).
    Complements primary API with different search capabilities and recent decisions.
    """
    phrase: str = Field(
        ..., 
        description="""Aranacak kavram/kelime. İki farklı arama türü desteklenir:
        • Normal arama: "mülkiyet hakkı" - kelimeler ayrı ayrı aranır
        • Tam cümle arama: "\"mülkiyet hakkı\"" - tırnak içindeki ifade aynen aranır
        Tam cümle aramalar daha kesin sonuçlar verir.
        
        Search phrase with exact matching support:
        • Regular search: "mülkiyet hakkı" - searches individual words separately
        • Exact phrase search: "\"mülkiyet hakkı\"" - searches for exact phrase as unit
        Exact phrase search provides more precise results with fewer false positives.
        """,
        example="\"mülkiyet hakkı\""
    )
    birimAdi: Optional[str] = Field(
        None, 
        description="""Daire/Kurul seçimi (52 seçenek - ana API ile aynı):
        • Hukuk daireleri: 1. Hukuk Dairesi - 23. Hukuk Dairesi
        • Ceza daireleri: 1. Ceza Dairesi - 23. Ceza Dairesi
        • Genel kurullar: Hukuk Genel Kurulu, Ceza Genel Kurulu
        • Özel kurullar: Hukuk/Ceza Daireleri Başkanlar Kurulu, Büyük Genel Kurulu
        
        Chamber filtering (52 options - same as primary API):
        • Civil chambers: 1. Hukuk Dairesi through 23. Hukuk Dairesi
        • Criminal chambers: 1. Ceza Dairesi through 23. Ceza Dairesi
        • General assemblies: Hukuk Genel Kurulu, Ceza Genel Kurulu
        • Special boards: Hukuk/Ceza Daireleri Başkanlar Kurulu, Büyük Genel Kurulu
        
        Use None for ALL chambers, or specify exact chamber name.
        """,
        example="1. Hukuk Dairesi"
    )
    kararTarihiStart: Optional[str] = Field(
        None, 
        description="""Karar başlangıç tarihi (ISO 8601 formatı):
        Format: YYYY-MM-DDTHH:MM:SS.000Z
        Örnek: "2024-01-01T00:00:00.000Z" - 1 Ocak 2024'ten itibaren kararlar
        kararTarihiEnd ile birlikte tarih aralığı filtrelemesi için kullanılır.
        
        Decision start date filter (ISO 8601 format):
        Format: YYYY-MM-DDTHH:MM:SS.000Z
        Example: "2024-01-01T00:00:00.000Z" for decisions from Jan 1, 2024
        Use with kararTarihiEnd for date range filtering.
        """,
        example="2024-01-01T00:00:00.000Z"
    )
    kararTarihiEnd: Optional[str] = Field(
        None, 
        description="""Karar bitiş tarihi (ISO 8601 formatı):
        Format: YYYY-MM-DDTHH:MM:SS.000Z
        Örnek: "2024-12-31T23:59:59.999Z" - 31 Aralık 2024'e kadar kararlar
        kararTarihiStart ile birlikte tarih aralığı filtrelemesi için kullanılır.
        
        Decision end date filter (ISO 8601 format):
        Format: YYYY-MM-DDTHH:MM:SS.000Z
        Example: "2024-12-31T23:59:59.999Z" for decisions until Dec 31, 2024
        Use with kararTarihiStart for date range filtering.
        """,
        example="2024-12-31T23:59:59.999Z"
    )
    pageSize: int = Field(20, description="Results per page (1-100)", ge=1, le=100)

class DanistayKeywordSearchRequest(BaseModel):
    """
    Keyword-based search for Council of State (Danıştay) decisions with Boolean logic.
    
    The Council of State is Turkey's highest administrative court, providing final
    rulings on administrative law matters with Boolean keyword operators.
    """
    andKelimeler: List[str] = Field(
        ..., 
        description="ALL keywords must be present (AND logic)",
        example=["idari işlem", "iptal"]
    )
    orKelimeler: Optional[List[str]] = Field(
        None, 
        description="ANY keyword can be present (OR logic)",
        example=["ruhsat", "izin", "lisans"]
    )
    notKelimeler: Optional[List[str]] = Field(
        None, 
        description="EXCLUDE if keywords present (NOT logic)",
        example=["vergi"]
    )
    pageSize: int = Field(20, description="Results per page (1-100)", ge=1, le=100)

class DanistayDetailedSearchRequest(BaseModel):
    """
    Detailed search for Council of State decisions with comprehensive filtering.
    Provides the most comprehensive search capabilities for administrative court decisions.
    """
    daire: Optional[str] = Field(
        None, 
        description="Chamber/Department filter (1. Daire through 17. Daire, special councils)",
        example="3. Daire"
    )
    baslangicTarihi: Optional[str] = Field(None, description="Start date (DD.MM.YYYY)", example="01.01.2020")
    bitisTarihi: Optional[str] = Field(None, description="End date (DD.MM.YYYY)", example="31.12.2024")
    esas: Optional[str] = Field(None, description="Case number (Esas No)", example="2024/123")
    karar: Optional[str] = Field(None, description="Decision number (Karar No)", example="2024/456")

class DanistayBedestenSearchRequest(BaseModel):
    """
    Council of State search using Bedesten API with chamber filtering and exact phrase search.
    Provides access to administrative court decisions with 27 chamber options.
    """
    phrase: str = Field(..., description="Search phrase (supports exact matching with quotes)")
    birimAdi: Optional[str] = Field(
        None, 
        description="""Chamber filtering (27 options):
        Main Councils: Büyük Gen.Kur., İdare Dava Daireleri Kurulu, Vergi Dava Daireleri Kurulu
        Chambers: 1. Daire through 17. Daire
        Military: Askeri Yüksek İdare Mahkemesi chambers
        """,
        example="3. Daire"
    )
    kararTarihiStart: Optional[str] = Field(None, description="Start date (ISO 8601)")
    kararTarihiEnd: Optional[str] = Field(None, description="End date (ISO 8601)")
    pageSize: int = Field(20, description="Results per page", ge=1, le=100)

class EmsalSearchRequest(BaseModel):
    """
    Search Precedent (Emsal) decisions from UYAP system across multiple court levels.
    Provides access to precedent decisions from various Turkish courts.
    """
    keyword: str = Field(..., description="Search keyword across decision texts")
    decision_year_karar: Optional[str] = Field(None, description="Decision year filter", example="2024")
    results_per_page: int = Field(20, description="Results per page", ge=1, le=100)

class UyusmazlikSearchRequest(BaseModel):
    """
    Search Court of Jurisdictional Disputes decisions.
    Resolves jurisdictional disputes between different court systems.
    """
    keywords: List[str] = Field(..., description="Search keywords", example=["görev", "uyuşmazlık"])
    page_to_fetch: int = Field(1, description="Page number", ge=1)

class AnayasaNormSearchRequest(BaseModel):
    """
    Search Constitutional Court norm control (judicial review) decisions.
    Turkey's highest constitutional authority for reviewing law constitutionality.
    """
    keywords_all: List[str] = Field(..., description="All required keywords", example=["eğitim hakkı", "anayasa"])
    period: Optional[str] = Field(None, description="Constitutional period (1=1961, 2=1982)", example="2")
    application_type: Optional[str] = Field(None, description="Application type (1=İptal)", example="1")
    results_per_page: int = Field(20, description="Results per page", ge=1, le=100)

class AnayasaBireyselSearchRequest(BaseModel):
    """
    Search Constitutional Court individual application decisions.
    Human rights violation cases through individual citizen petitions.
    """
    keywords: List[str] = Field(..., description="Search keywords", example=["ifade özgürlüğü", "basın"])
    page_to_fetch: int = Field(1, description="Page number", ge=1)

class KikSearchRequest(BaseModel):
    """
    Search Public Procurement Authority (KİK) decisions.
    Government procurement disputes and regulatory interpretations.
    """
    karar_tipi: Optional[str] = Field(
        None, 
        description="Decision type (rbUyusmazlik=Disputes, rbDuzenleyici=Regulatory, rbMahkeme=Court)",
        example="rbUyusmazlik"
    )
    karar_metni: Optional[str] = Field(None, description="Decision text search", example="ihale iptali")
    basvuru_konusu_ihale: Optional[str] = Field(None, description="Tender subject", example="danışmanlık")
    karar_tarihi_baslangic: Optional[str] = Field(None, description="Start date", example="01.01.2023")

class RekabetSearchRequest(BaseModel):
    """
    Search Competition Authority decisions.
    Antitrust, merger control, and competition law enforcement.
    """
    KararTuru: Optional[str] = Field(
        None, 
        description="Decision type (Birleşme ve Devralma, Rekabet İhlali, Muafiyet, etc.)",
        example="Birleşme ve Devralma"
    )
    PdfText: Optional[str] = Field(
        None, 
        description="Full-text search in decisions. Use quotes for exact phrases.",
        example="\"market definition\" telecommunications"
    )
    YayinlanmaTarihi: Optional[str] = Field(None, description="Publication date", example="01.01.2020")
    page: int = Field(1, description="Page number", ge=1)

class BedestenSearchRequest(BaseModel):
    """
    Generic search request for Bedesten API courts (Yerel Hukuk, İstinaf Hukuk, KYB).
    Supports exact phrase search and date filtering.
    """
    phrase: str = Field(
        ..., 
        description="Search phrase. Use quotes for exact matching: \"legal term\"",
        example="\"sözleşme ihlali\""
    )
    kararTarihiStart: Optional[str] = Field(None, description="Start date (ISO 8601)")
    kararTarihiEnd: Optional[str] = Field(None, description="End date (ISO 8601)")
    pageSize: int = Field(20, description="Results per page", ge=1, le=100)

class SayistaySearchRequest(BaseModel):
    """
    Search Court of Accounts (Sayıştay) decisions.
    Public audit, accountability, and financial oversight decisions.
    """
    keywords: List[str] = Field(..., description="Search keywords", example=["mali sorumluluk", "denetim"])
    page_to_fetch: int = Field(1, description="Page number", ge=1)

# ============================================================================
# BASIC SERVER ENDPOINTS (keeping from original)
# ============================================================================

@app.get("/", response_model=ServerInfo)
async def root():
    """Get comprehensive server information with database coverage"""
    return ServerInfo(
        name="Yargı MCP Server - Turkish Legal Database API",
        version="1.0.0", 
        description="Complete REST API for Turkish legal databases with 33 MCP tools",
        tools_count=len(mcp_server._tool_manager._tools),
        databases=[
            "Yargıtay (Court of Cassation) - 4 tools",
            "Danıştay (Council of State) - 5 tools", 
            "Emsal (UYAP Precedents) - 2 tools",
            "Uyuşmazlık Mahkemesi (Jurisdictional Disputes) - 2 tools",
            "Anayasa Mahkemesi (Constitutional Court) - 4 tools",
            "Kamu İhale Kurulu (Public Procurement) - 2 tools",
            "Rekabet Kurumu (Competition Authority) - 2 tools",
            "Sayıştay (Court of Accounts) - 6 tools",
            "Bedesten API Courts (Local/Appellate/KYB) - 6 tools"
        ],
        mcp_endpoint="/mcp-server/mcp/",
        api_docs="/docs"
    )

@app.get("/health", response_model=HealthCheck)
async def health_check():
    """Health check with comprehensive system status"""
    uptime = (datetime.now() - SERVER_START_TIME).total_seconds()
    return HealthCheck(
        status="healthy",
        timestamp=datetime.now(),
        uptime_seconds=uptime,
        tools_operational=len(mcp_server._tool_manager._tools) == 33
    )

@app.get("/api/tools", response_model=List[ToolInfo])
async def list_tools(
    search: Optional[str] = Query(None, description="Search tools by name or description"),
    database: Optional[str] = Query(None, description="Filter by database name")
):
    """List all 33 MCP tools with filtering capabilities"""
    tools = []
    for tool in mcp_server._tool_manager._tools.values():
        if search and search.lower() not in tool.name.lower() and search.lower() not in tool.description.lower():
            continue
        if database:
            db_lower = database.lower()
            if db_lower not in tool.name.lower() and db_lower not in tool.description.lower():
                continue
        
        params = {}
        if hasattr(tool, 'schema') and tool.schema:
            if hasattr(tool.schema, 'parameters'):
                params = tool.schema.parameters
            elif hasattr(tool.schema, '__annotations__'):
                params = {k: str(v) for k, v in tool.schema.__annotations__.items()}
        
        tools.append(ToolInfo(
            name=tool.name,
            description=tool.description,
            parameters=params
        ))
    return tools

# ============================================================================
# YARGITAY (COURT OF CASSATION) ENDPOINTS - 4 TOOLS
# ============================================================================

@app.post(
    "/api/yargitay/search", 
    tags=["Yargıtay"],
    summary="Search Court of Cassation (Primary API)",
    description="""Search Turkey's Supreme Court for civil and criminal precedents using advanced operators.

Key Features:
• Advanced search: AND (+), OR (space), NOT (-), wildcards (*), exact phrases ("")
• 52 chamber options (23 Civil + 23 Criminal + General Assemblies)
• Date range filtering • Case/decision number filtering • Pagination

Search Examples:
• OR search: property share (finds ANY words)
• Exact phrase: "property share" (finds exact phrase)
• AND required: +"property share" +"annulment reason"
• Wildcard: construct* (construction, constructive, etc.)
• Exclude terms: +"property share" -"construction contract"

Use for supreme court precedent research and legal principle analysis."""
)
async def search_yargitay(request: YargitaySearchRequest):
    """
    Searches Court of Cassation (Yargıtay) decisions using the primary official API.

    The Court of Cassation (Yargıtay) is Turkey's highest court for civil and criminal matters,
    equivalent to a Supreme Court. This tool provides access to the most comprehensive database
    of supreme court precedents with advanced search capabilities and filtering options.

    Key Features:
    • Advanced search operators (AND, OR, wildcards, exclusions)
    • Chamber filtering: 52 options (23 Civil (Hukuk) + 23 Criminal (Ceza) + General Assemblies (Genel Kurullar))
    • Date range filtering with DD.MM.YYYY format
    • Case number filtering (Case No (Esas No) and Decision No (Karar No))
    • Pagination support (1-100 results per page)
    • Multiple sorting options (by case number, decision number, date)

    SEARCH SYNTAX GUIDE:
    • Words with spaces: OR search ("property share" finds ANY of the words)
    • "Quotes": Exact phrase search ("property share" finds exact phrase)
    • Plus sign (+): AND search (property+share requires both words)
    • Asterisk (*): Wildcard (construct* matches variations)
    • Minus sign (-): Exclude terms (avoid unwanted results)

    Common Search Patterns:
    • Simple OR: property share (finds ~523K results)
    • Exact phrase: "property share" (finds ~22K results)
    • Multiple required: +"property share" +"annulment reason (bozma sebebi)" (finds ~234 results)
    • Wildcard expansion: construct* (matches construction, constructive, etc.)
    • Exclude unwanted: +"property share" -"construction contract"

    Use cases:
    • Research supreme court precedents and legal principles
    • Find decisions from specific chambers (Civil (Hukuk) vs Criminal (Ceza))
    • Search for interpretations of specific legal concepts
    • Analyze court reasoning on complex legal issues
    • Track legal developments over time periods

    Returns structured search results with decision metadata. Use get_yargitay_document_markdown()
    to retrieve full decision texts for detailed analysis.
    """
    args = {
        "arananKelime": request.arananKelime,
        "birimYrgKurulDaire": request.birimYrgKurulDaire, 
        "pageSize": request.pageSize
    }
    if request.baslangicTarihi:
        args["baslangicTarihi"] = request.baslangicTarihi
    if request.bitisTarihi:
        args["bitisTarihi"] = request.bitisTarihi
    return await call_mcp_tool("search_yargitay_detailed", args)

@app.post(
    "/api/yargitay/search-bedesten",
    tags=["Yargıtay"], 
    summary="Search Court of Cassation (Bedesten API)",
    description="""Alternative Court of Cassation search with exact phrase matching and recent decisions.

Key Features:
• Exact phrase search: "\"legal term\"" for precise matching
• Regular search: "legal term" for individual word matching  
• 52 chamber filtering options (same as primary API)
• ISO 8601 date filtering • Recent decision coverage

Use alongside primary search for comprehensive coverage. Exact phrase search provides
higher precision with fewer false positives."""
)
async def search_yargitay_bedesten(request: YargitayBedestenSearchRequest):
    """Search Court of Cassation using Bedesten API. Complements primary API for complete coverage."""
    args = {"phrase": request.phrase, "pageSize": request.pageSize}
    if request.birimAdi:
        args["birimAdi"] = request.birimAdi
    if request.kararTarihiStart:
        args["kararTarihiStart"] = request.kararTarihiStart
    if request.kararTarihiEnd:
        args["kararTarihiEnd"] = request.kararTarihiEnd
    return await call_mcp_tool("search_yargitay_bedesten", args)

@app.get(
    "/api/yargitay/document/{decision_id}",
    tags=["Yargıtay"],
    summary="Get Court of Cassation Document (Primary API)", 
    description="""Retrieve complete Court of Cassation decision in Markdown format.

Content includes:
• Complete legal reasoning and precedent analysis
• Detailed examination of lower court decisions  
• Citations of laws, regulations, and prior cases
• Final ruling with legal justification

Perfect for detailed legal analysis, precedent research, and citation building."""
)
async def get_yargitay_document(decision_id: str):
    """Get full Court of Cassation decision text in clean Markdown format."""
    return await call_mcp_tool("get_yargitay_document_markdown", {"id": decision_id})

@app.get(
    "/api/yargitay/bedesten-document/{document_id}",
    tags=["Yargıtay"],
    summary="Get Court of Cassation Document (Bedesten API)",
    description="""Retrieve Court of Cassation decision from Bedesten API in Markdown format.

Features:
• Supports both HTML and PDF source documents
• Clean Markdown conversion with legal structure preserved
• Removes technical artifacts for easy reading
• Compatible with documentId from Bedesten search results"""
)
async def get_yargitay_bedesten_document(document_id: str):
    """Get Court of Cassation document from Bedesten API in Markdown format."""
    return await call_mcp_tool("get_yargitay_bedesten_document_markdown", {"documentId": document_id})

# ============================================================================
# DANISTAY (COUNCIL OF STATE) ENDPOINTS - 5 TOOLS  
# ============================================================================

@app.post(
    "/api/danistay/search-keyword",
    tags=["Danıştay"],
    summary="Search Council of State (Keyword Logic)",
    description="""Search Turkey's highest administrative court using Boolean keyword logic.

Boolean Operators:
• AND keywords: ALL must be present (required terms)
• OR keywords: ANY can be present (alternative terms)  
• NOT keywords: EXCLUDE if present (unwanted terms)

Examples:
• Administrative acts: andKelimeler=["idari işlem", "iptal"]
• Permits/licenses: orKelimeler=["ruhsat", "izin", "lisans"]
• Exclude tax cases: notKelimeler=["vergi"]

Perfect for administrative law research and government action reviews."""
)
async def search_danistay_keyword(request: DanistayKeywordSearchRequest):
    """
    Searches Council of State (Danıştay) decisions using keyword-based logic.

    The Council of State (Danıştay) is Turkey's highest administrative court, responsible for
    reviewing administrative actions and providing administrative law precedents. This tool
    provides flexible keyword-based searching with Boolean logic operators.

    Key Features:
    • Boolean logic operators: AND, OR, NOT combinations
    • Multiple keyword lists for complex search strategies
    • Pagination support (1-100 results per page)
    • Administrative law focus (permits, licenses, public administration)
    • Complement to search_danistay_detailed for comprehensive coverage

    Keyword Logic:
    • andKelimeler: ALL keywords must be present (AND logic)
    • orKelimeler: ANY keyword can be present (OR logic)
    • notAndKelimeler: EXCLUDE if ALL keywords present (NOT AND)
    • notOrKelimeler: EXCLUDE if ANY keyword present (NOT OR)

    Administrative Law Use Cases:
    • Research administrative court precedents
    • Find decisions on specific government agencies
    • Search for rulings on permits (ruhsat) and licenses (izin)
    • Analyze administrative procedure interpretations
    • Study public administration legal principles

    Examples:
    • Simple AND: andKelimeler=["administrative act (idari işlem)", "annulment (iptal)"]
    • OR search: orKelimeler=["permit (ruhsat)", "permission (izin)", "license (lisans)"]
    • Complex: andKelimeler=["municipality (belediye)"], notOrKelimeler=["tax (vergi)"]

    Returns structured search results. Use get_danistay_document_markdown() for full texts.
    For comprehensive Council of State (Danıştay) research, also use search_danistay_detailed and search_danistay_bedesten.
    """
    args = {"andKelimeler": request.andKelimeler, "pageSize": request.pageSize}
    if request.orKelimeler:
        args["orKelimeler"] = request.orKelimeler
    if request.notKelimeler:
        args["notKelimeler"] = request.notKelimeler
    return await call_mcp_tool("search_danistay_by_keyword", args)

@app.post(
    "/api/danistay/search-detailed",
    tags=["Danıştay"],
    summary="Search Council of State (Detailed Criteria)",
    description="""Most comprehensive Council of State search with advanced filtering.

Advanced Filtering:
• Chamber targeting (1. Daire through 17. Daire, special councils)
• Case/decision number ranges • Date range filtering
• Legislation cross-referencing • Multiple sorting options

Use for specialized administrative law research, chamber-specific decisions,
and regulatory compliance analysis."""
)
async def search_danistay_detailed(request: DanistayDetailedSearchRequest):
    """Search Council of State with comprehensive filtering for specialized administrative law research."""
    args = {}
    for field in ["daire", "baslangicTarihi", "bitisTarihi", "esas", "karar"]:
        if getattr(request, field):
            args[field] = getattr(request, field)
    return await call_mcp_tool("search_danistay_detailed", args)

@app.post(
    "/api/danistay/search-bedesten",
    tags=["Danıştay"],
    summary="Search Council of State (Bedesten API)",
    description="""Council of State search via Bedesten API with 27 chamber options and exact phrase search.

Key Features:
• 27 chamber options (Main Councils, 17 Chambers, Military courts)
• Exact phrase search with double quotes for precision
• ISO 8601 date filtering • Alternative data source

Use with other Danıştay tools for complete administrative law coverage."""
)
async def search_danistay_bedesten(request: DanistayBedestenSearchRequest):
    """Search Council of State via Bedesten API. Use with other Danıştay tools for complete coverage."""
    args = {"phrase": request.phrase, "pageSize": request.pageSize}
    for field in ["birimAdi", "kararTarihiStart", "kararTarihiEnd"]:
        if getattr(request, field):
            args[field] = getattr(request, field)
    return await call_mcp_tool("search_danistay_bedesten", args)

@app.get(
    "/api/danistay/document/{decision_id}",
    tags=["Danıştay"],
    summary="Get Council of State Document (Primary API)",
    description="""Retrieve complete administrative court decision in Markdown format.

Content includes:
• Complete administrative law reasoning and precedent analysis
• Review of administrative actions and government decisions
• Citations of administrative laws and regulations
• Final administrative ruling with legal justification

Essential for administrative law research and government compliance analysis."""
)
async def get_danistay_document(decision_id: str):
    """Get full Council of State decision text in clean Markdown format."""
    return await call_mcp_tool("get_danistay_document_markdown", {"id": decision_id})

@app.get(
    "/api/danistay/bedesten-document/{document_id}",
    tags=["Danıştay"],
    summary="Get Council of State Document (Bedesten API)",
    description="""Retrieve Council of State decision from Bedesten API in Markdown format."""
)
async def get_danistay_bedesten_document(document_id: str):
    """Get Council of State document from Bedesten API in Markdown format."""
    return await call_mcp_tool("get_danistay_bedesten_document_markdown", {"documentId": document_id})

# ============================================================================
# BEDESTEN API COURTS (LOCAL/APPELLATE/KYB) - 6 TOOLS
# ============================================================================

@app.post(
    "/api/yerel-hukuk/search",
    tags=["Yerel Hukuk"],
    summary="Search Local Civil Courts",
    description="""Search first-instance civil court decisions using Bedesten API.

Local Civil Courts handle:
• Contract disputes • Property rights • Family law • Tort claims
• Commercial disputes • Consumer protection

Only available tool for local court decisions. Supports exact phrase search
and date filtering for precise legal research."""
)
async def search_yerel_hukuk(request: BedestenSearchRequest):
    """
    Searches Yerel Hukuk Mahkemesi (Local Civil Court) decisions using Bedesten API.
    
    This provides access to local court decisions that are not available through other APIs.
    Currently the only available tool for searching Yerel Hukuk Mahkemesi decisions.
    Local civil courts represent the first instance of civil litigation in Turkey.

    Local Civil Courts handle:
    • Contract disputes and commercial litigation
    • Property rights and real estate disputes
    • Family law matters (divorce, custody, inheritance)
    • Tort claims and compensation cases
    • Consumer protection issues
    • Employment disputes
    
    Returns structured search results with decision metadata. Use get_yerel_hukuk_bedesten_document_markdown()
    to retrieve full decision texts for detailed analysis.
    """
    args = {"phrase": request.phrase, "pageSize": request.pageSize}
    for field in ["kararTarihiStart", "kararTarihiEnd"]:
        if getattr(request, field):
            args[field] = getattr(request, field)
    return await call_mcp_tool("search_yerel_hukuk_bedesten", args)

@app.get("/api/yerel-hukuk/document/{document_id}", tags=["Yerel Hukuk"])
async def get_yerel_hukuk_document(document_id: str):
    """
    Retrieves a Yerel Hukuk Mahkemesi decision document from Bedesten API and converts to Markdown.
    
    This tool fetches complete local court decision texts using documentId from search results.
    Perfect for detailed analysis of first-instance civil court rulings.
    
    Supports both HTML and PDF content types, automatically converting to clean Markdown format.
    Use documentId from search_yerel_hukuk_bedesten results.
    """
    return await call_mcp_tool("get_yerel_hukuk_bedesten_document_markdown", {"documentId": document_id})

@app.post(
    "/api/istinaf-hukuk/search",
    tags=["İstinaf Hukuk"],
    summary="Search Civil Courts of Appeals",
    description="""Search intermediate appellate court decisions using Bedesten API.

İstinaf Courts are intermediate appellate courts handling appeals from local civil courts
before cases reach the Court of Cassation. Only available tool for İstinaf decisions."""
)
async def search_istinaf_hukuk(request: BedestenSearchRequest):
    """
    Searches İstinaf Hukuk Mahkemesi (Civil Court of Appeals) decisions using Bedesten API.

    İstinaf courts are intermediate appellate courts in the Turkish judicial system that handle
    appeals from local civil courts before cases reach Yargıtay (Court of Cassation).
    This is the only available tool for accessing İstinaf Hukuk Mahkemesi decisions.

    Key Features:
    • Date range filtering with ISO 8601 format (YYYY-MM-DDTHH:MM:SS.000Z)
    • Exact phrase search using double quotes: "\"legal term\"" 
    • Regular search for individual keywords
    • Pagination support (1-100 results per page)

    Use cases:
    • Research appellate court precedents
    • Track appeals from specific lower courts
    • Find decisions on specific legal issues at appellate level
    • Analyze intermediate court reasoning before supreme court review

    Returns structured data with decision metadata including dates, case numbers, and summaries.
    Use get_istinaf_hukuk_bedesten_document_markdown() to retrieve full decision texts.
    """
    args = {"phrase": request.phrase, "pageSize": request.pageSize}
    for field in ["kararTarihiStart", "kararTarihiEnd"]:
        if getattr(request, field):
            args[field] = getattr(request, field)
    return await call_mcp_tool("search_istinaf_hukuk_bedesten", args)

@app.get("/api/istinaf-hukuk/document/{document_id}", tags=["İstinaf Hukuk"])
async def get_istinaf_hukuk_document(document_id: str):
    """
    Retrieves the full text of an İstinaf Hukuk Mahkemesi decision document in Markdown format.

    This tool converts the original decision document (HTML or PDF) from Bedesten API
    into clean, readable Markdown format suitable for analysis and processing.

    Input Requirements:
    • documentId: Use the ID from search_istinaf_hukuk_bedesten results
    • Document ID must be non-empty string

    Output Format:
    • Clean Markdown text with proper formatting
    • Preserves legal structure (headers, paragraphs, citations)
    • Removes extraneous HTML/PDF artifacts

    Use for:
    • Reading full appellate court decision texts
    • Legal analysis of İstinaf court reasoning
    • Citation extraction and reference building
    • Content analysis and summarization
    """
    return await call_mcp_tool("get_istinaf_hukuk_bedesten_document_markdown", {"documentId": document_id})

@app.post(
    "/api/kyb/search",
    tags=["KYB"],
    summary="Search Extraordinary Appeals (KYB)",
    description="""Search Kanun Yararına Bozma (Extraordinary Appeal) decisions.

KYB is an extraordinary legal remedy where the Public Prosecutor's Office requests
review of finalized decisions in favor of law and defendants. Very rare but important
legal precedents. Only available tool for KYB decisions."""
)
async def search_kyb(request: BedestenSearchRequest):
    """
    Searches Kanun Yararına Bozma (KYB - Extraordinary Appeal) decisions using Bedesten API.

    KYB is an extraordinary legal remedy in the Turkish judicial system where the
    Public Prosecutor's Office can request review of finalized decisions in favor of
    the law and defendants. This is the only available tool for accessing KYB decisions.

    Key Features:
    • Date range filtering with ISO 8601 format (YYYY-MM-DDTHH:MM:SS.000Z)
    • Exact phrase search using double quotes: "\"extraordinary appeal\""
    • Regular search for individual keywords
    • Pagination support (1-100 results per page)

    Legal Significance:
    • Extraordinary remedy beyond regular appeals
    • Initiated by Public Prosecutor's Office
    • Reviews finalized decisions for legal errors
    • Can benefit defendants retroactively
    • Rare but important legal precedents

    Use cases:
    • Research extraordinary appeal precedents
    • Study prosecutorial challenges to final decisions
    • Analyze legal errors in finalized cases
    • Track KYB success rates and patterns

    Returns structured data with decision metadata. Use get_kyb_bedesten_document_markdown()
    to retrieve full decision texts for detailed analysis.
    """
    args = {"phrase": request.phrase, "pageSize": request.pageSize}
    for field in ["kararTarihiStart", "kararTarihiEnd"]:
        if getattr(request, field):
            args[field] = getattr(request, field)
    return await call_mcp_tool("search_kyb_bedesten", args)

@app.get("/api/kyb/document/{document_id}", tags=["KYB"])
async def get_kyb_document(document_id: str):
    """
    Retrieves the full text of a Kanun Yararına Bozma (KYB) decision document in Markdown format.

    This tool converts the original extraordinary appeal decision document (HTML or PDF)
    from Bedesten API into clean, readable Markdown format for analysis.

    Input Requirements:
    • documentId: Use the ID from search_kyb_bedesten results
    • Document ID must be non-empty string

    Output Format:
    • Clean Markdown text with legal formatting preserved
    • Structured content with headers and citations
    • Removes technical artifacts from source documents

    Special Value for KYB Documents:
    • Contains rare extraordinary appeal reasoning
    • Shows prosecutorial arguments for legal review
    • Documents correction of finalized legal errors
    • Provides precedent for similar extraordinary circumstances

    Use for:
    • Analyzing extraordinary appeal legal reasoning
    • Understanding prosecutorial review criteria
    • Research on legal error correction mechanisms
    • Studying retroactive benefit applications
    """
    return await call_mcp_tool("get_kyb_bedesten_document_markdown", {"documentId": document_id})

# ============================================================================
# ADDITIONAL COURTS - 12 TOOLS
# ============================================================================

@app.post("/api/emsal/search", tags=["Emsal"], summary="Search UYAP Precedents")
async def search_emsal(request: EmsalSearchRequest):
    """
    Searches for Precedent (Emsal) decisions using detailed criteria.

    The Precedent (Emsal) database contains precedent decisions from various Turkish courts
    integrated through the UYAP (National Judiciary Informatics System). This tool provides
    access to a comprehensive collection of court decisions that serve as legal precedents.

    Key Features:
    • Multi-court coverage (BAM, Civil courts, Regional chambers)
    • Keyword-based search across decision texts
    • Court-specific filtering for targeted research
    • Case number filtering (Case No (Esas No) and Decision No (Karar No) with ranges)
    • Date range filtering with DD.MM.YYYY format
    • Multiple sorting options and pagination support

    Court Selection Options:
    • BAM Civil Courts: Higher regional civil courts
    • Civil Courts: Local and first-instance civil courts
    • Regional Civil Chambers: Specialized civil court departments

    Precedent Research Use Cases:
    • Find precedent (emsal) decisions across multiple court levels
    • Research court interpretations of specific legal concepts
    • Analyze consistent legal reasoning patterns
    • Study regional variations in legal decisions
    • Track precedent development over time
    • Compare decisions from different court types

    Returns structured precedent data with court information and decision metadata.
    Use get_emsal_document_markdown() to retrieve full precedent decision texts.
    """
    args = {"keyword": request.keyword, "results_per_page": request.results_per_page}
    if request.decision_year_karar:
        args["decision_year_karar"] = request.decision_year_karar
    return await call_mcp_tool("search_emsal_detailed_decisions", args)

@app.get("/api/emsal/document/{decision_id}", tags=["Emsal"])
async def get_emsal_document(decision_id: str):
    """
    Retrieves the full text of a specific Emsal (UYAP Precedent) decision in Markdown format.

    This tool fetches complete precedent decision documents from the UYAP system and converts
    them to clean, readable Markdown format suitable for legal precedent analysis.

    Input Requirements:
    • decision_id: Decision ID from search_emsal_detailed_decisions results
    • ID must be non-empty string from UYAP Emsal database

    Output Format:
    • Clean Markdown text with legal precedent structure preserved
    • Organized sections: court info, case facts, legal reasoning, conclusion
    • Proper formatting for legal citations and cross-references
    • Removes technical artifacts from source documents

    Precedent Decision Content:
    • Complete court reasoning and legal analysis
    • Detailed examination of legal principles applied
    • Citation of relevant laws, regulations, and prior precedents
    • Final ruling with precedent-setting reasoning
    • Court-specific interpretations and legal standards

    Use for legal precedent research, citation building, and comparative legal analysis.
    """
    return await call_mcp_tool("get_emsal_document_markdown", {"decision_id": decision_id})

@app.post("/api/uyusmazlik/search", tags=["Uyuşmazlık"], summary="Search Jurisdictional Disputes")
async def search_uyusmazlik(request: UyusmazlikSearchRequest):
    """
    Searches for Court of Jurisdictional Disputes (Uyuşmazlık Mahkemesi) decisions.

    The Court of Jurisdictional Disputes (Uyuşmazlık Mahkemesi) resolves jurisdictional disputes between different court systems
    in Turkey, determining which court has jurisdiction over specific cases. This specialized
    court handles conflicts between civil, criminal, and administrative jurisdictions.

    Key Features:
    • Department filtering (Criminal, Civil, General Assembly decisions)
    • Dispute type classification (Jurisdiction vs Judgment disputes)
    • Decision outcome filtering (dispute resolution results)
    • Case number and date range filtering
    • Advanced text search with Boolean logic operators
    • Official Gazette reference search

    Dispute Types:
    • Jurisdictional Disputes (Görev Uyuşmazlığı): Which court has authority
    • Judgment Disputes (Hüküm Uyuşmazlığı): Conflicting final decisions

    Departments:
    • Criminal Section (Ceza Bölümü): Criminal section decisions
    • Civil Section (Hukuk Bölümü): Civil section decisions  
    • General Assembly Decisions (Genel Kurul Kararları): General Assembly decisions

    Use cases:
    • Research jurisdictional precedents
    • Understand court system boundaries
    • Analyze dispute resolution patterns
    • Study inter-court conflict resolution
    • Legal procedure and jurisdiction research

    Returns structured search results with dispute resolution information.
    """
    return await call_mcp_tool("search_uyusmazlik_decisions", {
        "keywords": request.keywords,
        "page_to_fetch": request.page_to_fetch
    })

@app.get("/api/uyusmazlik/document", tags=["Uyuşmazlık"])
async def get_uyusmazlik_document(document_url: str):
    """
    Retrieves the full text of a specific Uyuşmazlık Mahkemesi decision from its URL in Markdown format.

    This tool fetches complete jurisdictional dispute resolution decisions and converts them
    to clean, readable Markdown format suitable for legal analysis of inter-court disputes.

    Input Requirements:
    • document_url: Full URL to the decision document from search_uyusmazlik_decisions results
    • URL must be valid HttpUrl format from official Uyuşmazlık Mahkemesi database

    Output Format:
    • Clean Markdown text with jurisdictional dispute structure preserved
    • Organized sections: dispute facts, jurisdictional analysis, resolution ruling
    • Proper formatting for legal citations and court system references
    • Removes technical artifacts from source documents

    Jurisdictional Dispute Decision Content:
    • Complete analysis of jurisdictional conflicts between court systems
    • Detailed examination of applicable jurisdictional rules
    • Citation of relevant procedural laws and court organization statutes
    • Final resolution determining proper court jurisdiction
    • Reasoning for jurisdictional boundaries and court authority

    Use for understanding court system boundaries, analyzing jurisdictional precedents,
    and legal practice guidance on proper court selection.
    """
    return await call_mcp_tool("get_uyusmazlik_document_markdown_from_url", {"document_url": document_url})

@app.post("/api/anayasa/search-norm", tags=["Anayasa"], summary="Search Constitutional Court (Norm Control)")
async def search_anayasa_norm(request: AnayasaNormSearchRequest):
    """
    Searches Constitutional Court (Anayasa Mahkemesi) norm control decisions with comprehensive filtering.

    The Constitutional Court is Turkey's highest constitutional authority, responsible for judicial
    review of laws, regulations, and constitutional amendments. Norm control (Norm Denetimi) is the
    court's power to review the constitutionality of legal norms.

    Key Features:
    • Boolean keyword search (AND, OR, NOT logic)
    • Constitutional period filtering (1961 vs 1982 Constitution)
    • Case and decision number filtering
    • Date range filtering for review and decision dates
    • Application type classification (İptal, İtiraz, etc.)
    • Applicant filtering (government entities, opposition parties)
    • Official Gazette publication filtering
    • Judicial opinion analysis (dissents, different reasoning)
    • Court member and rapporteur filtering
    • Norm type classification (laws, regulations, decrees)
    • Review outcome filtering (constitutionality determinations)
    • Constitutional basis article referencing

    Constitutional Review Types:
    • Abstract review: Ex ante constitutional control
    • Concrete review: Constitutional questions during litigation
    • Legislative review: Parliamentary acts and government decrees
    • Regulatory review: Administrative regulations and bylaws

    Use cases:
    • Constitutional law research and analysis
    • Legislative drafting constitutional compliance
    • Academic constitutional law study
    • Legal precedent analysis for constitutional questions
    • Government policy constitutional assessment

    Returns structured constitutional court data with comprehensive metadata.
    """
    args = {"keywords_all": request.keywords_all, "results_per_page": request.results_per_page}
    for field in ["period", "application_type"]:
        if getattr(request, field):
            args[field] = getattr(request, field)
    return await call_mcp_tool("search_anayasa_norm_denetimi_decisions", args)

@app.get("/api/anayasa/norm-document", tags=["Anayasa"])
async def get_anayasa_norm_document(document_url: str, page_number: int = 1):
    """Get Constitutional Court norm control decision in paginated Markdown format."""
    return await call_mcp_tool("get_anayasa_norm_denetimi_document_markdown", {
        "document_url": document_url, "page_number": page_number
    })

@app.post("/api/anayasa/search-bireysel", tags=["Anayasa"], summary="Search Constitutional Court (Individual Applications)")
async def search_anayasa_bireysel(request: AnayasaBireyselSearchRequest):
    """
    Search Constitutional Court individual application (Bireysel Başvuru) decisions for human rights violation reports with keyword filtering.
    
    Individual applications allow citizens to petition the Constitutional Court directly for
    violations of fundamental rights and freedoms. This tool generates decision search reports
    that help identify relevant human rights violation cases.
    
    Key Features:
    • Keyword-based search with AND logic
    • Human rights violation case identification
    • Individual petition decision analysis
    • Fundamental rights and freedoms research
    • Pagination support for large result sets
    
    Individual Application System:
    • Direct citizen access to Constitutional Court
    • Human rights and fundamental freedoms protection
    • Alternative to European Court of Human Rights
    • Domestic remedy for constitutional violations
    • Individual justice and rights enforcement
    
    Human Rights Categories:
    • Right to life and personal liberty
    • Right to fair trial and due process
    • Freedom of expression and press
    • Freedom of religion and conscience
    • Property rights and economic freedoms
    • Right to privacy and family life
    • Political rights and democratic participation
    
    Use cases:
    • Human rights violation research
    • Individual petition precedent analysis
    • Constitutional rights interpretation study
    • Legal remedies for rights violations
    • Academic human rights law research
    • Civil society and NGO legal research
    
    Returns search report with case summaries and violation categories.
    Use get_anayasa_bireysel_document for full decision texts.
    """
    return await call_mcp_tool("search_anayasa_bireysel_basvuru_report", {
        "keywords": request.keywords, "page_to_fetch": request.page_to_fetch
    })

@app.get("/api/anayasa/bireysel-document", tags=["Anayasa"])
async def get_anayasa_bireysel_document(document_url: str, page_number: int = 1):
    """
    Retrieve the full text of a Constitutional Court individual application decision in paginated Markdown format.
    
    This tool fetches complete human rights violation decisions from individual applications
    and converts them to clean, readable Markdown format. Content is paginated into
    5,000-character chunks for easier processing.
    
    Input Requirements:
    • document_url: URL path (e.g., /BB/YYYY/NNNN) from search results
    • page_number: Page number for pagination (1-indexed, default: 1)
    
    Output Format:
    • Clean Markdown text with human rights case structure preserved
    • Organized sections: applicant info, violation claims, court analysis, ruling
    • Proper formatting for human rights law citations and references
    • Paginated content with navigation information
    
    Individual Application Decision Content:
    • Complete human rights violation analysis
    • Detailed examination of fundamental rights claims
    • Citation of constitutional articles and international human rights law
    • Final determination on rights violations with remedies
    • Analysis of domestic court proceedings and their adequacy
    • Individual remedy recommendations and compensation
    
    Use for:
    • Reading full human rights violation decisions
    • Human rights law research and precedent analysis
    • Understanding constitutional rights protection standards
    • Individual petition strategy development
    • Academic human rights and constitutional law study
    • Civil society monitoring of rights violations
    """
    return await call_mcp_tool("get_anayasa_bireysel_basvuru_document_markdown", {
        "document_url": document_url, "page_number": page_number
    })

@app.post("/api/kik/search", tags=["KİK"], summary="Search Public Procurement Authority")
async def search_kik(request: KikSearchRequest):
    """
    Search Public Procurement Authority (Kamu İhale Kurulu - KIK) decisions with comprehensive filtering for public procurement law and administrative dispute research.
    
    The Public Procurement Authority (KIK) is Turkey's procurement oversight body, responsible for
    regulating public procurement processes, resolving procurement disputes, and issuing interpretive
    decisions on public contracting laws. This tool provides access to official procurement decisions
    and regulatory guidance.
    
    Key Features:
    • Decision type filtering (Disputes, Regulatory, Court decisions)
    • Decision date range filtering for temporal analysis
    • Applicant and procuring entity filtering
    • Tender subject and content-based search
    • Decision number and reference tracking
    • Comprehensive metadata extraction
    
    Public Procurement Decision Types:
    • Uyuşmazlık Kararları: Dispute resolution decisions
    • Düzenleyici Kararlar: Regulatory and interpretive decisions
    • Mahkeme Kararları: Court decisions and judicial precedents
    
    Procurement Law Areas:
    • Tender procedure compliance and violations
    • Bid evaluation and award criteria disputes
    • Contractor qualification and eligibility
    • Contract modification and scope changes
    • Performance guarantees and penalty applications
    • Public procurement ethics and transparency
    • Emergency procurement and exceptional procedures
    
    Use cases:
    • Public procurement law research and compliance guidance
    • Tender dispute resolution precedent analysis
    • Government contracting risk assessment
    • Procurement policy and regulatory interpretation
    • Academic public administration and law study
    • Legal strategy development for procurement disputes
    
    Returns structured procurement authority data with comprehensive case metadata.
    Use get_kik_document for full decision texts with detailed reasoning.
    """
    args = {}
    for field in ["karar_tipi", "karar_metni", "basvuru_konusu_ihale", "karar_tarihi_baslangic"]:
        if getattr(request, field):
            args[field] = getattr(request, field)
    return await call_mcp_tool("search_kik_decisions", args)

@app.get("/api/kik/document/{decision_id}", tags=["KİK"])
async def get_kik_document(decision_id: str):
    """
    Retrieve the full text of a Public Procurement Authority (KIK) decision in paginated Markdown format.
    
    This tool fetches complete public procurement decisions and converts them from PDF to clean,
    readable Markdown format. Content is paginated into manageable chunks for processing lengthy
    procurement law decisions and regulatory interpretations.
    
    Input Requirements:
    • decision_id: KIK decision ID (base64 encoded karar_id) from search results
    • Decision ID must be non-empty string
    
    Output Format:
    • Clean Markdown text converted from original PDF documents
    • Organized sections: case summary, legal analysis, regulatory interpretation, decision
    • Proper formatting for procurement law citations and regulatory references
    • Paginated content with navigation information
    • Metadata including PDF source link and document information
    
    Public Procurement Decision Content:
    • Complete procurement dispute analysis and resolution
    • Detailed examination of tender procedures and compliance
    • Citation of procurement laws, regulations, and precedents
    • Final determination on procurement violations with corrective measures
    • Regulatory guidance and policy interpretations
    • Contractor liability and penalty determinations
    
    Use for:
    • Reading full public procurement authority decisions
    • Procurement law research and precedent analysis
    • Government contracting compliance and risk assessment
    • Tender dispute resolution strategy development
    • Academic public administration and procurement law study
    • Policy analysis and regulatory interpretation
    """
    return await call_mcp_tool("get_kik_document_markdown", {"decision_id": decision_id})

@app.post("/api/rekabet/search", tags=["Rekabet"], summary="Search Competition Authority")
async def search_rekabet(request: RekabetSearchRequest):
    """
    Search Competition Authority (Rekabet Kurumu) decisions with comprehensive filtering for competition law and antitrust research.
    
    The Competition Authority (Rekabet Kurumu) is Turkey's competition authority, responsible for enforcing antitrust laws,
    preventing anti-competitive practices, and regulating mergers and acquisitions. This tool
    provides access to official competition law decisions and regulatory interpretations.
    
    Key Features:
    • Decision type filtering (Mergers, Violations, Exemptions, etc.)
    • Title and content-based text search with exact phrase matching
    • Publication date filtering
    • Case year and decision number filtering
    • Pagination support for large result sets
    
    Competition Law Decision Types:
    • Birleşme ve Devralma: Merger and acquisition approvals
    • Rekabet İhlali: Competition violation investigations
    • Muafiyet: Exemption and negative clearance decisions
    • Geçici Tedbir: Interim measures and emergency orders
    • Sektör İncelemesi: Sector inquiry and market studies
    • Diğer: Other regulatory and interpretive decisions
    
    Competition Law Areas:
    • Anti-competitive agreements and cartels
    • Abuse of dominant market position
    • Merger control and market concentration
    • Vertical agreements and distribution restrictions
    • Unfair competition and consumer protection
    • Market definition and economic analysis
    
    Advanced Search:
    • Exact phrase matching with double quotes for precise legal terms
    • Content search across full decision texts (PdfText parameter)
    • Title search for specific case names or topics
    • Date range filtering for temporal analysis
    
    Example for exact phrase search: PdfText=\"tender process\" consultancy
    
    Use cases:
    • Competition law research and precedent analysis
    • Merger and acquisition due diligence
    • Antitrust compliance and risk assessment
    • Market analysis and competitive intelligence
    • Academic competition economics study
    • Legal strategy development for competition cases
    
    Returns structured competition authority data with comprehensive metadata.
    Use get_rekabet_document for full decision texts (paginated PDF conversion).
    """
    args = {"page": request.page}
    for field in ["KararTuru", "PdfText", "YayinlanmaTarihi"]:
        if getattr(request, field):
            args[field] = getattr(request, field)
    return await call_mcp_tool("search_rekabet_kurumu_decisions", args)

@app.get("/api/rekabet/document/{karar_id}", tags=["Rekabet"])
async def get_rekabet_document(karar_id: str, page_number: int = 1):
    """
    Retrieve the full text of a Competition Authority (Rekabet Kurumu) decision in paginated Markdown format converted from PDF.
    
    This tool fetches complete competition authority decisions and converts them from PDF to clean,
    readable Markdown format. Content is paginated for easier processing of lengthy competition law decisions.
    
    Input Requirements:
    • karar_id: GUID (kararId) from search_rekabet_kurumu_decisions results
    • page_number: Page number for pagination (1-indexed, default: 1)
    
    Output Format:
    • Clean Markdown text converted from original PDF documents
    • Organized sections: case summary, market analysis, legal reasoning, decision
    • Proper formatting for competition law citations and references
    • Paginated content with navigation information
    • Metadata including PDF source link and document information
    
    Competition Authority Decision Content:
    • Complete competition law analysis and market assessment
    • Detailed examination of anti-competitive practices
    • Economic analysis and market definition studies
    • Citation of competition laws, regulations, and precedents
    • Final determination on competition violations with remedies
    • Merger and acquisition approval conditions
    • Regulatory guidance and policy interpretations
    
    Use for:
    • Reading full competition authority decisions
    • Competition law research and precedent analysis
    • Market analysis and economic impact assessment
    • Antitrust compliance and risk evaluation
    • Academic competition economics and law study
    • Legal strategy development for competition cases
    """
    return await call_mcp_tool("get_rekabet_kurumu_document", {
        "karar_id": karar_id, "page_number": page_number
    })

# ============================================================================
# SAYISTAY (COURT OF ACCOUNTS) ENDPOINTS - 6 TOOLS
# ============================================================================

@app.post("/api/sayistay/search-genel-kurul", tags=["Sayıştay"], summary="Search Court of Accounts (General Assembly)")
async def search_sayistay_genel_kurul(request: SayistaySearchRequest):
    """
    Search Sayıştay Genel Kurul (General Assembly) decisions - highest-level audit precedents and interpretive rulings with keyword-based filtering.
    
    The General Assembly represents the highest decision-making body of Turkey's Court of Accounts,
    issuing authoritative interpretations of audit laws, precedential rulings on complex accountability
    issues, and binding guidance for audit practice. These decisions establish fundamental principles
    for public financial oversight and accountability standards.
    
    Key Features:
    • Keyword-based search with AND logic for precise case finding
    • Highest-level audit precedent identification
    • Interpretive ruling analysis and legal guidance extraction
    • Complex accountability issue resolution tracking
    • Pagination support for comprehensive result sets
    
    General Assembly Decision Authority:
    • Ultimate audit law interpretation and clarification
    • Precedential rulings binding on all audit chambers
    • Complex inter-chamber jurisdiction dispute resolution
    • Policy guidance for audit methodology and standards
    • Final determination on constitutional audit questions
    
    Public Audit Areas:
    • Government budget execution and compliance
    • Public institution financial management
    • State-owned enterprise oversight and accountability
    • Local government and municipal audit standards
    • Public procurement oversight and compliance monitoring
    • Performance audit methodology and effectiveness standards
    • Public revenue collection and tax administration audit
    
    Use Cases:
    • Research authoritative audit law interpretations
    • Find binding precedents for complex audit questions
    • Study evolution of public accountability standards
    • Analyze audit methodology development and refinement
    • Academic public administration and audit research
    • Government policy and accountability framework analysis
    
    Returns structured General Assembly data with comprehensive legal precedent metadata.
    Use get_sayistay_genel_kurul_document for full decision texts with detailed reasoning.
    """
    return await call_mcp_tool("search_sayistay_genel_kurul", {
        "keywords": request.keywords, "page_to_fetch": request.page_to_fetch
    })

@app.get("/api/sayistay/genel-kurul-document", tags=["Sayıştay"])
async def get_sayistay_genel_kurul_document(document_url: str, page_number: int = 1):
    """
    Retrieve the full text of a Sayıştay Genel Kurul decision document in Markdown format for detailed analysis.
    
    This tool converts the original General Assembly decision document into clean,
    readable Markdown format suitable for legal analysis and research.
    
    Input Requirements:
    • decision_id: Use the ID from search_sayistay_genel_kurul results
    • Decision ID must be non-empty string
    
    Output Format:
    • Clean Markdown text with legal formatting preserved
    • Structured content with reasoning and conclusions
    • Removes technical artifacts from source documents
    
    Use for:
    • Detailed analysis of audit precedents
    • Research on public accountability standards
    • Citation and reference building
    • Legal interpretation and case study development
    """
    return await call_mcp_tool("get_sayistay_genel_kurul_document_markdown", {
        "document_url": document_url, "page_number": page_number
    })

@app.post("/api/sayistay/search-temyiz-kurulu", tags=["Sayıştay"], summary="Search Court of Accounts (Appeals Board)")
async def search_sayistay_temyiz_kurulu(request: SayistaySearchRequest):
    """
    Search Sayıştay Temyiz Kurulu (Appeals Board) decisions - appellate review of audit chamber findings with advanced filtering and institutional analysis.
    
    The Appeals Board serves as the intermediate appellate authority in Turkey's audit system,
    reviewing first-instance chamber decisions on audit findings, liability determinations,
    and sanctions. Appeals Board decisions refine audit standards and ensure consistency
    across different audit chambers.
    
    Key Features:
    • Chamber-specific filtering for targeted appeals analysis
    • Institutional type categorization for audit pattern analysis
    • Decision and account year filtering for temporal trends
    • Audit subject matter classification and content search
    • Appeal outcome tracking and precedent identification
    • Pagination support for comprehensive coverage
    
    Appeals Board Authority:
    • Review and modification of chamber audit findings
    • Standardization of audit liability determinations
    • Consistency enforcement across audit chambers
    • Intermediate precedent development for audit practice
    • Quality control for first-instance audit decisions
    
    Audit Review Areas:
    • Government agency financial accountability appeals
    • Municipality and local government audit review
    • State enterprise oversight and performance audit appeals
    • Educational institution audit finding review
    • Healthcare system financial accountability appeals
    • Public procurement oversight and compliance review
    • Tax administration and revenue audit appeals
    
    Use Cases:
    • Research audit appeals patterns and outcomes
    • Study chamber decision consistency and standards
    • Analyze audit liability determination evolution
    • Find precedents for specific audit finding types
    • Track institutional audit patterns and compliance
    • Academic public accountability and audit law research
    
    Returns structured Appeals Board data with comprehensive appellate analysis metadata.
    Use get_sayistay_temyiz_kurulu_document for full appeals decisions with detailed reasoning.
    """
    return await call_mcp_tool("search_sayistay_temyiz_kurulu", {
        "keywords": request.keywords, "page_to_fetch": request.page_to_fetch
    })

@app.get("/api/sayistay/temyiz-kurulu-document", tags=["Sayıştay"])
async def get_sayistay_temyiz_kurulu_document(document_url: str, page_number: int = 1):
    """
    Retrieve the full text of a Sayıştay Temyiz Kurulu decision document in Markdown format for detailed appeals analysis.
    
    This tool converts the original Appeals Board decision document into clean,
    readable Markdown format for analysis of appellate reasoning and standards.
    
    Input Requirements:
    • decision_id: Use the ID from search_sayistay_temyiz_kurulu results
    • Decision ID must be non-empty string
    
    Output Format:
    • Clean Markdown text with appellate reasoning preserved
    • Structured content with original findings and appeals analysis
    • Removes technical artifacts from source documents
    
    Use for:
    • Analysis of appeals board reasoning and standards
    • Research on audit liability determination evolution
    • Understanding chamber decision review criteria
    • Precedent analysis for audit appeal cases
    """
    return await call_mcp_tool("get_sayistay_temyiz_kurulu_document_markdown", {
        "document_url": document_url, "page_number": page_number
    })

@app.post("/api/sayistay/search-daire", tags=["Sayıştay"], summary="Search Court of Accounts (Chambers)")
async def search_sayistay_daire(request: SayistaySearchRequest):
    """
    Search Sayıştay Daire (Chamber) decisions - first-instance audit findings and sanctions from individual audit chambers with comprehensive filtering and subject categorization.
    
    Chamber decisions represent first-instance audit findings, sanctions, and
    liability determinations issued by specialized audit chambers. These form
    the foundation of Turkey's public financial accountability system.
    
    Key Features:
    • Chamber-specific filtering (8 specialized audit chambers)
    • Decision and account year filtering (2012-2025)
    • Public administration type categorization
    • Subject matter classification and full-text search
    • Audit report tracking and institutional analysis
    
    Use Cases:
    • Research specific audit findings and sanctions
    • Study chamber specialization and jurisdiction
    • Analyze audit patterns by institution type
    • Find precedents for financial irregularities
    • Track audit evolution across fiscal years
    """
    return await call_mcp_tool("search_sayistay_daire", {
        "keywords": request.keywords, "page_to_fetch": request.page_to_fetch
    })

@app.get("/api/sayistay/daire-document", tags=["Sayıştay"])
async def get_sayistay_daire_document(document_url: str, page_number: int = 1):
    """
    Retrieve the full text of a Sayıştay Daire decision document in Markdown format for detailed audit findings analysis.
    
    This tool converts the original chamber decision document into clean,
    readable Markdown format for analysis of first-instance audit findings.
    
    Input Requirements:
    • decision_id: Use the ID from search_sayistay_daire results  
    • Decision ID must be non-empty string
    
    Output Format:
    • Clean Markdown text with audit findings preserved
    • Structured content with violations and sanctions
    • Removes technical artifacts from source documents
    
    Use for:
    • Detailed analysis of audit findings and methodology
    • Research on specific types of financial irregularities
    • Understanding chamber jurisdiction and specialization
    • Case study development for audit training and compliance
    """
    return await call_mcp_tool("get_sayistay_daire_document_markdown", {
        "document_url": document_url, "page_number": page_number
    })

# ============================================================================
# ADDITIONAL API ENDPOINTS
# ============================================================================

@app.get("/api/databases")
async def list_databases():
    """Comprehensive database information with tool mappings"""
    return {
        "total_tools": 33,
        "databases": {
            "yargitay": {
                "name": "Yargıtay (Court of Cassation)",
                "description": "Turkey's Supreme Court for civil and criminal matters",
                "tools": 4,
                "chambers": 52,
                "search_tools": ["search_yargitay", "search_yargitay_bedesten"],
                "document_tools": ["get_yargitay_document", "get_yargitay_bedesten_document"]
            },
            "danistay": {
                "name": "Danıştay (Council of State)", 
                "description": "Turkey's Supreme Administrative Court",
                "tools": 5,
                "chambers": 27,
                "search_tools": ["search_danistay_keyword", "search_danistay_detailed", "search_danistay_bedesten"],
                "document_tools": ["get_danistay_document", "get_danistay_bedesten_document"]
            },
            "anayasa": {
                "name": "Anayasa Mahkemesi (Constitutional Court)",
                "description": "Constitutional review and individual applications",
                "tools": 4,
                "features": ["norm_control", "individual_applications", "human_rights"]
            },
            "rekabet": {
                "name": "Rekabet Kurumu (Competition Authority)",
                "description": "Antitrust and merger control",
                "tools": 2,
                "coverage": ["mergers", "cartels", "market_abuse", "sector_inquiries"]
            },
            "kik": {
                "name": "Kamu İhale Kurulu (Public Procurement Authority)",
                "description": "Government procurement disputes",
                "tools": 2,
                "coverage": ["procurement_disputes", "regulatory_decisions", "tender_violations"]
            },
            "sayistay": {
                "name": "Sayıştay (Court of Accounts)",
                "description": "Public audit and financial accountability", 
                "tools": 6,
                "levels": ["general_assembly", "appeals_board", "audit_chambers"]
            },
            "emsal": {
                "name": "Emsal (UYAP Precedents)",
                "description": "Cross-court precedent database",
                "tools": 2,
                "coverage": ["multi_court", "precedent_analysis"]
            },
            "uyusmazlik": {
                "name": "Uyuşmazlık Mahkemesi (Jurisdictional Disputes)",
                "description": "Inter-court jurisdiction disputes",
                "tools": 2,
                "specialization": "jurisdictional_conflicts"
            },
            "bedesten_courts": {
                "name": "Bedesten API Courts (Local/Appellate/KYB)",
                "description": "First instance, appellate, and extraordinary appeal courts",
                "tools": 6,
                "courts": ["yerel_hukuk", "istinaf_hukuk", "kyb"],
                "coverage": "complete_court_hierarchy"
            }
        }
    }

@app.get("/api/stats")
async def get_statistics():
    """Comprehensive API statistics and capabilities"""
    uptime = (datetime.now() - SERVER_START_TIME).total_seconds()
    return {
        "server": {
            "uptime_seconds": uptime,
            "start_time": SERVER_START_TIME.isoformat(),
            "version": "1.0.0",
            "status": "operational"
        },
        "coverage": {
            "total_tools": 33,
            "total_databases": 9,
            "total_chambers": 79,  # 52 Yargıtay + 27 Danıştay
            "search_tools": 16,
            "document_tools": 17
        },
        "capabilities": {
            "advanced_search_operators": True,
            "exact_phrase_search": True,
            "date_range_filtering": True,
            "chamber_filtering": True,
            "boolean_logic": True,
            "wildcard_search": True,
            "pagination": True,
            "markdown_conversion": True,
            "pdf_processing": True,
            "dual_api_support": True
        },
        "legal_coverage": {
            "supreme_courts": ["Yargıtay", "Danıştay"],
            "constitutional_law": "Anayasa Mahkemesi",
            "administrative_law": "Full coverage",
            "competition_law": "Rekabet Kurumu",
            "public_procurement": "KİK",
            "public_audit": "Sayıştay",
            "court_hierarchy": "Complete (Local → Appellate → Supreme)",
            "specialized_courts": ["Uyuşmazlık", "Constitutional", "Administrative"]
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
