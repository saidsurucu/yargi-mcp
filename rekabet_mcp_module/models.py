# rekabet_mcp_module/models.py

from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional, Any
from enum import Enum

# Enum for decision type GUIDs (used by the client and expected by the website)
class RekabetKararTuruGuidEnum(str, Enum):
    TUMU = ""  # Represents "All" or "Select Decision Type"
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
    sayfaAdi: Optional[str] = Field(None, description="Search in decision title (Başlık).")
    YayinlanmaTarihi: Optional[str] = Field(None, description="Publication date (Yayım Tarihi), e.g., DD.MM.YYYY.")
    PdfText: Optional[str] = Field(
        None,
        description='Search in decision text (Metin). For an exact phrase match, enclose the phrase in double quotes (e.g., "\\"vertical agreement\\" competition). The website indicates that using "" provides more precise results for phrases.'
    )
    # This field uses the GUID enum as it's used by the client to make the actual web request.
    KararTuruID: Optional[RekabetKararTuruGuidEnum] = Field(RekabetKararTuruGuidEnum.TUMU, description="Decision type (Karar Türü) GUID for internal client use, corresponding to the website's values.")
    KararSayisi: Optional[str] = Field(None, description="Decision number (Karar Sayısı).")
    KararTarihi: Optional[str] = Field(None, description="Decision date (Karar Tarihi), e.g., DD.MM.YYYY.")
    page: int = Field(1, ge=1, description="Page number to fetch for results list.")

class RekabetDecisionSummary(BaseModel):
    """Model for a single Rekabet Kurumu decision summary from search results."""
    publication_date: Optional[str] = Field(None, description="Publication Date (Yayımlanma Tarihi).")
    decision_number: Optional[str] = Field(None, description="Decision Number (Karar Sayısı).")
    decision_date: Optional[str] = Field(None, description="Decision Date (Karar Tarihi).")
    decision_type_text: Optional[str] = Field(None, description="Decision Type as text (Karar Türü - metin olarak).")
    title: Optional[str] = Field(None, description="Decision title or summary text.")
    decision_url: Optional[HttpUrl] = Field(None, description="URL to the decision's landing page (e.g., /Karar?kararId=...).")
    karar_id: Optional[str] = Field(None, description="GUID of the decision, extracted from its URL.")
    related_cases_url: Optional[HttpUrl] = Field(None, description="URL to related court cases page, if available.")

class RekabetSearchResult(BaseModel):
    """Model for the overall search result for Rekabet Kurumu decisions."""
    decisions: List[RekabetDecisionSummary]
    total_records_found: Optional[int] = Field(None, description="Total number of records found matching the query.")
    retrieved_page_number: int = Field(description="The page number of the results that were retrieved.")
    total_pages: Optional[int] = Field(None, description="Total number of pages available for the query.")

class RekabetDocument(BaseModel):
    """
    Model for a Rekabet Kurumu decision document.
    Contains metadata from the landing page, a link to the PDF,
    and the PDF's content converted to paginated Markdown.
    """
    source_landing_page_url: HttpUrl = Field(description="The URL of the decision's landing page from which the PDF was identified.")
    karar_id: str = Field(description="GUID of the decision.")
    
    title_on_landing_page: Optional[str] = Field(None, description="Title as found on the landing page (e.g., from <title> tag or a main heading). Could be a generic title if direct PDF.")
    pdf_url: Optional[HttpUrl] = Field(None, description="Direct URL to the decision PDF document, if successfully found and resolved.")
    
    # Fields for Markdown content derived from the PDF
    markdown_chunk: Optional[str] = Field(None, description="A 5,000 character chunk of the Markdown content derived from the decision PDF.")
    current_page: int = Field(1, description="The current page number of the PDF-derived markdown chunk (1-indexed).")
    total_pages: int = Field(1, description="Total number of pages for the full PDF-derived markdown content. Will be 0 if content could not be processed.")
    is_paginated: bool = Field(False, description="True if the full PDF-derived markdown content is split into multiple pages.")
    
    error_message: Optional[str] = Field(None, description="Contains an error message if the document retrieval or processing failed at any stage.")