# kik_mcp_module/models.py
from pydantic import BaseModel, Field, HttpUrl, computed_field, ConfigDict
from typing import List, Optional
from enum import Enum
import base64 # Base64 encoding/decoding için

class KikKararTipi(str, Enum):
    """Enum for KIK (Public Procurement Authority) Decision Types."""
    UYUSMAZLIK = "rbUyusmazlik"
    DUZENLEYICI = "rbDuzenleyici"
    MAHKEME = "rbMahkeme"

class KikSearchRequest(BaseModel):
    """Model for KIK Decision search criteria."""
    karar_tipi: KikKararTipi = Field(KikKararTipi.UYUSMAZLIK, description="Type")
    karar_no: Optional[str] = Field(None, description="Number")
    karar_tarihi_baslangic: Optional[str] = Field(None, description="Start date", pattern=r"^\d{2}\.\d{2}\.\d{4}$")
    karar_tarihi_bitis: Optional[str] = Field(None, description="End date", pattern=r"^\d{2}\.\d{2}\.\d{4}$")
    resmi_gazete_sayisi: Optional[str] = Field(None, description="Gazette no")
    resmi_gazete_tarihi: Optional[str] = Field(None, description="Gazette date", pattern=r"^\d{2}\.\d{2}\.\d{4}$")
    basvuru_konusu_ihale: Optional[str] = Field(None, description="Tender subject")
    basvuru_sahibi: Optional[str] = Field(None, description="Applicant")
    ihaleyi_yapan_idare: Optional[str] = Field(None, description="Entity")
    yil: Optional[str] = Field(None, description="Year")
    karar_metni: Optional[str] = Field(None, description="Text search")
    page: int = Field(1, ge=1, description="Page")

class KikDecisionEntry(BaseModel):
    """Represents a single decision entry from KIK search results."""
    preview_event_target: str = Field(..., description="Internal event target for fetching details.")
    karar_no_str: str = Field(..., alias="kararNo", description="Raw decision number as extracted from KIK (e.g., '2024/UH.II-1766').")
    karar_tipi: KikKararTipi = Field(..., description="The type of decision this entry belongs to.")
    
    karar_tarihi_str: str = Field(..., alias="kararTarihi", description="Decision date.")
    idare_str: Optional[str] = Field(None, alias="idare", description="Procuring entity.")
    basvuru_sahibi_str: Optional[str] = Field(None, alias="basvuruSahibi", description="Applicant.")
    ihale_konusu_str: Optional[str] = Field(None, alias="ihaleKonusu", description="Tender subject.")

    @computed_field
    @property
    def karar_id(self) -> str:
        """
        A Base64 encoded unique ID for the decision, combining decision type and number.
        Format before encoding: "{karar_tipi.value}|{karar_no_str}"
        """
        combined_key = f"{self.karar_tipi.value}|{self.karar_no_str}"
        return base64.b64encode(combined_key.encode('utf-8')).decode('utf-8')

    model_config = ConfigDict(populate_by_name=True)

class KikSearchResult(BaseModel):
    """Model for KIK search results."""
    decisions: List[KikDecisionEntry]
    total_records: int = 0
    current_page: int = 1

class KikDocumentMarkdown(BaseModel):
    """
    KIK decision document, with Markdown content potentially paginated.
    """
    retrieved_with_karar_id: Optional[str] = Field(None, description="The Base64 encoded karar_id that was used to request this document.")
    # Decode edilmiş karar no ve tipini de yanıt olarak ekleyelim, Claude için faydalı olabilir.
    retrieved_karar_no: Optional[str] = Field(None, description="The raw KIK Decision Number (e.g., '2024/UH.II-1766') this document pertains to.")
    retrieved_karar_tipi: Optional[KikKararTipi] = Field(None, description="The KIK Decision Type this document pertains to.")
    
    karar_id_param_from_url: Optional[str] = Field(None, alias="kararIdParam", description="The KIK system's internal KararId parameter from the document's display URL (KurulKararGoster.aspx).")
    markdown_chunk: Optional[str] = Field(None, description="The requested chunk of the decision content converted to Markdown.")
    source_url: Optional[str] = Field(None, description="The source URL of the original document (KurulKararGoster.aspx).")
    error_message: Optional[str] = Field(None, description="Error message if document retrieval or processing failed.")
    current_page: int = Field(1, description="The current page number of the markdown chunk being returned.")
    total_pages: int = Field(1, description="The total number of pages the full markdown content is divided into.")
    is_paginated: bool = Field(False, description="True if the full markdown content is split into multiple pages.")
    full_content_char_count: Optional[int] = Field(None, description="Total character count of the full markdown content before chunking.")

    model_config = ConfigDict(populate_by_name=True)