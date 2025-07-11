# danistay_mcp_module/models.py

from pydantic import BaseModel, Field, HttpUrl, ConfigDict
from typing import List, Optional, Dict, Any

class DanistayBaseSearchRequest(BaseModel):
    """Base model for common search parameters for Danistay."""
    pageSize: int = Field(default=10, ge=1, le=100)
    pageNumber: int = Field(default=1, ge=1)
    # siralama and siralamaDirection are part of detailed search, not necessarily keyword search
    # as per user's provided payloads.

class DanistayKeywordSearchRequestData(BaseModel):
    """Internal data model for the keyword search payload's 'data' field."""
    andKelimeler: List[str] = Field(default_factory=list)
    orKelimeler: List[str] = Field(default_factory=list)
    notAndKelimeler: List[str] = Field(default_factory=list)
    notOrKelimeler: List[str] = Field(default_factory=list)
    pageSize: int
    pageNumber: int

class DanistayKeywordSearchRequest(BaseModel): # This is the model the MCP tool will accept
    """Model for keyword-based search request for Danistay."""
    andKelimeler: List[str] = Field(default_factory=list, description="Keywords for AND logic (VE Mantığı), e.g., ['word1', 'word2']")
    orKelimeler: List[str] = Field(default_factory=list, description="Keywords for OR logic (VEYA Mantığı).")
    notAndKelimeler: List[str] = Field(default_factory=list, description="Keywords for NOT AND logic (VE DEĞİL Mantığı).")
    notOrKelimeler: List[str] = Field(default_factory=list, description="Keywords for NOT OR logic (VEYA DEĞİL Mantığı).")
    pageSize: int = Field(default=10, ge=1, le=100)
    pageNumber: int = Field(default=1, ge=1)

class DanistayDetailedSearchRequestData(BaseModel): # Internal data model for detailed search payload
    """Internal data model for the detailed search payload's 'data' field."""
    daire: Optional[str] = "" # API expects empty string for None
    esasYil: Optional[str] = ""
    esasIlkSiraNo: Optional[str] = ""
    esasSonSiraNo: Optional[str] = ""
    kararYil: Optional[str] = ""
    kararIlkSiraNo: Optional[str] = ""
    kararSonSiraNo: Optional[str] = ""
    baslangicTarihi: Optional[str] = ""
    bitisTarihi: Optional[str] = ""
    mevzuatNumarasi: Optional[str] = ""
    mevzuatAdi: Optional[str] = ""
    madde: Optional[str] = ""
    siralama: str # Seems mandatory in detailed search payload
    siralamaDirection: str # Seems mandatory
    pageSize: int
    pageNumber: int
    # Note: 'arananKelime' is not in the detailed search payload example provided by user.
    # If it can be included, it should be added here.

class DanistayDetailedSearchRequest(DanistayBaseSearchRequest): # MCP tool will accept this
    """Model for detailed search request for Danistay."""
    daire: Optional[str] = Field(None, description="Chamber/Department name (e.g., '1. Daire').")
    esasYil: Optional[str] = Field(None, description="Case year for 'Esas No'.")
    esasIlkSiraNo: Optional[str] = Field(None, description="Starting sequence for 'Esas No'.")
    esasSonSiraNo: Optional[str] = Field(None, description="Ending sequence for 'Esas No'.")
    kararYil: Optional[str] = Field(None, description="Decision year for 'Karar No'.")
    kararIlkSiraNo: Optional[str] = Field(None, description="Starting sequence for 'Karar No'.")
    kararSonSiraNo: Optional[str] = Field(None, description="Ending sequence for 'Karar No'.")
    baslangicTarihi: Optional[str] = Field(None, description="Start date for decision (DD.MM.YYYY).")
    bitisTarihi: Optional[str] = Field(None, description="End date for decision (DD.MM.YYYY).")
    mevzuatNumarasi: Optional[str] = Field(None, description="Legislation number.")
    mevzuatAdi: Optional[str] = Field(None, description="Legislation name.")
    madde: Optional[str] = Field(None, description="Article number.")
    siralama: str = Field("1", description="Sorting criteria (e.g., 1: Esas No, 3: Karar Tarihi).")
    siralamaDirection: str = Field("desc", description="Sorting direction ('asc' or 'desc').")
    # Add a general keyword field if detailed search also supports it
    # arananKelime: Optional[str] = Field(None, description="General keyword for detailed search.")


class DanistayApiDecisionEntry(BaseModel):
    """Model for an individual decision entry from the Danistay API search response.
       Based on user-provided response samples for both keyword and detailed search.
    """
    id: str
    # The API response for keyword search uses "daireKurul", detailed search example uses "daire".
    # We use an alias to handle both and map to a consistent field name "chamber".
    chamber: Optional[str] = Field(None, alias="daire", description="The chamber or board.")
    esasNo: Optional[str] = Field(None)
    kararNo: Optional[str] = Field(None)
    kararTarihi: Optional[str] = Field(None)
    arananKelime: Optional[str] = Field(None, description="Matched keyword (Aranan Kelime) if provided in response.")
    # index: Optional[int] = None # Present in response, can be added if needed by MCP tool
    # siraNo: Optional[int] = None # Present in detailed response, can be added

    document_url: Optional[HttpUrl] = Field(None, description="URL (Belge URL) to the full document, constructed by the client.")

    model_config = ConfigDict(populate_by_name=True, extra='ignore')  # Important for alias to work and ignore extra fields

class DanistayApiResponseInnerData(BaseModel):
    """Model for the inner 'data' object in the Danistay API search response."""
    data: List[DanistayApiDecisionEntry]
    recordsTotal: int
    recordsFiltered: int
    draw: Optional[int] = Field(None, description="Draw counter (Çizim Sayıcısı) from API, usually for DataTables.")

class DanistayApiResponse(BaseModel):
    """Model for the complete search response from the Danistay API."""
    data: Optional[DanistayApiResponseInnerData] = Field(None, description="Response data, can be null when no results found")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Optional metadata (Meta Veri) from API.")

class DanistayDocumentMarkdown(BaseModel):
    """Model for a Danistay decision document, containing only Markdown content."""
    id: str
    markdown_content: Optional[str] = Field(None, description="The decision content (Karar İçeriği) converted to Markdown.")
    source_url: HttpUrl

class CompactDanistaySearchResult(BaseModel):
    """A compact search result model for the MCP tool to return."""
    decisions: List[DanistayApiDecisionEntry]
    total_records: int
    requested_page: int
    page_size: int