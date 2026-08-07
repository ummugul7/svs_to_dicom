# SVS to DICOM Dönüştürücü

proje SVS uzantılı patoloji görüntü dosyalarını DICOM formatına dönüştüren bir web servisi ve arka planda çalışan bir izleyici (observer) içerir. 

Projeye web arayüzü üzerinden veya doğrudan izlenen bir klasör aracılığıyla SVS dosyaları eklenebilir. Yüklenen dosyalar asenkron olarak işlenir, WsiDicomizer kullanılarak DICOM formatına dönüştürülür ve verileri veritabanına kaydedilir. 

## Özellikler
- **Web Arayüzü**: Dosya yükleme ve durumu görüntüleme.
- **Klasör İzleyici (Observer)**: Belirli bir klasörü izleyerek içine atılan SVS dosyalarını otomatik olarak işleme.

## Kütüphaneler 
- **Flask**: API ve web servisi için
- **SQLAlchemy**: ORM işlemleri için
- **psycopg2**: PostgreSQL veritabanı bağlantısı için
- **OpenSlide**: SVS dosyalarını okumak için
- **WsiDicomizer**: SVS dosyasını DICOM formatına çevirmek için
- **concurrent.futures**: Thread yönetiminin otomatik yapılması için
- **watchdog**: Klasördeki değişiklikleri izlemek (observer) için

## Kurulum ve Çalıştırma

1. Projenin bulunduğu klasörde `docker compose up` komutu ile veya ide üzerinden containerları ayağa kaldırın.
2. Projeyi (web servisini) ayağa kaldırmak için terminalde `python main.py` komutunu çalıştırın ve `http://127.0.0.1:8000/upload` adresi ile dosya yükleme işlemine başlayın.
3. İzleyiciyi (Observer) çalıştırmak istiyorsanız yeni bir terminal penceresi açıp `python src/observer.py` komutunu çalıştırın.