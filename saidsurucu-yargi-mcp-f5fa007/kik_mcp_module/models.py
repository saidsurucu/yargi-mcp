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
    karar_no: str = Field("", description="No")
    karar_tarihi_baslangic: str = Field("", description="Start", pattern=r"^\d{2}\.\d{2}\.\d{4}$|^$")
    karar_tarihi_bitis: str = Field("", description="End", pattern=r"^\d{2}\.\d{2}\.\d{4}$|^$")
    resmi_gazete_sayisi: str = Field("", description="Gazette")
    resmi_gazete_tarihi: str = Field("", description="Date", pattern=r"^\d{2}\.\d{2}\.\d{4}$|^$")
    basvuru_konusu_ihale: str = Field("", description="Subject")
    basvuru_sahibi: str = Field("", description="Applicant")
    ihaleyi_yapan_idare: str = Field("", description="Entity")
    yil: str = Field("", description="Year")
    karar_metni: str = Field("", description="Text")
    page: int = Field(1, ge=1, description="Page")

class KikDecisionEntry(BaseModel):
    """Represents a single decision entry from KIK search results."""
    preview_event_target: str = Field(..., description="Event target")
    karar_no_str: str = Field(..., alias="kararNo", description="Decision number")
    karar_tipi: KikKararTipi = Field(..., description="Decision type")
    
    karar_tarihi_str: str = Field(..., alias="kararTarihi", description="Date")
    idare_str: str = Field("", alias="idare", description="Entity")
    basvuru_sahibi_str: str = Field("", alias="basvuruSahibi", description="Applicant")
    ihale_konusu_str: str = Field("", alias="ihaleKonusu", description="Subject")

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
    retrieved_with_karar_id: Optional[str] = Field(None, description="Request ID")
    retrieved_karar_no: Optional[str] = Field(None, description="Decision number")
    retrieved_karar_tipi: Optional[KikKararTipi] = Field(None, description="Decision type")
    
    karar_id_param_from_url: Optional[str] = Field(None, alias="kararIdParam", description="Internal ID")
    markdown_chunk: Optional[str] = Field(None, description="Content")
    source_url: Optional[str] = Field(None, description="Source URL")
    error_message: Optional[str] = Field(None, description="Error")
    current_page: int = Field(1, description="Page")
    total_pages: int = Field(1, description="Total pages")
    is_paginated: bool = Field(False, description="Paginated")
    full_content_char_count: Optional[int] = Field(None, description="Char count")

    model_config = ConfigDict(populate_by_name=True)