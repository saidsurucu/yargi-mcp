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
    arananKelime: Optional[str] = Field("", description="""Keyword to search for with advanced operators support:
        • Simple words: 'arsa payı' (OR logic - finds documents with ANY word)
        • Exact phrases: '"arsa payı"' (finds exact phrase)
        • AND logic: 'arsa+payı' (both words required)
        • Wildcards: 'bozma*' (matches bozma, bozması, bozmanın, etc.)
        • Multiple required: '+"arsa payı" +"bozma sebebi"'
        • Exclusion: '+"arsa payı" -"inşaat sözleşmesi"'
        Examples: arsa payı | "arsa payı" | +"mülkiyet hakkı" +"bozma sebebi" | hukuk*""")
    # Department/Board selection - Complete Court of Cassation chamber hierarchy
    birimYrgKurulDaire: Optional[str] = Field("ALL", description="""
        Court of Cassation (Yargıtay) chamber/board selection. Options include:
        - 'ALL' for all chambers
        - Civil: 'Civil General Assembly (Hukuk Genel Kurulu)', '1st Civil Chamber (1. Hukuk Dairesi)' through '23rd Civil Chamber (23. Hukuk Dairesi)', 'Civil Chambers Presidents Board (Hukuk Daireleri Başkanlar Kurulu)'
        - Criminal: 'Criminal General Assembly (Ceza Genel Kurulu)', '1st Criminal Chamber (1. Ceza Dairesi)' through '23rd Criminal Chamber (23. Ceza Dairesi)', 'Criminal Chambers Presidents Board (Ceza Daireleri Başkanlar Kurulu)'
        - General: 'Grand General Assembly (Büyük Genel Kurulu)'
        Total: 52 possible values (including 'ALL' for all chambers)
    """)
    birimYrgHukukDaire: Optional[str] = Field("", description="Legacy field - use birimYrgKurulDaire instead for chamber selection")
    birimYrgCezaDaire: Optional[str] = Field("", description="Legacy field - use birimYrgKurulDaire instead for chamber selection")
    
    esasYil: Optional[str] = Field("", description="""Case year for 'Esas No' filtering. 
        Format: YYYY (e.g., '2024')
        Use with sequence numbers for precise case targeting""")
    esasIlkSiraNo: Optional[str] = Field("", description="""Starting sequence number for 'Esas No' range filtering.
        Format: numeric string (e.g., '1', '100')
        Use with esasSonSiraNo for range: cases 100-200 in specified year""")
    esasSonSiraNo: Optional[str] = Field("", description="""Ending sequence number for 'Esas No' range filtering.
        Format: numeric string (e.g., '500', '1000')
        Creates range from esasIlkSiraNo to this number""")
    
    kararYil: Optional[str] = Field("", description="""Decision year for 'Karar No' filtering.
        Format: YYYY (e.g., '2024')
        Filters decisions by the year they were issued""")
    kararIlkSiraNo: Optional[str] = Field("", description="""Starting sequence number for 'Karar No' range filtering.
        Format: numeric string (e.g., '1', '50')
        Use with kararSonSiraNo for decision number ranges""")
    kararSonSiraNo: Optional[str] = Field("", description="""Ending sequence number for 'Karar No' range filtering.
        Format: numeric string (e.g., '100', '500')
        Creates range from kararIlkSiraNo to this number""")
    
    baslangicTarihi: Optional[str] = Field("", description="""Start date for decision search.
        Format: DD.MM.YYYY (e.g., '01.01.2024')
        Use with bitisTarihi for date range filtering
        Examples: '01.01.2024', '15.06.2023'""")
    bitisTarihi: Optional[str] = Field("", description="""End date for decision search.
        Format: DD.MM.YYYY (e.g., '31.12.2024')
        Creates date range from baslangicTarihi to this date
        Examples: '31.12.2024', '30.06.2023'""")
    
    siralama: Optional[str] = Field("3", description="""Sorting criteria for search results:
        • '1': Esas No (Case Number) - sorts by case registration order
        • '2': Karar No (Decision Number) - sorts by decision issuance order  
        • '3': Karar Tarihi (Decision Date) - sorts by chronological order [DEFAULT]
        Recommended: Use '3' for most recent decisions first""")
    siralamaDirection: Optional[str] = Field("desc", description="""Sorting direction for results:
        • 'desc': Descending order (newest/highest first) [DEFAULT]
        • 'asc': Ascending order (oldest/lowest first)
        Most common: 'desc' for latest decisions first""")
    
    pageSize: int = Field(10, ge=1, le=100, description="""Number of results per page.
        Range: 1-100 results per page
        Recommended: 10-50 for balanced performance and coverage
        Large values (50-100) for comprehensive analysis""")
    pageNumber: int = Field(1, ge=1, description="""Page number to retrieve (1-indexed).
        Start with 1 for first page
        Use with pageSize to navigate through large result sets
        Example: pageSize=50, pageNumber=3 gets results 101-150""")

class YargitayApiDecisionEntry(BaseModel):
    """Model for an individual decision entry from the Yargitay API search response."""
    id: str # Unique system ID of the decision
    daire: Optional[str] = Field(None, description="The chamber (Daire) that made the decision.")
    esasNo: Optional[str] = Field(None, alias="esasNo", description="Case registry number (Esas No).")
    kararNo: Optional[str] = Field(None, alias="kararNo", description="Decision number (Karar No).")
    kararTarihi: Optional[str] = Field(None, alias="kararTarihi", description="Date of the decision (Karar Tarihi).")
    arananKelime: Optional[str] = Field(None, alias="arananKelime", description="Matched keyword (Aranan Kelime) in the search result item.")
    # 'index' and 'siraNo' from API response are not critical for MCP tool, so omitted for brevity
    
    # This field will be populated by the client after fetching the search list
    document_url: Optional[HttpUrl] = Field(None, description="Direct URL (Belge URL) to the decision document.")

    model_config = ConfigDict(populate_by_name=True)  # To allow populating by alias from API response


class YargitayApiResponseInnerData(BaseModel):
    """Model for the inner 'data' object in the Yargitay API search response."""
    data: List[YargitayApiDecisionEntry]
    # draw: Optional[int] = None # Typically used by DataTables, not essential for MCP
    recordsTotal: int # Total number of records matching the query
    recordsFiltered: int # Total number of records after filtering (usually same as recordsTotal)

class YargitayApiSearchResponse(BaseModel):
    """Model for the complete search response from the Yargitay API."""
    data: YargitayApiResponseInnerData
    # metadata: Optional[Dict[str, Any]] = None # Optional metadata from API

class YargitayDocumentMarkdown(BaseModel):
    """Model for a Yargitay decision document, containing only Markdown content."""
    id: str = Field(..., description="The unique ID (Belge Kimliği) of the document.")
    markdown_content: Optional[str] = Field(None, description="The decision content (Karar İçeriği) converted to Markdown.")
    source_url: HttpUrl = Field(..., description="The source URL (Kaynak URL) of the original document.")

class CompactYargitaySearchResult(BaseModel):
    """A more compact search result model for the MCP tool to return."""
    decisions: List[YargitayApiDecisionEntry]
    total_records: int
    requested_page: int
    page_size: int