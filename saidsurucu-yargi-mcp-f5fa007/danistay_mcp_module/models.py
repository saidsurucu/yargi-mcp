# danistay_mcp_module/models.py

from pydantic import BaseModel, Field, HttpUrl, ConfigDict
from typing import List, Optional, Dict, Any

class DanistayBaseSearchRequest(BaseModel):
    """Base model for common search parameters for Danistay."""
    pageSize: int = Field(default=10, ge=1, le=10)
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
    andKelimeler: List[str] = Field(default_factory=list, description="AND keywords")
    orKelimeler: List[str] = Field(default_factory=list, description="OR keywords")
    notAndKelimeler: List[str] = Field(default_factory=list, description="NOT AND keywords")
    notOrKelimeler: List[str] = Field(default_factory=list, description="NOT OR keywords")
    pageSize: int = Field(default=10, ge=1, le=10)
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
    daire: str = Field("", description="Chamber")
    esasYil: str = Field("", description="Case year")
    esasIlkSiraNo: str = Field("", description="Start case no")
    esasSonSiraNo: str = Field("", description="End case no")
    kararYil: str = Field("", description="Decision year")
    kararIlkSiraNo: str = Field("", description="Start decision no")
    kararSonSiraNo: str = Field("", description="End decision no")
    baslangicTarihi: str = Field("", description="Start date")
    bitisTarihi: str = Field("", description="End date")
    mevzuatNumarasi: str = Field("", description="Law number")
    mevzuatAdi: str = Field("", description="Law name")
    madde: str = Field("", description="Article")
    # Add a general keyword field if detailed search also supports it
    # arananKelime: Optional[str] = Field(None, description="General keyword for detailed search.")


class DanistayApiDecisionEntry(BaseModel):
    """Model for an individual decision entry from the Danistay API search response.
       Based on user-provided response samples for both keyword and detailed search.
    """
    id: str
    # The API response for keyword search uses "daireKurul", detailed search example uses "daire".
    # We use an alias to handle both and map to a consistent field name "chamber".
    chamber: str = Field("", alias="daire", description="Chamber")
    esasNo: str = Field("", description="Case number")
    kararNo: str = Field("", description="Decision number")
    kararTarihi: str = Field("", description="Decision date")
    arananKelime: str = Field("", description="Keyword")
    # index: Optional[int] = None # Present in response, can be added if needed by MCP tool
    # siraNo: Optional[int] = None # Present in detailed response, can be added

    document_url: Optional[HttpUrl] = Field(None, description="Document URL")

    model_config = ConfigDict(populate_by_name=True, extra='ignore')  # Important for alias to work and ignore extra fields

class DanistayApiResponseInnerData(BaseModel):
    """Model for the inner 'data' object in the Danistay API search response."""
    data: List[DanistayApiDecisionEntry]
    recordsTotal: int
    recordsFiltered: int
    draw: int = Field(0, description="Draw counter")

class DanistayApiResponse(BaseModel):
    """Model for the complete search response from the Danistay API."""
    data: Optional[DanistayApiResponseInnerData] = Field(None, description="Response data, can be null when no results found")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Optional metadata (Meta Veri) from API.")

class DanistayDocumentMarkdown(BaseModel):
    """Model for a Danistay decision document, containing only Markdown content."""
    id: str
    markdown_content: str = Field("", description="The decision content (Karar İçeriği) converted to Markdown.")
    source_url: HttpUrl

class CompactDanistaySearchResult(BaseModel):
    """A compact search result model for the MCP tool to return."""
    decisions: List[DanistayApiDecisionEntry]
    total_records: int
    requested_page: int
    page_size: int