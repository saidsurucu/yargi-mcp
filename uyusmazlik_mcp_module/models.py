# uyusmazlik_mcp_module/models.py

from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional
from enum import Enum

# Enum definitions for user-friendly input based on the provided HTML form
class UyusmazlikBolumEnum(str, Enum):
    """User-friendly names for 'BolumId'."""
    TUMU = "ALL" # Represents "...Seçiniz..." or all
    CEZA_BOLUMU = "Ceza Bölümü"
    GENEL_KURUL_KARARLARI = "Genel Kurul Kararları"
    HUKUK_BOLUMU = "Hukuk Bölümü"

class UyusmazlikTuruEnum(str, Enum):
    """User-friendly names for 'UyusmazlikId'."""
    TUMU = "ALL" # Represents "...Seçiniz..." or all
    GOREV_UYUSMAZLIGI = "Görev Uyuşmazlığı"
    HUKUM_UYUSMAZLIGI = "Hüküm Uyuşmazlığı"

class UyusmazlikKararSonucuEnum(str, Enum): # Based on checkbox text in the form
    """User-friendly names for 'KararSonucuList' items."""
    HUKUM_UYUSMAZLIGI_OLMADIGINA_DAIR = "Hüküm Uyuşmazlığı Olmadığına Dair"
    HUKUM_UYUSMAZLIGI_OLDUGUNA_DAIR = "Hüküm Uyuşmazlığı Olduğuna Dair"
    # Add other "Karar Sonucu" options from the form's checkboxes as Enum members
    # Example: GOREVLI_YARGI_YERI_ADLI = "Görevli Yargı Yeri Belirlenmesine Dair (Adli Yargı)"
    # The client will map these enum values (which are strings) to their respective IDs.

class UyusmazlikSearchRequest(BaseModel): # This is the model the MCP tool will accept
    """Model for Uyuşmazlık Mahkemesi search request using user-friendly terms."""
    icerik: Optional[str] = Field("", description="Search text")
    
    bolum: Optional[UyusmazlikBolumEnum] = Field(
        UyusmazlikBolumEnum.TUMU, 
        description="Department"
    )
    uyusmazlik_turu: Optional[UyusmazlikTuruEnum] = Field(
        UyusmazlikTuruEnum.TUMU, 
        description="Dispute type"
    )
    
    # User provides a list of user-friendly names for Karar Sonucu
    karar_sonuclari: Optional[List[UyusmazlikKararSonucuEnum]] = Field( # Changed to list of Enums
        default_factory=list, 
        description="Decision types"
    )
    
    esas_yil: Optional[str] = Field("", description="Case year")
    esas_sayisi: Optional[str] = Field("", description="Case no")
    karar_yil: Optional[str] = Field("", description="Decision year")
    karar_sayisi: Optional[str] = Field("", description="Decision no")
    kanun_no: Optional[str] = Field("", description="Law no")
    
    karar_date_begin: Optional[str] = Field("", description="Start date (DD.MM.YYYY)")
    karar_date_end: Optional[str] = Field("", description="End date (DD.MM.YYYY)")
    
    resmi_gazete_sayi: Optional[str] = Field("", description="Gazette no")
    resmi_gazete_date: Optional[str] = Field("", description="Gazette date (DD.MM.YYYY)")
    
    # Detailed text search fields from the "icerikDetail" section of the form
    tumce: Optional[str] = Field("", description="Exact phrase")
    wild_card: Optional[str] = Field("", description="Wildcard search")
    hepsi: Optional[str] = Field("", description="All words")
    herhangi_birisi: Optional[str] = Field("", description="Any word")
    not_hepsi: Optional[str] = Field("", description="Exclude words")

class UyusmazlikApiDecisionEntry(BaseModel):
    """Model for an individual decision entry parsed from Uyuşmazlık API's HTML search response."""
    karar_sayisi: Optional[str] = Field(None)
    esas_sayisi: Optional[str] = Field(None)
    bolum: Optional[str] = Field(None)
    uyusmazlik_konusu: Optional[str] = Field(None)
    karar_sonucu: Optional[str] = Field(None)
    popover_content: Optional[str] = Field(None, description="Summary")
    document_url: HttpUrl # Full URL to the decision document HTML page
    pdf_url: Optional[HttpUrl] = Field(None, description="PDF URL")

class UyusmazlikSearchResponse(BaseModel): # This is what the MCP tool will return
    """Response model for Uyuşmazlık Mahkemesi search results for the MCP tool."""
    decisions: List[UyusmazlikApiDecisionEntry]
    total_records_found: Optional[int] = Field(None, description="Total number of records found for the query, if available.")

class UyusmazlikDocumentMarkdown(BaseModel):
    """Model for an Uyuşmazlık decision document, containing only Markdown content."""
    source_url: HttpUrl # The URL from which the content was fetched
    markdown_content: Optional[str] = Field(None, description="The decision content converted to Markdown.")