# SVS to DICOM Dönüştürücü
bir klasörde bulunan tüm SVS dosyalrını , DICOM formatına dönüştüren ve zip halinde döndüren bir servis 
## Neler kullandım 
postgresql veritabanı, loglama işlemi ve dbnin kullanılması için bir docker compose dosyası eklendi.

## Kütüphaneler 
ORM için SQLAlchemy
API servisi için flask
svs dosyalarını okumak için OpenSlide
svs dosyasını dicoma çevirmek için  WsiDicomizer
thread yönetiminin otomatik yapılması için  concurrent.futures
db için de psycopg2 


## Kurulum ve Çalıştırma
- projenin bulunduğu klaörde docker compose up komutu ile veya ide üzerinden containeri ayağa kaldırın,
- Projeyi ayağa kaldırmak için terminalde `python main.py` komutunu çalıştırın ve http://127.0.0.1:8000/upload ile dosya yükleme işlemine başlayın.