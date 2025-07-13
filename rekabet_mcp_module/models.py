# rekabet_mcp_module/models.py

from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional, Any
from enum import Enum

# Enum for decision type GUIDs (used by the client and expected by the website)
class RekabetKararTuruGuidEnum(str, Enum):
    TUMU = "ALL"  # Represents "All" or "Select Decision Type"
    BIRLESME_DEVRALMA = "2fff0979-9f9d-42d7-8c2e-a30705889542"  # Merger and Acquisition
    DIGER = "dda8feaf-c919-405c-9da1-823f22b45ad9"  # Other
    MENFI_TESPIT_MUAFIYET = "95ccd210-5304-49c5-b9e0-8ee53c50d4e8"  # Negative Clearance and Exemption
    OZELLESTIRME = "e1f14505-842b-4af5-95d1-312d6de1a541"  # Privatization
    REKABET_IHLALI = "720614bf-efd1-4dca-9785-b98eb65f2677"  # Competition Infringement

# Enum for user-friendly decision type names (for server tool parameters)
# These correspond to the display names on the website's select dropdown.
class RekabetKararTuruAdiEnum(str, Enum):
    TUMU = "Tümü"  # Corresponds to the empty value "" for GUID, meaning "All"
    BIRLESME_VE_DEVRALMA = "Birleşme ve Devralma"
    DIGER = "Diğer"
    MENFI_TESPIT_VE_MUAFIYET = "Menfi Tespit ve Muafiyet"
    OZELLESTIRME = "Özelleştirme"
    REKABET_IHLALI = "Rekabet İhlali"

class RekabetKurumuSearchRequest(BaseModel):
    """Model for Rekabet Kurumu (Turkish Competition Authority) search request."""
    sayfaAdi: Optional[str] = Field(None, description="Title")
    YayinlanmaTarihi: Optional[str] = Field(None, description="Date")
    PdfText: Optional[str] = Field(None, description="Text")
    KararTuruID: Optional[RekabetKararTuruGuidEnum] = Field(RekabetKararTuruGuidEnum.TUMU, description="Type")
    KararSayisi: Optional[str] = Field(None, description="No")
    KararTarihi: Optional[str] = Field(None, description="Date")
    page: int = Field(1, ge=1, description="Page")

class RekabetDecisionSummary(BaseModel):
    """Model for a single Rekabet Kurumu decision summary from search results."""
    publication_date: Optional[str] = Field(None, description="Pub date")
    decision_number: Optional[str] = Field(None, description="Number")
    decision_date: Optional[str] = Field(None, description="Date")
    decision_type_text: Optional[str] = Field(None, description="Type")
    title: Optional[str] = Field(None, description="Title")
    decision_url: Optional[HttpUrl] = Field(None, description="URL")
    karar_id: Optional[str] = Field(None, description="ID")
    related_cases_url: Optional[HttpUrl] = Field(None, description="Cases URL")

class RekabetSearchResult(BaseModel):
    """Model for the overall search result for Rekabet Kurumu decisions."""
    decisions: List[RekabetDecisionSummary]
    total_records_found: Optional[int] = Field(None, description="Total")
    retrieved_page_number: int = Field(description="Page")
    total_pages: Optional[int] = Field(None, description="Pages")

class RekabetDocument(BaseModel):
    """
    Model for a Rekabet Kurumu decision document.
    Contains metadata from the landing page, a link to the PDF,
    and the PDF's content converted to paginated Markdown.
    """
    source_landing_page_url: HttpUrl = Field(description="Source URL")
    karar_id: str = Field(description="ID")
    
    title_on_landing_page: Optional[str] = Field(None, description="Title")
    pdf_url: Optional[HttpUrl] = Field(None, description="PDF URL")
    
    markdown_chunk: Optional[str] = Field(None, description="Content")
    current_page: int = Field(1, description="Page")
    total_pages: int = Field(1, description="Total pages")
    is_paginated: bool = Field(False, description="Paginated")
    
    error_message: Optional[str] = Field(None, description="Error")