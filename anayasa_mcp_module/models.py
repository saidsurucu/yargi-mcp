# anayasa_mcp_module/models.py

from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional, Dict, Any
from enum import Enum

# --- Enums (AnayasaDonemEnum, AnayasaBasvuruTuruEnum, etc. - same as before) ---
class AnayasaDonemEnum(str, Enum):
    TUMU = "ALL"
    DONEM_1961 = "1"
    DONEM_1982 = "2"

class AnayasaBasvuruTuruEnum(str, Enum):
    TUMU = "ALL"
    IPTAL = "1"
    ITIRAZ = "2"
    DIGER = "3"

class AnayasaVarYokEnum(str, Enum):
    TUMU = "ALL"
    YOK = "0"
    VAR = "1"

class AnayasaNormTuruEnum(str, Enum):
    TUMU = "ALL"
    ANAYASA = "1"
    ANAYASA_DEGISTIREN_KANUN = "2"
    CUMHURBASKANLIGI_KARARNAMESI = "14"
    ICTUZUK = "3"
    KANUN = "4"
    KANUN_HUKMUNDE_KARARNAME = "5"
    KARAR = "6"
    NIZAMNAME = "7"
    TALIMATNAME = "8"
    TARIFE = "9"
    TBMM_KARARI = "10"
    TEZKERE = "11"
    TUZUK = "12"
    YOK_SECENEGI = "0"
    YONETMELIK = "13"

class AnayasaIncelemeSonucuEnum(str, Enum):
    TUMU = "ALL"
    ESAS_ACILMAMIS_SAYILMA = "1"
    ESAS_IPTAL = "2"
    ESAS_KARAR_YER_OLMADIGI = "3"
    ESAS_RET = "4"
    ILK_ACILMAMIS_SAYILMA = "5"
    ILK_ISIN_GERI_CEVRILMESI = "6"
    ILK_KARAR_YER_OLMADIGI = "7"
    ILK_RET = "8"
    KANUN_6216_M43_4_IPTAL = "12"

class AnayasaSonucGerekcesiEnum(str, Enum):
    TUMU = "ALL"
    ANAYASAYA_AYKIRI_DEGIL = "29"
    ANAYASAYA_ESAS_YONUNDEN_AYKIRILIK = "1"
    ANAYASAYA_ESAS_YONUNDEN_UYGUNLUK = "2"
    ANAYASAYA_SEKIL_ESAS_UYGUNLUK = "30"
    ANAYASAYA_SEKIL_YONUNDEN_AYKIRILIK = "3"
    ANAYASAYA_SEKIL_YONUNDEN_UYGUNLUK = "4"
    AYKIRILIK_ANAYASAYA_ESAS_YONUNDEN_DUPLICATE = "27"
    BASVURU_KARARI = "5"
    DENETIM_DISI = "6"
    DIGER_GEREKCE_1 = "7"
    DIGER_GEREKCE_2 = "8"
    EKSIKLIGIN_GIDERILMEMESI = "9"
    GEREKCE = "10"
    GOREV = "11"
    GOREV_YETKI = "12"
    GOREVLI_MAHKEME = "13"
    GORULMEKTE_OLAN_DAVA = "14"
    MAHKEME = "15"
    NORMDA_DEGISIKLIK_YAPILMASI = "16"
    NORMUN_YURURLUKTEN_KALDIRILMASI = "17"
    ON_YIL_YASAGI = "18"
    SURE = "19"
    USULE_UYMAMA = "20"
    UYGULANACAK_NORM = "21"
    UYGULANAMAZ_HALE_GELME = "22"
    YETKI = "23"
    YETKI_SURE = "24"
    YOK_HUKMUNDE_OLMAMA = "25"
    YOKLUK = "26"
# --- End Enums ---

class AnayasaNormDenetimiSearchRequest(BaseModel):
    """Model for Anayasa Mahkemesi (Norm Denetimi) search request for the MCP tool."""
    keywords_all: Optional[List[str]] = Field(default_factory=list, description="Keywords for AND logic (KelimeAra[]).")
    keywords_any: Optional[List[str]] = Field(default_factory=list, description="Keywords for OR logic (HerhangiBirKelimeAra[]).")
    keywords_exclude: Optional[List[str]] = Field(default_factory=list, description="Keywords to exclude (BulunmayanKelimeAra[]).")
    period: Optional[AnayasaDonemEnum] = Field(default=AnayasaDonemEnum.TUMU, description="Constitutional period (Donemler_id).")
    case_number_esas: Optional[str] = Field(None, description="Case registry number (EsasNo), e.g., '2023/123'.")
    decision_number_karar: Optional[str] = Field(None, description="Decision number (KararNo), e.g., '2023/456'.")
    first_review_date_start: Optional[str] = Field(None, description="First review start date (IlkIncelemeTarihiIlk), format DD/MM/YYYY.")
    first_review_date_end: Optional[str] = Field(None, description="First review end date (IlkIncelemeTarihiSon), format DD/MM/YYYY.")
    decision_date_start: Optional[str] = Field(None, description="Decision start date (KararTarihiIlk), format DD/MM/YYYY.")
    decision_date_end: Optional[str] = Field(None, description="Decision end date (KararTarihiSon), format DD/MM/YYYY.")
    application_type: Optional[AnayasaBasvuruTuruEnum] = Field(default=AnayasaBasvuruTuruEnum.TUMU, description="Type of application (BasvuruTurler_id).")
    applicant_general_name: Optional[str] = Field(None, description="General applicant name (BasvuranGeneller_id).")
    applicant_specific_name: Optional[str] = Field(None, description="Specific applicant name (BasvuranOzeller_id).")
    official_gazette_date_start: Optional[str] = Field(None, description="Official Gazette start date (ResmiGazeteTarihiIlk), format DD/MM/YYYY.")
    official_gazette_date_end: Optional[str] = Field(None, description="Official Gazette end date (ResmiGazeteTarihiSon), format DD/MM/YYYY.")
    official_gazette_number_start: Optional[str] = Field(None, description="Official Gazette starting number (ResmiGazeteSayisiIlk).")
    official_gazette_number_end: Optional[str] = Field(None, description="Official Gazette ending number (ResmiGazeteSayisiSon).")
    has_press_release: Optional[AnayasaVarYokEnum] = Field(default=AnayasaVarYokEnum.TUMU, description="Press release available (BasinDuyurusu).")
    has_dissenting_opinion: Optional[AnayasaVarYokEnum] = Field(default=AnayasaVarYokEnum.TUMU, description="Dissenting opinion exists (KarsiOy).")
    has_different_reasoning: Optional[AnayasaVarYokEnum] = Field(default=AnayasaVarYokEnum.TUMU, description="Different reasoning exists (FarkliGerekce).")
    attending_members_names: Optional[List[str]] = Field(default_factory=list, description="List of attending members' exact names (Uyeler_id[]).")
    rapporteur_name: Optional[str] = Field(None, description="Rapporteur's exact name (Raportorler_id).")
    norm_type: Optional[AnayasaNormTuruEnum] = Field(default=AnayasaNormTuruEnum.TUMU, description="Type of the reviewed norm (NormunTurler_id).")
    norm_id_or_name: Optional[str] = Field(None, description="Number or name of the norm (NormunNumarasiAdlar_id).")
    norm_article: Optional[str] = Field(None, description="Article number of the norm (NormunMaddeNumarasi).")
    review_outcomes: Optional[List[AnayasaIncelemeSonucuEnum]] = Field(default_factory=list, description="List of review types and outcomes (IncelemeTuruKararSonuclar_id[]).")
    reason_for_final_outcome: Optional[AnayasaSonucGerekcesiEnum] = Field(default=AnayasaSonucGerekcesiEnum.TUMU, description="Main reason for the decision outcome (KararSonucununGerekcesi).")
    basis_constitution_article_numbers: Optional[List[str]] = Field(default_factory=list, description="List of supporting Constitution article numbers (DayanakHukmu[]).")
    results_per_page: Optional[int] = Field(10, ge=1, le=10, description="Results per page.")
    page_to_fetch: Optional[int] = Field(1, ge=1, description="Page number to fetch for results list.")
    sort_by_criteria: Optional[str] = Field("KararTarihi", description="Sort criteria. Options: 'KararTarihi', 'YayinTarihi', 'Toplam' (keyword count).")

class AnayasaReviewedNormInfo(BaseModel):
    """Details of a norm reviewed within an AYM decision summary."""
    norm_name_or_number: Optional[str] = None
    article_number: Optional[str] = None
    review_type_and_outcome: Optional[str] = None
    outcome_reason: Optional[str] = None
    basis_constitution_articles_cited: List[str] = Field(default_factory=list)
    postponement_period: Optional[str] = None

class AnayasaDecisionSummary(BaseModel):
    """Model for a single Anayasa Mahkemesi (Norm Denetimi) decision summary from search results."""
    decision_reference_no: Optional[str] = None
    decision_page_url: Optional[HttpUrl] = None
    keywords_found_count: Optional[int] = None
    application_type_summary: Optional[str] = None
    applicant_summary: Optional[str] = None
    decision_outcome_summary: Optional[str] = None
    decision_date_summary: Optional[str] = None
    reviewed_norms: List[AnayasaReviewedNormInfo] = Field(default_factory=list)

class AnayasaSearchResult(BaseModel):
    """Model for the overall search result for Anayasa Mahkemesi Norm Denetimi decisions."""
    decisions: List[AnayasaDecisionSummary]
    total_records_found: Optional[int] = None
    retrieved_page_number: Optional[int] = None

class AnayasaDocumentMarkdown(BaseModel):
    """
    Model for an Anayasa Mahkemesi (Norm Denetimi) decision document, containing a chunk of Markdown content
    and pagination information.
    """
    source_url: HttpUrl
    decision_reference_no_from_page: Optional[str] = Field(None, description="E.K. No parsed from the document page.")
    decision_date_from_page: Optional[str] = Field(None, description="Decision date parsed from the document page.")
    official_gazette_info_from_page: Optional[str] = Field(None, description="Official Gazette info parsed from the document page.")
    markdown_chunk: Optional[str] = Field(None, description="A 5,000 character chunk of the Markdown content.") # Corrected chunk size
    current_page: int = Field(description="The current page number of the markdown chunk (1-indexed).")
    total_pages: int = Field(description="Total number of pages for the full markdown content.")
    is_paginated: bool = Field(description="True if the full markdown content is split into multiple pages.")


# --- Models for Anayasa Mahkemesi - Bireysel Başvuru Karar Raporu ---

class AnayasaBireyselReportSearchRequest(BaseModel):
    """Model for Anayasa Mahkemesi (Bireysel Başvuru) 'Karar Arama Raporu' search request."""
    keywords: Optional[List[str]] = Field(default_factory=list, description="Keywords for AND logic (KelimeAra[]).")
    page_to_fetch: int = Field(1, ge=1, description="Page number to fetch for the report (page). Default is 1.")

class AnayasaBireyselReportDecisionDetail(BaseModel):
    """Details of a specific right/claim within a Bireysel Başvuru decision summary in a report."""
    hak: Optional[str] = Field(None, description="İhlal edildiği iddia edilen hak (örneğin, Mülkiyet hakkı).")
    mudahale_iddiasi: Optional[str] = Field(None, description="İhlale neden olan müdahale iddiası.")
    sonuc: Optional[str] = Field(None, description="İnceleme sonucu (örneğin, İhlal, Düşme).")
    giderim: Optional[str] = Field(None, description="Kararlaştırılan giderim (örneğin, Yeniden yargılama).")

class AnayasaBireyselReportDecisionSummary(BaseModel):
    """Model for a single Anayasa Mahkemesi (Bireysel Başvuru) decision summary from a 'Karar Arama Raporu'."""
    title: Optional[str] = Field(None, description="Başvurunun başlığı (e.g., 'HASAN DURMUŞ Başvurusuna İlişkin Karar').")
    decision_reference_no: Optional[str] = Field(None, description="Başvuru Numarası (e.g., '2019/19126').")
    decision_page_url: Optional[HttpUrl] = Field(None, description="URL to the full decision page.")
    decision_type_summary: Optional[str] = Field(None, description="Karar Türü (Başvuru Sonucu) (e.g., 'Esas (İhlal)').")
    decision_making_body: Optional[str] = Field(None, description="Kararı Veren Birim (e.g., 'Genel Kurul', 'Birinci Bölüm').")
    application_date_summary: Optional[str] = Field(None, description="Başvuru Tarihi (DD/MM/YYYY).")
    decision_date_summary: Optional[str] = Field(None, description="Karar Tarihi (DD/MM/YYYY).")
    application_subject_summary: Optional[str] = Field(None, description="Başvuru konusunun özeti.")
    details: List[AnayasaBireyselReportDecisionDetail] = Field(default_factory=list, description="İncelenen haklar ve sonuçlarına ilişkin detaylar.")

class AnayasaBireyselReportSearchResult(BaseModel):
    """Model for the overall search result for Anayasa Mahkemesi 'Karar Arama Raporu'."""
    decisions: List[AnayasaBireyselReportDecisionSummary]
    total_records_found: Optional[int] = Field(None, description="Raporda bulunan toplam karar sayısı.")
    retrieved_page_number: int = Field(description="Alınan rapor sayfa numarası.")


class AnayasaBireyselBasvuruDocumentMarkdown(BaseModel):
    """
    Model for an Anayasa Mahkemesi (Bireysel Başvuru) decision document, containing a chunk of Markdown content
    and pagination information. Fetched from /BB/YYYY/NNNN paths.
    """
    source_url: HttpUrl
    basvuru_no_from_page: Optional[str] = Field(None, description="Başvuru Numarası (B.No) parsed from the document page.")
    karar_tarihi_from_page: Optional[str] = Field(None, description="Decision date parsed from the document page.")
    basvuru_tarihi_from_page: Optional[str] = Field(None, description="Application date parsed from the document page.")
    karari_veren_birim_from_page: Optional[str] = Field(None, description="Deciding body (Bölüm/Genel Kurul) parsed from the document page.")
    karar_turu_from_page: Optional[str] = Field(None, description="Decision type (Başvuru Sonucu) parsed from the document page.")
    resmi_gazete_info_from_page: Optional[str] = Field(None, description="Official Gazette info parsed from the document page, if available.")
    markdown_chunk: Optional[str] = Field(None, description="A 5,000 character chunk of the Markdown content.")
    current_page: int = Field(description="The current page number of the markdown chunk (1-indexed).")
    total_pages: int = Field(description="Total number of pages for the full markdown content.")
    is_paginated: bool = Field(description="True if the full markdown content is split into multiple pages.")

# --- End Models for Bireysel Başvuru ---