# Yargı MCP: Türk Hukuk Kaynakları için MCP Sunucusu

[![Star History Chart](https://api.star-history.com/svg?repos=saidsurucu/yargi-mcp&type=Date)](https://www.star-history.com/#saidsurucu/yargi-mcp&Date)

Bu proje, çeşitli Türk hukuk kaynaklarına (Yargıtay, Danıştay, Emsal Kararlar, Uyuşmazlık Mahkemesi, Anayasa Mahkemesi - Norm Denetimi ile Bireysel Başvuru Kararları ve Kamu İhale Kurulu Kararları) erişimi kolaylaştıran bir [FastMCP](https://gofastmcp.com/) sunucusu oluşturur. Bu sayede, bu kaynaklardan veri arama ve belge getirme işlemleri, Model Context Protocol (MCP) destekleyen LLM (Büyük Dil Modeli) uygulamaları (örneğin Claude Desktop) ve diğer istemciler tarafından araç (tool) olarak kullanılabilir hale gelir.

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
    * **KİK (Kamu İhale Kurulu):** Çeşitli kriterlerle Kurul kararlarını arama; uzun karar metinlerini (varsayılan 5.000 karakterlik) sayfalanmış Markdown formatında getirme (Playwright ile tarayıcı otomasyonu kullanılır).
* Karar metinlerinin daha kolay işlenebilmesi için Markdown formatına çevrilmesi.
* Claude Desktop uygulaması ile `fastmcp install` komutu kullanılarak kolay entegrasyon.

### FastAPI Sunucusu

Araçlara doğrudan HTTP üzerinden erişmek için `fastapi_server.py` dosyasını çalıştırabilirsiniz:

```bash
uvicorn fastapi_server:app --reload
```

Bu sunucu, MCP araçlarını RESTful endpoint'ler olarak sunar. Örneğin Yargıtay karar araması için `/yargitay/search/detailed` adresine POST isteği gönderebilirsiniz.

---
📋 **Ön Gereksinimler**

Bu Yargı MCP aracını Claude Desktop ile kullanabilmek için öncelikle aşağıdaki yazılımların sisteminizde kurulu olması gerekmektedir:

1.  **Claude Desktop:** Henüz kurmadıysanız, [Claude Desktop web sitesinden](https://claude.ai/desktop) işletim sisteminize uygun sürümü indirip kurun.
2.  **Python Sürümü:** **Python 3.11** sürümü tavsiye edilir. Python 3.12 ve üzeri yeni sürümler, bazı bağımlılıklarda (özellikle `playwright` ve ilişkili tarayıcı sürücüleri) belirli ortamlarda uyumluluk sorunlarına yol açabilir. Bu proje için 3.11 sürümü stabilite açısından önerilmektedir.
    * **Windows Kullanıcıları:** Eğer Python kurulu değilse, [python.org/downloads/windows/](https://www.python.org/downloads/windows/) adresinden Python 3.11'in uygun bir sürümünü indirip kurabilirsiniz. Kurulum sırasında "**Add Python to PATH**" (Python'ı PATH'e ekle) seçeneğini işaretlemeyi unutmayın.
    * **macOS Kullanıcıları:** macOS genellikle Python ile birlikte gelir. Terminal'de `python3 --version` yazarak kontrol edebilirsiniz. Eğer Python 3.11 değilse veya eski bir sürümse, [python.org](https://www.python.org/downloads/macos/) adresinden veya [Homebrew](https://brew.sh/) (`brew install python@3.11`) ile kurabilirsiniz.
    * **Linux Kullanıcıları:** Çoğu Linux dağıtımı Python ile gelir. Terminal'de `python3 --version` yazarak kontrol edebilirsiniz. Gerekirse dağıtımınızın paket yöneticisi ile Python 3.11'i kurabilirsiniz (örn: `sudo apt update && sudo apt install python3.11 python3.11-pip python3.11-venv` veya dağıtımınıza uygun komutlar).
3.  **Paket Yöneticisi:** `pip` (Python ile birlikte gelir) veya tercihen `uv` ([Astral](https://astral.sh/uv) tarafından geliştirilen hızlı Python paket yöneticisi). Kurulum script'lerimiz `uv`'yi sizin için kurmayı deneyecektir.
4.  **Playwright Tarayıcıları:** KİK modülü Playwright kullandığı için, ilgili tarayıcıların kurulmuş olması gerekir. `KikApiClient` varsayılan olarak Chromium kullanır. Eğer Playwright veya tarayıcıları manuel kuracaksanız:
    ```bash
    # Önce playwright kütüphanesini kurun (uv veya pip ile)
    # uv pip install playwright 
    # pip install playwright

    # Sonra tarayıcıları kurun (proje bağımlılıkları kurulduktan sonra da yapılabilir)
    playwright install --with-deps chromium 
    # '--with-deps' chromium için gerekli işletim sistemi bağımlılıklarını da kurmaya çalışır.
    ```
    Kurulum scriptleri (`install.bat`, `install.sh`, `install.py`) genellikle `playwright` Python kütüphanesini kurar. Tarayıcıların ayrıca `playwright install` ile kurulması gerekebilir; eğer sunucu başlatılırken KİK modülü hata verirse, bu adımı manuel olarak çalıştırmanız gerekebilir.

---
🚀 **Kolay Kurulum Adımları (Claude Desktop için)**

Bu bölüm, teknik bilgisi daha az olan kullanıcıların **Yargı MCP** araçlarını Claude Desktop uygulamalarına hızlı ve kolay bir şekilde entegre etmeleri için hazırlanmıştır.

**Öncelikle Yapılması Gerekenler:**

1.  **Proje Dosyalarını İndirin:**
    * Bu GitHub deposunun ana sayfasına gidin.
    * Yeşil renkli "**<> Code**" düğmesine tıklayın.
    * Açılan menüden "**Download ZIP**" seçeneğini seçin.
    * İndirdiğiniz ZIP dosyasını bilgisayarınızda kolayca erişebileceğiniz bir klasöre çıkartın (örneğin, `Belgelerim` veya `Masaüstü` altında `yargi-mcp` adında bir klasör oluşturabilirsiniz).

Proje dosyalarını bilgisayarınıza aldıktan sonra, işletim sisteminize uygun kurulum script'ini çalıştırabilirsiniz.

### Windows Kullanıcıları İçin (`install.bat`)

1.  Proje dosyalarını çıkarttığınız klasörün içine gidin (örneğin, `C:\Users\KULLANICIADINIZ\Documents\yargi-mcp` klasörü).
2.  `install.bat` adlı dosyayı bulun.
3.  Bu dosyaya **çift tıklayarak** çalıştırın.
4.  Kurulum sırasında bir komut istemi penceresi açılacak ve bazı mesajlar göreceksiniz. Script, gerekli araçları (`uv`, `fastmcp` CLI, `playwright` ve tarayıcıları) sisteminize kurmayı deneyecek ve ardından "**Yargı MCP**" aracını Claude Desktop'a entegre edecektir.
    * *Not: Bu işlem sırasında script sizden yönetici onayı isteyebilir veya internet bağlantısı gerektirebilir. `uv` kurulumu için PowerShell script çalıştırma politikalarınızda geçici bir değişiklik yapılması gerekebilir; script bunu sizin için halletmeye çalışacaktır.*
5.  Kurulum tamamlandığında, komut istemi penceresinde bir başarı mesajı göreceksiniz. Pencere, "Devam etmek için bir tuşa basın..." mesajıyla açık kalacaktır. Herhangi bir tuşa basarak pencereyi kapatabilirsiniz.
6.  **Önemli:** Kurulumun etkili olması için Claude Desktop uygulamasını tamamen kapatıp yeniden başlatmanız gerekebilir.

### macOS ve Linux Kullanıcıları İçin (`install.sh`)

1.  Proje dosyalarını çıkarttığınız klasörün içine gidin (örneğin, `/Users/KULLANICIADINIZ/Documents/yargi-mcp` klasörü).
2.  **Terminal** uygulamasını açın:
    * **macOS'te:**
        1.  **Finder**'ı açın.
        2.  Proje dosyalarını çıkarttığınız klasöre (`yargi-mcp` gibi) gidin.
        3.  Finder penceresinin en altındaki yol çubuğunda (Path Bar), klasör adının üzerine **Control tuşuna basılı tutarak tıklayın** (veya sağ tıklayın).
        4.  Açılan menüden "**Terminal'de Aç**" seçeneğini seçin. (Eğer bu seçenek yoksa, Finder'da `Görünüm > Yol Çubuğunu Göster` seçeneğinin aktif olduğundan emin olun. Alternatif olarak, `Uygulamalar > İzlenceler > Terminal` yolunu izleyip `cd` komutuyla klasörünüze gidin.)
    * **Linux'ta:** Genellikle dosya yöneticisinde klasöre sağ tıklayıp "Burada Terminal Aç" seçeneğini kullanabilir veya Ctrl+Alt+T kısayoluyla terminal açıp `cd` komutuyla klasörünüze gidebilirsiniz.
3.  Terminalde, doğru klasörde olduğunuzdan emin olduktan sonra, script'e çalıştırma izni verin (bu işlemi sadece bir kez yapmanız yeterlidir):
    ```bash
    chmod +x install.sh
    ```
4.  Script'i çalıştırın:
    ```bash
    ./install.sh
    ```
5.  Kurulum sırasında terminalde bazı mesajlar göreceksiniz. Script, gerekli araçları (`uv`, `fastmcp` CLI) sisteminize kurmayı deneyecek ve ardından "**Yargı MCP**" aracını Claude Desktop'a entegre edecektir.
    * *Not: Bu işlem sırasında script sizden şifrenizi (`sudo` yetkileri için, özellikle `uv` kurulumunda) isteyebilir veya internet bağlantısı gerektirebilir.*
6.  Kurulum tamamlandığında, terminalde bir başarı mesajı göreceksiniz.
7.  **Önemli:** Kurulumun etkili olması için Claude Desktop uygulamasını tamamen kapatıp yeniden başlatmanız gerekebilir. Ayrıca, eğer `uv` veya `fastmcp` PATH'e yeni eklendiyse, terminalinizi de yeniden başlatmanız veya shell profilinizi (`~/.bashrc`, `~/.zshrc`, `~/.profile` vb.) `source ~/.zshrc` (veya kullandığınız shell'e uygun komutla) yeniden yüklemeniz gerekebilir. Script bu konuda sizi uyaracaktır.

### Python Script ile Kurulum (`install.py`) (Platform Bağımsız Alternatif)

Eğer yukarıdaki işletim sistemine özel script'lerde sorun yaşarsanız veya Python tabanlı bir kurulumu tercih ediyorsanız, `install.py` script'ini kullanabilirsiniz. Bu yöntem, sisteminizde Python 3.11'in ve `pip` paket yöneticisinin kurulu ve çalışır durumda olmasını gerektirir.

1.  Proje dosyalarını çıkarttığınız klasörün içine Terminal veya Komut İstemi ile gidin.
2.  Aşağıdaki komutu çalıştırın (sisteminizdeki Python 3 komutuna göre `python` veya `python3` kullanın):
    ```bash
    python3 install.py 
    ```
    veya
    ```bash
    python install.py
    ```
3.  Script, size gerekli adımlarda rehberlik edecek ve kurulumu tamamlamaya çalışacaktır. Kurulum sırasında ek bağımlılıkların indirilmesi gerekebilir.

---

**Kurulum Sonrası**

Kurulum başarıyla tamamlandıktan sonra, Claude Desktop uygulamasını (gerekirse yeniden başlatarak) açın. Araçlar menüsünde (genellikle ekranın sağ alt köşesindeki çekiç 🛠️ simgesi altında) "**Yargı MCP**" adlı yeni aracı görmelisiniz.

Herhangi bir sorunla karşılaşırsanız, lütfen [GitHub Issues](https://github.com/saidsurucu/yargi-mcp/issues) bölümünden bize bildirin.

⚙️ **Kurulum Adımları (Claude Desktop Entegrasyonu Odaklı)**

Claude Desktop uygulamasına yükleme yapabilmek için öncelikle `uv` (önerilir) ve `fastmcp` komut satırı araçlarını kurmanız, ardından proje dosyalarını almanız gerekmektedir.

**1. `uv` Kurulumu (Önerilir)**

* **macOS ve Linux için:**
    ```bash
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```
* **Windows için (PowerShell kullanarak):**
    ```powershell
    powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
    ```
* Kurulumdan sonra, `uv` komutunun sisteminiz tarafından tanınması için terminalinizi yeniden başlatmanız veya `PATH` ortam değişkeninizi güncellemeniz gerekebilir. `uv --version` komutu ile kurulumu doğrulayabilirsiniz.

**2. `fastmcp` Komut Satırı Aracının (CLI) Kurulumu**

* **`uv` kullanarak (önerilir):**
    ```bash
    uv pip install fastmcp
    ```
* **`pip` kullanarak (alternatif):**
    ```bash
    pip install fastmcp
    ```
    `fastmcp --version` komutu ile kurulumu doğrulayabilirsiniz.

**3. Proje Dosyalarını Alın**

Bu Yargı MCP sunucusunun kaynak kodlarını bilgisayarınıza indirin:
```bash
git clone https://github.com/saidsurucu/yargi-mcp.git
cd yargi-mcp
```
Bu README.md dosyasının ve `mcp_server_main.py` script'inin bulunduğu dizine `cd` komutu ile geçmiş olacaksınız.

**4. Sunucuya Özel Bağımlılıkların Bilinmesi**

Bu sunucunun (`mcp_server_main.py`) çalışması için aşağıdaki Python kütüphanelerine ihtiyacı vardır. Bu kütüphaneler `fastmcp install` sırasında `--with` parametreleriyle belirtilecektir:

```text
# requirements.txt
fastmcp
httpx
beautifulsoup4
markitdown
pydantic
aiohttp
playwright
```
(Eğer sunucuyu bağımsız olarak geliştirmek veya test etmek isterseniz, projenizin kök dizininde bir sanal ortam oluşturup – örn: `uv venv` & `source .venv/bin/activate` – bu bağımlılıkları `uv pip install -r requirements.txt` komutuyla kurabilirsiniz.)

🚀 **Claude Desktop Entegrasyonu (`fastmcp install` ile - Önerilen)**

Yukarıdaki kurulum adımlarını tamamladıktan sonra, bu sunucuyu Claude Desktop uygulamasına kalıcı bir araç olarak eklemenin en kolay yolu `fastmcp install` komutunu kullanmaktır:

1.  Terminalde `mcp_server_main.py` dosyasının bulunduğu `yargi-mcp` dizininde olduğunuzdan emin olun.
2.  Aşağıdaki komutu çalıştırın:

    ```bash
    fastmcp install mcp_server_main.py \
        --name "Yargı MCP" \
        --with httpx \
        --with beautifulsoup4 \
        --with markitdown \
        --with pydantic \
        --with aiohttp \
        --with playwright
    ```

    * `--name "Yargı MCP"`: Araç Claude Desktop'ta bu isimle görünecektir.
    * `--with ...`: Sunucunun çalışması için gereken Python bağımlılıklarını belirtir.

    Bu komut, `uv` kullanarak (eğer kuruluysa ve bulunabiliyorsa) sunucunuz için izole bir Python ortamı oluşturacak, belirtilen bağımlılıkları kuracak ve aracı Claude Desktop uygulamasına kaydedecektir. Playwright tarayıcılarının (`playwright install chromium` gibi) ayrıca kurulması gerekebilir.

⚙️ **Claude Desktop Manuel Kurulumu (Yapılandırma Dosyası ile - Alternatif)**

1.  **Claude Desktop Ayarları**'nı açın.
2.  **Developer** sekmesine gidin ve **Edit Config** düğmesine tıklayın.
3.  Açılan `claude_desktop_config.json` dosyasını bir metin düzenleyici ile açın.
4.  `mcpServers` nesnesine aşağıdaki JSON bloğunu ekleyin:

    ```json
    {
      "mcpServers": {
        // ... (varsa diğer sunucu tanımlamalarınız) ...

        "Yargı MCP": {
          "command": "uv",
          "args": [
            "run",
            "--with", "httpx",
            "--with", "beautifulsoup4",
            "--with", "markitdown",
            "--with", "pydantic",
            "--with", "aiohttp",
            "--with", "playwright", 
            "--with", "fastmcp",
            "fastmcp", "run", 
            "/TAM/PROJE/YOLUNUZ/yargi-mcp/mcp_server_main.py" 
          ]
        }
      }
    }
    ```
    * **Önemli:** `/TAM/PROJE/YOLUNUZ/yargi-mcp/mcp_server_main.py` kısmını, `mcp_server_main.py` dosyasının sisteminizdeki **tam ve doğru yolu** ile değiştirmeyi unutmayın.
5.  Claude Desktop'ı yeniden başlatın.

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

📜 **Lisans**

Bu proje MIT Lisansı altında lisanslanmıştır. Detaylar için `LICENSE` dosyasına bakınız.