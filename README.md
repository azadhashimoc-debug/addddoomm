# VocalSplit AI Backend

Bu backend, Android uygulamasından gelen ses dosyalarını alır ve Demucs AI modelini kullanarak vokal ve enstrümantal kısımları birbirinden ayırır.

## Gereksinimler

1. **Python 3.8+**
2. **FFmpeg**: Sisteminizde yüklü ve PATH'e eklenmiş olmalıdır.
   - Windows için: [gyan.dev](https://www.gyan.dev/ffmpeg/builds/) adresinden indirin, zipten çıkarın ve `bin` klasörünü sistem PATH'ine ekleyin.
3. **Demucs**: `pip install demucs` (requirements.txt içinde mevcuttur).

## Kurulum ve Çalıştırma

1. `backend` klasörüne gidin.
2. `run_backend.bat` dosyasını çalıştırın (Veya manuel olarak `pip install -r requirements.txt` ve `uvicorn app.main:app --host 0.0.0.0 --port 8000` yapın).
3. API dokümantasyonu: `http://localhost:8000/docs`

## Android Bağlantısı

- **Emulator**: `10.0.2.2:8000` adresini kullanır (Otomatik ayarlanmıştır).
- **Gerçek Telefon**: Bilgisayarınızın lokal IP adresini (örneğin `192.168.1.50:8000`) `ApiClient.kt` dosyasında `BASE_URL` olarak ayarlamanız gerekir.

## Klasör Yapısı

- `data/uploads`: Yüklenen orijinal dosyalar.
- `data/outputs`: Ayrıştırılmış vokal ve enstrümantal dosyaları.
- `vocal_split.db`: İş takibi için SQLite veritabanı.
