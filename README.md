## Weverse Stock Alert

Bu proje TXT artist mağazasındaki tüm ana kategoreleri (2025 BLACK FRIDAY, PPULBATU, MERCH, ALBUM, TOUR MERCH, DVD/MEDIA, GLOBAL MEMBERSHIP, JAPAN MEMBERSHIP, US MEMBERSHIP, SEASON'S GREETINGS, WEVERSE, WEVERSE MERCH) düzenli olarak kontrol edip stok geri dönüşü veya fiyat düşüşü olduğunda e-posta ile haber vermek için hazırlandı.

### Kurulum

1. Sanal ortamı aktive et:
   ```
   .\.venv\Scripts\Activate.ps1
   ```
2. Bağımlılıkları yükle:
   ```
   pip install -r requirements.txt
   ```
3. `config.example.json` dosyasını `config.json` olarak kopyala ve SMTP bilgilerini, gönderen adresi ve alıcı listelerini doldur.

### Çalıştırma

```
python monitor.py
```

İlk çalıştırmada mevcut durum `state.json` dosyasına kaydedilir ve e-posta gönderilmez. Sonraki çalıştırmalarda:
- `status` değeri `SOLD_OUT` → başka bir değere dönerse “stok geldi” uyarısı üretir.
- `price` değeri düşerse “fiyat indirimi” olarak raporlar.

Eğer değişiklik yoksa sadece state güncellenir.

### Otomatik Kontrol

Windows Task Scheduler’da yeni bir görev oluşturup şu komutu ekleyebilirsin:

```
Action: Start a program
Program/script: powershell.exe
Arguments: -ExecutionPolicy Bypass -Command "& 'C:\Users\DUYGU\Desktop\weverse stock alert\.venv\Scripts\Activate.ps1'; python 'C:\Users\DUYGU\Desktop\weverse stock alert\monitor.py'"
```

Görevi 10-15 dakikalık aralıklarla tetiklemek yeterli olacaktır.

### GitHub Actions ile çalıştırma

Bilgisayarın açık kalmasına gerek bırakmadan bulutta çalıştırmak istersen bu repo için GitHub Actions workflow’u ekledik (`.github/workflows/weverse-monitor.yml`). Kurulum adımları:

1. Kaynak kodu GitHub’a push et.
2. Repo ayarlarından **Settings → Secrets and variables → Actions** bölümüne girip aşağıdaki sırada *Repository Secret* oluştur:
   - `SMTP_HOST` (örn. `smtp.gmail.com`)
   - `SMTP_PORT` (örn. `587`)
   - `USE_TLS` (`true` ya da `false`)
   - `SMTP_USER`
   - `SMTP_PASSWORD` (Gmail için uygulama şifresi)
   - `EMAIL_SENDER` (gönderici adres)
   - `EMAIL_RECIPIENTS` (virgülle ayrılmış alıcı listesi, örn. `kisi1@mail.com,kisi2@mail.com`)
3. Actions sekmesinden workflow’u bir kez **Run workflow** diyerek manuel tetikle; sonrasında her 15 dakikada bir otomatik çalışır.
4. Workflow çalışması sırasında `state.json` güncellenirse GitHub botu otomatik commit/push yapar, böylece bir sonraki run önceki durumu bilir.

Not: Workflow yalnızca schedule/manual tetiklenir, push’larda otomatik çalışmaz. Secret’larda değişiklik yaparsan workflow’u yeniden tetiklemeyi unutma.

