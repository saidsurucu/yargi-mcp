# Yargı MCP: Türk Hukuk Kaynakları için MCP Sunucusu

[![Star History Chart](https://api.star-history.com/svg?repos=saidsurucu/yargi-mcp&type=Date)](https://www.star-history.com/#saidsurucu/yargi-mcp&Date)

Bu proje, çeşitli Türk hukuk kaynaklarına (Yargıtay, Danıştay, Emsal Kararlar, Uyuşmazlık Mahkemesi, Anayasa Mahkemesi - Norm Denetimi ile Bireysel Başvuru Kararları, Kamu İhale Kurulu Kararları ve Rekabet Kurumu Kararları) erişimi kolaylaştıran bir [FastMCP](https://gofastmcp.com/) sunucusu oluşturur. Bu sayede, bu kaynaklardan veri arama ve belge getirme işlemleri, Model Context Protocol (MCP) destekleyen LLM (Büyük Dil Modeli) uygulamaları (örneğin Claude Desktop veya [5ire](https://5ire.app)) ve diğer istemciler tarafından araç (tool) olarak kullanılabilir hale gelir.

![örnek](./ornek.png)

🎯 **Temel Özellikler**

* Çeşitli Türk hukuk veritabanlarına programatik erişim için standart bir MCP arayüzü.
* Aşağıdaki kurumların kararlarını arama ve getirme yeteneği:
    * **Yargıtay:** Detaylı kriterlerle karar arama ve karar metinlerini Markdown formatında getirme.
    * **Danıştay:** Anahtar kelime bazlı ve detaylı kriterlerle karar arama; karar metinlerini Markdown formatında getirme.
    * **Emsal (UYAP):** Detaylı kriterlerle emsal karar arama ve karar metinlerini Markdown formatında getirme.
    * **Uyuşmazlık Mahkemesi:** Form tabanlı kriterlerle karar arama ve karar metinlerini (URL ile erişilen) Markdown formatında getirme.
    * **Anayasa Mahkemesi (Norm Denetimi):** Kapsamlı kriterlerle norm denetimi kararlarını arama; uzun karar metinlerini (5.000 karakterlik) sayfalanmış Markdown formatında getirme.
    * **Anayasa Mahkemesi (Bireysel Başvuru):** Kapsamlı kriterlerle bireysel başvuru "Karar Arama Raporu" oluşturma ve listedeki kararların metinlerini (5.000 karakterlik) sayfalanmış Markdown formatında getirme.
    * **KİK (Kamu İhale Kurulu):** Çeşitli kriterlerle Kurul kararlarını arama; uzun karar metinlerini (varsayılan 5.000 karakterlik) sayfalanmış Markdown formatında getirme.
    * **Rekabet Kurumu:** Çeşitli kriterlerle Kurul kararlarını arama; karar metinlerini Markdown formatında getirme.

* Karar metinlerinin daha kolay işlenebilmesi için Markdown formatına çevrilmesi.
* Claude Desktop uygulaması ile `fastmcp install` komutu kullanılarak kolay entegrasyon.
* Yargı MCP artık [5ire](https://5ire.app) gibi Claude Desktop haricindeki MCP istemcilerini de destekliyor!
---
🚀 **Claude Haricindeki Modellerle Kullanmak İçin Çok Kolay Kurulum (Örnek: 5ire için)**

Bu bölüm, Yargı MCP aracını 5ire gibi Claude Desktop dışındaki MCP istemcileriyle kullanmak isteyenler içindir.

* **Python Kurulumu:** Sisteminizde Python 3.11 veya üzeri kurulu olmalıdır. Kurulum sırasında "**Add Python to PATH**" (Python'ı PATH'e ekle) seçeneğini işaretlemeyi unutmayın. [Buradan](https://www.python.org/downloads/) indirebilirsiniz.
* **Git Kurulumu (Windows):** Bilgisayarınıza [git](https://git-scm.com/downloads/win) yazılımını indirip kurun. "Git for Windows/x64 Setup" seçeneğini indirmelisiniz.
* **`uv` Kurulumu:**
    * **Windows Kullanıcıları (PowerShell):** Bir CMD ekranı açın ve bu kodu çalıştırın: `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`
    * **Mac/Linux Kullanıcıları (Terminal):** Bir Terminal ekranı açın ve bu kodu çalıştırın: `curl -LsSf https://astral.sh/uv/install.sh | sh`
* **Microsoft Visual C++ Redistributable (Windows):** Bazı Python paketlerinin doğru çalışması için gereklidir. [Buradan](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist?view=msvc-170) indirip kurun.
* İşletim sisteminize uygun [5ire](https://5ire.app) MCP istemcisini indirip kurun.
* 5ire'ı açın. **Workspace -> Providers** menüsünden kullanmak istediğiniz LLM servisinin API anahtarını girin.
* **Tools** menüsüne girin. **+Local** veya **New** yazan butona basın.
    * **Tool Key:** `yargimcp`
    * **Name:** `Yargı MCP`
    * **Command:**
        ```
        uvx --from git+https://github.com/saidsurucu/yargi-mcp yargi-mcp
        ```
    * **Save** butonuna basarak kaydedin.
![5ire ayarları](./5ire-settings.png)
* Şimdi **Tools** altında **Yargı MCP**'yi görüyor olmalısınız. Üstüne geldiğinizde sağda çıkan butona tıklayıp etkinleştirin (yeşil ışık yanmalı).
* Artık Yargı MCP ile konuşabilirsiniz.

### FastAPI Sunucusu

Araçlara doğrudan HTTP üzerinden erişmek için `fastapi_server.py` dosyasını çalıştırabilirsiniz:

```bash
uvicorn fastapi_server:app --reload
```

Bu sunucu, MCP araçlarını RESTful endpoint'ler olarak sunar. Örneğin Yargıtay karar araması için `/yargitay/search/detailed` adresine POST isteği gönderebilirsiniz.

---
⚙️ **Claude Desktop Manuel Kurulumu**


1.  **Ön Gereksinimler:** Python, `uv`, (Windows için) Microsoft Visual C++ Redistributable'ın sisteminizde kurulu olduğundan emin olun. Detaylı bilgi için yukarıdaki "5ire için Kurulum" bölümündeki ilgili adımlara bakabilirsiniz.
2.  Claude Desktop **Settings -> Developer -> Edit Config**.
3.  Açılan `claude_desktop_config.json` dosyasına `mcpServers` altına ekleyin:

    ```json
    {
      "mcpServers": {
        // ... (varsa diğer sunucularınız) ...
        "Yargı MCP": {
          "command": "uvx",
          "args": [
            "--from", "git+https://github.com/saidsurucu/yargi-mcp",
            "yargi-mcp"
          ]
        }
      }
    }
    ```
4.  Claude Desktop'ı kapatıp yeniden başlatın.

🛠️ **Kullanılabilir Araçlar (MCP Tools)**

Bu FastMCP sunucusu aşağıdaki temel araçları sunar:


* **Yargıtay Araçları:**
    * `search_yargitay_detailed(search_query: YargitayDetailedSearchRequest) -> CompactYargitaySearchResult`: Yargıtay kararlarını detaylı kriterlerle arar.
    * `get_yargitay_document_markdown(id: str) -> YargitayDocumentMarkdown`: Belirli bir Yargıtay kararının metnini Markdown formatında getirir.

* **Danıştay Araçları:**
    * `search_danistay_by_keyword(search_query: DanistayKeywordSearchRequest) -> CompactDanistaySearchResult`: Danıştay kararlarını anahtar kelimelerle arar.
    * `search_danistay_detailed(search_query: DanistayDetailedSearchRequest) -> CompactDanistaySearchResult`: Danıştay kararlarını detaylı kriterlerle arar.
    * `get_danistay_document_markdown(id: str) -> DanistayDocumentMarkdown`: Belirli bir Danıştay kararının metnini Markdown formatında getirir.

* **Emsal Karar Araçları:**
    * `search_emsal_detailed_decisions(search_query: EmsalSearchRequest) -> CompactEmsalSearchResult`: Emsal (UYAP) kararlarını detaylı kriterlerle arar.
    * `get_emsal_document_markdown(id: str) -> EmsalDocumentMarkdown`: Belirli bir Emsal kararının metnini Markdown formatında getirir.

* **Uyuşmazlık Mahkemesi Araçları:**
    * `search_uyusmazlik_decisions(search_params: UyusmazlikSearchRequest) -> UyusmazlikSearchResponse`: Uyuşmazlık Mahkemesi kararlarını çeşitli form kriterleriyle arar.
    * `get_uyusmazlik_document_markdown_from_url(document_url: HttpUrl) -> UyusmazlikDocumentMarkdown`: Bir Uyuşmazlık kararını tam URL'sinden alıp Markdown formatında getirir.

* **Anayasa Mahkemesi (Norm Denetimi) Araçları:**
    * `search_anayasa_norm_denetimi_decisions(search_query: AnayasaNormDenetimiSearchRequest) -> AnayasaSearchResult`: AYM Norm Denetimi kararlarını kapsamlı kriterlerle arar.
    * `get_anayasa_norm_denetimi_document_markdown(document_url: str, page_number: Optional[int] = 1) -> AnayasaDocumentMarkdown`: Belirli bir AYM Norm Denetimi kararını URL'sinden alır ve 5.000 karakterlik sayfalanmış Markdown içeriğini getirir.

* **Anayasa Mahkemesi (Bireysel Başvuru) Araçları:**
    * `search_anayasa_bireysel_basvuru_report(search_query: AnayasaBireyselReportSearchRequest) -> AnayasaBireyselReportSearchResult`: AYM Bireysel Başvuru "Karar Arama Raporu" oluşturur.
    * `get_anayasa_bireysel_basvuru_document_markdown(document_url_path: str, page_number: Optional[int] = 1) -> AnayasaBireyselBasvuruDocumentMarkdown`: Belirli bir AYM Bireysel Başvuru kararını URL path'inden alır ve 5.000 karakterlik sayfalanmış Markdown içeriğini getirir.

* **KİK (Kamu İhale Kurulu) Araçları:**
    * `search_kik_decisions(search_query: KikSearchRequest) -> KikSearchResult`: KİK (Kamu İhale Kurulu) kararlarını arar. 
    * `get_kik_document_markdown(karar_id: str, page_number: Optional[int] = 1) -> KikDocumentMarkdown`: Belirli bir KİK kararını, Base64 ile encode edilmiş `karar_id`'sini kullanarak alır ve 5.000 karakterlik sayfalanmış Markdown içeriğini getirir.
* **Rekabet Kurumu Araçları:**
    * `search_rekabet_kurumu_decisions(KararTuru: Literal[...], ...) -> RekabetSearchResult`: Rekabet Kurumu kararlarını arar. `KararTuru` için kullanıcı dostu isimler kullanılır (örn: "Birleşme ve Devralma").
    * `get_rekabet_kurumu_document(karar_id: str, page_number: Optional[int] = 1) -> RekabetDocument`: Belirli bir Rekabet Kurumu kararını `karar_id` ile alır. Kararın PDF formatındaki orijinalinden istenen sayfayı ayıklar ve Markdown formatında döndürür.


📜 **Lisans**

Bu proje MIT Lisansı altında lisanslanmıştır. Detaylar için `LICENSE` dosyasına bakınız.
