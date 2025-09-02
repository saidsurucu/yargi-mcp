# kik_mcp_module/models_v2.py
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from datetime import datetime
from enum import Enum

# New KIK v2 API Models

class KikV2DecisionType(str, Enum):
    """KIK v2 Decision Types with corresponding endpoints."""
    UYUSMAZLIK = "uyusmazlik"        # Disputes - GetKurulKararlari
    DUZENLEYICI = "duzenleyici"      # Regulatory - GetKurulKararlariDk  
    MAHKEME = "mahkeme"              # Court - GetKurulKararlariMk

class KikV2SearchRequest(BaseModel):
    """Model for KIK v2 API search request."""
    KararMetni: str = Field("", description="Decision text search query")
    KararNo: str = Field("", description="Decision number (e.g., '2025/UH.II-1801')")
    BasvuranAdi: str = Field("", description="Applicant name")
    IdareAdi: str = Field("", description="Administration name")
    BaslangicTarihi: str = Field("", description="Start date (YYYY-MM-DD)")
    BitisTarihi: str = Field("", description="End date (YYYY-MM-DD)")
    
class KikV2KeyValuePair(BaseModel):
    """Key-value pair for KIK v2 API request."""
    key: str
    value: str

class KikV2QueryRequest(BaseModel):
    """Nested query structure for KIK v2 API."""
    keyValueOfstringanyType: List[KikV2KeyValuePair]

class KikV2RequestData(BaseModel):
    """Main request data structure for KIK v2 API."""
    keyValuePairs: KikV2QueryRequest

# Request Payloads for different decision types
class KikV2SearchPayload(BaseModel):
    """Complete payload for KIK v2 API search - Uyuşmazlık (Disputes)."""
    sorgulaKurulKararlari: KikV2RequestData

class KikV2SearchPayloadDk(BaseModel):
    """Complete payload for KIK v2 API search - Düzenleyici (Regulatory)."""
    sorgulaKurulKararlariDk: KikV2RequestData

class KikV2SearchPayloadMk(BaseModel):
    """Complete payload for KIK v2 API search - Mahkeme (Court)."""
    sorgulaKurulKararlariMk: KikV2RequestData

# Response Models

class KikV2DecisionDetail(BaseModel):
    """Individual decision detail from KIK v2 API response."""
    resmiGazeteMukerrerSayi: str = Field("", description="Official Gazette duplicate number")
    itiraz: str = Field("", description="Objection")
    yayinlanmaTarihi: str = Field("", description="Publication date")
    idareAdi: str = Field("", description="Administration name")
    uzmanTCKN: str = Field("", description="Expert TCKN")
    resmiGazeteTarihi: str = Field("", description="Official Gazette date")
    basvuruKonusu: str = Field("", description="Application subject")
    kararTurKod: str = Field("", description="Decision type code")
    kararTurAciklama: str = Field("", description="Decision type description")
    karar: str = Field("", description="Decision text")
    kararNo: str = Field("", description="Decision number")
    resmiGazeteSayisi: str = Field("", description="Official Gazette number")
    inceleme: str = Field("", description="Review")
    basvuruTarihi: str = Field("", description="Application date")
    kararNitelikKod: str = Field("", description="Decision nature code")
    resmiGazeteMukerrer: str = Field("", description="Official Gazette duplicate")
    basvuruSayisi: str = Field("", description="Application number")
    basvuran: str = Field("", description="Applicant")
    kararNitelik: str = Field("", description="Decision nature")
    uyusmazlikKararNo: str = Field("", description="Dispute decision number")
    kurulNo: str = Field("", description="Board number")
    gundemMaddesiSiraNo: str = Field("", description="Agenda item sequence")
    kararTarihi: str = Field("", description="Decision date (ISO format)")
    dosyaBirimKodu: str = Field("", description="File unit code")
    gundemMaddesiId: str = Field("", description="Agenda item ID")

class KikV2DecisionGroup(BaseModel):
    """Group of decision details."""
    KurulKararTutanakDetayi: List[KikV2DecisionDetail] = Field(alias="kurulKararTutanakDetayi")
    
    model_config = ConfigDict(populate_by_name=True)

class KikV2SearchResultData(BaseModel):
    """Search result data structure."""
    hataKodu: str = Field("", description="Error code")
    hataMesaji: str = Field("", description="Error message") 
    KurulKararTutanakDetayListesi: List[KikV2DecisionGroup]
    
    model_config = ConfigDict(populate_by_name=True)

class KikV2SearchResultWrapper(BaseModel):
    """Wrapper for search result."""
    SorgulaKurulKararlariResult: KikV2SearchResultData

# Base Response Models
class KikV2SearchResponse(BaseModel):
    """Complete KIK v2 API search response for Uyuşmazlık (Disputes)."""
    SorgulaKurulKararlariResponse: KikV2SearchResultWrapper

# Düzenleyici Kararlar (Regulatory Decisions) Response Models
class KikV2SearchResultWrapperDk(BaseModel):
    """Wrapper for regulatory decisions search result."""
    SorgulaKurulKararlariDkResult: KikV2SearchResultData

class KikV2SearchResponseDk(BaseModel):
    """Complete KIK v2 API search response for Düzenleyici (Regulatory) decisions."""
    SorgulaKurulKararlariDkResponse: KikV2SearchResultWrapperDk

# Mahkeme Kararlar (Court Decisions) Response Models  
class KikV2SearchResultWrapperMk(BaseModel):
    """Wrapper for court decisions search result."""
    SorgulaKurulKararlariMkResult: KikV2SearchResultData

class KikV2SearchResponseMk(BaseModel):
    """Complete KIK v2 API search response for Mahkeme (Court) decisions."""
    SorgulaKurulKararlariMkResponse: KikV2SearchResultWrapperMk

# Simplified Models for MCP Tools

class KikV2CompactDecision(BaseModel):
    """Compact decision format for MCP tool responses."""
    kararNo: str = Field("", description="Decision number")
    kararTarihi: str = Field("", description="Decision date")
    basvuran: str = Field("", description="Applicant")
    idareAdi: str = Field("", description="Administration")
    basvuruKonusu: str = Field("", description="Application subject")
    gundemMaddesiId: str = Field("", description="Document ID for retrieval")
    decision_type: str = Field("", description="Decision type (uyusmazlik/duzenleyici/mahkeme)")
    
class KikV2SearchResult(BaseModel):
    """Compact search results for MCP tools."""
    decisions: List[KikV2CompactDecision]
    total_records: int = Field(0, description="Total number of decisions found")
    page: int = Field(1, description="Current page number")
    error_code: str = Field("", description="API error code")
    error_message: str = Field("", description="API error message")

class KikV2DocumentMarkdown(BaseModel):
    """Document content in Markdown format."""
    document_id: str = Field("", description="Document ID")
    kararNo: str = Field("", description="Decision number")
    markdown_content: str = Field("", description="Decision content in Markdown")
    source_url: str = Field("", description="Source URL")
    error_message: str = Field("", description="Error message if retrieval failed")