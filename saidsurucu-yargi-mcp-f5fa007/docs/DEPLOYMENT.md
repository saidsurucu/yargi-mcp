# Yargı MCP Server Dağıtım Rehberi

Bu rehber, Yargı MCP Server'ın ASGI web servisi olarak çeşitli dağıtım seçeneklerini kapsar.

## İçindekiler

- [Hızlı Başlangıç](#hızlı-başlangıç)
- [Yerel Geliştirme](#yerel-geliştirme)
- [Production Dağıtımı](#production-dağıtımı)
- [Cloud Dağıtımı](#cloud-dağıtımı)
- [Docker Dağıtımı](#docker-dağıtımı)
- [Güvenlik Hususları](#güvenlik-hususları)
- [İzleme](#izleme)

## Hızlı Başlangıç

### 1. Bağımlılıkları Yükleyin

```bash
# ASGI sunucusu için uvicorn yükleyin
pip install uvicorn

# Veya tüm bağımlılıklarla birlikte yükleyin
pip install -e .
pip install uvicorn
```

### 2. Sunucuyu Çalıştırın

```bash
# Temel başlatma
python run_asgi.py

# Veya doğrudan uvicorn ile
uvicorn asgi_app:app --host 0.0.0.0 --port 8000
```

Sunucu şu adreslerde kullanılabilir olacak:
- MCP Endpoint: `http://localhost:8000/mcp/`
- Sağlık Kontrolü: `http://localhost:8000/health`
- API Durumu: `http://localhost:8000/status`

## Yerel Geliştirme

### Otomatik Yeniden Yükleme ile Geliştirme Sunucusu

```bash
python run_asgi.py --reload --log-level debug
```

### FastAPI Entegrasyonunu Kullanma

Ek REST API endpoint'leri için:

```bash
uvicorn fastapi_app:app --reload
```

Bu şunları sağlar:
- `/docs` adresinde interaktif API dokümantasyonu
- `/api/tools` adresinde araç listesi
- `/api/databases` adresinde veritabanı bilgileri

### Ortam Değişkenleri

`.env.example` dosyasını temel alarak bir `.env` dosyası oluşturun:

```bash
cp .env.example .env
```

Temel değişkenler:
- `HOST`: Sunucu host adresi (varsayılan: 127.0.0.1)
- `PORT`: Sunucu portu (varsayılan: 8000)
- `ALLOWED_ORIGINS`: CORS kökenleri (virgülle ayrılmış)
- `LOG_LEVEL`: Log seviyesi (debug, info, warning, error)

## Production Dağıtımı

### 1. Uvicorn ile Çoklu Worker Kullanımı

```bash
python run_asgi.py --host 0.0.0.0 --port 8000 --workers 4
```

### 2. Gunicorn Kullanımı

```bash
pip install gunicorn
gunicorn asgi_app:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### 3. Nginx Reverse Proxy ile

1. Nginx'i yükleyin
2. Sağlanan `nginx.conf` dosyasını kullanın:

```bash
sudo cp nginx.conf /etc/nginx/sites-available/yargi-mcp
sudo ln -s /etc/nginx/sites-available/yargi-mcp /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 4. Systemd Servisi

`/etc/systemd/system/yargi-mcp.service` dosyasını oluşturun:

```ini
[Unit]
Description=Yargı MCP Server
After=network.target

[Service]
Type=exec
User=www-data
WorkingDirectory=/opt/yargi-mcp
Environment="PATH=/opt/yargi-mcp/venv/bin"
ExecStart=/opt/yargi-mcp/venv/bin/uvicorn asgi_app:app --host 0.0.0.0 --port 8000 --workers 4
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Etkinleştirin ve başlatın:

```bash
sudo systemctl enable yargi-mcp
sudo systemctl start yargi-mcp
```

## Cloud Dağıtımı

### Heroku

1. `Procfile` oluşturun:
```
web: uvicorn asgi_app:app --host 0.0.0.0 --port $PORT
```

2. Dağıtın:
```bash
heroku create uygulama-isminiz
git push heroku main
```

### Railway

1. `railway.json` ekleyin:
```json
{
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "uvicorn asgi_app:app --host 0.0.0.0 --port $PORT"
  }
}
```

2. Railway CLI veya GitHub entegrasyonu ile dağıtın

### Google Cloud Run

1. Container oluşturun:
```bash
docker build -t yargi-mcp .
docker tag yargi-mcp gcr.io/PROJE_ADINIZ/yargi-mcp
docker push gcr.io/PROJE_ADINIZ/yargi-mcp
```

2. Dağıtın:
```bash
gcloud run deploy yargi-mcp \
  --image gcr.io/PROJE_ADINIZ/yargi-mcp \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

### AWS Lambda (Mangum kullanarak)

1. Mangum'u yükleyin:
```bash
pip install mangum
```

2. `lambda_handler.py` oluşturun:
```python
from mangum import Mangum
from asgi_app import app

handler = Mangum(app, lifespan="off")
```

3. AWS SAM veya Serverless Framework kullanarak dağıtın

## Docker Dağıtımı

### Tek Container

```bash
# Oluşturun
docker build -t yargi-mcp .

# Çalıştırın
docker run -p 8000:8000 --env-file .env yargi-mcp
```

### Docker Compose

```bash
# Geliştirme
docker-compose up

# Nginx ile Production
docker-compose --profile production up

# Redis önbellekleme ile
docker-compose --profile with-cache up
```

### Kubernetes

Deployment YAML oluşturun:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: yargi-mcp
spec:
  replicas: 3
  selector:
    matchLabels:
      app: yargi-mcp
  template:
    metadata:
      labels:
        app: yargi-mcp
    spec:
      containers:
      - name: yargi-mcp
        image: yargi-mcp:latest
        ports:
        - containerPort: 8000
        env:
        - name: HOST
          value: "0.0.0.0"
        - name: PORT
          value: "8000"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 30
---
apiVersion: v1
kind: Service
metadata:
  name: yargi-mcp-service
spec:
  selector:
    app: yargi-mcp
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer
```

## Güvenlik Hususları

### 1. Kimlik Doğrulama

`API_TOKEN` ortam değişkenini ayarlayarak token kimlik doğrulamasını etkinleştirin:

```bash
export API_TOKEN=gizli-token-degeri
```

Ardından isteklere ekleyin:
```bash
curl -H "Authorization: Bearer gizli-token-degeri" http://localhost:8000/api/tools
```

### 2. HTTPS/SSL

Production için her zaman HTTPS kullanın:

1. SSL sertifikası edinin (Let's Encrypt vb.)
2. Nginx veya cloud sağlayıcıda yapılandırın
3. `ALLOWED_ORIGINS` değerini https:// kullanacak şekilde güncelleyin

### 3. Rate Limiting (Hız Sınırlama)

Sağlanan Nginx yapılandırması rate limiting içerir:
- API endpoint'leri: 10 istek/saniye
- MCP endpoint: 100 istek/saniye

### 4. CORS Yapılandırması

Production için belirli kaynaklara izin verin:

```bash
ALLOWED_ORIGINS=https://app.sizindomain.com,https://www.sizindomain.com
```

## İzleme

### Sağlık Kontrolleri

`/health` endpoint'ini izleyin:

```bash
curl http://localhost:8000/health
```

Yanıt:
```json
{
  "status": "healthy",
  "timestamp": "2024-12-26T10:00:00",
  "uptime_seconds": 3600,
  "tools_operational": true
}
```

### Loglama

Ortam değişkeni ile log seviyesini yapılandırın:

```bash
LOG_LEVEL=info  # veya debug, warning, error
```

Loglar şuraya yazılır:
- Konsol (stdout)
- `logs/mcp_server.log` dosyası

### Metrikler (Opsiyonel)

OpenTelemetry desteği için:

```bash
pip install opentelemetry-instrumentation-fastapi
```

Ortam değişkenlerini ayarlayın:
```bash
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
OTEL_SERVICE_NAME=yargi-mcp-server
```

## Sorun Giderme

### Port Zaten Kullanımda

```bash
# 8000 portunu kullanan işlemi bulun
lsof -i :8000

# İşlemi sonlandırın
kill -9 <PID>
```

### İzin Hataları

Dosya izinlerinin doğru olduğundan emin olun:

```bash
chmod +x run_asgi.py
chown -R www-data:www-data /opt/yargi-mcp
```

### Bellek Sorunları

Büyük belge işleme için worker belleğini artırın:

```bash
# systemd servisinde
Environment="PYTHONMALLOC=malloc"
LimitNOFILE=65536
```

### Zaman Aşımı Sorunları

Zaman aşımlarını ayarlayın:
1. Uvicorn: `--timeout-keep-alive 75`
2. Nginx: `proxy_read_timeout 300s;`
3. Cloud sağlayıcılar: Platform özel zaman aşımı ayarlarını kontrol edin

## Performans Ayarlama

### 1. Worker İşlemleri

- Geliştirme: 1 worker
- Production: CPU çekirdeği başına 2-4 worker

### 2. Bağlantı Havuzlama

Sunucu varsayılan olarak httpx ile bağlantı havuzlama kullanır.

### 3. Önbellekleme (Gelecek Geliştirme)

Redis önbellekleme docker-compose ile etkinleştirilebilir:

```bash
docker-compose --profile with-cache up
```

### 4. Veritabanı Zaman Aşımları

`.env` dosyasında veritabanı başına zaman aşımlarını ayarlayın:

```bash
YARGITAY_TIMEOUT=60
DANISTAY_TIMEOUT=60
ANAYASA_TIMEOUT=90
```

## Destek

Sorunlar ve sorular için:
- GitHub Issues: https://github.com/saidsurucu/yargi-mcp/issues
- Dokümantasyon: README.md dosyasına bakın