# emsal_mcp_module/models.py

from pydantic import BaseModel, Field, HttpUrl, ConfigDict
from typing import List, Optional, Dict, Any

class EmsalDetailedSearchRequestData(BaseModel):
    """
    Internal model for the 'data' object in the Emsal detailed search payload.
    Field names use aliases to match the exact keys in the API payload
    (e.g., "Bam Hukuk Mahkemeleri" with spaces).
    The API expects empty strings for None/omitted optional fields.
    """
    arananKelime: Optional[str] = ""
    
    Bam_Hukuk_Mahkemeleri: Optional[str] = Field(None, alias="Bam Hukuk Mahkemeleri")
    Hukuk_Mahkemeleri: Optional[str] = Field(None, alias="Hukuk Mahkemeleri")
    # Add other specific court type fields from the form if they are separate keys in payload
    # E.g., "Ceza Mahkemeleri", "İdari Mahkemeler" etc.
    
    birimHukukMah: Optional[str] = Field("", description="Regional chambers (+ separated)") 

    esasYil: Optional[str] = ""
    esasIlkSiraNo: Optional[str] = ""
    esasSonSiraNo: Optional[str] = ""
    kararYil: Optional[str] = ""
    kararIlkSiraNo: Optional[str] = ""
    kararSonSiraNo: Optional[str] = ""
    baslangicTarihi: Optional[str] = ""
    bitisTarihi: Optional[str] = ""
    siralama: str # Mandatory in payload example
    siralamaDirection: str # Mandatory in payload example
    pageSize: int
    pageNumber: int
    
    model_config = ConfigDict(populate_by_name=True)  # Enables use of alias in serialization (when dumping to dict for payload)

class EmsalSearchRequest(BaseModel): # This is the model the MCP tool will accept
    """Model for Emsal detailed search request, with user-friendly field names."""
    keyword: Optional[str] = Field(None, description="Keyword")
    
    selected_bam_civil_court: Optional[str] = Field(None, description="BAM Civil Court")
    selected_civil_court: Optional[str] = Field(None, description="Civil Court")
    selected_regional_civil_chambers: Optional[List[str]] = Field(default_factory=list, description="Regional chambers")

    case_year_esas: Optional[str] = Field(None, description="Case year")
    case_start_seq_esas: Optional[str] = Field(None, description="Start case no")
    case_end_seq_esas: Optional[str] = Field(None, description="End case no")
    
    decision_year_karar: Optional[str] = Field(None, description="Decision year")
    decision_start_seq_karar: Optional[str] = Field(None, description="Start decision no")
    decision_end_seq_karar: Optional[str] = Field(None, description="End decision no")
    
    start_date: Optional[str] = Field(None, description="Start date (DD.MM.YYYY)")
    end_date: Optional[str] = Field(None, description="End date (DD.MM.YYYY)")
    
    sort_criteria: str = Field("1", description="Sort by")
    sort_direction: str = Field("desc", description="Direction")
    
    page_number: int = Field(default=1, ge=1)
    page_size: int = Field(default=10, ge=1, le=10)


class EmsalApiDecisionEntry(BaseModel):
    """Model for an individual decision entry from the Emsal API search response."""
    id: str
    daire: Optional[str] = Field(None, description="Chamber")
    esasNo: Optional[str] = Field(None)
    kararNo: Optional[str] = Field(None)
    kararTarihi: Optional[str] = Field(None)
    arananKelime: Optional[str] = Field(None, description="Keyword")
    durum: Optional[str] = Field(None, description="Status")
    # index: Optional[int] = None # Present in Emsal response, can be added if tool needs it

    document_url: Optional[HttpUrl] = Field(None, description="Document URL")

    model_config = ConfigDict(extra='ignore')

class EmsalApiResponseInnerData(BaseModel):
    """Model for the inner 'data' object in the Emsal API search response."""
    data: List[EmsalApiDecisionEntry]
    recordsTotal: int
    recordsFiltered: int
    draw: Optional[int] = Field(None, description="Draw counter (Çizim Sayıcısı) from API, usually for DataTables.")

class EmsalApiResponse(BaseModel):
    """Model for the complete search response from the Emsal API."""
    data: EmsalApiResponseInnerData
    metadata: Optional[Dict[str, Any]] = Field(None, description="Optional metadata (Meta Veri) from API, if any.")

class EmsalDocumentMarkdown(BaseModel):
    """Model for an Emsal decision document, containing only Markdown content."""
    id: str
    markdown_content: Optional[str] = Field(None, description="The decision content (Karar İçeriği) converted to Markdown.")
    source_url: HttpUrl

class CompactEmsalSearchResult(BaseModel):
    """A compact search result model for the MCP tool to return."""
    decisions: List[EmsalApiDecisionEntry]
    total_records: int
    requested_page: int
    page_size: int