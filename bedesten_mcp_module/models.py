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
    pageSize: int = Field(..., description="""Number of results per page.
        Range: 1-100 results per page
        Recommended: 10-50 for balanced performance
        Higher values for comprehensive analysis""")
    pageNumber: int = Field(..., description="""Page number to retrieve (1-indexed).
        Start with 1 for first page
        Calculate total pages from response.data.total / pageSize
        Navigate: pageNumber=2 gets next set of results""")
    itemTypeList: List[str] = Field(..., description="""Court type filter - determines which court decisions to search:
        • ["YARGITAYKARARI"]: Court of Cassation (Yargıtay) - supreme court civil/criminal decisions
        • ["DANISTAYKARAR"]: Council of State (Danıştay) - administrative court decisions
        • ["YERELHUKUK"]: Local Civil Courts (Yerel Hukuk Mahkemeleri) - first instance civil decisions
        • ["ISTINAFHUKUK"]: Civil Courts of Appeals (İstinaf Hukuk Mahkemeleri) - appellate court decisions
        • ["KYB"]: Extraordinary Appeal (Kanun Yararına Bozma) - extraordinary appeal decisions
        Note: Use single-item list for specific court type targeting""")
    phrase: str = Field(..., description="""Search phrase/keyword with advanced search support:
        • Regular search: "mülkiyet kararı" - searches words separately
        • Exact phrase: "\"mülkiyet kararı\"" - searches exact phrase (more precise)
        • Legal concepts: "\"idari işlem\"", "\"sözleşme ihlali\"", "\"tazminat davası\""
        • Empty string: searches all documents (use with filters)
        Exact phrases significantly reduce false positives for precise legal research""")
    birimAdi: Optional[Union[YargitayBirimEnum, DanistayBirimEnum]] = Field(None, description="""
        Chamber/Department (Daire) filter (optional). Available options depend on itemTypeList:
        
        For YARGITAYKARARI - Court of Cassation (52 options):
        - None/null for ALL chambers
        - 'Civil General Assembly (Hukuk Genel Kurulu)', '1st Civil Chamber (1. Hukuk Dairesi)' through '23rd Civil Chamber (23. Hukuk Dairesi)'
        - 'Criminal General Assembly (Ceza Genel Kurulu)', '1st Criminal Chamber (1. Ceza Dairesi)' through '23rd Criminal Chamber (23. Ceza Dairesi)'  
        - 'Civil Chambers Presidents Board (Hukuk Daireleri Başkanlar Kurulu)', 'Criminal Chambers Presidents Board (Ceza Daireleri Başkanlar Kurulu)'
        - 'Grand General Assembly (Büyük Genel Kurulu)'
        
        For DANISTAYKARAR - Council of State (27 options):
        - None/null for ALL chambers
        - 'Grand General Assembly (Büyük Gen.Kur.)', 'Administrative Cases Chambers Council (İdare Dava Daireleri Kurulu)', 'Tax Cases Chambers Council (Vergi Dava Daireleri Kurulu)'
        - '1st Chamber (1. Daire)' through '17th Chamber (17. Daire)'
        - 'Precedents Unification Council (İçtihatları Birleştirme Kurulu)', 'Administrative Affairs Council (İdari İşler Kurulu)', 'Presidents Council (Başkanlar Kurulu)'
        - Military courts: 'Military High Administrative Court (Askeri Yüksek İdare Mahkemesi)' variants
    """)
    kararTarihiStart: Optional[str] = Field(None, description="""Decision start date (Karar Tarihi Başlangıç) filter (optional).
        Format: YYYY-MM-DDTHH:MM:SS.000Z (ISO 8601 with Z timezone)
        Examples:
        • "2024-01-01T00:00:00.000Z" - from beginning of 2024
        • "2023-06-15T00:00:00.000Z" - from June 15, 2023
        • "2024-03-01T00:00:00.000Z" - from March 1, 2024
        Use with kararTarihiEnd for date range, or alone for "from date" filtering""")
    kararTarihiEnd: Optional[str] = Field(None, description="""Decision end date (Karar Tarihi Bitiş) filter (optional).
        Format: YYYY-MM-DDTHH:MM:SS.000Z (ISO 8601 with Z timezone)
        Examples:
        • "2024-12-31T23:59:59.999Z" - until end of 2024
        • "2023-12-31T23:59:59.999Z" - until end of 2023  
        • "2024-06-30T23:59:59.999Z" - until end of June 2024
        Use with kararTarihiStart for date range, or alone for "until date" filtering""")
    sortFields: List[str] = Field(default=["KARAR_TARIHI"], description="""Sorting field (Sıralama Alanı) specification.
        ["KARAR_TARIHI"]: Sort by decision date (Karar Tarihi) [DEFAULT]
        Most common use case for chronological ordering""")
    sortDirection: str = Field(default="desc", description="""Sort direction (Sıralama Yönü) for results.
        "desc": Descending order - newest decisions first [DEFAULT]
        "asc": Ascending order - oldest decisions first
        Recommended: "desc" for latest legal developments""")

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
    data: BedestenSearchDataResponse
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