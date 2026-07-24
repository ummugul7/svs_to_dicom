# SVS to DICOM Dönüştürücü
bir klasörde bulunan tüm SVS dosyalrını , DICOM formatına dönüştüren ve zip halinde döndüren bir servis 
## Neler kullandım 
postgresql veritabanı, loglama işlemi ve dbnin kullanılması için bir docker compose dosyası eklendi.

## Kütüphaneler 
ORM için SQLAlchemy
APİ servisi için FastAPİ 
svs dosyalarını okumak için OpenSlide
svs dosyasını dicoma çevirmek için  WsiDicomizer
thread yönetiminin otomatik yapılması için  concurrent.futures
db için de psycopg2 

```mermaid
graph TD
    A[klasör yüklencek] --> B[sırayla doysalar tarancak]
    B --> C[.svs uzantısında sahip olanlar uniq bir slide_id değeri ile kaydedilecek]
    C --> D[dosyaya ait bir hash değeri üretilecek]
    D --> E[hash değeri dbdeki değerler ile karşılaştırılacak]
    E --> F[değer yoksa dosya DİCOM fotmatına kaydedilip dbye bilgiler eklenecek  ]
    F --> G[tüm dosya taranınca işlem bitercek]
```

## Kurulum ve Çalıştırma
- Projeyi ayağa kaldırmak için terminalde `python main.py` komutunu çalıştırabilirsiniz.
- Yükleme testi için ana dizindeki `test_upload.html` dosyasını tarayıcıda açabilirsiniz.


NOT: arayüz deneme için oluşturuldu 