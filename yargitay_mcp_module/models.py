# yargitay_mcp_module/models.py

from pydantic import BaseModel, Field, HttpUrl, ConfigDict
from typing import List, Optional, Dict, Any, Literal

# Yargıtay Chamber/Board Options
YargitayBirimEnum = Literal[
    "ALL",  # "ALL" for all chambers
    # Hukuk (Civil) Chambers
    "Hukuk Genel Kurulu",
    "1. Hukuk Dairesi", "2. Hukuk Dairesi", "3. Hukuk Dairesi", "4. Hukuk Dairesi",
    "5. Hukuk Dairesi", "6. Hukuk Dairesi", "7. Hukuk Dairesi", "8. Hukuk Dairesi",
    "9. Hukuk Dairesi", "10. Hukuk Dairesi", "11. Hukuk Dairesi", "12. Hukuk Dairesi",
    "13. Hukuk Dairesi", "14. Hukuk Dairesi", "15. Hukuk Dairesi", "16. Hukuk Dairesi",
    "17. Hukuk Dairesi", "18. Hukuk Dairesi", "19. Hukuk Dairesi", "20. Hukuk Dairesi",
    "21. Hukuk Dairesi", "22. Hukuk Dairesi", "23. Hukuk Dairesi",
    "Hukuk Daireleri Başkanlar Kurulu",
    # Ceza (Criminal) Chambers
    "Ceza Genel Kurulu", 
    "1. Ceza Dairesi", "2. Ceza Dairesi", "3. Ceza Dairesi", "4. Ceza Dairesi",
    "5. Ceza Dairesi", "6. Ceza Dairesi", "7. Ceza Dairesi", "8. Ceza Dairesi",
    "9. Ceza Dairesi", "10. Ceza Dairesi", "11. Ceza Dairesi", "12. Ceza Dairesi",
    "13. Ceza Dairesi", "14. Ceza Dairesi", "15. Ceza Dairesi", "16. Ceza Dairesi",
    "17. Ceza Dairesi", "18. Ceza Dairesi", "19. Ceza Dairesi", "20. Ceza Dairesi",
    "21. Ceza Dairesi", "22. Ceza Dairesi", "23. Ceza Dairesi",
    "Ceza Daireleri Başkanlar Kurulu",
    # General Assembly
    "Büyük Genel Kurulu"
]

class YargitayDetailedSearchRequest(BaseModel):
    """
    Model for the 'data' object sent in the request payload
    to Yargitay's detailed search endpoint (e.g., /aramadetaylist).
    Based on the payload provided by the user.
    """
    arananKelime: Optional[str] = Field("", description="Turkish keywords (supports +word -word \"phrase\" operators)")
    # Department/Board selection - Complete Court of Cassation chamber hierarchy
    birimYrgKurulDaire: Optional[str] = Field("ALL", description="Chamber (ALL or specific chamber name)")
    
    esasYil: Optional[str] = Field("", description="Case year (YYYY)")
    esasIlkSiraNo: Optional[str] = Field("", description="Start case no")
    esasSonSiraNo: Optional[str] = Field("", description="End case no")
    
    kararYil: Optional[str] = Field("", description="Decision year (YYYY)")
    kararIlkSiraNo: Optional[str] = Field("", description="Start decision no")
    kararSonSiraNo: Optional[str] = Field("", description="End decision no")
    
    baslangicTarihi: Optional[str] = Field("", description="Start date (DD.MM.YYYY)")
    bitisTarihi: Optional[str] = Field("", description="End date (DD.MM.YYYY)")
    
    
    pageSize: int = Field(10, ge=1, le=10, description="Results per page (1-100)")
    pageNumber: int = Field(1, ge=1, description="Page number (1-indexed)")

class YargitayApiDecisionEntry(BaseModel):
    """Model for an individual decision entry from the Yargitay API search response."""
    id: str # Unique system ID of the decision
    daire: Optional[str] = Field(None, description="Chamber")
    esasNo: Optional[str] = Field(None, alias="esasNo", description="Case no")
    kararNo: Optional[str] = Field(None, alias="kararNo", description="Decision no")
    kararTarihi: Optional[str] = Field(None, alias="kararTarihi", description="Date")
    # 'index' and 'siraNo' from API response are not critical for MCP tool, so omitted for brevity
    
    # This field will be populated by the client after fetching the search list
    document_url: Optional[HttpUrl] = Field(None, description="Document URL")

    model_config = ConfigDict(populate_by_name=True)  # To allow populating by alias from API response


class YargitayApiResponseInnerData(BaseModel):
    """Model for the inner 'data' object in the Yargitay API search response."""
    data: List[YargitayApiDecisionEntry] = Field(default_factory=list)
    # draw: Optional[int] = None # Typically used by DataTables, not essential for MCP
    recordsTotal: int = Field(default=0) # Total number of records matching the query
    recordsFiltered: int = Field(default=0) # Total number of records after filtering (usually same as recordsTotal)

class YargitayApiSearchResponse(BaseModel):
    """Model for the complete search response from the Yargitay API."""
    data: Optional[YargitayApiResponseInnerData] = Field(default_factory=lambda: YargitayApiResponseInnerData())
    # metadata: Optional[Dict[str, Any]] = None # Optional metadata from API

class YargitayDocumentMarkdown(BaseModel):
    """Model for a Yargitay decision document, containing only Markdown content."""
    id: str = Field(..., description="Document ID")
    markdown_content: Optional[str] = Field(None, description="Content")
    source_url: HttpUrl = Field(..., description="Source URL")

class CleanYargitayDecisionEntry(BaseModel):
    """Clean decision entry without arananKelime field to reduce token usage."""
    id: str
    daire: Optional[str] = Field(None, description="Chamber")
    esasNo: Optional[str] = Field(None, description="Case no")
    kararNo: Optional[str] = Field(None, description="Decision no")
    kararTarihi: Optional[str] = Field(None, description="Date")
    document_url: Optional[HttpUrl] = Field(None, description="Document URL")

class CompactYargitaySearchResult(BaseModel):
    """A more compact search result model for the MCP tool to return."""
    decisions: List[CleanYargitayDecisionEntry]
    total_records: int
    requested_page: int
    page_size: int