# sayistay_mcp_module/models.py

from pydantic import BaseModel, Field
from typing import Optional, List, Union, Dict, Any, Literal
from enum import Enum
from .enums import DaireEnum, KamuIdaresiTuruEnum, WebKararKonusuEnum

# --- Unified Enums ---
class SayistayDecisionTypeEnum(str, Enum):
    GENEL_KURUL = "genel_kurul"
    TEMYIZ_KURULU = "temyiz_kurulu"
    DAIRE = "daire"

# ============================================================================
# Genel Kurul (General Assembly) Models
# ============================================================================

class GenelKurulSearchRequest(BaseModel):
    """
    Search request for Sayıştay Genel Kurul (General Assembly) decisions.
    
    Genel Kurul decisions are precedent-setting rulings made by the full assembly
    of the Turkish Court of Accounts, typically addressing interpretation of
    audit and accountability regulations.
    """
    karar_no: str = Field("", description="Decision no")
    karar_ek: str = Field("", description="Appendix no")
    
    karar_tarih_baslangic: str = Field("", description="Start year (YYYY)")
    
    karar_tarih_bitis: str = Field("", description="End year")
    
    karar_tamami: str = Field("", description="Value")
    
    # DataTables pagination
    start: int = Field(0, description="Starting record for pagination (0-based)")
    length: int = Field(10, description="Number of records per page (1-10)")

class GenelKurulDecision(BaseModel):
    """Single Genel Kurul decision entry from search results."""
    id: int = Field(..., description="Unique decision ID")
    karar_no: str = Field(..., description="Decision number (e.g., '5415/1')")
    karar_tarih: str = Field(..., description="Decision date in DD.MM.YYYY format")
    karar_ozeti: str = Field(..., description="Decision summary/abstract")

class GenelKurulSearchResponse(BaseModel):
    """Response from Genel Kurul search endpoint."""
    decisions: List[GenelKurulDecision] = Field(default_factory=list, description="List of matching decisions")
    total_records: int = Field(0, description="Total number of matching records")
    total_filtered: int = Field(0, description="Number of records after filtering")
    draw: int = Field(1, description="DataTables draw counter")

# ============================================================================
# Temyiz Kurulu (Appeals Board) Models
# ============================================================================

class TemyizKuruluSearchRequest(BaseModel):
    """
    Search request for Sayıştay Temyiz Kurulu (Appeals Board) decisions.
    
    Temyiz Kurulu reviews appeals against audit chamber decisions,
    providing higher-level review of audit findings and sanctions.
    """
    ilam_dairesi: DaireEnum = Field("ALL", description="Value")
    
    yili: str = Field("", description="Value")
    
    karar_tarih_baslangic: str = Field("", description="Value")
    
    karar_tarih_bitis: str = Field("", description="End year")
    
    kamu_idaresi_turu: KamuIdaresiTuruEnum = Field("ALL", description="Value")
    
    ilam_no: str = Field("", description="Audit report number (İlam No, max 50 chars)")
    dosya_no: str = Field("", description="File number for the case")
    temyiz_tutanak_no: str = Field("", description="Appeals board meeting minutes number")
    
    temyiz_karar: str = Field("", description="Value")
    
    web_karar_konusu: WebKararKonusuEnum = Field("ALL", description="Value")
    
    # DataTables pagination
    start: int = Field(0, description="Starting record for pagination (0-based)")
    length: int = Field(10, description="Number of records per page (1-10)")

class TemyizKuruluDecision(BaseModel):
    """Single Temyiz Kurulu decision entry from search results."""
    id: int = Field(..., description="Unique decision ID")
    temyiz_tutanak_tarihi: str = Field(..., description="Appeals board meeting date in DD.MM.YYYY format")
    ilam_dairesi: int = Field(..., description="Chamber number (1-8)")
    temyiz_karar: str = Field(..., description="Appeals decision summary and reasoning")

class TemyizKuruluSearchResponse(BaseModel):
    """Response from Temyiz Kurulu search endpoint."""
    decisions: List[TemyizKuruluDecision] = Field(default_factory=list, description="List of matching appeals decisions")
    total_records: int = Field(0, description="Total number of matching records")
    total_filtered: int = Field(0, description="Number of records after filtering")
    draw: int = Field(1, description="DataTables draw counter")

# ============================================================================
# Daire (Chamber) Models  
# ============================================================================

class DaireSearchRequest(BaseModel):
    """
    Search request for Sayıştay Daire (Chamber) decisions.
    
    Daire decisions are first-instance audit findings and sanctions
    issued by individual audit chambers before potential appeals.
    """
    yargilama_dairesi: DaireEnum = Field("ALL", description="Value")
    
    karar_tarih_baslangic: str = Field("", description="Value")
    
    karar_tarih_bitis: str = Field("", description="End year")
    
    ilam_no: str = Field("", description="Audit report number (İlam No, max 50 chars)")
    
    kamu_idaresi_turu: KamuIdaresiTuruEnum = Field("ALL", description="Value")
    
    hesap_yili: str = Field("", description="Value")
    
    web_karar_konusu: WebKararKonusuEnum = Field("ALL", description="Value")
    
    web_karar_metni: str = Field("", description="Value")
    
    # DataTables pagination
    start: int = Field(0, description="Starting record for pagination (0-based)")
    length: int = Field(10, description="Number of records per page (1-10)")

class DaireDecision(BaseModel):
    """Single Daire decision entry from search results."""
    id: int = Field(..., description="Unique decision ID")
    yargilama_dairesi: int = Field(..., description="Chamber number (1-8)")
    karar_tarih: str = Field(..., description="Decision date in DD.MM.YYYY format")
    karar_no: str = Field(..., description="Decision number")
    ilam_no: str = Field("", description="Audit report number (may be null)")
    madde_no: int = Field(..., description="Article/item number within the decision")
    kamu_idaresi_turu: str = Field(..., description="Public administration type")
    hesap_yili: int = Field(..., description="Account year being audited")
    web_karar_konusu: str = Field(..., description="Decision subject category")
    web_karar_metni: str = Field(..., description="Decision text/summary")

class DaireSearchResponse(BaseModel):
    """Response from Daire search endpoint."""
    decisions: List[DaireDecision] = Field(default_factory=list, description="List of matching chamber decisions")
    total_records: int = Field(0, description="Total number of matching records")
    total_filtered: int = Field(0, description="Number of records after filtering")
    draw: int = Field(1, description="DataTables draw counter")

# ============================================================================
# Document Models
# ============================================================================

class SayistayDocumentMarkdown(BaseModel):
    """
    Sayıştay decision document converted to Markdown format.
    
    Used for retrieving full text of decisions from any of the three
    decision types (Genel Kurul, Temyiz Kurulu, Daire).
    """
    decision_id: str = Field(..., description="Unique decision identifier")
    decision_type: str = Field(..., description="Value")
    source_url: str = Field(..., description="Original URL where the document was retrieved")
    markdown_content: Optional[str] = Field(None, description="Full decision text converted to Markdown format")
    retrieval_date: Optional[str] = Field(None, description="Date when document was retrieved (ISO format)")
    error_message: Optional[str] = Field(None, description="Error message if document retrieval failed")

# ============================================================================
# Unified Models
# ============================================================================

class SayistayUnifiedSearchRequest(BaseModel):
    """Unified search request for all Sayıştay decision types."""
    decision_type: Literal["genel_kurul", "temyiz_kurulu", "daire"] = Field(..., description="Decision type: genel_kurul, temyiz_kurulu, or daire")
    
    # Common pagination parameters
    start: int = Field(0, ge=0, description="Starting record for pagination (0-based)")
    length: int = Field(10, ge=1, le=100, description="Number of records per page (1-100)")
    
    # Common search parameters
    karar_tarih_baslangic: str = Field("", description="Start date (DD.MM.YYYY format)")
    karar_tarih_bitis: str = Field("", description="End date (DD.MM.YYYY format)")
    kamu_idaresi_turu: KamuIdaresiTuruEnum = Field("ALL", description="Public administration type filter")
    ilam_no: str = Field("", description="Audit report number (İlam No, max 50 chars)")
    web_karar_konusu: WebKararKonusuEnum = Field("ALL", description="Decision subject category filter")
    
    # Genel Kurul specific parameters (ignored for other types)
    karar_no: str = Field("", description="Decision number (genel_kurul only)")
    karar_ek: str = Field("", description="Decision appendix number (genel_kurul only)")
    karar_tamami: str = Field("", description="Full text search (genel_kurul only)")
    
    # Temyiz Kurulu specific parameters (ignored for other types)
    ilam_dairesi: DaireEnum = Field("ALL", description="Audit chamber selection (temyiz_kurulu only)")
    yili: str = Field("", description="Year (YYYY format, temyiz_kurulu only)")
    dosya_no: str = Field("", description="File number (temyiz_kurulu only)")
    temyiz_tutanak_no: str = Field("", description="Appeals board meeting minutes number (temyiz_kurulu only)")
    temyiz_karar: str = Field("", description="Appeals decision text search (temyiz_kurulu only)")
    
    # Daire specific parameters (ignored for other types)
    yargilama_dairesi: DaireEnum = Field("ALL", description="Chamber selection (daire only)")
    hesap_yili: str = Field("", description="Account year (daire only)")
    web_karar_metni: str = Field("", description="Decision text search (daire only)")

class SayistayUnifiedSearchResult(BaseModel):
    """Unified search result containing decisions from any Sayıştay decision type."""
    decision_type: Literal["genel_kurul", "temyiz_kurulu", "daire"] = Field(..., description="Type of decisions returned")
    decisions: List[Dict[str, Any]] = Field(default_factory=list, description="Decision list (structure varies by type)")
    total_records: int = Field(0, description="Total number of records found")
    total_filtered: int = Field(0, description="Number of records after filtering")
    draw: int = Field(1, description="DataTables draw counter")

class SayistayUnifiedDocumentMarkdown(BaseModel):
    """Unified document model for all Sayıştay decision types."""
    decision_type: Literal["genel_kurul", "temyiz_kurulu", "daire"] = Field(..., description="Type of document")
    decision_id: str = Field(..., description="Decision ID")
    source_url: str = Field(..., description="Source URL of the document")
    document_data: Dict[str, Any] = Field(default_factory=dict, description="Document content and metadata")
    markdown_content: Optional[str] = Field(None, description="Markdown content")
    error_message: Optional[str] = Field(None, description="Error message if retrieval failed")