# mcp_server_main.py
import asyncio
import atexit
import logging
import os
from pydantic import HttpUrl, Field 
from typing import Optional, Dict, List, Literal
import urllib.parse

# --- Logging Configuration Start ---
LOG_DIRECTORY = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
if not os.path.exists(LOG_DIRECTORY):
    os.makedirs(LOG_DIRECTORY)
LOG_FILE_PATH = os.path.join(LOG_DIRECTORY, "mcp_server.log")

root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG) 

log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(threadName)s - %(message)s')

file_handler = logging.FileHandler(LOG_FILE_PATH, mode='a', encoding='utf-8')
file_handler.setFormatter(log_formatter)
file_handler.setLevel(logging.DEBUG)
root_logger.addHandler(file_handler)

console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)
console_handler.setLevel(logging.INFO) 
root_logger.addHandler(console_handler)

logger = logging.getLogger(__name__)
# --- Logging Configuration End ---

from fastmcp import FastMCP

# --- Module Imports ---
from yargitay_mcp_module.client import YargitayOfficialApiClient
from yargitay_mcp_module.models import (
    YargitayDetailedSearchRequest, YargitayDocumentMarkdown, CompactYargitaySearchResult
)
from danistay_mcp_module.client import DanistayApiClient
from danistay_mcp_module.models import (
    DanistayKeywordSearchRequest, DanistayDetailedSearchRequest,
    DanistayDocumentMarkdown, CompactDanistaySearchResult
)
from emsal_mcp_module.client import EmsalApiClient
from emsal_mcp_module.models import (
    EmsalSearchRequest, EmsalDocumentMarkdown, CompactEmsalSearchResult
)
from uyusmazlik_mcp_module.client import UyusmazlikApiClient
from uyusmazlik_mcp_module.models import (
    UyusmazlikSearchRequest, UyusmazlikSearchResponse, UyusmazlikDocumentMarkdown,
    UyusmazlikBolumEnum, UyusmazlikTuruEnum, UyusmazlikKararSonucuEnum
)
from anayasa_mcp_module.client import AnayasaMahkemesiApiClient
from anayasa_mcp_module.bireysel_client import AnayasaBireyselBasvuruApiClient
from anayasa_mcp_module.models import (
    AnayasaNormDenetimiSearchRequest,
    AnayasaSearchResult,
    AnayasaDocumentMarkdown,
    AnayasaBireyselReportSearchRequest,
    AnayasaBireyselReportSearchResult,
    AnayasaBireyselBasvuruDocumentMarkdown,
    AnayasaDonemEnum, AnayasaBasvuruTuruEnum, AnayasaVarYokEnum,
    AnayasaNormTuruEnum, AnayasaIncelemeSonucuEnum, AnayasaSonucGerekcesiEnum
)
# KIK Module Imports
from kik_mcp_module.client import KikApiClient
from kik_mcp_module.models import ( 
    KikKararTipi, 
    KikSearchRequest,
    KikSearchResult,
    KikDocumentMarkdown 
)

from rekabet_mcp_module.client import RekabetKurumuApiClient
from rekabet_mcp_module.models import (
    RekabetKurumuSearchRequest,
    RekabetSearchResult,
    RekabetDocument,
    RekabetKararTuruGuidEnum
)


app = FastMCP(
    name="YargiMCP",
    instructions="MCP server for TR legal databases (Yargitay, Danistay, Emsal, Uyusmazlik, Anayasa-Norm, Anayasa-Bireysel, KIK).",
    dependencies=["httpx", "beautifulsoup4", "markitdown", "pydantic", "aiohttp", "playwright"]
)

# --- API Client Instances ---
yargitay_client_instance = YargitayOfficialApiClient()
danistay_client_instance = DanistayApiClient()
emsal_client_instance = EmsalApiClient()
uyusmazlik_client_instance = UyusmazlikApiClient()
anayasa_norm_client_instance = AnayasaMahkemesiApiClient()
anayasa_bireysel_client_instance = AnayasaBireyselBasvuruApiClient()
kik_client_instance = KikApiClient()
rekabet_client_instance = RekabetKurumuApiClient()


KARAR_TURU_ADI_TO_GUID_ENUM_MAP = {
    "": RekabetKararTuruGuidEnum.TUMU, 
    "Birleşme ve Devralma": RekabetKararTuruGuidEnum.BIRLESME_DEVRALMA,
    "Diğer": RekabetKararTuruGuidEnum.DIGER,
    "Menfi Tespit ve Muafiyet": RekabetKararTuruGuidEnum.MENFI_TESPIT_MUAFIYET,
    "Özelleştirme": RekabetKararTuruGuidEnum.OZELLESTIRME,
    "Rekabet İhlali": RekabetKararTuruGuidEnum.REKABET_IHLALI,
}

# --- MCP Tools for Yargitay ---
@app.tool()
async def search_yargitay_detailed(
    arananKelime: str = Field("", description="""Keyword to search for.
    Search operators:
    • Space between words = OR logic (arsa payı → "arsa" OR "payı")
    • "exact phrase" = Exact match ("arsa payı" → exact phrase)
    • word1+word2 = AND logic (arsa+payı → both words required)
    • word* = Wildcard (bozma* → bozma, bozması, bozmanın, etc.)
    • +"phrase1" +"phrase2" = Multiple required phrases
    • +"required" -"excluded" = Include and exclude
    Examples: arsa payı | "arsa payı" | +"arsa payı" +"bozma sebebi" | bozma*"""),
    birimYrgKurulDaire: str = Field("", description="Yargitay Board Unit (e.g., 'Hukuk Genel Kurulu')."),
    birimYrgHukukDaire: str = Field("", description="Yargitay Civil Chamber (e.g., '1. Hukuk Dairesi')."),
    birimYrgCezaDaire: str = Field("", description="Yargitay Criminal Chamber."),
    esasYil: str = Field("", description="Case year for 'Esas No'."),
    esasIlkSiraNo: str = Field("", description="Starting sequence number for 'Esas No'."),
    esasSonSiraNo: str = Field("", description="Ending sequence number for 'Esas No'."),
    kararYil: str = Field("", description="Decision year for 'Karar No'."),
    kararIlkSiraNo: str = Field("", description="Starting sequence number for 'Karar No'."),
    kararSonSiraNo: str = Field("", description="Ending sequence number for 'Karar No'."),
    baslangicTarihi: str = Field("", description="Start date for decision search (DD.MM.YYYY)."),
    bitisTarihi: str = Field("", description="End date for decision search (DD.MM.YYYY)."),
    siralama: str = Field("3", description="Sorting criteria (1: Esas No, 2: Karar No, 3: Karar Tarihi)."),
    siralamaDirection: str = Field("desc", description="Sorting direction ('asc' or 'desc')."),
    pageSize: int = Field(10, ge=1, le=100, description="Number of results per page."),
    pageNumber: int = Field(1, ge=1, description="Page number to retrieve.")
) -> CompactYargitaySearchResult:
    """Searches Yargitay (Court of Cassation) decisions using detailed criteria.
    
    SEARCH SYNTAX GUIDE:
    - Words with spaces: OR search (finds documents with ANY of the words)
    - "Quotes": Exact phrase search
    - Plus sign (+): AND search (both/all words required)
    - Asterisk (*): Wildcard (matches word variations)
    - Minus sign (-): Exclude terms
    
    Common patterns:
    - Simple: arsa payı (finds ~523K results)
    - Exact: "arsa payı" (finds ~22K results)  
    - Combined: +"arsa payı" +"bozma sebebi" (finds ~234 results)
    - Wildcard: inşaat* (matches inşaat, inşaatı, inşaatın, etc.)
    - Exclusion: +"arsa payı" -"inşaat sözleşmesi"
    """
    
    search_query = YargitayDetailedSearchRequest(
        arananKelime=arananKelime,
        birimYrgKurulDaire=birimYrgKurulDaire,
        birimYrgHukukDaire=birimYrgHukukDaire,
        birimYrgCezaDaire=birimYrgCezaDaire,
        esasYil=esasYil,
        esasIlkSiraNo=esasIlkSiraNo,
        esasSonSiraNo=esasSonSiraNo,
        kararYil=kararYil,
        kararIlkSiraNo=kararIlkSiraNo,
        kararSonSiraNo=kararSonSiraNo,
        baslangicTarihi=baslangicTarihi,
        bitisTarihi=bitisTarihi,
        siralama=siralama,
        siralamaDirection=siralamaDirection,
        pageSize=pageSize,
        pageNumber=pageNumber
    )
    
    logger.info(f"Tool 'search_yargitay_detailed' called: {search_query.model_dump_json(exclude_none=True, indent=2)}")
    try:
        api_response = await yargitay_client_instance.search_detailed_decisions(search_query)
        if api_response.data:
            return CompactYargitaySearchResult(
                decisions=api_response.data.data,
                total_records=api_response.data.recordsTotal,
                requested_page=search_query.pageNumber,
                page_size=search_query.pageSize)
        logger.warning("API response for Yargitay search did not contain expected data structure.")
        return CompactYargitaySearchResult(decisions=[], total_records=0, requested_page=search_query.pageNumber, page_size=search_query.pageSize)
    except Exception as e:
        logger.exception(f"Error in tool 'search_yargitay_detailed'.")
        raise

@app.tool()
async def get_yargitay_document_markdown(id: str) -> YargitayDocumentMarkdown:
    """Retrieves a specific Yargitay decision by its ID and returns its content as Markdown. Use id field from previous Yargıtay search results."""
    logger.info(f"Tool 'get_yargitay_document_markdown' called for ID: {id}")
    if not id or not id.strip(): raise ValueError("Document ID must be a non-empty string.")
    try:
        return await yargitay_client_instance.get_decision_document_as_markdown(id)
    except Exception as e:
        logger.exception(f"Error in tool 'get_yargitay_document_markdown'.")
        raise

# --- MCP Tools for Danistay ---
@app.tool()
async def search_danistay_by_keyword(
    andKelimeler: List[str] = Field(default_factory=list, description="Keywords for AND logic, e.g., ['word1', 'word2']"),
    orKelimeler: List[str] = Field(default_factory=list, description="Keywords for OR logic."),
    notAndKelimeler: List[str] = Field(default_factory=list, description="Keywords for NOT AND logic."),
    notOrKelimeler: List[str] = Field(default_factory=list, description="Keywords for NOT OR logic."),
    pageNumber: int = Field(1, ge=1, description="Page number."),
    pageSize: int = Field(10, ge=1, le=100, description="Results per page.")
) -> CompactDanistaySearchResult:
    """Searches Danıştay (Council of State) decisions using keywords."""
    
    search_query = DanistayKeywordSearchRequest(
        andKelimeler=andKelimeler,
        orKelimeler=orKelimeler,
        notAndKelimeler=notAndKelimeler,
        notOrKelimeler=notOrKelimeler,
        pageNumber=pageNumber,
        pageSize=pageSize
    )
    
    logger.info(f"Tool 'search_danistay_by_keyword' called.")
    try:
        api_response = await danistay_client_instance.search_keyword_decisions(search_query)
        if api_response.data:
            return CompactDanistaySearchResult(
                decisions=api_response.data.data,
                total_records=api_response.data.recordsTotal,
                requested_page=search_query.pageNumber,
                page_size=search_query.pageSize)
        logger.warning("API response for Danistay keyword search did not contain expected data structure.")
        return CompactDanistaySearchResult(decisions=[], total_records=0, requested_page=search_query.pageNumber, page_size=search_query.pageSize)
    except Exception as e:
        logger.exception(f"Error in tool 'search_danistay_by_keyword'.")
        raise

@app.tool()
async def search_danistay_detailed(
    daire: Optional[str] = Field(None, description="Chamber/Department name (e.g., '1. Daire')."),
    esasYil: Optional[str] = Field(None, description="Case year for 'Esas No'."),
    esasIlkSiraNo: Optional[str] = Field(None, description="Starting sequence for 'Esas No'."),
    esasSonSiraNo: Optional[str] = Field(None, description="Ending sequence for 'Esas No'."),
    kararYil: Optional[str] = Field(None, description="Decision year for 'Karar No'."),
    kararIlkSiraNo: Optional[str] = Field(None, description="Starting sequence for 'Karar No'."),
    kararSonSiraNo: Optional[str] = Field(None, description="Ending sequence for 'Karar No'."),
    baslangicTarihi: Optional[str] = Field(None, description="Start date for decision (DD.MM.YYYY)."),
    bitisTarihi: Optional[str] = Field(None, description="End date for decision (DD.MM.YYYY)."),
    mevzuatNumarasi: Optional[str] = Field(None, description="Legislation number."),
    mevzuatAdi: Optional[str] = Field(None, description="Legislation name."),
    madde: Optional[str] = Field(None, description="Article number."),
    siralama: str = Field("1", description="Sorting criteria (e.g., 1: Esas No, 3: Karar Tarihi)."),
    siralamaDirection: str = Field("desc", description="Sorting direction ('asc' or 'desc')."),
    pageNumber: int = Field(1, ge=1, description="Page number."),
    pageSize: int = Field(10, ge=1, le=100, description="Results per page.")
) -> CompactDanistaySearchResult:
    """Performs a detailed search for Danıştay (Council of State) decisions."""
    
    search_query = DanistayDetailedSearchRequest(
        daire=daire,
        esasYil=esasYil,
        esasIlkSiraNo=esasIlkSiraNo,
        esasSonSiraNo=esasSonSiraNo,
        kararYil=kararYil,
        kararIlkSiraNo=kararIlkSiraNo,
        kararSonSiraNo=kararSonSiraNo,
        baslangicTarihi=baslangicTarihi,
        bitisTarihi=bitisTarihi,
        mevzuatNumarasi=mevzuatNumarasi,
        mevzuatAdi=mevzuatAdi,
        madde=madde,
        siralama=siralama,
        siralamaDirection=siralamaDirection,
        pageNumber=pageNumber,
        pageSize=pageSize
    )
    
    logger.info(f"Tool 'search_danistay_detailed' called.")
    try:
        api_response = await danistay_client_instance.search_detailed_decisions(search_query)
        if api_response.data:
            return CompactDanistaySearchResult(
                decisions=api_response.data.data,
                total_records=api_response.data.recordsTotal,
                requested_page=search_query.pageNumber,
                page_size=search_query.pageSize)
        logger.warning("API response for Danistay detailed search did not contain expected data structure.")
        return CompactDanistaySearchResult(decisions=[], total_records=0, requested_page=search_query.pageNumber, page_size=search_query.pageSize)
    except Exception as e:
        logger.exception(f"Error in tool 'search_danistay_detailed'.")
        raise

@app.tool()
async def get_danistay_document_markdown(id: str) -> DanistayDocumentMarkdown:
    """Retrieves a specific Danıştay decision by ID and returns its content as Markdown."""
    logger.info(f"Tool 'get_danistay_document_markdown' called for ID: {id}")
    if not id or not id.strip(): raise ValueError("Document ID must be a non-empty string for Danıştay.")
    try:
        return await danistay_client_instance.get_decision_document_as_markdown(id)
    except Exception as e:
        logger.exception(f"Error in tool 'get_danistay_document_markdown'.")
        raise

# --- MCP Tools for Emsal ---
@app.tool()
async def search_emsal_detailed_decisions(
    keyword: Optional[str] = Field(None, description="Keyword to search."),
    selected_bam_civil_court: Optional[str] = Field(None, description="Selected BAM Civil Court."),
    selected_civil_court: Optional[str] = Field(None, description="Selected Civil Court."),
    selected_regional_civil_chambers: List[str] = Field(default_factory=list, description="Selected Regional Civil Chambers."),
    case_year_esas: Optional[str] = Field(None, description="Case year for 'Esas No'."),
    case_start_seq_esas: Optional[str] = Field(None, description="Starting sequence for 'Esas No'."),
    case_end_seq_esas: Optional[str] = Field(None, description="Ending sequence for 'Esas No'."),
    decision_year_karar: Optional[str] = Field(None, description="Decision year for 'Karar No'."),
    decision_start_seq_karar: Optional[str] = Field(None, description="Starting sequence for 'Karar No'."),
    decision_end_seq_karar: Optional[str] = Field(None, description="Ending sequence for 'Karar No'."),
    start_date: Optional[str] = Field(None, description="Start date for decision (DD.MM.YYYY)."),
    end_date: Optional[str] = Field(None, description="End date for decision (DD.MM.YYYY)."),
    sort_criteria: str = Field("1", description="Sorting criteria (e.g., 1: Esas No)."),
    sort_direction: str = Field("desc", description="Sorting direction ('asc' or 'desc')."),
    page_number: int = Field(1, ge=1, description="Page number."),
    page_size: int = Field(10, ge=1, le=100, description="Results per page.")
) -> CompactEmsalSearchResult:
    """Searches for Emsal (UYAP Precedent) decisions using detailed criteria."""
    
    search_query = EmsalSearchRequest(
        keyword=keyword,
        selected_bam_civil_court=selected_bam_civil_court,
        selected_civil_court=selected_civil_court,
        selected_regional_civil_chambers=selected_regional_civil_chambers,
        case_year_esas=case_year_esas,
        case_start_seq_esas=case_start_seq_esas,
        case_end_seq_esas=case_end_seq_esas,
        decision_year_karar=decision_year_karar,
        decision_start_seq_karar=decision_start_seq_karar,
        decision_end_seq_karar=decision_end_seq_karar,
        start_date=start_date,
        end_date=end_date,
        sort_criteria=sort_criteria,
        sort_direction=sort_direction,
        page_number=page_number,
        page_size=page_size
    )
    
    logger.info(f"Tool 'search_emsal_detailed_decisions' called.")
    try:
        api_response = await emsal_client_instance.search_detailed_decisions(search_query)
        if api_response.data:
            return CompactEmsalSearchResult(
                decisions=api_response.data.data,
                total_records=api_response.data.totalRecords if api_response.data.totalRecords is not None else 0,
                requested_page=search_query.page_number,
                page_size=search_query.page_size
            )
        logger.warning("API response for Emsal search did not contain expected data structure.")
        return CompactEmsalSearchResult(decisions=[], total_records=0, requested_page=search_query.page_number, page_size=search_query.page_size)
    except Exception as e:
        logger.exception(f"Error in tool 'search_emsal_detailed_decisions'.")
        raise

@app.tool()
async def get_emsal_document_markdown(id: str) -> EmsalDocumentMarkdown:
    """Retrieves a specific Emsal decision by ID and returns its content as Markdown."""
    logger.info(f"Tool 'get_emsal_document_markdown' called for ID: {id}")
    if not id or not id.strip(): raise ValueError("Document ID required for Emsal.")
    try:
        return await emsal_client_instance.get_decision_document_as_markdown(id)
    except Exception as e:
        logger.exception(f"Error in tool 'get_emsal_document_markdown'.")
        raise

# --- MCP Tools for Uyusmazlik ---
@app.tool()
async def search_uyusmazlik_decisions(
    icerik: str = Field("", description="Keyword or content for main text search."),
    bolum: Literal["", "Ceza Bölümü", "Genel Kurul Kararları", "Hukuk Bölümü"] = Field("", description="Select the department (Bölüm)."),
    uyusmazlik_turu: Literal["", "Görev Uyuşmazlığı", "Hüküm Uyuşmazlığı"] = Field("", description="Select the type of dispute."),
    karar_sonuclari: List[Literal["Hüküm Uyuşmazlığı Olmadığına Dair", "Hüküm Uyuşmazlığı Olduğuna Dair"]] = Field(default_factory=list, description="List of desired 'Karar Sonucu' types."),
    esas_yil: str = Field("", description="Case year ('Esas Yılı')."),
    esas_sayisi: str = Field("", description="Case number ('Esas Sayısı')."),
    karar_yil: str = Field("", description="Decision year ('Karar Yılı')."),
    karar_sayisi: str = Field("", description="Decision number ('Karar Sayısı')."),
    kanun_no: str = Field("", description="Relevant Law Number."),
    karar_date_begin: str = Field("", description="Decision start date (DD.MM.YYYY)."),
    karar_date_end: str = Field("", description="Decision end date (DD.MM.YYYY)."),
    resmi_gazete_sayi: str = Field("", description="Official Gazette number."),
    resmi_gazete_date: str = Field("", description="Official Gazette date (DD.MM.YYYY)."),
    tumce: str = Field("", description="Exact phrase search."),
    wild_card: str = Field("", description="Search for phrase and its inflections."),
    hepsi: str = Field("", description="Search for texts containing all specified words."),
    herhangi_birisi: str = Field("", description="Search for texts containing any of the specified words."),
    not_hepsi: str = Field("", description="Exclude texts containing these specified words.")
) -> UyusmazlikSearchResponse:
    """Searches for Uyuşmazlık Mahkemesi (Court of Jurisdictional Disputes) decisions using various criteria."""
    
    # Convert string literals to enums
    bolum_enum = UyusmazlikBolumEnum(bolum) if bolum else UyusmazlikBolumEnum.TUMU
    uyusmazlik_turu_enum = UyusmazlikTuruEnum(uyusmazlik_turu) if uyusmazlik_turu else UyusmazlikTuruEnum.TUMU
    karar_sonuclari_enums = [UyusmazlikKararSonucuEnum(ks) for ks in karar_sonuclari]
    
    search_params = UyusmazlikSearchRequest(
        icerik=icerik,
        bolum=bolum_enum,
        uyusmazlik_turu=uyusmazlik_turu_enum,
        karar_sonuclari=karar_sonuclari_enums,
        esas_yil=esas_yil,
        esas_sayisi=esas_sayisi,
        karar_yil=karar_yil,
        karar_sayisi=karar_sayisi,
        kanun_no=kanun_no,
        karar_date_begin=karar_date_begin,
        karar_date_end=karar_date_end,
        resmi_gazete_sayi=resmi_gazete_sayi,
        resmi_gazete_date=resmi_gazete_date,
        tumce=tumce,
        wild_card=wild_card,
        hepsi=hepsi,
        herhangi_birisi=herhangi_birisi,
        not_hepsi=not_hepsi
    )
    
    logger.info(f"Tool 'search_uyusmazlik_decisions' called.")
    try:
        return await uyusmazlik_client_instance.search_decisions(search_params)
    except Exception as e:
        logger.exception(f"Error in tool 'search_uyusmazlik_decisions'.")
        raise

@app.tool()
async def get_uyusmazlik_document_markdown_from_url(document_url: HttpUrl) -> UyusmazlikDocumentMarkdown:
    """
    Retrieves a specific Uyuşmazlık Mahkemesi decision from its full URL
    and returns its content as Markdown.
    The URL is typically obtained from the 'search_uyusmazlik_decisions' tool results.
    """
    logger.info(f"Tool 'get_uyusmazlik_document_markdown_from_url' called for URL: {str(document_url)}")
    if not document_url:
        raise ValueError("Document URL (document_url) is required for Uyuşmazlık document retrieval.")
    try:
        return await uyusmazlik_client_instance.get_decision_document_as_markdown(str(document_url))
    except Exception as e:
        logger.exception(f"Error in tool 'get_uyusmazlik_document_markdown_from_url'.")
        raise

# --- MCP Tools for Anayasa Mahkemesi (Norm Denetimi) ---
@app.tool()
async def search_anayasa_norm_denetimi_decisions(
    keywords_all: List[str] = Field(default_factory=list, description="Keywords for AND logic."),
    keywords_any: List[str] = Field(default_factory=list, description="Keywords for OR logic."),
    keywords_exclude: List[str] = Field(default_factory=list, description="Keywords to exclude."),
    period: Literal["", "1", "2"] = Field("", description="Constitutional period ('': All, '1': 1961, '2': 1982)."),
    case_number_esas: Optional[str] = Field(None, description="Case registry number (e.g., '2023/123')."),
    decision_number_karar: Optional[str] = Field(None, description="Decision number (e.g., '2023/456')."),
    first_review_date_start: Optional[str] = Field(None, description="First review start date (DD/MM/YYYY)."),
    first_review_date_end: Optional[str] = Field(None, description="First review end date (DD/MM/YYYY)."),
    decision_date_start: Optional[str] = Field(None, description="Decision start date (DD/MM/YYYY)."),
    decision_date_end: Optional[str] = Field(None, description="Decision end date (DD/MM/YYYY)."),
    application_type: Literal["", "1", "2", "3"] = Field("", description="Application type ('': All, '1': İptal, '2': İtiraz, '3': Diğer)."),
    applicant_general_name: Optional[str] = Field(None, description="General applicant name."),
    applicant_specific_name: Optional[str] = Field(None, description="Specific applicant name."),
    official_gazette_date_start: Optional[str] = Field(None, description="Official Gazette start date (DD/MM/YYYY)."),
    official_gazette_date_end: Optional[str] = Field(None, description="Official Gazette end date (DD/MM/YYYY)."),
    official_gazette_number_start: Optional[str] = Field(None, description="Official Gazette starting number."),
    official_gazette_number_end: Optional[str] = Field(None, description="Official Gazette ending number."),
    has_press_release: Literal["", "0", "1"] = Field("", description="Press release ('': All, '0': No, '1': Yes)."),
    has_dissenting_opinion: Literal["", "0", "1"] = Field("", description="Dissenting opinion ('': All, '0': No, '1': Yes)."),
    has_different_reasoning: Literal["", "0", "1"] = Field("", description="Different reasoning ('': All, '0': No, '1': Yes)."),
    attending_members_names: List[str] = Field(default_factory=list, description="List of attending members' exact names."),
    rapporteur_name: Optional[str] = Field(None, description="Rapporteur's exact name."),
    norm_type: Literal["", "1", "2", "14", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "0", "13"] = Field("", description="Type of reviewed norm."),
    norm_id_or_name: Optional[str] = Field(None, description="Number or name of the norm."),
    norm_article: Optional[str] = Field(None, description="Article number of the norm."),
    review_outcomes: List[Literal["", "1", "2", "3", "4", "5", "6", "7", "8", "12"]] = Field(default_factory=list, description="List of review outcomes."),
    reason_for_final_outcome: Literal["", "29", "1", "2", "30", "3", "4", "27", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15", "16", "17", "18", "19", "20", "21", "22", "23", "24", "25", "26"] = Field("", description="Main reason for decision outcome."),
    basis_constitution_article_numbers: List[str] = Field(default_factory=list, description="List of supporting Constitution article numbers."),
    results_per_page: int = Field(10, description="Results per page (10, 20, 30, 40, 50)."),
    page_to_fetch: int = Field(1, ge=1, description="Page number to fetch."),
    sort_by_criteria: str = Field("KararTarihi", description="Sort criteria ('KararTarihi', 'YayinTarihi', 'Toplam').")
) -> AnayasaSearchResult:
    """
    Searches Anayasa Mahkemesi (Constitutional Court) Norm Denetimi (Norm Control) decisions
    using criteria from https://normkararlarbilgibankasi.anayasa.gov.tr.
    """
    
    # Convert string literals to enums
    period_enum = AnayasaDonemEnum(period)
    application_type_enum = AnayasaBasvuruTuruEnum(application_type)
    has_press_release_enum = AnayasaVarYokEnum(has_press_release)
    has_dissenting_opinion_enum = AnayasaVarYokEnum(has_dissenting_opinion)
    has_different_reasoning_enum = AnayasaVarYokEnum(has_different_reasoning)
    norm_type_enum = AnayasaNormTuruEnum(norm_type)
    review_outcomes_enums = [AnayasaIncelemeSonucuEnum(ro) for ro in review_outcomes]
    reason_for_final_outcome_enum = AnayasaSonucGerekcesiEnum(reason_for_final_outcome)
    
    search_query = AnayasaNormDenetimiSearchRequest(
        keywords_all=keywords_all,
        keywords_any=keywords_any,
        keywords_exclude=keywords_exclude,
        period=period_enum,
        case_number_esas=case_number_esas,
        decision_number_karar=decision_number_karar,
        first_review_date_start=first_review_date_start,
        first_review_date_end=first_review_date_end,
        decision_date_start=decision_date_start,
        decision_date_end=decision_date_end,
        application_type=application_type_enum,
        applicant_general_name=applicant_general_name,
        applicant_specific_name=applicant_specific_name,
        official_gazette_date_start=official_gazette_date_start,
        official_gazette_date_end=official_gazette_date_end,
        official_gazette_number_start=official_gazette_number_start,
        official_gazette_number_end=official_gazette_number_end,
        has_press_release=has_press_release_enum,
        has_dissenting_opinion=has_dissenting_opinion_enum,
        has_different_reasoning=has_different_reasoning_enum,
        attending_members_names=attending_members_names,
        rapporteur_name=rapporteur_name,
        norm_type=norm_type_enum,
        norm_id_or_name=norm_id_or_name,
        norm_article=norm_article,
        review_outcomes=review_outcomes_enums,
        reason_for_final_outcome=reason_for_final_outcome_enum,
        basis_constitution_article_numbers=basis_constitution_article_numbers,
        results_per_page=results_per_page,
        page_to_fetch=page_to_fetch,
        sort_by_criteria=sort_by_criteria
    )
    
    logger.info(f"Tool 'search_anayasa_norm_denetimi_decisions' called.")
    try:
        return await anayasa_norm_client_instance.search_norm_denetimi_decisions(search_query)
    except Exception as e:
        logger.exception(f"Error in tool 'search_anayasa_norm_denetimi_decisions'.")
        raise

@app.tool()
async def get_anayasa_norm_denetimi_document_markdown(
    document_url: str = Field(..., description="The URL path (e.g., /ND/YYYY/NN) or full https URL of the AYM Norm Denetimi decision from normkararlarbilgibankasi.anayasa.gov.tr."),
    page_number: Optional[int] = Field(1, ge=1, description="Page number for paginated Markdown content (1-indexed). Default is 1 (first 5,000 characters).")
) -> AnayasaDocumentMarkdown:
    """
    Retrieves a specific Anayasa Mahkemesi (Norm Denetimi) decision
    from its URL and returns its content as paginated Markdown.
    Content is paginated if it exceeds 5,000 characters. Use 'page_number' for subsequent pages.
    """
    logger.info(f"Tool 'get_anayasa_norm_denetimi_document_markdown' called for URL: {document_url}, Page: {page_number}")
    if not document_url or not document_url.strip():
        raise ValueError("Document URL is required for Anayasa Norm Denetimi document retrieval.")
    current_page_to_fetch = page_number if page_number is not None and page_number >= 1 else 1
    try:
        return await anayasa_norm_client_instance.get_decision_document_as_markdown(document_url, page_number=current_page_to_fetch)
    except Exception as e:
        logger.exception(f"Error in tool 'get_anayasa_norm_denetimi_document_markdown'.")
        raise

# --- MCP Tools for Anayasa Mahkemesi (Bireysel Başvuru Karar Raporu & Belgeler) ---
@app.tool()
async def search_anayasa_bireysel_basvuru_report(
    keywords: List[str] = Field(default_factory=list, description="Keywords for AND logic."),
    page_to_fetch: int = Field(1, ge=1, description="Page number to fetch for the report. Default is 1.")
) -> AnayasaBireyselReportSearchResult:
    """
    Searches Anayasa Mahkemesi (Constitutional Court) Bireysel Başvuru (Individual Application)
    decisions and generates a 'Karar Arama Raporu' (Decision Search Report).
    This is for https://kararlarbilgibankasi.anayasa.gov.tr (uses KararBulteni=1).
    """
    
    search_query = AnayasaBireyselReportSearchRequest(
        keywords=keywords,
        page_to_fetch=page_to_fetch
    )
    
    logger.info(f"Tool 'search_anayasa_bireysel_basvuru_report' called.")
    try:
        return await anayasa_bireysel_client_instance.search_bireysel_basvuru_report(search_query)
    except Exception as e:
        logger.exception(f"Error in tool 'search_anayasa_bireysel_basvuru_report'.")
        raise

@app.tool()
async def get_anayasa_bireysel_basvuru_document_markdown(
    document_url_path: str = Field(..., description="The URL path (e.g., /BB/YYYY/NNNN) of the AYM Bireysel Başvuru decision from kararlarbilgibankasi.anayasa.gov.tr."),
    page_number: Optional[int] = Field(1, ge=1, description="Page number for paginated Markdown content (1-indexed). Default is 1 (first 5,000 characters).")
) -> AnayasaBireyselBasvuruDocumentMarkdown:
    """
    Retrieves a specific Anayasa Mahkemesi Bireysel Başvuru (Individual Application) decision
    from its URL path (e.g., /BB/YYYY/NNNN) and returns content as paginated Markdown.
    Content is paginated if it exceeds 5,000 characters. Use 'page_number' for subsequent pages.
    """
    logger.info(f"Tool 'get_anayasa_bireysel_basvuru_document_markdown' called for URL path: {document_url_path}, Page: {page_number}")
    if not document_url_path or not document_url_path.strip() or not document_url_path.startswith("/BB/"):
        raise ValueError("Document URL path (e.g., /BB/YYYY/NNNN) is required for Anayasa Bireysel Başvuru document retrieval.")
    current_page_to_fetch = page_number if page_number is not None and page_number >= 1 else 1
    try:
        return await anayasa_bireysel_client_instance.get_decision_document_as_markdown(document_url_path, page_number=current_page_to_fetch)
    except Exception as e:
        logger.exception(f"Error in tool 'get_anayasa_bireysel_basvuru_document_markdown'.")
        raise

# --- MCP Tools for KIK (Kamu İhale Kurulu) ---
@app.tool()
async def search_kik_decisions(
    karar_tipi: Literal["rbUyusmazlik", "rbDuzenleyici", "rbMahkeme"] = Field("rbUyusmazlik", description="Type of KIK Decision."),
    karar_no: Optional[str] = Field(None, description="Decision Number (e.g., '2024/UH.II-1766')."),
    karar_tarihi_baslangic: Optional[str] = Field(None, description="Decision Date Start (DD.MM.YYYY)."),
    karar_tarihi_bitis: Optional[str] = Field(None, description="Decision Date End (DD.MM.YYYY)."),
    basvuru_sahibi: Optional[str] = Field(None, description="Applicant."),
    ihaleyi_yapan_idare: Optional[str] = Field(None, description="Procuring Entity."),
    basvuru_konusu_ihale: Optional[str] = Field(None, description="Tender subject of the application."),
    karar_metni: Optional[str] = Field(None, description="Keyword/phrase in decision text."),
    yil: Optional[str] = Field(None, description="Year of the decision."),
    resmi_gazete_tarihi: Optional[str] = Field(None, description="Official Gazette Date (DD.MM.YYYY)."),
    resmi_gazete_sayisi: Optional[str] = Field(None, description="Official Gazette Number."),
    page: int = Field(1, ge=1, description="Results page number.")
) -> KikSearchResult:
    """
    Searches KIK (Public Procurement Authority) decisions.
    """
    
    # Convert string literal to enum
    karar_tipi_enum = KikKararTipi(karar_tipi)
    
    search_query = KikSearchRequest(
        karar_tipi=karar_tipi_enum,
        karar_no=karar_no,
        karar_tarihi_baslangic=karar_tarihi_baslangic,
        karar_tarihi_bitis=karar_tarihi_bitis,
        basvuru_sahibi=basvuru_sahibi,
        ihaleyi_yapan_idare=ihaleyi_yapan_idare,
        basvuru_konusu_ihale=basvuru_konusu_ihale,
        karar_metni=karar_metni,
        yil=yil,
        resmi_gazete_tarihi=resmi_gazete_tarihi,
        resmi_gazete_sayisi=resmi_gazete_sayisi,
        page=page
    )
    
    logger.info(f"Tool 'search_kik_decisions' called.")
    try:
        api_response = await kik_client_instance.search_decisions(search_query)
        page_param_for_log = search_query.page if hasattr(search_query, 'page') else 1
        if not api_response.decisions and api_response.total_records == 0 and page_param_for_log == 1:
             logger.warning(f"KIK search returned no decisions for query.")
        return api_response
    except Exception as e:
        logger.exception(f"Error in KIK search tool 'search_kik_decisions'.")
        current_page_val = search_query.page if hasattr(search_query, 'page') else 1
        return KikSearchResult(decisions=[], total_records=0, current_page=current_page_val)

@app.tool()
async def get_kik_document_markdown(
    karar_id: str = Field(..., description="The Base64 encoded KIK decision identifier."),
    page_number: Optional[int] = Field(1, ge=1, description="Page number for paginated Markdown content (1-indexed). Default is 1.")
) -> KikDocumentMarkdown:
    """
    Retrieves a specific KIK (Public Procurement Authority) decision using its Base64 encoded 'karar_id'.
    Content is returned as paginated Markdown. 
    """
    logger.info(f"Tool 'get_kik_document_markdown' called for KIK karar_id: {karar_id}, Markdown Page: {page_number}")
    
    if not karar_id or not karar_id.strip():
        logger.error("KIK Document retrieval: karar_id cannot be empty.")
        return KikDocumentMarkdown( 
            retrieved_with_karar_id=karar_id,
            error_message="karar_id is required and must be a non-empty string.",
            current_page=page_number or 1,
            total_pages=1,
            is_paginated=False
            )

    current_page_to_fetch = page_number if page_number is not None and page_number >= 1 else 1

    try:
        return await kik_client_instance.get_decision_document_as_markdown(
            karar_id_b64=karar_id, 
            page_number=current_page_to_fetch
        )
    except Exception as e:
        logger.exception(f"Error in KIK document retrieval tool 'get_kik_document_markdown' for karar_id: {karar_id}")
        return KikDocumentMarkdown(
            retrieved_with_karar_id=karar_id,
            error_message=f"Tool-level error during KIK document retrieval: {str(e)}",
            current_page=current_page_to_fetch, 
            total_pages=1, 
            is_paginated=False
        )
@app.tool()
async def search_rekabet_kurumu_decisions(
    sayfaAdi: Optional[str] = Field(None, description="Search in decision title (Başlık)."),
    YayinlanmaTarihi: Optional[str] = Field(None, description="Publication date (Yayım Tarihi), e.g., DD.MM.YYYY."),
    PdfText: Optional[str] = Field(
        None,
        description='Search in decision text (Metin). For an exact phrase match, enclose the phrase in double quotes (e.g., "\\"vertical agreement\\" competition). The website indicates that using "" provides more precise results for phrases.'
    ),
    KararTuru: Literal[ 
        "", 
        "Birleşme ve Devralma",
        "Diğer",
        "Menfi Tespit ve Muafiyet",
        "Özelleştirme",
        "Rekabet İhlali"
    ] = Field("", description="Decision type (Karar Türü). Leave empty for 'All'. Options: '', 'Birleşme ve Devralma', 'Diğer', 'Menfi Tespit ve Muafiyet', 'Özelleştirme', 'Rekabet İhlali'."),
    KararSayisi: Optional[str] = Field(None, description="Decision number (Karar Sayısı)."),
    KararTarihi: Optional[str] = Field(None, description="Decision date (Karar Tarihi), e.g., DD.MM.YYYY."),
    page: int = Field(1, ge=1, description="Page number to fetch for the results list.")
) -> RekabetSearchResult:
    """
    Searches decisions of the Turkish Competition Authority (Rekabet Kurumu).
    For an exact phrase search in the 'PdfText' field, enclose the phrase in double quotes.
    Example for PdfText: "\\"tender process\\" consultancy"
    """
    
    karar_turu_guid_enum = KARAR_TURU_ADI_TO_GUID_ENUM_MAP.get(KararTuru)

    try:
        if karar_turu_guid_enum is None: 
            logger.warning(f"Invalid user-provided KararTuru: '{KararTuru}'. Defaulting to TUMU (all).")
            karar_turu_guid_enum = RekabetKararTuruGuidEnum.TUMU
    except Exception as e_map: 
        logger.error(f"Error mapping KararTuru '{KararTuru}': {e_map}. Defaulting to TUMU.")
        karar_turu_guid_enum = RekabetKararTuruGuidEnum.TUMU

    search_query = RekabetKurumuSearchRequest(
        sayfaAdi=sayfaAdi,
        YayinlanmaTarihi=YayinlanmaTarihi,
        PdfText=PdfText,
        KararTuruID=karar_turu_guid_enum, 
        KararSayisi=KararSayisi,
        KararTarihi=KararTarihi,
        page=page
    )
    logger.info(f"Tool 'search_rekabet_kurumu_decisions' called. Query: {search_query.model_dump_json(exclude_none=True, indent=2)}")
    try:
       
        return await rekabet_client_instance.search_decisions(search_query)
    except Exception as e:
        logger.exception("Error in tool 'search_rekabet_kurumu_decisions'.")
        return RekabetSearchResult(decisions=[], retrieved_page_number=page, total_records_found=0, total_pages=0)

@app.tool()
async def get_rekabet_kurumu_document(
    karar_id: str = Field(..., description="GUID (kararId) of the Rekabet Kurumu decision. This ID is obtained from search results."),
    page_number: Optional[int] = Field(1, ge=1, description="Requested page number for the Markdown content converted from PDF (1-indexed). Default is 1.")
) -> RekabetDocument:
    """
    Retrieves information for a specific Turkish Competition Authority (Rekabet Kurumu) decision
    (landing page metadata, PDF link) and its PDF content converted to paginated Markdown.
    """
    logger.info(f"Tool 'get_rekabet_kurumu_document' called. Karar ID: {karar_id}, Markdown Page: {page_number}")
    
    current_page_to_fetch = page_number if page_number is not None and page_number >= 1 else 1
    
    try:
      
        return await rekabet_client_instance.get_decision_document(karar_id, page_number=current_page_to_fetch)
    except Exception as e:
        logger.exception(f"Error in tool 'get_rekabet_kurumu_document'. Karar ID: {karar_id}")
        raise 

# --- Application Shutdown Handling ---
def perform_cleanup():
    logger.info("MCP Server performing cleanup...")
    try:
        loop = asyncio.get_event_loop_policy().get_event_loop()
        if loop.is_closed(): 
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
    except RuntimeError: 
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    clients_to_close = [
        globals().get('yargitay_client_instance'),
        globals().get('danistay_client_instance'),
        globals().get('emsal_client_instance'),
        globals().get('uyusmazlik_client_instance'),
        globals().get('anayasa_norm_client_instance'),
        globals().get('anayasa_bireysel_client_instance'),
        globals().get('kik_client_instance'),
        globals().get('rekabet_client_instance')
    ]
    async def close_all_clients_async():
        tasks = []
        for client_instance in clients_to_close:
            if client_instance and hasattr(client_instance, 'close_client_session') and callable(client_instance.close_client_session):
                logger.info(f"Scheduling close for client session: {client_instance.__class__.__name__}")
                tasks.append(client_instance.close_client_session())
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    client_name = "Unknown Client"
                    if i < len(clients_to_close) and clients_to_close[i] is not None:
                        client_name = clients_to_close[i].__class__.__name__
                    logger.error(f"Error closing client {client_name}: {result}")
    try:
        if loop.is_running(): 
            asyncio.ensure_future(close_all_clients_async(), loop=loop)
            logger.info("Client cleanup tasks scheduled on running event loop.")
        else:
            loop.run_until_complete(close_all_clients_async())
            logger.info("Client cleanup tasks completed via run_until_complete.")
    except Exception as e: 
        logger.error(f"Error during atexit cleanup execution: {e}", exc_info=True)
    logger.info("MCP Server atexit cleanup process finished.")

atexit.register(perform_cleanup)

def main():
    logger.info(f"Starting {app.name} server via main() function...")
    logger.info(f"Logs will be written to: {LOG_FILE_PATH}")
    try:
        app.run()
    except KeyboardInterrupt: 
        logger.info("Server shut down by user (KeyboardInterrupt).")
    except Exception as e: 
        logger.exception("Server failed to start or crashed.")
    finally:
        logger.info(f"{app.name} server has shut down.")

if __name__ == "__main__": 
    main()