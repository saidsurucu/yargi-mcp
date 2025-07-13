# bedesten_mcp_module/models.py

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal, Union
from datetime import datetime

# Import YargitayBirimEnum for chamber filtering
from yargitay_mcp_module.models import YargitayBirimEnum

# Danıştay Chamber/Board Options
DanistayBirimEnum = Literal[
    "ALL",  # "ALL" for all chambers
    # Main Councils
    "Büyük Gen.Kur.",  # Grand General Assembly
    "İdare Dava Daireleri Kurulu",  # Administrative Cases Chambers Council
    "Vergi Dava Daireleri Kurulu",  # Tax Cases Chambers Council
    "İçtihatları Birleştirme Kurulu",  # Precedents Unification Council
    "İdari İşler Kurulu",  # Administrative Affairs Council
    "Başkanlar Kurulu",  # Presidents Council
    # Chambers
    "1. Daire", "2. Daire", "3. Daire", "4. Daire", "5. Daire",
    "6. Daire", "7. Daire", "8. Daire", "9. Daire", "10. Daire",
    "11. Daire", "12. Daire", "13. Daire", "14. Daire", "15. Daire",
    "16. Daire", "17. Daire",
    # Military High Administrative Court
    "Askeri Yüksek İdare Mahkemesi",
    "Askeri Yüksek İdare Mahkemesi Daireler Kurulu",
    "Askeri Yüksek İdare Mahkemesi Başsavcılığı",
    "Askeri Yüksek İdare Mahkemesi 1. Daire",
    "Askeri Yüksek İdare Mahkemesi 2. Daire", 
    "Askeri Yüksek İdare Mahkemesi 3. Daire"
]

# Search Request Models
class BedestenSearchData(BaseModel):
    pageSize: int = Field(..., description="Results per page (1-10)")
    pageNumber: int = Field(..., description="Page number (1-indexed)")
    itemTypeList: List[str] = Field(..., description="Court type filter (YARGITAYKARARI/DANISTAYKARAR/YERELHUKUK/ISTINAFHUKUK/KYB)")
    phrase: str = Field(..., description="Search phrase (use \"exact phrase\" for precise matching)")
    birimAdi: Optional[Union[YargitayBirimEnum, DanistayBirimEnum]] = Field(None, description="Chamber filter (optional)")
    kararTarihiStart: Optional[str] = Field(None, description="Start date (ISO 8601 format)")
    kararTarihiEnd: Optional[str] = Field(None, description="End date (ISO 8601 format)")
    sortFields: List[str] = Field(default=["KARAR_TARIHI"], description="Sort fields")
    sortDirection: str = Field(default="desc", description="Sort direction (asc/desc)")

class BedestenSearchRequest(BaseModel):
    data: BedestenSearchData
    applicationName: str = "UyapMevzuat"
    paging: bool = True

# Search Response Models
class BedestenItemType(BaseModel):
    name: str
    description: str

class BedestenDecisionEntry(BaseModel):
    documentId: str
    itemType: BedestenItemType
    birimId: Optional[str] = None
    birimAdi: Optional[str]
    esasNoYil: Optional[int] = None
    esasNoSira: Optional[int] = None
    kararNoYil: Optional[int] = None
    kararNoSira: Optional[int] = None
    kararTuru: Optional[str] = None
    kararTarihi: str
    kararTarihiStr: str
    kesinlesmeDurumu: Optional[str] = None
    kararNo: Optional[str] = None
    esasNo: Optional[str] = None

class BedestenSearchDataResponse(BaseModel):
    emsalKararList: List[BedestenDecisionEntry]
    total: int
    start: int

class BedestenSearchResponse(BaseModel):
    data: Optional[BedestenSearchDataResponse]
    metadata: Dict[str, Any]

# Document Request/Response Models
class BedestenDocumentRequestData(BaseModel):
    documentId: str

class BedestenDocumentRequest(BaseModel):
    data: BedestenDocumentRequestData
    applicationName: str = "UyapMevzuat"

class BedestenDocumentData(BaseModel):
    content: str  # Base64 encoded HTML or PDF
    mimeType: str
    version: int

class BedestenDocumentResponse(BaseModel):
    data: BedestenDocumentData
    metadata: Dict[str, Any]

class BedestenDocumentMarkdown(BaseModel):
    documentId: str = Field(..., description="The document ID (Belge Kimliği) from Bedesten")
    markdown_content: Optional[str] = Field(None, description="The decision content (Karar İçeriği) converted to Markdown")
    source_url: str = Field(..., description="The source URL (Kaynak URL) of the document")
    mime_type: Optional[str] = Field(None, description="Original content type (İçerik Türü) (text/html or application/pdf)")