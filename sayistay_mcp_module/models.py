# sayistay_mcp_module/models.py

from pydantic import BaseModel, Field
from typing import Optional, List, Union
from .enums import DaireEnum, KamuIdaresiTuruEnum, WebKararKonusuEnum

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
    karar_no: Optional[str] = Field(None, description="Decision no")
    karar_ek: Optional[str] = Field(None, description="Appendix no")
    
    karar_tarih_baslangic: Optional[str] = Field(None, description="Start year (YYYY)")
    
    karar_tarih_bitis: Optional[str] = Field(None, description="End year")
    
    karar_tamami: Optional[str] = Field(None, description="Value")
    
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
    
    yili: Optional[str] = Field(None, description="Value")
    
    karar_tarih_baslangic: Optional[str] = Field(None, description="Value")
    
    karar_tarih_bitis: Optional[str] = Field(None, description="End year")
    
    kamu_idaresi_turu: KamuIdaresiTuruEnum = Field("ALL", description="Value")
    
    ilam_no: Optional[str] = Field(None, description="Audit report number (İlam No, max 50 chars)")
    dosya_no: Optional[str] = Field(None, description="File number for the case")
    temyiz_tutanak_no: Optional[str] = Field(None, description="Appeals board meeting minutes number")
    
    temyiz_karar: Optional[str] = Field(None, description="Value")
    
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
    
    karar_tarih_baslangic: Optional[str] = Field(None, description="Value")
    
    karar_tarih_bitis: Optional[str] = Field(None, description="End year")
    
    ilam_no: Optional[str] = Field(None, description="Audit report number (İlam No, max 50 chars)")
    
    kamu_idaresi_turu: KamuIdaresiTuruEnum = Field("ALL", description="Value")
    
    hesap_yili: Optional[str] = Field(None, description="Value")
    
    web_karar_konusu: WebKararKonusuEnum = Field("ALL", description="Value")
    
    web_karar_metni: Optional[str] = Field(None, description="Value")
    
    # DataTables pagination
    start: int = Field(0, description="Starting record for pagination (0-based)")
    length: int = Field(10, description="Number of records per page (1-10)")

class DaireDecision(BaseModel):
    """Single Daire decision entry from search results."""
    id: int = Field(..., description="Unique decision ID")
    yargilama_dairesi: int = Field(..., description="Chamber number (1-8)")
    karar_tarih: str = Field(..., description="Decision date in DD.MM.YYYY format")
    karar_no: str = Field(..., description="Decision number")
    ilam_no: Optional[str] = Field(None, description="Audit report number (may be null)")
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