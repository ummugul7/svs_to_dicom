# SVS to DICOM API
Tıbbi patoloji görüntülerini (`.svs`) yükleyip, arka planda DICOM formatına dönüştüren bir FastAPI servisidir.
## 🚀 Özellikler
- `.svs` yükleme ve arka planda DICOM dönüştürme.
- OpenSlide ile metadata okuma ve özellik çıkarımı.
- Önizleme için "thumbnail" ve bölgesel kesit (tile) alma.
## 📋 Kurulum ve Çalıştırma
1. Sanal ortam (venv) oluşturun ve aktifleştirin.
2. Bağımlılıkları yükleyin:
   ```bash
   pip install -r requirements.txt
   ```
3. Uygulamayı başlatın:
   ```bash
   python main.py
   ```
**Not:** API'yi test etmek için tarayıcıda `http://127.0.0.1:8000/docs` adresini açabilirsiniz (Swagger UI).
## 📡 Uç Noktalar (Endpoints)
|
 Uç Nokta 
|
 Açıklama 
|
|
:---
|
:---
|
|
`POST /upload`
|
 SVS dosyasını yükler, dönüştürmeyi başlatır. 
|
|
`GET /metadata`
|
 Slayt özelliklerini (çözünürlük, cihaz vb.) getirir. 
|
|
`GET /properties`
|
 Ham OpenSlide özelliklerini döndürür. 
|
|
`GET /thumbnail`
|
 Hızlı önizleme resmi (PNG) döner. 
|
|
`GET /tile`
|
 Büyük görüntüden bölgesel kesit (PNG) alır. 
|
|
`GET /download-dicom-zip`
|
 Dönüşüm bittiyse ZIP formatında DICOM dosyalarını indirir. 
|
