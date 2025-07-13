# mcp_server_main.py
import asyncio
import atexit
import logging
import os
import httpx
from pydantic import HttpUrl, Field 
from typing import Optional, Dict, List, Literal, Any, Union
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

# Create FastMCP app directly without authentication wrapper
from fastmcp import FastMCP

def create_app():
    """Create basic FastMCP app without authentication wrapper"""
    return FastMCP("Yargı MCP Server")

# --- Module Imports ---
from yargitay_mcp_module.client import YargitayOfficialApiClient
from yargitay_mcp_module.models import (
    YargitayDetailedSearchRequest, YargitayDocumentMarkdown, CompactYargitaySearchResult,
    YargitayBirimEnum, CleanYargitayDecisionEntry
)
from bedesten_mcp_module.client import BedestenApiClient
from bedesten_mcp_module.models import (
    BedestenSearchRequest, BedestenSearchData,
    BedestenDocumentMarkdown, DanistayBirimEnum
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

from sayistay_mcp_module.client import SayistayApiClient
from sayistay_mcp_module.models import (
    GenelKurulSearchRequest, GenelKurulSearchResponse,
    TemyizKuruluSearchRequest, TemyizKuruluSearchResponse,
    DaireSearchRequest, DaireSearchResponse,
    SayistayDocumentMarkdown
)
from sayistay_mcp_module.enums import DaireEnum, KamuIdaresiTuruEnum, WebKararKonusuEnum

# KVKK Module Imports
from kvkk_mcp_module.client import KvkkApiClient
from kvkk_mcp_module.models import (
    KvkkSearchRequest,
    KvkkSearchResult,
    KvkkDocumentMarkdown
)


app = create_app()

# --- Tool Documentation Resources ---
@app.resource("docs://tools/yargitay")
async def get_yargitay_tools_documentation() -> str:
    """Get document content as Markdown."""
    return """
# Yargıtay (Court of Cassation) Tools Documentation

## Court Hierarchy and Position
Yargıtay is Turkey's highest civil and criminal court. It serves as the final appellate authority and establishes legal precedents for civil and criminal cases.

**Dual API System:**
- **Primary API (search_yargitay_detailed)**: Official karararama.yargitay.gov.tr
- **Bedesten API (search_yargitay_bedesten)**: Alternative bedesten.adalet.gov.tr

## Chamber Filtering Options (52 Total)

### Civil Chambers (Hukuk Daireleri)
- **Civil General Assembly** (Hukuk Genel Kurulu)
- **1st Civil Chamber** through **23rd Civil Chamber** (23 civil chambers)
- **Civil Chambers Presidents Board** (Hukuk Daireleri Başkanlar Kurulu)

### Criminal Chambers (Ceza Daireleri)  
- **Criminal General Assembly** (Ceza Genel Kurulu)
- **1st Criminal Chamber** through **23rd Criminal Chamber** (23 criminal chambers)
- **Criminal Chambers Presidents Board** (Ceza Daireleri Başkanlar Kurulu)

### General Assemblies
- **Grand General Assembly** (Büyük Genel Kurulu)

## Search Techniques

### Primary API (search_yargitay_detailed)
```
Simple search: "mülkiyet"
AND operator: "mülkiyet AND tapu"
OR operator: "mülkiyet OR tapu" 
NOT operator: "mülkiyet NOT satış"
Wildcard: "mülk*"
Exact phrase: "\"mülkiyet hakkı\""
```

### Bedesten API (search_yargitay_bedesten)
```
Regular search: phrase="mülkiyet kararı"
Exact phrase: phrase="\"mülkiyet kararı\""
Date filtering: kararTarihiStart="2024-01-01T00:00:00.000Z"
```

## Usage Scenarios
- **Precedent research**: Supreme court decisions on specific topics
- **Chamber-specific search**: Relevant chambers for specific legal areas  
- **Historical analysis**: Decision trends in specific periods
- **Jurisprudence tracking**: Changes in legal opinions

## Best Practices
1. **Use dual APIs**: Try both APIs for maximum coverage
2. **Chamber filtering**: Select chambers based on relevant legal area
3. **Exact phrases**: Use "\"term\"" for precise terms in Bedesten API
4. **Date range**: Focus on last 2-3 years for recent developments

## Common Civil Chambers
- **1st Civil**: Property, land registry, liens
- **4th Civil**: Labor law, collective agreements
- **11th Civil**: Insurance, social security
- **15th Civil**: Compensation, tort
- **21st Civil**: Execution and bankruptcy

## Common Criminal Chambers  
- **1st Criminal**: General criminal offenses
- **8th Criminal**: Economic and commercial crimes
- **12th Criminal**: Official misconduct
"""

@app.resource("docs://tools/danistay")  
async def get_danistay_tools_documentation() -> str:
    """Get document content as Markdown."""
    return """
# Danıştay (Council of State) Tools Documentation

## Court Hierarchy and Position
Danıştay is Turkey's highest administrative court. It makes final decisions on administrative acts and actions.

**Triple API System:**
- **Keyword API (search_danistay_by_keyword)**: AND/OR/NOT logic
- **Detailed API (search_danistay_detailed)**: Comprehensive criteria  
- **Bedesten API (search_danistay_bedesten)**: Alternative access

## Chamber Filtering Options (27 Total)

### Main Councils
- **Grand General Assembly** (Büyük Gen.Kur.)
- **Administrative Cases Council** (İdare Dava Daireleri Kurulu)
- **Tax Cases Council** (Vergi Dava Daireleri Kurulu)
- **Precedents Unification Council** (İçtihatları Birleştirme Kurulu)

### Chambers (1-17)
- **1st Chamber** through **17th Chamber** (Administrative case chambers)

### Military Courts
- **Military High Administrative Court** (Askeri Yüksek İdare Mahkemesi)
- **Military High Administrative Court 1st-3rd Chambers**

## Search Techniques

### Keyword API
```
AND logic: andKelimeler=["imar", "plan"]
OR logic: orKelimeler=["iptal", "yürütmeyi durdurma"]  
NOT logic: notKelimeler=["ceza"]
```

### Detailed API
```
Chamber selection: daire="3. Daire"
Case year: esasYil="2024"
Decision date: kararTarihiBaslangic="01.01.2024"
Legislation: mevzuatId=123
```

### Bedesten API  
```
Regular: phrase="idari işlem"
Exact: phrase="\"idari işlem\""
Date: kararTarihiStart="2024-01-01T00:00:00.000Z"
```

## Usage Scenarios
- **Administrative law research**: Public administration decisions
- **Tax law**: Financial matters and tax disputes
- **Urban planning law**: City planning and building permits
- **Personnel law**: Civil servant rights

## Common Chamber Specializations
- **1st Chamber**: Municipal, urban planning, environment  
- **2nd Chamber**: Tax, customs, financial
- **3rd Chamber**: Personnel, personal rights
- **5th Chamber**: Administrative fines
- **8th Chamber**: Higher education, education
- **10th Chamber**: Health, social security

## Best Practices
1. **Triple API**: Use all three APIs for maximum coverage
2. **Chamber selection**: Choose specialized chambers by subject area
3. **Mevzuat bağlantısı**: İlgili kanun/tüzükle filtreleme
4. **Kesin terim**: İdari hukuk terminolojisi için exact search
"""

@app.resource("docs://tools/constitutional_court")
async def get_constitutional_court_tools_documentation() -> str:
    """Get document content as Markdown."""
    return """
# Anayasa Mahkemesi (Constitutional Court) Tools Documentation

## Court Position
Constitutional Court is Turkey's highest judicial body. It has two main functions:

### 1. Norm Control (Norm Control)
**Tool**: search_anayasa_norm_denetimi_decisions
- Reviews constitutional compliance of laws and regulations
- Abstract and concrete norm control

### 2. Individual Application (Individual Application)  
**Tool**: search_anayasa_bireysel_basvuru_report
- Citizens' fundamental rights violation applications
- Turkey's human rights protection mechanism

## Norm Control Features

### Comprehensive Filtering
- **Application type**: Annulment, Objection, Other
- **Applicant**: President, Parliament, Courts
- **Legislation type**: Law, Decree, Regulation, Rules of procedure
- **Result type**: Annulment, Rejection, Partial annulment

### Advanced Search
- **Member names**: Full names of participating justices
- **Rapporteur**: Case rapporteur 
- **Dissenting opinion**: Minority opinion, different view
- **Press release**: Important decisions

## Bireysel Başvuru Özellikleri

### Temel Haklar Kategorileri
- **Yaşam hakkı**: Ölüm olayları, güvenlik
- **Adil yargılanma**: Süre, tarafsızlık, duruşma hakkı  
- **İfade özgürlüğü**: Basın, düşünce, akademik özgürlük
- **Din özgürlüğü**: İbadet, vicdan özgürlüğü
- **Mülkiyet hakkı**: Kamulaştırma, tapu
- **Özel hayat**: Gizlilik, aile hayatı

### Başvuru Süreci
- **Yurtiçi yollar**: Önce mahkeme kararı gerekli
- **Süre sınırı**: 30 gün (60 gün istisnai)
- **Kabul edilebilirlik**: Ön inceleme kriterleri

## Paginated Content (5,000 characters)
Her iki tool da sayfalanmış Markdown döndürür:
- **page_number**: Sayfa numarası (1'den başlar)
- **total_pages**: Toplam sayfa sayısı
- **current_page**: Mevcut sayfa

## Usage Scenarios

### Norm Denetimi
- **Kanun anayasaya uygunluk**: Yeni çıkan kanunların kontrolü
- **Mahkeme iptali**: Kanunun belirli maddeleri
- **Mevzuat uyum**: Anayasa değişikliği sonrası

### Bireysel Başvuru
- **İnsan hakları araştırması**: AİHM öncesi iç hukuk
- **Temel hak ihlalleri**: Sistematik ihlal tespiti
- **Emsal karar**: Benzer davalar için içtihat

## Parameter Details
### search_anayasa_norm_denetimi_decisions
- **keywords_all**: Keywords for AND logic (all must be present)
- **keywords_any**: Keywords for OR logic (any can be present) 
- **keywords_exclude**: Keywords to exclude from results
- **period**: Constitutional period - "ALL", "1" (1961 Constitution), "2" (1982 Constitution)
- **case_number_esas**: Case registry number (e.g., '2023/123')
- **decision_number_karar**: Decision number (e.g., '2023/456')
- **first_review_date_start/end**: First review date range (DD/MM/YYYY)
- **decision_date_start/end**: Decision date range (DD/MM/YYYY)
- **application_type**: "ALL", "1" (İptal), "2" (İtiraz), "3" (Diğer)
- **applicant_general_name**: General applicant name
- **applicant_specific_name**: Specific applicant name
- **official_gazette_date_start/end**: Official Gazette date range
- **official_gazette_number_start/end**: Official Gazette number range
- **has_press_release**: "ALL", "0" (No), "1" (Yes)
- **has_dissenting_opinion**: "ALL", "0" (No), "1" (Yes)
- **has_different_reasoning**: "ALL", "0" (No), "1" (Yes)
- **attending_members_names**: List of attending members' exact names
- **rapporteur_name**: Rapporteur's exact name
- **norm_type**: Type of reviewed norm (law, decree, regulation, etc.)
- **norm_id_or_name**: Number or name of the norm
- **norm_article**: Article number of the norm
- **review_outcomes**: List of review outcomes
- **reason_for_final_outcome**: Main reason for decision outcome
- **basis_constitution_article_numbers**: Supporting Constitution article numbers
- **results_per_page**: Results per page (10, 20, 30, 40, 50)
- **page_to_fetch**: Page number to fetch
- **sort_by_criteria**: Sort criteria ('KararTarihi', 'YayinTarihi', 'Toplam')

### search_anayasa_bireysel_basvuru_report
- **keywords**: Keywords for AND logic (all must be present)
- **page_to_fetch**: Page number for the report (default: 1)

### Document Tools
- **document_url**: URL path or full URL of the decision
- **page_number**: Page number for paginated content (1-indexed, default: 1)

## Best Practices
1. **Norm control önce**: Kanun iptal edilmiş mi kontrol
2. **Bireysel başvuru ikinci**: Kişisel hak ihlalleri için
3. **Tarih aralığı**: Anayasa değişiklikleri sonrası dönemler
4. **Anahtar kelime kombinasyonu**: Temel hak + konu alanı
5. **Sayfa yönetimi**: Uzun kararlarda sayfa sayfa okuyun
"""

@app.resource("docs://tools/emsal")
async def get_emsal_tools_documentation() -> str:
    """Get document content as Markdown."""
    return """
# Emsal (UYAP Precedent System) Tools Documentation

## System Position
Central precedent decision system providing access to all court decisions through the UYAP system.

## Court Options
- **Yargıtay**: First and second instance courts
- **Danıştay**: Administrative court decisions
- **Other**: Regional courts of justice, civil courts

## Advanced Filtering Features
- **Court type**: Civil, criminal, administrative
- **Case/Decision number**: File tracking system
- **Date range**: Flexible date selection
- **Content search**: Keyword search within decision text

## Usage Scenarios
- **Kapsamlı emsal**: Tüm mahkeme seviyelerinden karar toplama
- **Güncel içtihat**: En son hukuki gelişmeler
- **Cross-reference**: Farklı mahkeme görüşlerini karşılaştırma

## Best Practices
1. **Spesifik terimler**: Hukuki terminoloji kullanın
2. **Geniş arama**: Önce genel, sonra spesifik
3. **Tarih stratejisi**: Mevzuat değişiklikleri dikkate alın
4. **Cross-platform**: Aynı konuyu farklı mahkemelerde arayın
"""

@app.resource("docs://tools/uyusmazlik")
async def get_uyusmazlik_tools_documentation() -> str:
    """Get document content as Markdown."""
    return """
# Uyuşmazlık Mahkemesi Tools Documentation

## Court Position
Adli ve idari yargı arasındaki görev uyuşmazlıklarını çözen özel yetkili mahkeme.

## Dispute Types
- **Görev uyuşmazlığı**: Hangi mahkeme bakacak konusunda anlaşmazlık
- **Hüküm uyuşmazlığı**: Çelişkili mahkeme kararları
- **Yetki uyuşmazlığı**: Yerel yetki sorunları

## Form-Based Search Criteria
- **Karar türü**: Müspet, menfi, hüküm uyuşmazlığı
- **Taraf mahkemeler**: Adli-idari yargı organları
- **Konu alanı**: Hukuk dalı bazlı filtreleme
- **Tarih aralığı**: Karar tarihi seçimi

## Usage Scenarios
- **Yargı türü belirleme**: Hangi mahkemenin yetkili olduğu
- **Çelişkili kararlar**: Farklı mahkeme kararları arasındaki uyuşmazlık
- **Yetki sorunları**: Mahkeme yetkisi tartışmaları

## Best Practices
1. **Net kriterler**: Arama kriterlerini spesifik tutun
2. **Taraf bilgisi**: Uyuşmazlık taraflarını belirtin
3. **Konu odaklı**: İlgili hukuk dalını seçin
"""

@app.resource("docs://tools/kik")
async def get_kik_tools_documentation() -> str:
    """Get document content as Markdown."""
    return """
# KİK (Kamu İhale Kurumu) Tools Documentation

## Kurum Konumu
Kamu ihale uyuşmazlıklarının ilk ve son merci çözüm organı. Kamu İhale Kanunu kapsamındaki tüm ihaleler için yetkili.

## Decision Types
- **Uyuşmazlık**: İhale süreç itirazları
- **Düzenleyici**: Mevzuat ve uygulama kararları  
- **Mahkeme**: Mahkeme kararlarının uygulanması

## Filtreleme Seçenekleri
- **Karar numarası**: 2024/UH.II-1766 formatında
- **Tarih aralığı**: Karar tarihi filtreleme
- **İhaleyi yapan idare**: Bakanlık, belediye, hastane, üniversite
- **Başvuru sahibi**: Şirket, firma adı
- **İhale konusu**: Mal, hizmet, yapım işi

## Sayfalanmış İçerik Özelliği
5.000 karakterlik sayfalar halinde Markdown formatında sunulur.

## Usage Scenarios
- **İhale hukuku**: Kamu alımları, süreç kuralları
- **Başvuru hazırlığı**: Benzer davalar, emsal kararlar
- **Mevzuat yorumu**: Kamu İhale Kanunu uygulaması
- **İtiraz stratejisi**: Başarılı itiraz örnekleri

## İhale Süreç Aşamaları
1. **İhale öncesi**: İlan, şartname hazırlığı
2. **İhale aşaması**: Teklif verme, değerlendirme
3. **İhale sonrası**: Sonuç bildirimi, itirazlar
4. **Sözleşme**: İmza, uygulama

## Parameter Details
### search_kik_decisions  
- **karar_tipi**: Decision type - "rbUyusmazlik" (disputes), "rbDuzenleyici" (regulatory), "rbMahkeme" (court)
- **karar_no**: Decision number (e.g., '2024/UH.II-1766')
- **karar_tarihi_baslangic**: Decision start date (DD.MM.YYYY format)
- **karar_tarihi_bitis**: Decision end date (DD.MM.YYYY format)
- **basvuru_sahibi**: Applicant name/company
- **ihaleyi_yapan_idare**: Procuring entity (ministry, municipality, etc.)
- **basvuru_konusu_ihale**: Tender subject/description
- **karar_metni**: Text search with operators: +word (AND), -word (exclude)
- **yil**: Decision year
- **resmi_gazete_tarihi**: Official Gazette date (DD.MM.YYYY)
- **resmi_gazete_sayisi**: Official Gazette number
- **page**: Results page number

### get_kik_document_markdown
- **karar_id**: Base64 encoded decision identifier from search results
- **page_number**: Page number for paginated content (1-indexed, default: 1)

## Best Practices
1. **İhale türü**: Açık, belli istekliler arası, pazarlık
2. **Süreç aşaması**: Hangi aşamada sorun olduğu
3. **Hukuki dayanak**: İlgili KİK kanun maddesi
4. **Sayfa yönetimi**: Uzun kararları bölümler halinde okuyun
"""

@app.resource("docs://tools/rekabet")
async def get_rekabet_tools_documentation() -> str:
    """Get document content as Markdown."""
    return """
# Rekabet Kurumu (Competition Authority) Tools Documentation

## Kurum Konumu  
Rekabet hukuku ihlallerini inceleyen ve ceza veren idari otorite. Rekabet Kanunu kapsamında yetkili.

## Decision Types
- **Birleşme ve Devralma**: Şirket satın almaları, füzyonlar
- **Rekabet İhlali**: Anlaşma, hakim durum kötüye kullanımı
- **Menfi Tespit ve Muafiyet**: İhlal yok kararları, muafiyetler
- **Özelleştirme**: Kamu şirketleri satışı onayları

## Filtreleme Özellikleri
- **PDF metin arama**: Tam metin içinde kelime arama
- **Karar türü**: Spesifik kategori seçimi
- **Tarih aralığı**: 1997'den günümüze karar arşivi
- **Sektör**: Telekomünikasyon, bankacılık, enerji, perakende

## Rekabet Hukuku Temel Kavramları
- **Hakim durum**: Pazar gücü
- **Kartel**: Fiyat anlaşması
- **Dikey anlaşmalar**: Tedarikci-bayi ilişkileri
- **Konsantrasyon**: Birleşme işlemleri

## Usage Scenarios
- **Antitrust araştırması**: Tekelleşme, kartel soruşturmaları  
- **Birleşme incelemesi**: M&A transaction değerlendirmesi
- **Sektör analizi**: Belirli pazarlardaki rekabet durumu
- **Ceza hesaplama**: İhlal cezası örnekleri

## Sektörel Uzmanlık Alanları
1. **Telekomünikasyon**: Operatör rekabeti
2. **Enerji**: Elektrik, doğalgaz piyasası
3. **Finans**: Bankacılık, sigorta
4. **Perakende**: Zincir mağazalar
5. **İnşaat**: Müteahhitlik sektörü

## Parameter Details
### search_rekabet_kurumu_decisions
- **sayfaAdi**: Search in decision title (Başlık)
- **YayinlanmaTarihi**: Publication date (DD.MM.YYYY format)
- **PdfText**: Search text. For exact phrases use double quotes: "vertical agreement"
- **KararTuru**: Decision type - "Birleşme ve Devralma", "Rekabet İhlali", etc.
- **KararSayisi**: Decision number (Karar Sayısı)
- **KararTarihi**: Decision date (DD.MM.YYYY format)
- **page**: Page number for results list

### get_rekabet_kurumu_document
- **karar_id**: GUID from search results
- **page_number**: Requested page for Markdown content (1-indexed, default: 1)

## Best Practices
1. **Sektör odaklı**: İlgili sektörde arama yapın
2. **Karar türü seçimi**: İhtiyacınıza uygun kategori
3. **Güncel mevzuat**: Mevzuat değişiklikleri takibi
4. **Sayfa yönetimi**: Uzun analizleri bölümler halinde
"""

@app.resource("docs://tools/bedesten_api_courts")
async def get_bedesten_api_courts_documentation() -> str:
    """Get document content as Markdown."""
    return """
# Bedesten API Mahkemeleri Tools Documentation

## Bedesten API Sistemi
bedesten.adalet.gov.tr üzerinden Türk adalet sistemi hiyerarşisindeki mahkemelere erişim.

## Mahkeme Hiyerarşisi Kapsamı

### 1. Yerel Hukuk Mahkemeleri (Local Civil Courts)
**Tool**: search_yerel_hukuk_bedesten
- **Konum**: İlk derece mahkemeler
- **Yetki**: Hukuki uyuşmazlıklar (sözleşme, tazminat, mülkiyet)
- **Önem**: Toplumun günlük hukuki sorunları

### 2. İstinaf Hukuk Mahkemeleri (Civil Courts of Appeals)  
**Tool**: search_istinaf_hukuk_bedesten
- **Konum**: Orta derece (Yerel -> İstinaf -> Yargıtay)
- **Yetki**: Yerel mahkeme kararlarına itiraz
- **Önem**: Temyiz öncesi son kontrol

### 3. Kanun Yararına Bozma (KYB)
**Tool**: search_kyb_bedesten  
- **Konum**: Olağanüstü kanun yolu
- **Başvuru sahibi**: Cumhuriyet Başsavcılığı
- **Amaç**: Hukuka aykırı kararları düzeltme
- **Özellik**: Sanık aleyhine olsa bile hukuk yararına

## Ortak Bedesten API Özellikleri

### Tarih Filtreleme (ISO 8601)
```
Başlangıç: kararTarihiStart="2024-01-01T00:00:00.000Z"
Bitiş: kararTarihiEnd="2024-12-31T23:59:59.999Z"
Tek gün: "2024-06-25T00:00:00.000Z" - "2024-06-25T23:59:59.999Z"
```

### Kesin Cümle Arama
```
Normal: phrase="sözleşme ihlali"  (kelimeler ayrı ayrı)
Kesin: phrase="\"sözleşme ihlali\""  (tam cümle)
```

### Sayfalama
- **pageSize**: 1-100 arası sonuç sayısı
- **pageNumber**: Sayfa numarası (1'den başlar)

## Mahkeme Özellikleri

### Yerel Hukuk Mahkemeleri
**Yaygın Dava Türleri**:
- Sözleşme ihlali davaları
- Tazminat talepleri  
- Mülkiyet uyuşmazlıkları
- Aile hukuku (boşanma, nafaka)
- Ticari uyuşmazlıklar (küçük-orta ölçek)

**Kullanım Senaryoları**:
- Günlük hukuki sorunlar
- Vatandaş hakları
- Ticaret hukuku temelleri
- İcra takipleri

### İstinaf Hukuk Mahkemeleri  
**İnceleme Kapsamı**:
- Yerel mahkeme kararlarının kontrolü
- Hukuki ve maddi hata arayışı
- Yeniden yargılama (sınırlı)

**Kullanım Senaryoları**:
- Temyiz stratejisi gelişitirme
- İstinaf mahkemesi içtihatları
- Yerel-üst mahkeme uyumu analizi

### Kanun Yararına Bozma (KYB)
**Başvuru Koşulları**:
- Kesinleşmiş mahkeme kararı
- Hukuka açık aykırılık
- Cumhuriyet Başsavcılığı başvurusu
- Sanık aleyhine sonuç doğurmama

**Kullanım Senaryoları**:
- Sistematik hukuki hatalar
- İçtihat birliğini sağlama
- Hukuk güvenliği
- Nadir ve özel hukuki durumlar

## Arama Stratejileri

### Hiyerarşik Arama
```
1. Yerel mahkeme -> Gündelik sorunlar
2. İstinaf -> Kompleks yorumlar  
3. KYB -> İstisnai hukuki durumlar
```

### Kesin Terim Kullanımı
```
Yerel: "\"sözleşme ihlali\""
İstinaf: "\"temyiz incelemesi\""  
KYB: "\"kanun yararına bozma\""
```

### Tarih Stratejisi
- **Son 2 yıl**: Güncel içtihat
- **5-10 yıl**: Yerleşik görüşler
- **Mevzuat değişikliği sonrası**: Yeni uygulamalar

## Best Practices
1. **Hiyerarşi takibi**: Alt mahkemeden üst mahkemeye
2. **Kesin cümle**: Hukuki terimler için "\"terim\""
3. **Tarih aralığı**: İlgili mevzuat dönemleri
4. **Cross-reference**: Aynı konuyu farklı seviyelerde
5. **Minimal sonuç**: KYB çok nadir, az sonuç beklenir

## Document ID Formatı
Tüm Bedesten mahkemeleri documentId döndürür:
- **Format**: Alfanumerik string
- **Kullanım**: get_*_bedesten_document_markdown fonksiyonları
- **İçerik**: HTML/PDF -> Markdown conversion
"""

@app.resource("docs://tools/sayistay")
async def get_sayistay_tools_documentation() -> str:
    """Get document content as Markdown."""
    return """
# Sayıştay (Court of Accounts) Tools Documentation

## Sayıştay'ın Konumu
Türkiye'nin en üst mali denetim organı. Kamu kaynaklarının kullanımını denetler ve mali disiplini sağlar.

## Üç Tür Karar Sistemi

### 1. Genel Kurul Kararları (Interpretive Rulings)
**Tool**: search_sayistay_genel_kurul
- **İşlev**: Mali mevzuat yorumlama
- **Kapsam**: 2006-2024 yılları arası
- **Özellik**: Bağlayıcı yorumlar

**Filtreleme Seçenekleri**:
- **Karar numarası**: Spesifik karar arama
- **Tarih aralığı**: Başlangıç-bitiş tarihleri
- **Karar tamamı**: Tam metin arama (400 karakter)

### 2. Temyiz Kurulu Kararları (Appeals Board)
**Tool**: search_sayistay_temyiz_kurulu  
- **İşlev**: Daire kararlarına itiraz incelemesi
- **8 Daire Filtreleme**: Uzmanlık alanlarına göre

**Daire Uzmanlaşmaları**:
- **1. Daire**: Genel bütçeli idareler
- **2. Daire**: Mahalli idareler  
- **3. Daire**: Sosyal güvenlik kurumları
- **4. Daire**: KİT ve bağlı ortaklıklar
- **5. Daire**: Düzenleyici kuruluşlar
- **6. Daire**: Vakıflar, dernekler
- **7. Daire**: Üniversiteler, eğitim
- **8. Daire**: Yatırım projeleri

**Filtreleme Seçenekleri**:
- **İdare türü**: Bakanlık, belediye, üniversite, KİT
- **Temyiz karar**: Tam metin arama
- **Konu sınıflandırması**: Harcama, gelir, taşınır-taşınmaz

### 3. Daire Kararları (Chamber Decisions)  
**Tool**: search_sayistay_daire
- **İşlev**: İlk derece denetim bulguları
- **8 Daire**: Aynı uzmanlaşma alanları

**Filtreleme Seçenekleri**:
- **Yargılama dairesi**: 1-8 arası daire seçimi
- **Hesap yılı**: Mali yıl bazlı
- **Web karar metni**: İçerik arama

## Ortak Özellikler

### Sayfalanmış Markdown
Tüm Sayıştay belgeleri sayfalanmış format:
- **5.000 karakter** per sayfa
- **page_number**: Sayfa numarası
- **total_pages**: Toplam sayfa

### Tarih Aralığı Desteği
- **Genel Kurul**: 2006-2024 (18 yıl)
- **Temyiz/Daire**: Mevcut veriler üzerinde

## Usage Scenarios

### Mali Mevzuat Araştırması
```
Genel Kurul -> Hukuki yorum
Temyiz -> Uygulama detayları  
Daire -> Spesifik örnekler
```

### Kamu Mali Yönetimi
- **Bütçe uygulama**: Harcama usulleri
- **İhale süreçleri**: Kamu alımları denetimi
- **Personel giderleri**: Özlük hakları mali boyutu
- **Yatırım projeleri**: Büyük ölçekli projeler

### Kurumsal Denetim
- **KİT yönetimi**: Kamu iktisadi teşebbüsleri
- **Belediye maliyesi**: Yerel yönetim harcamaları  
- **Üniversite bütçesi**: Yükseköğretim mali yönetimi
- **Sosyal güvenlik**: SGK, Bağ-Kur mali işlemleri

## Arama Stratejileri

### Hiyerarşik Yaklaşım
1. **Genel Kurul**: Konunun hukuki çerçevesi
2. **Temyiz**: Tartışmalı uygulamalar
3. **Daire**: Günlük uygulama örnekleri

### Daire Bazlı Strateji
```
Mali konu -> İlgili daire seçimi -> Derinlemesine arama
Örnek: KİT mali sorunları -> 4. Daire
```

### Tarih Odaklı Strateji
- **Son 2 yıl**: Güncel uygulamalar
- **5 yıl**: Yerleşik görüşler  
- **2006-2024**: Tarihsel gelişim

## Best Practices
1. **Daire uzmanlaşması**: İlgili kuruma uygun daire
2. **Hiyerarşik sıralama**: Genel Kurul -> Temyiz -> Daire
3. **Mali dönem**: Bütçe yılları bazında arama
4. **Teknik terimler**: Mali mevzuat terminolojisi
5. **Cross-reference**: Farklı seviyelerden görüş karşılaştırma

## İdare Türü Kodları
- **1**: Genel bütçeli
- **2**: Özel bütçeli  
- **3**: Düzenleyici kuruluşlar
- **4**: Mahalli idareler
- **5**: Sosyal güvenlik
- **6**: KİT
- **7**: Vakıf/dernek
- **8**: Diğer kamu kuruluşları
"""

@app.resource("docs://tools/kvkk")
async def get_kvkk_tools_documentation() -> str:
    """Get document content as Markdown."""
    return """
# KVKK (Personal Data Protection Authority) Tools Documentation

## KVKK'nın Konumu
Kişisel Verilerin Korunması Kanunu'nun (KVKK) uygulanmasını denetleyen otorite.
Türkiye'nin GDPR equivalent'ı olarak işlev görür.

## Brave Search API Sistemi
**Özellik**: Brave Search API ile kvkk.gov.tr sitesi taraması
- **Site hedeflemeli**: Otomatik `site:kvkk.gov.tr "karar özeti"`
- **Türkçe optimize**: Türkçe hukuki terimler için optimize
- **Sayfalama**: page ve pageSize parametreleri

## KVKK Karar Türleri

### İdari Para Cezaları
- **Veri ihlalleri**: Kişisel veri güvenliği ihlalleri
- **Rıza eksiklikleri**: Açık rıza alınmaması
- **Bilgilendirme yetersizliği**: Veri sahibi bilgilendirme
- **Yurtdışı aktarım**: İzinsiz veri transferi

### Uyum Değerlendirmeleri
- **GDPR uyumluluğu**: AB mevzuatı ile uyum
- **Veri koruma politikaları**: Kurumsal politika değerlendirme
- **Teknik önlemler**: Güvenlik tedbirleri yeterliliği

### Veri İhlali Bildirimları
- **24 saat kuralı**: İhlal bildirimi süreleri
- **Etki değerlendirmesi**: İhlal büyüklüğü analizi
- **Düzeltici tedbirler**: İhlal sonrası alınacak önlemler

## Arama Stratejileri

### Türkçe Hukuki Terimler
```
Temel: "açık rıza", "veri ihlali", "kişisel veri"
Teknik: "veri koruma", "güvenlik tedbirleri", "şifreleme"  
Süreç: "bildirimi", "değerlendirme", "denetim"
GDPR: "GDPR uyum", "Avrupa Birliği", "yeterlilik kararı"
```

### Sektör Bazlı Aramalar
```
Teknoloji: "e-ticaret", "mobil uygulama", "web sitesi"
Sağlık: "hasta bilgileri", "tıbbi veriler"
Finans: "bankacılık", "kredi kartı", "müşteri bilgileri"
Eğitim: "öğrenci verileri", "elektronik okul"
```

### Ceza Türü Aramalar
```
İdari ceza: "idari para cezası", "ihlal tespiti"
Uyarı: "uyarı kararı", "önlem alınması"
Red: "şikayet redi", "yetki dışı"
```

## Paginated Content (5,000 characters)
KVKK belgeleri sayfalanmış Markdown formatında:
- **page_number**: Sayfa numarası (1'den başlar)
- **total_pages**: Toplam sayfa sayısı  
- **current_page**: Mevcut sayfa
- **is_paginated**: Sayfalanma durumu

## Usage Scenarios

### Veri Koruma Uyumu
- **GDPR compliance**: AB mevzuatı ile uyum kontrolü
- **Şirket politikaları**: Kurumsal veri koruma
- **Teknik önlemler**: Güvenlik tedbirleri benchmarking
- **Uluslararası transfer**: Yurtdışı veri aktarımı kuralları

### İhlal Analizi
- **Benzer vakalar**: Aynı türde ihlal örnekleri
- **Ceza miktarları**: İhlal türüne göre ceza analizi
- **Düzeltici tedbirler**: İhlal sonrası yapılması gerekenler
- **Önleme stratejileri**: Proaktif koruma tedbirleri

### Sektörel Araştırma
- **E-ticaret**: Online mağaza veri koruma
- **Sağlık**: Hasta verileri güvenliği
- **Finans**: Müşteri bilgileri koruma
- **Teknoloji**: Uygulama ve platform sorumlulukları

## KVKK Hukuki Framework

### Temel İlkeler
1. **Hukuka uygunluk**: Kanuna uygun işleme
2. **Dürüstlük**: İyi niyet ilkesi
3. **Şeffaflık**: Açık bilgilendirme
4. **Amaçla sınırlılık**: Belirli amaçla işleme
5. **Veri minimizasyonu**: Gerekli minimum veri
6. **Doğruluk**: Güncel ve doğru veri

### Veri Sahibi Hakları
- **Bilgi alma**: Veri işlendiğini öğrenme
- **Erişim**: Verilerine erişim talep etme
- **Düzeltme**: Yanlış verileri düzeltme
- **Silme**: Verilerin silinmesini isteme
- **İtiraz**: Veri işlemeye karşı çıkma

## Best Practices
1. **Türkçe terimler**: Orijinal hukuki terminoloji
2. **Sektör odaklı**: İlgili sektörle filtreleme
3. **Güncel gelişmeler**: Son 2-3 yıl öncelikli
4. **GDPR referansı**: AB mevzuatı ile karşılaştırma
5. **Sayfa yönetimi**: Uzun kararları bölümler halinde

## Yaygın KVKK Terimleri Sözlüğü
- **Açık rıza**: Explicit consent
- **Veri sorumlusu**: Data controller  
- **Veri işleyici**: Data processor
- **Kişisel veri**: Personal data
- **Özel nitelikli veri**: Special categories of data
- **Veri ihlali**: Data breach
- **Veri koruma**: Data protection
- **Yurtdışı aktarım**: International transfer
"""


# --- API Client Instances ---
yargitay_client_instance = YargitayOfficialApiClient()
danistay_client_instance = DanistayApiClient()
emsal_client_instance = EmsalApiClient()
uyusmazlik_client_instance = UyusmazlikApiClient()
anayasa_norm_client_instance = AnayasaMahkemesiApiClient()
anayasa_bireysel_client_instance = AnayasaBireyselBasvuruApiClient()
kik_client_instance = KikApiClient()
rekabet_client_instance = RekabetKurumuApiClient()
bedesten_client_instance = BedestenApiClient()
sayistay_client_instance = SayistayApiClient()
kvkk_client_instance = KvkkApiClient()


KARAR_TURU_ADI_TO_GUID_ENUM_MAP = {
    "": RekabetKararTuruGuidEnum.TUMU,  # Keep for backward compatibility
    "ALL": RekabetKararTuruGuidEnum.TUMU,  # Map "ALL" to TUMU
    "Birleşme ve Devralma": RekabetKararTuruGuidEnum.BIRLESME_DEVRALMA,
    "Diğer": RekabetKararTuruGuidEnum.DIGER,
    "Menfi Tespit ve Muafiyet": RekabetKararTuruGuidEnum.MENFI_TESPIT_MUAFIYET,
    "Özelleştirme": RekabetKararTuruGuidEnum.OZELLESTIRME,
    "Rekabet İhlali": RekabetKararTuruGuidEnum.REKABET_IHLALI,
}

# --- MCP Tools for Yargitay ---
@app.tool(
    description="Search Yargıtay decisions using primary API with 52 chamber filtering and advanced operators. Before using, read docs://tools/yargitay",
    annotations={
        "readOnlyHint": True,
        "openWorldHint": True,
        "idempotentHint": True
    }
)
async def search_yargitay_detailed(
    arananKelime: str = Field("", description="Search keyword with OR/AND/wildcard operators"),
    birimYrgKurulDaire: str = Field("ALL", description="Chamber selection (52 options: Civil/Criminal chambers, General Assemblies)"),
    birimYrgHukukDaire: str = Field("", description="Legacy field - use birimYrgKurulDaire instead"),
    birimYrgCezaDaire: str = Field("", description="Legacy field - use birimYrgKurulDaire instead"),
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
    pageSize: int = Field(10, ge=1, le=10, description="Number of results per page."),
    pageNumber: int = Field(1, ge=1, description="Page number to retrieve.")
) -> CompactYargitaySearchResult:
    """Search Yargıtay decisions using primary API with 52 chamber filtering and advanced operators."""
    
    # Convert "ALL" to empty string for API compatibility
    if birimYrgKurulDaire == "ALL":
        birimYrgKurulDaire = ""
    
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
        if api_response and api_response.data and api_response.data.data:
            # Convert to clean decision entries without arananKelime field
            clean_decisions = [
                CleanYargitayDecisionEntry(
                    id=decision.id,
                    daire=decision.daire,
                    esasNo=decision.esasNo,
                    kararNo=decision.kararNo,
                    kararTarihi=decision.kararTarihi,
                    document_url=decision.document_url
                )
                for decision in api_response.data.data
            ]
            return CompactYargitaySearchResult(
                decisions=clean_decisions,
                total_records=api_response.data.recordsTotal if api_response.data else 0,
                requested_page=search_query.pageNumber,
                page_size=search_query.pageSize)
        logger.warning("API response for Yargitay search did not contain expected data structure.")
        return CompactYargitaySearchResult(decisions=[], total_records=0, requested_page=search_query.pageNumber, page_size=search_query.pageSize)
    except Exception as e:
        logger.exception(f"Error in tool 'search_yargitay_detailed'.")
        raise

@app.tool(
    description="Retrieve full text of a Yargıtay decision in Markdown format. Before using, read docs://tools/yargitay",
    annotations={
        "readOnlyHint": True,
        "idempotentHint": True
    }
)
async def get_yargitay_document_markdown(id: str) -> YargitayDocumentMarkdown:
    """Get Yargıtay decision text as Markdown. Use ID from search results."""
    logger.info(f"Tool 'get_yargitay_document_markdown' called for ID: {id}")
    if not id or not id.strip(): raise ValueError("Document ID must be a non-empty string.")
    try:
        return await yargitay_client_instance.get_decision_document_as_markdown(id)
    except Exception as e:
        logger.exception(f"Error in tool 'get_yargitay_document_markdown'.")
        raise

# --- MCP Tools for Danistay ---
@app.tool(
    description="Search Danıştay decisions using keyword logic with AND/OR/NOT operators. Before using, read docs://tools/danistay",
    annotations={
        "readOnlyHint": True,
        "openWorldHint": True,
        "idempotentHint": True
    }
)
async def search_danistay_by_keyword(
    andKelimeler: List[str] = Field(default_factory=list, description="Keywords for AND logic, e.g., ['word1', 'word2']"),
    orKelimeler: List[str] = Field(default_factory=list, description="Keywords for OR logic."),
    notAndKelimeler: List[str] = Field(default_factory=list, description="Keywords for NOT AND logic."),
    notOrKelimeler: List[str] = Field(default_factory=list, description="Keywords for NOT OR logic."),
    pageNumber: int = Field(1, ge=1, description="Page number."),
    pageSize: int = Field(10, ge=1, le=10, description="Results per page.")
) -> CompactDanistaySearchResult:
    """Search Danıştay decisions with keyword logic."""
    
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

@app.tool(
    description="Search Danıştay decisions with detailed criteria including chamber selection and case numbers. Before using, read docs://tools/danistay",
    annotations={
        "readOnlyHint": True,
        "openWorldHint": True,
        "idempotentHint": True
    }
)
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
    pageSize: int = Field(10, ge=1, le=10, description="Results per page.")
) -> CompactDanistaySearchResult:
    """Search Danıştay decisions with detailed filtering."""
    
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

@app.tool(
    description="Retrieve full text of a Danıştay decision in Markdown format. Before using, read docs://tools/danistay",
    annotations={
        "readOnlyHint": True,
        "idempotentHint": True
    }
)
async def get_danistay_document_markdown(id: str) -> DanistayDocumentMarkdown:
    """Get Danıştay decision text as Markdown. Use ID from search results."""
    logger.info(f"Tool 'get_danistay_document_markdown' called for ID: {id}")
    if not id or not id.strip(): raise ValueError("Document ID must be a non-empty string for Danıştay.")
    try:
        return await danistay_client_instance.get_decision_document_as_markdown(id)
    except Exception as e:
        logger.exception(f"Error in tool 'get_danistay_document_markdown'.")
        raise

# --- MCP Tools for Emsal ---
@app.tool(
    description="Search Emsal precedent decisions with detailed criteria across Turkish courts. Before using, read docs://tools/emsal",
    annotations={
        "readOnlyHint": True,
        "openWorldHint": True,
        "idempotentHint": True
    }
)
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
    page_number: int = Field(1, ge=1, description="Page number (accepts int)."),
    page_size: int = Field(10, ge=1, le=10, description="Results per page.")
) -> CompactEmsalSearchResult:
    """Search Emsal precedent decisions with detailed criteria."""
    
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
                total_records=api_response.data.recordsTotal if api_response.data.recordsTotal is not None else 0,
                requested_page=search_query.page_number,
                page_size=search_query.page_size
            )
        logger.warning("API response for Emsal search did not contain expected data structure.")
        return CompactEmsalSearchResult(decisions=[], total_records=0, requested_page=search_query.page_number, page_size=search_query.page_size)
    except Exception as e:
        logger.exception(f"Error in tool 'search_emsal_detailed_decisions'.")
        raise

@app.tool(
    description="Retrieve full text of an Emsal precedent decision in Markdown format. Before using, read docs://tools/emsal",
    annotations={
        "readOnlyHint": True,
        "idempotentHint": True
    }
)
async def get_emsal_document_markdown(id: str) -> EmsalDocumentMarkdown:
    """Get document as Markdown."""
    logger.info(f"Tool 'get_emsal_document_markdown' called for ID: {id}")
    if not id or not id.strip(): raise ValueError("Document ID required for Emsal.")
    try:
        return await emsal_client_instance.get_decision_document_as_markdown(id)
    except Exception as e:
        logger.exception(f"Error in tool 'get_emsal_document_markdown'.")
        raise

# --- MCP Tools for Uyusmazlik ---
@app.tool(
    description="Search Uyuşmazlık Mahkemesi decisions for jurisdictional disputes between court systems. Before using, read docs://tools/uyusmazlik",
    annotations={
        "readOnlyHint": True,
        "openWorldHint": True,
        "idempotentHint": True
    }
)
async def search_uyusmazlik_decisions(
    icerik: str = Field("", description="Keyword or content for main text search."),
    bolum: Literal["ALL", "Ceza Bölümü", "Genel Kurul Kararları", "Hukuk Bölümü"] = Field("ALL", description="Select the department (Bölüm). Use 'ALL' for all departments."),
    uyusmazlik_turu: Literal["ALL", "Görev Uyuşmazlığı", "Hüküm Uyuşmazlığı"] = Field("ALL", description="Select the type of dispute. Use 'ALL' for all types."),
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
    """Search Court of Jurisdictional Disputes decisions."""
    
    # Convert string literals to enums
    # Map "ALL" to TUMU for backward compatibility
    if bolum == "ALL":
        bolum_enum = UyusmazlikBolumEnum.TUMU
    else:
        bolum_enum = UyusmazlikBolumEnum(bolum) if bolum else UyusmazlikBolumEnum.TUMU
    
    if uyusmazlik_turu == "ALL":
        uyusmazlik_turu_enum = UyusmazlikTuruEnum.TUMU
    else:
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

@app.tool(
    description="Retrieve full text of an Uyuşmazlık Mahkemesi decision from URL in Markdown format. Before using, read docs://tools/uyusmazlik",
    annotations={
        "readOnlyHint": True,
        "idempotentHint": True
    }
)
async def get_uyusmazlik_document_markdown_from_url(
    document_url: str = Field(..., description="Full URL to the Uyuşmazlık Mahkemesi decision document from search results")
) -> UyusmazlikDocumentMarkdown:
    """Get Uyuşmazlık Mahkemesi decision as Markdown."""
    logger.info(f"Tool 'get_uyusmazlik_document_markdown_from_url' called for URL: {str(document_url)}")
    if not document_url:
        raise ValueError("Document URL (document_url) is required for Uyuşmazlık document retrieval.")
    try:
        return await uyusmazlik_client_instance.get_decision_document_as_markdown(str(document_url))
    except Exception as e:
        logger.exception(f"Error in tool 'get_uyusmazlik_document_markdown_from_url'.")
        raise

# --- MCP Tools for Anayasa Mahkemesi (Norm Denetimi) ---
@app.tool(
    description="Search Constitutional Court norm control decisions with comprehensive filtering and legal criteria. Before using, read docs://tools/constitutional_court",
    annotations={
        "readOnlyHint": True,
        "openWorldHint": True,
        "idempotentHint": True
    }
)
async def search_anayasa_norm_denetimi_decisions(
    keywords_all: List[str] = Field(default_factory=list, description="AND keywords"),
    keywords_any: List[str] = Field(default_factory=list, description="OR keywords"),
    keywords_exclude: List[str] = Field(default_factory=list, description="Exclude keywords"),
    period: Literal["ALL", "1", "2"] = Field("ALL", description="Period"),
    case_number_esas: Optional[str] = Field(None, description="Case number"),
    decision_number_karar: Optional[str] = Field(None, description="Decision number"),
    first_review_date_start: Optional[str] = Field(None, description="Review start date"),
    first_review_date_end: Optional[str] = Field(None, description="Review end date"),
    decision_date_start: Optional[str] = Field(None, description="Decision start"),
    decision_date_end: Optional[str] = Field(None, description="Decision end"),
    application_type: Literal["ALL", "1", "2", "3"] = Field("ALL", description="App type"),
    applicant_general_name: Optional[str] = Field(None, description="Applicant"),
    applicant_specific_name: Optional[str] = Field(None, description="Specific name"),
    official_gazette_date_start: Optional[str] = Field(None, description="Gazette start"),
    official_gazette_date_end: Optional[str] = Field(None, description="Gazette end"),
    official_gazette_number_start: Optional[str] = Field(None, description="Gazette no start"),
    official_gazette_number_end: Optional[str] = Field(None, description="Gazette no end"),
    has_press_release: Literal["ALL", "0", "1"] = Field("ALL", description="Press release"),
    has_dissenting_opinion: Literal["ALL", "0", "1"] = Field("ALL", description="Dissenting"),
    has_different_reasoning: Literal["ALL", "0", "1"] = Field("ALL", description="Different reason"),
    attending_members_names: List[str] = Field(default_factory=list, description="Members"),
    rapporteur_name: Optional[str] = Field(None, description="Rapporteur"),
    norm_type: Literal["ALL", "1", "2", "14", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "0", "13"] = Field("ALL", description="Norm type"),
    norm_id_or_name: Optional[str] = Field(None, description="Norm name"),
    norm_article: Optional[str] = Field(None, description="Article"),
    review_outcomes: List[Literal["ALL", "1", "2", "3", "4", "5", "6", "7", "8", "12"]] = Field(default_factory=list, description="Outcomes"),
    reason_for_final_outcome: Literal["ALL", "29", "1", "2", "30", "3", "4", "27", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15", "16", "17", "18", "19", "20", "21", "22", "23", "24", "25", "26"] = Field("ALL", description="Reason"),
    basis_constitution_article_numbers: List[str] = Field(default_factory=list, description="Articles"),
    results_per_page: int = Field(10, description="Count"),
    page_to_fetch: int = Field(1, ge=1, description="Page"),
    sort_by_criteria: str = Field("KararTarihi", description="Sort")
) -> AnayasaSearchResult:
    """Search Constitutional Court norm control decisions with comprehensive filtering."""
    
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

@app.tool(
    description="Retrieve full text of a Constitutional Court norm control decision in paginated Markdown format. Before using, read docs://tools/constitutional_court",
    annotations={
        "readOnlyHint": True,
        "idempotentHint": True
    }
)
async def get_anayasa_norm_denetimi_document_markdown(
    document_url: str = Field(..., description="The URL path (e.g., /ND/YYYY/NN) or full https URL of the AYM Norm Denetimi decision from normkararlarbilgibankasi.anayasa.gov.tr."),
    page_number: Optional[int] = Field(1, ge=1, description="Page number for paginated Markdown content (1-indexed, accepts int). Default is 1 (first 5,000 characters).")
) -> AnayasaDocumentMarkdown:
    """Get Constitutional Court norm control decision as paginated Markdown."""
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
@app.tool(
    description="Search Constitutional Court individual application decisions for human rights violation reports. Before using, read docs://tools/constitutional_court",
    annotations={
        "readOnlyHint": True,
        "openWorldHint": True,
        "idempotentHint": True
    }
)
async def search_anayasa_bireysel_basvuru_report(
    keywords: List[str] = Field(default_factory=list, description="Keywords for AND logic."),
    page_to_fetch: int = Field(1, ge=1, description="Page number to fetch for the report. Default is 1.")
) -> AnayasaBireyselReportSearchResult:
    """Search Constitutional Court individual application decisions."""
    
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

@app.tool(
    description="Parameter description",
    annotations={
        "readOnlyHint": True,
        "idempotentHint": True
    }
)
async def get_anayasa_bireysel_basvuru_document_markdown(
    document_url_path: str = Field(..., description="The URL path (e.g., /BB/YYYY/NNNN) of the AYM Bireysel Başvuru decision from kararlarbilgibankasi.anayasa.gov.tr."),
    page_number: Union[int, str] = Field(1, description="Page number for paginated Markdown content (1-indexed, accepts int). Default is 1 (first 5,000 characters).")
) -> AnayasaBireyselBasvuruDocumentMarkdown:
    """Get Constitutional Court individual application decision as paginated Markdown."""
    logger.info(f"Tool 'get_anayasa_bireysel_basvuru_document_markdown' called for URL path: {document_url_path}, Page: {page_number}")
    if not document_url_path or not document_url_path.strip() or not document_url_path.startswith("/BB/"):
        raise ValueError("Document URL path (e.g., /BB/YYYY/NNNN) is required for Anayasa Bireysel Başvuru document retrieval.")
    
    # Handle both int and string page_number inputs
    try:
        current_page_to_fetch = int(page_number) if page_number is not None else 1
        if current_page_to_fetch < 1:
            current_page_to_fetch = 1
    except (ValueError, TypeError):
        current_page_to_fetch = 1
    try:
        return await anayasa_bireysel_client_instance.get_decision_document_as_markdown(document_url_path, page_number=current_page_to_fetch)
    except Exception as e:
        logger.exception(f"Error in tool 'get_anayasa_bireysel_basvuru_document_markdown'.")
        raise

# --- MCP Tools for KIK (Kamu İhale Kurulu) ---
@app.tool(
    description="Search Public Procurement Authority (KİK) decisions for procurement law and administrative disputes. Before using, read docs://tools/kik",
    annotations={
        "readOnlyHint": True,
        "openWorldHint": True,
        "idempotentHint": True
    }
)
async def search_kik_decisions(
    karar_tipi: Literal["rbUyusmazlik", "rbDuzenleyici", "rbMahkeme"] = Field("rbUyusmazlik", description="Type of KIK Decision."),
    karar_no: Optional[str] = Field(None, description="Decision Number (e.g., '2024/UH.II-1766')."),
    karar_tarihi_baslangic: Optional[str] = Field(None, description="Decision Date Start (DD.MM.YYYY)."),
    karar_tarihi_bitis: Optional[str] = Field(None, description="Decision Date End (DD.MM.YYYY)."),
    basvuru_sahibi: Optional[str] = Field(None, description="Applicant."),
    ihaleyi_yapan_idare: Optional[str] = Field(None, description="Procuring Entity."),
    basvuru_konusu_ihale: Optional[str] = Field(None, description="Tender subject of the application."),
    karar_metni: Optional[str] = Field(None, description="""
        Keyword/phrase in decision text. Advanced search operators supported:
        - word1+word2 = AND logic (+anayasa +mahkeme -> both words required)
        - +"required" -"excluded" = Include and exclude (+ihale -"iptal")
        Examples: anayasa | +anayasa +mahkeme | +ihale -"iptal"
    """),
    yil: Optional[str] = Field(None, description="Year of the decision."),
    resmi_gazete_tarihi: Optional[str] = Field(None, description="Official Gazette Date (DD.MM.YYYY)."),
    resmi_gazete_sayisi: Optional[str] = Field(None, description="Official Gazette Number."),
    page: int = Field(1, ge=1, description="Results page number.")
) -> KikSearchResult:
    """Search Public Procurement Authority (KIK) decisions."""
    
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

@app.tool(
    description="Retrieve full text of a Public Procurement Authority (KİK) decision in paginated Markdown format. Before using, read docs://tools/kik",
    annotations={
        "readOnlyHint": True,
        "idempotentHint": True
    }
)
async def get_kik_document_markdown(
    karar_id: str = Field(..., description="The Base64 encoded KIK decision identifier."),
    page_number: Optional[int] = Field(1, ge=1, description="Page number for paginated Markdown content (1-indexed, accepts int). Default is 1.")
) -> KikDocumentMarkdown:
    """Get KIK decision as paginated Markdown."""
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
@app.tool(
    description="Search Competition Authority (Rekabet Kurumu) decisions for competition law and antitrust research. Before using, read docs://tools/rekabet",
    annotations={
        "readOnlyHint": True,
        "openWorldHint": True,
        "idempotentHint": True
    }
)
async def search_rekabet_kurumu_decisions(
    sayfaAdi: Optional[str] = Field(None, description="Search in decision title (Başlık)."),
    YayinlanmaTarihi: Optional[str] = Field(None, description="Publication date (Yayım Tarihi), e.g., DD.MM.YYYY."),
    PdfText: Optional[str] = Field(
        None,
        description='Search in decision text (Metin). For an exact phrase match, enclose the phrase in double quotes (e.g., "\\"vertical agreement\\" competition). The website indicates that using "" provides more precise results for phrases.'
    ),
    KararTuru: Literal[ 
        "ALL", 
        "Birleşme ve Devralma",
        "Diğer",
        "Menfi Tespit ve Muafiyet",
        "Özelleştirme",
        "Rekabet İhlali"
    ] = Field("ALL", description="Parameter description"),
    KararSayisi: Optional[str] = Field(None, description="Decision number (Karar Sayısı)."),
    KararTarihi: Optional[str] = Field(None, description="Decision date (Karar Tarihi), e.g., DD.MM.YYYY."),
    page: int = Field(1, ge=1, description="Page number to fetch for the results list.")
) -> RekabetSearchResult:
    """Search Competition Authority decisions."""
    
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

@app.tool(
    description="Retrieve full text of a Competition Authority decision in paginated Markdown format. Before using, read docs://tools/rekabet",
    annotations={
        "readOnlyHint": True,
        "idempotentHint": True
    }
)
async def get_rekabet_kurumu_document(
    karar_id: str = Field(..., description="GUID (kararId) of the Rekabet Kurumu decision. This ID is obtained from search results."),
    page_number: Optional[int] = Field(1, ge=1, description="Requested page number for the Markdown content converted from PDF (1-indexed, accepts int). Default is 1.")
) -> RekabetDocument:
    """Get Competition Authority decision as paginated Markdown."""
    logger.info(f"Tool 'get_rekabet_kurumu_document' called. Karar ID: {karar_id}, Markdown Page: {page_number}")
    
    current_page_to_fetch = page_number if page_number is not None and page_number >= 1 else 1
    
    try:
      
        return await rekabet_client_instance.get_decision_document(karar_id, page_number=current_page_to_fetch)
    except Exception as e:
        logger.exception(f"Error in tool 'get_rekabet_kurumu_document'. Karar ID: {karar_id}")
        raise 

# --- MCP Tools for Bedesten (Alternative Yargitay Search) ---
@app.tool(
    description="Search Yargıtay decisions using Bedesten API with chamber selection and date filtering. Before using, read docs://tools/yargitay",
    annotations={
        "readOnlyHint": True,
        "openWorldHint": True,
        "idempotentHint": True
    }
)
async def search_yargitay_bedesten(
    phrase: str = Field(..., description="Search phrase with advanced operators"),
    pageSize: int = Field(10, ge=1, le=10, description="Sayfa başına sonuç sayısı"),
    pageNumber: int = Field(1, ge=1, description="Sayfa numarası"),
    birimAdi: Optional[YargitayBirimEnum] = Field(None, description="See docs for details"),
    kararTarihiStart: Optional[str] = Field(None, description="Start date for filtering (ISO 8601 format)"),
    kararTarihiEnd: Optional[str] = Field(None, description="End date for filtering (ISO 8601 format)")
) -> dict:
    """Search function for legal decisions."""
    search_data = BedestenSearchData(
        pageSize=pageSize,
        pageNumber=pageNumber,
        itemTypeList=["YARGITAYKARARI"],  # Only Yargıtay decisions
        phrase=phrase,
        birimAdi=birimAdi,
        kararTarihiStart=kararTarihiStart,
        kararTarihiEnd=kararTarihiEnd
    )
    
    search_request = BedestenSearchRequest(data=search_data)
    
    logger.info(f"Tool 'search_yargitay_bedesten' called: phrase='{phrase}', birimAdi='{birimAdi}', dateRange='{kararTarihiStart}' to '{kararTarihiEnd}', page={pageNumber}")
    
    try:
        response = await bedesten_client_instance.search_documents(search_request)
        
        # Handle potential None data
        if response.data is None:
            return {
                "decisions": [],
                "total_records": 0,
                "requested_page": pageNumber,
                "page_size": pageSize,
                "error": "No data returned from Bedesten API"
            }
        
        # Return simplified response format
        return {
            "decisions": [d.model_dump() for d in response.data.emsalKararList],
            "total_records": response.data.total,
            "requested_page": pageNumber,
            "page_size": pageSize
        }
    except Exception as e:
        logger.exception("Error in tool 'search_yargitay_bedesten'")
        raise

@app.tool(
    description="Retrieve Yargıtay decision document from Bedesten API in Markdown format. Before using, read docs://tools/yargitay",
    annotations={
        "readOnlyHint": True,
        "openWorldHint": True,
        "idempotentHint": True
    }
)
async def get_yargitay_bedesten_document_markdown(
    documentId: str = Field(..., description="Document ID from Bedesten search results")
) -> BedestenDocumentMarkdown:
    """Get document as Markdown."""
    logger.info(f"Tool 'get_yargitay_bedesten_document_markdown' called for ID: {documentId}")
    
    if not documentId or not documentId.strip():
        raise ValueError("Document ID must be a non-empty string.")
    
    try:
        return await bedesten_client_instance.get_document_as_markdown(documentId)
    except Exception as e:
        logger.exception("Error in tool 'get_yargitay_bedesten_document_markdown'")
        raise

# --- MCP Tools for Bedesten (Alternative Danıştay Search) ---
@app.tool(
    description="Search Danıştay decisions using Bedesten API with chamber selection and date filtering. Before using, read docs://tools/danistay",
    annotations={
        "readOnlyHint": True,
        "openWorldHint": True,
        "idempotentHint": True
    }
)
async def search_danistay_bedesten(
    phrase: str = Field(..., description="Search phrase with advanced operators"),
    pageSize: int = Field(10, ge=1, le=10, description="Sayfa başına sonuç sayısı"),
    pageNumber: int = Field(1, ge=1, description="Sayfa numarası"),
    birimAdi: Optional[DanistayBirimEnum] = Field(None, description="See docs for details"),
    kararTarihiStart: Optional[str] = Field(None, description="Start date for filtering (ISO 8601 format)"),
    kararTarihiEnd: Optional[str] = Field(None, description="End date for filtering (ISO 8601 format)")
) -> dict:
    """Search function for legal decisions."""
    search_data = BedestenSearchData(
        pageSize=pageSize,
        pageNumber=pageNumber,
        itemTypeList=["DANISTAYKARAR"],  # Only Danıştay decisions
        phrase=phrase,
        birimAdi=birimAdi,
        kararTarihiStart=kararTarihiStart,
        kararTarihiEnd=kararTarihiEnd
    )
    
    search_request = BedestenSearchRequest(data=search_data)
    
    logger.info(f"Tool 'search_danistay_bedesten' called: phrase='{phrase}', birimAdi='{birimAdi}', dateRange='{kararTarihiStart}' to '{kararTarihiEnd}', page={pageNumber}")
    
    try:
        response = await bedesten_client_instance.search_documents(search_request)
        
        # Handle potential None data
        if response.data is None:
            return {
                "decisions": [],
                "total_records": 0,
                "requested_page": pageNumber,
                "page_size": pageSize,
                "error": "No data returned from Bedesten API"
            }
        
        # Return simplified response format
        return {
            "decisions": [d.model_dump() for d in response.data.emsalKararList],
            "total_records": response.data.total,
            "requested_page": pageNumber,
            "page_size": pageSize
        }
    except Exception as e:
        logger.exception("Error in tool 'search_danistay_bedesten'")
        raise

@app.tool(
    description="Retrieve Danıştay decision document from Bedesten API in Markdown format. Before using, read docs://tools/danistay",
    annotations={
        "readOnlyHint": True,
        "openWorldHint": True,
        "idempotentHint": True
    }
)
async def get_danistay_bedesten_document_markdown(
    documentId: str = Field(..., description="Document ID from Bedesten search results")
) -> BedestenDocumentMarkdown:
    """Get document as Markdown."""
    logger.info(f"Tool 'get_danistay_bedesten_document_markdown' called for ID: {documentId}")
    
    if not documentId or not documentId.strip():
        raise ValueError("Document ID must be a non-empty string.")
    
    try:
        return await bedesten_client_instance.get_document_as_markdown(documentId)
    except Exception as e:
        logger.exception("Error in tool 'get_danistay_bedesten_document_markdown'")
        raise

# --- MCP Tools for Bedesten (Yerel Hukuk Mahkemesi Search) ---
@app.tool(
    description="Search Local Civil Courts (Yerel Hukuk Mahkemeleri) decisions using Bedesten API. Before using, read docs://tools/bedesten_api_courts",
    annotations={
        "readOnlyHint": True,
        "openWorldHint": True,
        "idempotentHint": True
    }
)
async def search_yerel_hukuk_bedesten(
    phrase: str = Field(..., description="Search phrase with advanced operators"),
    pageSize: int = Field(10, ge=1, le=10, description="Sayfa başına sonuç sayısı"),
    pageNumber: int = Field(1, ge=1, description="Sayfa numarası"),
    kararTarihiStart: Optional[str] = Field(None, description="Start date for filtering (ISO 8601 format)"),
    kararTarihiEnd: Optional[str] = Field(None, description="End date for filtering (ISO 8601 format)")
) -> dict:
    """Search Local Civil Court decisions using Bedesten API."""
    search_data = BedestenSearchData(
        pageSize=pageSize,
        pageNumber=pageNumber,
        itemTypeList=["YERELHUKUK"],  # Local Civil Court decisions
        phrase=phrase,
        kararTarihiStart=kararTarihiStart,
        kararTarihiEnd=kararTarihiEnd
    )
    
    search_request = BedestenSearchRequest(data=search_data)
    
    logger.info(f"Tool 'search_yerel_hukuk_bedesten' called: phrase='{phrase}', dateRange='{kararTarihiStart}' to '{kararTarihiEnd}', page={pageNumber}")
    
    try:
        response = await bedesten_client_instance.search_documents(search_request)
        
        # Handle potential None data
        if response.data is None:
            return {
                "decisions": [],
                "total_records": 0,
                "requested_page": pageNumber,
                "page_size": pageSize,
                "error": "No data returned from Bedesten API"
            }
        
        # Return simplified response format
        return {
            "decisions": [d.model_dump() for d in response.data.emsalKararList],
            "total_records": response.data.total,
            "requested_page": pageNumber,
            "page_size": pageSize
        }
    except Exception as e:
        logger.exception("Error in tool 'search_yerel_hukuk_bedesten'")
        raise

@app.tool(
    description="Retrieve local civil court decision document from Bedesten API in Markdown format. Before using, read docs://tools/bedesten_api_courts",
    annotations={
        "readOnlyHint": True,
        "openWorldHint": True,
        "idempotentHint": True
    }
)
async def get_yerel_hukuk_bedesten_document_markdown(
    documentId: str = Field(..., description="Document ID from Bedesten search results")
) -> BedestenDocumentMarkdown:
    """Get Local Civil Court decision as Markdown."""
    logger.info(f"Tool 'get_yerel_hukuk_bedesten_document_markdown' called for ID: {documentId}")
    
    if not documentId or not documentId.strip():
        raise ValueError("Document ID must be a non-empty string.")
    
    try:
        return await bedesten_client_instance.get_document_as_markdown(documentId)
    except Exception as e:
        logger.exception("Error in tool 'get_yerel_hukuk_bedesten_document_markdown'")
        raise

# --- MCP Tools for Bedesten (İstinaf Hukuk Mahkemesi Search) ---
@app.tool(
    description="Search Civil Courts of Appeals (İstinaf Hukuk Mahkemeleri) decisions using Bedesten API. Before using, read docs://tools/bedesten_api_courts",
    annotations={
        "readOnlyHint": True,
        "openWorldHint": True,
        "idempotentHint": True
    }
)
async def search_istinaf_hukuk_bedesten(
    phrase: str = Field(..., description="Search phrase with advanced operators"),
    pageSize: int = Field(10, ge=1, le=10, description="Sayfa başına sonuç sayısı"),
    pageNumber: int = Field(1, ge=1, description="Sayfa numarası"),
    kararTarihiStart: Optional[str] = Field(None, description="Start date for filtering (ISO 8601 format)"),
    kararTarihiEnd: Optional[str] = Field(None, description="End date for filtering (ISO 8601 format)")
) -> dict:
    """Search Civil Court of Appeals decisions using Bedesten API."""
    search_data = BedestenSearchData(
        pageSize=pageSize,
        pageNumber=pageNumber,
        itemTypeList=["ISTINAFHUKUK"],  # Civil Court of Appeals decisions
        phrase=phrase,
        kararTarihiStart=kararTarihiStart,
        kararTarihiEnd=kararTarihiEnd
    )
    
    search_request = BedestenSearchRequest(data=search_data)
    
    logger.info(f"Tool 'search_istinaf_hukuk_bedesten' called: phrase='{phrase}', dateRange='{kararTarihiStart}' to '{kararTarihiEnd}', page={pageNumber}")
    
    try:
        response = await bedesten_client_instance.search_documents(search_request)
        
        # Handle potential None data
        if response.data is None:
            return {
                "decisions": [],
                "total_records": 0,
                "requested_page": pageNumber,
                "page_size": pageSize,
                "error": "No data returned from Bedesten API"
            }
        
        # Return simplified response format
        return {
            "decisions": [d.model_dump() for d in response.data.emsalKararList],
            "total_records": response.data.total,
            "requested_page": pageNumber,
            "page_size": pageSize
        }
    except Exception as e:
        logger.exception("Error in tool 'search_istinaf_hukuk_bedesten'")
        raise

@app.tool(
    description="Retrieve İstinaf Hukuk Mahkemesi decision document from Bedesten API in Markdown format. Before using, read docs://tools/bedesten_api_courts",
    annotations={
        "readOnlyHint": True,
        "idempotentHint": True
    }
)
async def get_istinaf_hukuk_bedesten_document_markdown(
    documentId: str = Field(..., description="Document ID from Bedesten search results")
) -> BedestenDocumentMarkdown:
    """Get Civil Court of Appeals decision as Markdown."""
    logger.info(f"Tool 'get_istinaf_hukuk_bedesten_document_markdown' called for ID: {documentId}")
    
    if not documentId or not documentId.strip():
        raise ValueError("Document ID must be a non-empty string.")
    
    try:
        return await bedesten_client_instance.get_document_as_markdown(documentId)
    except Exception as e:
        logger.exception("Error in tool 'get_istinaf_hukuk_bedesten_document_markdown'")
        raise

# --- MCP Tools for Bedesten (Kanun Yararına Bozma Search) ---
@app.tool(
    description="Search Extraordinary Appeal (Kanun Yararına Bozma - KYB) decisions using Bedesten API. Before using, read docs://tools/bedesten_api_courts",
    annotations={
        "readOnlyHint": True,
        "openWorldHint": True,
        "idempotentHint": True
    }
)
async def search_kyb_bedesten(
    phrase: str = Field(..., description="Search phrase with advanced operators"),
    pageSize: int = Field(10, ge=1, le=10, description="Sayfa başına sonuç sayısı"),
    pageNumber: int = Field(1, ge=1, description="Sayfa numarası"),
    kararTarihiStart: Optional[str] = Field(None, description="Start date for filtering (ISO 8601 format)"),
    kararTarihiEnd: Optional[str] = Field(None, description="End date for filtering (ISO 8601 format)")
) -> dict:
    """Search Extraordinary Appeal (KYB) decisions using Bedesten API."""
    search_data = BedestenSearchData(
        pageSize=pageSize,
        pageNumber=pageNumber,
        itemTypeList=["KYB"],  # Kanun Yararına Bozma decisions
        phrase=phrase,
        kararTarihiStart=kararTarihiStart,
        kararTarihiEnd=kararTarihiEnd
    )
    
    search_request = BedestenSearchRequest(data=search_data)
    
    logger.info(f"Tool 'search_kyb_bedesten' called: phrase='{phrase}', dateRange='{kararTarihiStart}' to '{kararTarihiEnd}', page={pageNumber}")
    
    try:
        response = await bedesten_client_instance.search_documents(search_request)
        
        # Handle potential None data
        if response.data is None:
            return {
                "decisions": [],
                "total_records": 0,
                "requested_page": pageNumber,
                "page_size": pageSize,
                "error": "No data returned from Bedesten API"
            }
        
        # Return simplified response format
        return {
            "decisions": [d.model_dump() for d in response.data.emsalKararList],
            "total_records": response.data.total,
            "requested_page": pageNumber,
            "page_size": pageSize
        }
    except Exception as e:
        logger.exception("Error in tool 'search_kyb_bedesten'")
        raise

@app.tool(
    description="Retrieve Kanun Yararına Bozma (KYB) decision document from Bedesten API in Markdown format. Before using, read docs://tools/bedesten_api_courts",
    annotations={
        "readOnlyHint": True,
        "idempotentHint": True
    }
)
async def get_kyb_bedesten_document_markdown(
    documentId: str = Field(..., description="Document ID from Bedesten search results")
) -> BedestenDocumentMarkdown:
    """Get Extraordinary Appeal (KYB) decision as Markdown."""
    logger.info(f"Tool 'get_kyb_bedesten_document_markdown' called for ID: {documentId}")
    
    if not documentId or not documentId.strip():
        raise ValueError("Document ID must be a non-empty string.")
    
    try:
        return await bedesten_client_instance.get_document_as_markdown(documentId)
    except Exception as e:
        logger.exception("Error in tool 'get_kyb_bedesten_document_markdown'")
        raise

# --- MCP Tools for Sayıştay (Turkish Court of Accounts) ---

@app.tool(
    description="Search Sayıştay Genel Kurul decisions for audit and accountability regulations. Before using, read docs://tools/sayistay",
    annotations={
        "readOnlyHint": True,
        "openWorldHint": True,
        "idempotentHint": True
    }
)
async def search_sayistay_genel_kurul(
    karar_no: Optional[str] = Field(None, description="Decision number to search for (e.g., '5415')"),
    karar_ek: Optional[str] = Field(None, description="Decision appendix number (max 99, e.g., '1')"),
    karar_tarih_baslangic: Optional[str] = Field(None, description="See docs for details"),
    karar_tarih_bitis: Optional[str] = Field(None, description="See docs for details"),
    karar_tamami: Optional[str] = Field(None, description="See docs for details"),
    start: int = Field(0, description="Starting record for pagination (0-based)"),
    length: int = Field(10, description="Number of records per page (1-100)")
) -> GenelKurulSearchResponse:
    """Search Sayıştay General Assembly decisions."""
    logger.info(f"Tool 'search_sayistay_genel_kurul' called with params: karar_no={karar_no}, karar_ek={karar_ek}, date_range={karar_tarih_baslangic}-{karar_tarih_bitis}, content={karar_tamami}")
    
    try:
        search_request = GenelKurulSearchRequest(
            karar_no=karar_no,
            karar_ek=karar_ek,
            karar_tarih_baslangic=karar_tarih_baslangic,
            karar_tarih_bitis=karar_tarih_bitis,
            karar_tamami=karar_tamami,
            start=start,
            length=length
        )
        return await sayistay_client_instance.search_genel_kurul_decisions(search_request)
    except Exception as e:
        logger.exception("Error in tool 'search_sayistay_genel_kurul'")
        raise

@app.tool(
    description="Search Sayıştay Temyiz Kurulu decisions with chamber filtering and comprehensive search criteria. Before using, read docs://tools/sayistay",
    annotations={
        "readOnlyHint": True,
        "openWorldHint": True,
        "idempotentHint": True
    }
)
async def search_sayistay_temyiz_kurulu(
    ilam_dairesi: DaireEnum = Field("ALL", description="See docs for details"),
    yili: Optional[str] = Field(None, description="See docs for details"),
    karar_tarih_baslangic: Optional[str] = Field(None, description="See docs for details"),
    karar_tarih_bitis: Optional[str] = Field(None, description="See docs for details"),
    kamu_idaresi_turu: KamuIdaresiTuruEnum = Field("ALL", description="See docs for details"),
    ilam_no: Optional[str] = Field(None, description="Audit report number (İlam No, max 50 chars)"),
    dosya_no: Optional[str] = Field(None, description="File number for the case"),
    temyiz_tutanak_no: Optional[str] = Field(None, description="Appeals board meeting minutes number"),
    temyiz_karar: Optional[str] = Field(None, description="See docs for details"),
    web_karar_konusu: WebKararKonusuEnum = Field("ALL", description="See docs for details"),
    start: int = Field(0, description="Starting record for pagination (0-based)"),
    length: int = Field(10, description="Number of records per page (1-100)")
) -> TemyizKuruluSearchResponse:
    """Search Sayıştay Appeals Board decisions."""
    logger.info(f"Tool 'search_sayistay_temyiz_kurulu' called with params: chamber={ilam_dairesi}, year={yili}, admin_type={kamu_idaresi_turu}, subject={web_karar_konusu}")
    
    try:
        search_request = TemyizKuruluSearchRequest(
            ilam_dairesi=ilam_dairesi,
            yili=yili,
            karar_tarih_baslangic=karar_tarih_baslangic,
            karar_tarih_bitis=karar_tarih_bitis,
            kamu_idaresi_turu=kamu_idaresi_turu,
            ilam_no=ilam_no,
            dosya_no=dosya_no,
            temyiz_tutanak_no=temyiz_tutanak_no,
            temyiz_karar=temyiz_karar,
            web_karar_konusu=web_karar_konusu,
            start=start,
            length=length
        )
        return await sayistay_client_instance.search_temyiz_kurulu_decisions(search_request)
    except Exception as e:
        logger.exception("Error in tool 'search_sayistay_temyiz_kurulu'")
        raise

@app.tool(
    description="Search Sayıştay Daire decisions with chamber filtering and subject categorization. Before using, read docs://tools/sayistay",
    annotations={
        "readOnlyHint": True,
        "openWorldHint": True,
        "idempotentHint": True
    }
)
async def search_sayistay_daire(
    yargilama_dairesi: DaireEnum = Field("ALL", description="See docs for details"),
    karar_tarih_baslangic: Optional[str] = Field(None, description="See docs for details"),
    karar_tarih_bitis: Optional[str] = Field(None, description="See docs for details"),
    ilam_no: Optional[str] = Field(None, description="Audit report number (İlam No, max 50 chars)"),
    kamu_idaresi_turu: KamuIdaresiTuruEnum = Field("ALL", description="See docs for details"),
    hesap_yili: Optional[str] = Field(None, description="See docs for details"),
    web_karar_konusu: WebKararKonusuEnum = Field("ALL", description="See docs for details"),
    web_karar_metni: Optional[str] = Field(None, description="See docs for details"),
    start: int = Field(0, description="Starting record for pagination (0-based)"),
    length: int = Field(10, description="Number of records per page (1-100)")
) -> DaireSearchResponse:
    """Search Sayıştay Chamber decisions."""
    logger.info(f"Tool 'search_sayistay_daire' called with params: chamber={yargilama_dairesi}, admin_type={kamu_idaresi_turu}, subject={web_karar_konusu}, content={web_karar_metni}")
    
    try:
        search_request = DaireSearchRequest(
            yargilama_dairesi=yargilama_dairesi,
            karar_tarih_baslangic=karar_tarih_baslangic,
            karar_tarih_bitis=karar_tarih_bitis,
            ilam_no=ilam_no,
            kamu_idaresi_turu=kamu_idaresi_turu,
            hesap_yili=hesap_yili,
            web_karar_konusu=web_karar_konusu,
            web_karar_metni=web_karar_metni,
            start=start,
            length=length
        )
        return await sayistay_client_instance.search_daire_decisions(search_request)
    except Exception as e:
        logger.exception("Error in tool 'search_sayistay_daire'")
        raise

@app.tool(
    description="Retrieve Sayıştay Genel Kurul decision document in Markdown format. Before using, read docs://tools/sayistay",
    annotations={
        "readOnlyHint": True,
        "openWorldHint": False,
        "idempotentHint": True
    }
)
async def get_sayistay_genel_kurul_document_markdown(
    decision_id: str = Field(..., description="Decision ID from search_sayistay_genel_kurul results")
) -> SayistayDocumentMarkdown:
    """Get Sayıştay General Assembly decision as Markdown."""
    logger.info(f"Tool 'get_sayistay_genel_kurul_document_markdown' called for ID: {decision_id}")
    
    if not decision_id or not decision_id.strip():
        raise ValueError("Decision ID must be a non-empty string.")
    
    try:
        return await sayistay_client_instance.get_document_as_markdown(decision_id, "genel_kurul")
    except Exception as e:
        logger.exception("Error in tool 'get_sayistay_genel_kurul_document_markdown'")
        raise

@app.tool(
    description="Retrieve Sayıştay Temyiz Kurulu decision document in Markdown format. Before using, read docs://tools/sayistay",
    annotations={
        "readOnlyHint": True,
        "openWorldHint": False,
        "idempotentHint": True
    }
)
async def get_sayistay_temyiz_kurulu_document_markdown(
    decision_id: str = Field(..., description="Decision ID from search_sayistay_temyiz_kurulu results")
) -> SayistayDocumentMarkdown:
    """Get Sayıştay Appeals Board decision as Markdown."""
    logger.info(f"Tool 'get_sayistay_temyiz_kurulu_document_markdown' called for ID: {decision_id}")
    
    if not decision_id or not decision_id.strip():
        raise ValueError("Decision ID must be a non-empty string.")
    
    try:
        return await sayistay_client_instance.get_document_as_markdown(decision_id, "temyiz_kurulu")
    except Exception as e:
        logger.exception("Error in tool 'get_sayistay_temyiz_kurulu_document_markdown'")
        raise

@app.tool(
    description="Retrieve Sayıştay Daire decision document in Markdown format. Before using, read docs://tools/sayistay",
    annotations={
        "readOnlyHint": True,
        "openWorldHint": False,
        "idempotentHint": True
    }
)
async def get_sayistay_daire_document_markdown(
    decision_id: str = Field(..., description="Decision ID from search_sayistay_daire results")
) -> SayistayDocumentMarkdown:
    """Get Sayıştay Chamber decision as Markdown."""
    logger.info(f"Tool 'get_sayistay_daire_document_markdown' called for ID: {decision_id}")
    
    if not decision_id or not decision_id.strip():
        raise ValueError("Decision ID must be a non-empty string.")
    
    try:
        return await sayistay_client_instance.get_document_as_markdown(decision_id, "daire")
    except Exception as e:
        logger.exception("Error in tool 'get_sayistay_daire_document_markdown'")
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
        globals().get('rekabet_client_instance'),
        globals().get('bedesten_client_instance'),
        globals().get('sayistay_client_instance'),
        globals().get('kvkk_client_instance')
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

# --- Health Check Tools ---
@app.tool(
    description="Check if Turkish government legal database servers are operational",
    annotations={
        "readOnlyHint": True,
        "idempotentHint": True
    }
)
async def check_government_servers_health() -> Dict[str, Any]:
    """Check health status of Turkish government legal database servers."""
    logger.info("Health check tool called for government servers")
    
    health_results = {}
    
    # Check Yargıtay server
    try:
        yargitay_payload = {
            "data": {
                "aranan": "karar",
                "arananKelime": "karar", 
                "pageSize": 10,
                "pageNumber": 1
            }
        }
        
        async with httpx.AsyncClient(
            headers={
                "Accept": "*/*",
                "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
                "Connection": "keep-alive",
                "Content-Type": "application/json; charset=UTF-8",
                "Origin": "https://karararama.yargitay.gov.tr",
                "Referer": "https://karararama.yargitay.gov.tr/",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors", 
                "Sec-Fetch-Site": "same-origin",
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
                "X-Requested-With": "XMLHttpRequest"
            },
            timeout=30.0,
            verify=False
        ) as client:
            response = await client.post(
                "https://karararama.yargitay.gov.tr/aramalist",
                json=yargitay_payload
            )
            
            if response.status_code == 200:
                response_data = response.json()
                records_total = response_data.get("data", {}).get("recordsTotal", 0)
                
                if records_total > 0:
                    health_results["yargitay"] = {
                        "status": "healthy",
                        "records_total": records_total,
                        "response_time_ms": response.elapsed.total_seconds() * 1000
                    }
                else:
                    health_results["yargitay"] = {
                        "status": "unhealthy",
                        "reason": "recordsTotal is 0 or missing",
                        "response_time_ms": response.elapsed.total_seconds() * 1000
                    }
            else:
                health_results["yargitay"] = {
                    "status": "unhealthy", 
                    "reason": f"HTTP {response.status_code}",
                    "response_time_ms": response.elapsed.total_seconds() * 1000
                }
                
    except Exception as e:
        health_results["yargitay"] = {
            "status": "unhealthy",
            "reason": f"Connection error: {str(e)}"
        }
    
    # Check Bedesten API server
    try:
        bedesten_payload = {
            "phrase": "karar",
            "itemTypeList": ["YARGITAYKARARI"], 
            "pageSize": 5,
            "page": 1
        }
        
        async with httpx.AsyncClient(
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "Mozilla/5.0 Health Check"
            },
            timeout=30.0,
            verify=False
        ) as client:
            response = await client.post(
                "https://bedesten.adalet.gov.tr/api/search",
                json=bedesten_payload
            )
            
            if response.status_code == 200:
                response_data = response.json()
                total_found = response_data.get("totalFound", 0)
                
                if total_found > 0:
                    health_results["bedesten"] = {
                        "status": "healthy", 
                        "total_found": total_found,
                        "response_time_ms": response.elapsed.total_seconds() * 1000
                    }
                else:
                    health_results["bedesten"] = {
                        "status": "unhealthy",
                        "reason": "totalFound is 0 or missing",
                        "response_time_ms": response.elapsed.total_seconds() * 1000
                    }
            else:
                health_results["bedesten"] = {
                    "status": "unhealthy",
                    "reason": f"HTTP {response.status_code}",
                    "response_time_ms": response.elapsed.total_seconds() * 1000
                }
                
    except Exception as e:
        health_results["bedesten"] = {
            "status": "unhealthy", 
            "reason": f"Connection error: {str(e)}"
        }
    
    # Overall health assessment
    healthy_servers = sum(1 for server in health_results.values() if server["status"] == "healthy")
    total_servers = len(health_results)
    
    overall_status = "healthy" if healthy_servers == total_servers else "degraded" if healthy_servers > 0 else "unhealthy"
    
    return {
        "overall_status": overall_status,
        "healthy_servers": healthy_servers,
        "total_servers": total_servers,
        "servers": health_results,
        "check_timestamp": f"{__import__('datetime').datetime.now().isoformat()}"
    }

# --- MCP Tools for KVKK ---
@app.tool(
    description="Search KVKK decisions using Brave Search API for data protection authority decisions. Before using, read docs://tools/kvkk",
    annotations={
        "readOnlyHint": True,
        "openWorldHint": True,
        "idempotentHint": True
    }
)
async def search_kvkk_decisions(
    keywords: str = Field(..., description="Turkish keywords for KVKK decision search"),
    page: int = Field(1, ge=1, le=50, description="Page number for results (1-50)."),
    pageSize: int = Field(10, ge=1, le=20, description="Number of results per page (1-20).")
) -> KvkkSearchResult:
    """Search function for legal decisions."""
    logger.info(f"KVKK search tool called with keywords: {keywords}")
    
    search_request = KvkkSearchRequest(
        keywords=keywords,
        page=page,
        pageSize=pageSize
    )
    
    try:
        result = await kvkk_client_instance.search_decisions(search_request)
        logger.info(f"KVKK search completed. Found {len(result.decisions)} decisions on page {page}")
        return result
    except Exception as e:
        logger.exception(f"Error in KVKK search: {e}")
        # Return empty result on error
        return KvkkSearchResult(
            decisions=[],
            total_results=0,
            page=page,
            pageSize=pageSize,
            query=keywords
        )

@app.tool(
    description="Retrieve KVKK decision document in Markdown format with metadata extraction. Before using, read docs://tools/kvkk",
    annotations={
        "readOnlyHint": True,
        "openWorldHint": False,
        "idempotentHint": True
    }
)
async def get_kvkk_document_markdown(
    decision_url: str = Field(..., description="See docs for details"),
    page_number: Union[int, str] = Field(1, description="Page number for paginated Markdown content (1-indexed, accepts int). Default is 1 (first 5,000 characters).")
) -> KvkkDocumentMarkdown:
    """Get KVKK decision as paginated Markdown."""
    logger.info(f"KVKK document retrieval tool called for URL: {decision_url}")
    
    # Handle page_number type conversion (Union[int, str] -> int)
    if isinstance(page_number, str):
        try:
            page_number = int(page_number)
        except ValueError:
            logger.warning(f"Invalid page_number string '{page_number}', defaulting to 1")
            page_number = 1
    
    if not decision_url or not decision_url.strip():
        return KvkkDocumentMarkdown(
            source_url=HttpUrl("https://www.kvkk.gov.tr"),
            title=None,
            decision_date=None,
            decision_number=None,
            subject_summary=None,
            markdown_chunk=None,
            current_page=page_number or 1,
            total_pages=0,
            is_paginated=False,
            error_message="Decision URL is required and cannot be empty."
        )
    
    try:
        # Validate URL format
        if not decision_url.startswith("https://www.kvkk.gov.tr/"):
            return KvkkDocumentMarkdown(
                source_url=HttpUrl(decision_url),
                title=None,
                decision_date=None,
                decision_number=None,
                subject_summary=None,
                markdown_chunk=None,
                current_page=page_number or 1,
                total_pages=0,
                is_paginated=False,
                error_message="Invalid KVKK decision URL format. URL must start with https://www.kvkk.gov.tr/"
            )
        
        result = await kvkk_client_instance.get_decision_document(decision_url, page_number or 1)
        logger.info(f"KVKK document retrieved successfully. Page {result.current_page}/{result.total_pages}, Content length: {len(result.markdown_chunk) if result.markdown_chunk else 0}")
        return result
        
    except Exception as e:
        logger.exception(f"Error retrieving KVKK document: {e}")
        return KvkkDocumentMarkdown(
            source_url=HttpUrl(decision_url),
            title=None,
            decision_date=None,
            decision_number=None,
            subject_summary=None,
            markdown_chunk=None,
            current_page=page_number or 1,
            total_pages=0,
            is_paginated=False,
            error_message=f"Error retrieving KVKK document: {str(e)}"
        )

# --- ChatGPT Deep Research Compatible Tools ---

def get_preview_text(markdown_content: str, skip_chars: int = 100, preview_chars: int = 200) -> str:
    """
    Extract a preview of document text by skipping headers and showing meaningful content.
    
    Args:
        markdown_content: Full document content in markdown format
        skip_chars: Number of characters to skip from the beginning (default: 100)
        preview_chars: Number of characters to show in preview (default: 200)
    
    Returns:
        Preview text suitable for ChatGPT Deep Research
    """
    if not markdown_content:
        return ""
    
    # Remove common markdown artifacts and clean up
    cleaned_content = markdown_content.strip()
    
    # Skip the first N characters (usually headers, metadata)
    if len(cleaned_content) > skip_chars:
        content_start = cleaned_content[skip_chars:]
    else:
        content_start = cleaned_content
    
    # Get the next N characters for preview
    if len(content_start) > preview_chars:
        preview = content_start[:preview_chars]
    else:
        preview = content_start
    
    # Clean up the preview - remove incomplete sentences at the end
    preview = preview.strip()
    
    # If preview ends mid-sentence, try to end at last complete sentence
    if preview and not preview.endswith('.'):
        last_period = preview.rfind('.')
        if last_period > 50:  # Only if there's a reasonable sentence
            preview = preview[:last_period + 1]
    
    # Add ellipsis if content was truncated
    if len(content_start) > preview_chars:
        preview += "..."
    
    return preview.strip()

@app.tool(
    description="DO NOT USE unless you are ChatGPT Deep Research. Search Turkish courts (Turkish keywords only). Supports: +term (must have), -term (exclude), \"exact phrase\", term1 OR term2",
    annotations={
        "readOnlyHint": True,
        "openWorldHint": True,
        "idempotentHint": True
    }
)
async def search(
    query: str = Field(..., description="Turkish search query")
) -> Dict[str, List[Dict[str, str]]]:
    """
    Bedesten API search tool for ChatGPT Deep Research compatibility.
    
    This tool searches Turkish legal databases via the unified Bedesten API.
    It supports advanced search operators and covers all major court types.
    
    USAGE RESTRICTION: Only for ChatGPT Deep Research workflows.
    For regular legal research, use specific court tools like search_yargitay_bedesten.
    
    Returns:
    Object with "results" field containing a list of documents with id, title, text preview, and url
    as required by ChatGPT Deep Research specification.
    """
    logger.info(f"ChatGPT Deep Research search tool called with query: {query}")
    
    results = []
    
    try:
        # Search all court types via unified Bedesten API
        court_types = [
            ("YARGITAYKARARI", "Yargıtay", "yargitay_bedesten"),
            ("DANISTAYKARAR", "Danıştay", "danistay_bedesten"), 
            ("YERELHUKUK", "Yerel Hukuk Mahkemesi", "yerel_hukuk_bedesten"),
            ("ISTINAFHUKUK", "İstinaf Hukuk Mahkemesi", "istinaf_hukuk_bedesten"),
            ("KYB", "Kanun Yararına Bozma", "kyb_bedesten")
        ]
        
        for item_type, court_name, id_prefix in court_types:
            try:
                search_results = await bedesten_client_instance.search_documents(
                    BedestenSearchRequest(
                        data=BedestenSearchData(
                            phrase=query,  # Use query as-is to support both regular and exact phrase searches
                            itemTypeList=[item_type],
                            pageSize=10,
                            pageNumber=1
                        )
                    )
                )
                
                # Handle potential None data
                if search_results.data is None:
                    logger.warning(f"No data returned from Bedesten API for {court_name}")
                    continue
                
                # Add results from this court type (limit to top 5 per court)
                for decision in search_results.data.emsalKararList[:5]:
                    # For ChatGPT Deep Research, fetch document content for preview
                    try:
                        # Fetch document content for preview
                        doc = await bedesten_client_instance.get_document_as_markdown(decision.documentId)
                        
                        # Generate preview text (skip first 100 chars, show next 200)
                        preview_text = get_preview_text(doc.markdown_content, skip_chars=100, preview_chars=200)
                        
                        # Build title from metadata
                        title_parts = []
                        if decision.birimAdi:
                            title_parts.append(decision.birimAdi)
                        if decision.esasNo:
                            title_parts.append(f"Esas: {decision.esasNo}")
                        if decision.kararNo:
                            title_parts.append(f"Karar: {decision.kararNo}")
                        if decision.kararTarihiStr:
                            title_parts.append(f"Tarih: {decision.kararTarihiStr}")
                        
                        if title_parts:
                            title = " - ".join(title_parts)
                        else:
                            title = f"{court_name} - Document {decision.documentId}"
                        
                        # Add to results in OpenAI format
                        results.append({
                            "id": decision.documentId,
                            "title": title,
                            "text": preview_text,
                            "url": f"https://mevzuat.adalet.gov.tr/ictihat/{decision.documentId}"
                        })
                        
                    except Exception as e:
                        logger.warning(f"Could not fetch preview for document {decision.documentId}: {e}")
                        # Add minimal result without preview
                        results.append({
                            "id": decision.documentId,
                            "title": f"{court_name} - Document {decision.documentId}",
                            "text": "Document preview not available",
                            "url": f"https://mevzuat.adalet.gov.tr/ictihat/{decision.documentId}"
                        })
                    
                if search_results.data:
                    logger.info(f"Found {len(search_results.data.emsalKararList)} results from {court_name}")
                else:
                    logger.info(f"Found 0 results from {court_name} (no data returned)")
                
            except Exception as e:
                logger.warning(f"Bedesten API search error for {court_name}: {e}")
        
        # Comment out other API implementations for ChatGPT Deep Research
        """
        # Other API implementations disabled for ChatGPT Deep Research
        # These are available through specific court tools:
        
        # Yargıtay Official API - use search_yargitay_detailed instead
        # Danıştay Official API - use search_danistay_by_keyword instead  
        # Constitutional Court - use search_anayasa_norm_denetimi_decisions instead
        # Competition Authority - use search_rekabet_kurumu_decisions instead
        # Public Procurement Authority - use search_kik_decisions instead
        # Court of Accounts - use search_sayistay_* tools instead
        # UYAP Emsal - use search_emsal_detailed_decisions instead
        # Jurisdictional Disputes Court - use search_uyusmazlik_decisions instead
        """
        
        logger.info(f"ChatGPT Deep Research search completed. Found {len(results)} results via Bedesten API.")
        return {"results": results}
        
    except Exception as e:
        logger.exception("Error in ChatGPT Deep Research search tool")
        # Return partial results if any were found
        if results:
            return {"results": results}
        raise

@app.tool(
    description="DO NOT USE unless you are ChatGPT Deep Research. Fetch document by ID. See docs for details",
    annotations={
        "readOnlyHint": True,
        "openWorldHint": False,  # Retrieves specific documents, not exploring
        "idempotentHint": True
    }
)
async def fetch(
    id: str = Field(..., description="Document identifier from search results (numeric only)")
) -> Dict[str, Any]:
    """
    Bedesten API fetch tool for ChatGPT Deep Research compatibility.
    
    Retrieves the full text content of Turkish legal documents via unified Bedesten API.
    Converts documents from HTML/PDF to clean Markdown format.
    
    USAGE RESTRICTION: Only for ChatGPT Deep Research workflows.
    For regular legal research, use specific court document tools.
    
    Input Format:
    - id: Numeric document identifier from search results (e.g., "730113500", "71370900")
    
    Returns:
    Single object with numeric id, title, text (full Markdown content), mevzuat.adalet.gov.tr url, and metadata fields
    as required by ChatGPT Deep Research specification.
    """
    logger.info(f"ChatGPT Deep Research fetch tool called for document ID: {id}")
    
    if not id or not id.strip():
        raise ValueError("Document ID must be a non-empty string")
    
    try:
        # Use the numeric ID directly with Bedesten API
        doc = await bedesten_client_instance.get_document_as_markdown(id)
        
        # Try to get additional metadata by searching for this specific document
        title = f"Turkish Legal Document {id}"
        try:
            # Quick search to get metadata for better title
            search_results = await bedesten_client_instance.search_documents(
                BedestenSearchRequest(
                    data=BedestenSearchData(
                        phrase=id,  # Search by document ID
                        pageSize=1,
                        pageNumber=1
                    )
                )
            )
            
            if search_results.data and search_results.data.emsalKararList:
                decision = search_results.data.emsalKararList[0]
                if decision.documentId == id:
                    # Build a proper title from metadata
                    title_parts = []
                    if decision.birimAdi:
                        title_parts.append(decision.birimAdi)
                    if decision.esasNo:
                        title_parts.append(f"Esas: {decision.esasNo}")
                    if decision.kararNo:
                        title_parts.append(f"Karar: {decision.kararNo}")
                    if decision.kararTarihiStr:
                        title_parts.append(f"Tarih: {decision.kararTarihiStr}")
                    
                    if title_parts:
                        title = " - ".join(title_parts)
                    else:
                        title = f"Turkish Legal Decision {id}"
        except Exception as e:
            logger.warning(f"Could not fetch metadata for document {id}: {e}")
        
        return {
            "id": id,
            "title": title,
            "text": doc.markdown_content,
            "url": f"https://mevzuat.adalet.gov.tr/ictihat/{id}",
            "metadata": {
                "database": "Turkish Legal Database via Bedesten API",
                "document_id": id,
                "source_url": doc.source_url,
                "mime_type": doc.mime_type,
                "api_source": "Bedesten Unified API",
                "chatgpt_deep_research": True
            }
        }
        
        # Comment out other API implementations for ChatGPT Deep Research
        """
        # Other API implementations disabled for ChatGPT Deep Research
        # These are available through specific court document tools:
        
        elif id.startswith("yargitay_"):
            # Yargıtay Official API - use get_yargitay_document_markdown instead
            doc_id = id.replace("yargitay_", "")
            doc = await yargitay_client_instance.get_decision_document_as_markdown(doc_id)
            
        elif id.startswith("danistay_"):
            # Danıştay Official API - use get_danistay_document_markdown instead
            doc_id = id.replace("danistay_", "")
            doc = await danistay_client_instance.get_decision_document_as_markdown(doc_id)
            
        elif id.startswith("anayasa_"):
            # Constitutional Court - use get_anayasa_norm_denetimi_document_markdown instead
            doc_id = id.replace("anayasa_", "")
            doc = await anayasa_norm_client_instance.get_decision_document_as_markdown(...)
            
        elif id.startswith("rekabet_"):
            # Competition Authority - use get_rekabet_kurumu_document instead
            doc_id = id.replace("rekabet_", "")
            doc = await rekabet_client_instance.get_decision_document(...)
            
        elif id.startswith("kik_"):
            # Public Procurement Authority - use get_kik_decision_document_as_markdown instead
            doc_id = id.replace("kik_", "")
            doc = await kik_client_instance.get_decision_document_as_markdown(doc_id)
            
        elif id.startswith("local_"):
            # This was already using Bedesten API, but deprecated for ChatGPT Deep Research
            doc_id = id.replace("local_", "")
            doc = await bedesten_client_instance.get_document_as_markdown(doc_id)
        """
        
    except Exception as e:
        logger.exception(f"Error fetching ChatGPT Deep Research document {id}")
        raise

def ensure_playwright_browsers():
    """Ensure Playwright browsers are installed for KIK tool functionality."""
    try:
        import subprocess
        import os
        
        # Check if chromium is already installed
        chromium_path = os.path.expanduser("~/Library/Caches/ms-playwright/chromium-1179")
        if os.path.exists(chromium_path):
            logger.info("Playwright Chromium browser already installed.")
            return
        
        logger.info("Installing Playwright Chromium browser for KIK tool...")
        result = subprocess.run(
            ["python", "-m", "playwright", "install", "chromium"],
            capture_output=True,
            text=True,
            timeout=300  # 5 minutes timeout
        )
        
        if result.returncode == 0:
            logger.info("Playwright Chromium browser installed successfully.")
        else:
            logger.warning(f"Failed to install Playwright browser: {result.stderr}")
            logger.warning("KIK tool may not work properly without Playwright browsers.")
            
    except Exception as e:
        logger.warning(f"Could not auto-install Playwright browsers: {e}")
        logger.warning("KIK tool may not work properly. Manual installation: 'playwright install chromium'")

def main():
    logger.info(f"Starting {app.name} server via main() function...")
    logger.info(f"Logs will be written to: {LOG_FILE_PATH}")
    
    # Ensure Playwright browsers are installed
    ensure_playwright_browsers()
    
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