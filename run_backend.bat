@echo off
cd /d %~dp0
echo VocalSplit AI Backend Baslatiliyor...

:: Gerekli kutuphaneleri yukle
python -m pip install -r requirements.txt
python migrate_db.py
python migrate_ip.py
python migrate_options.py
python migrate_users.py
python migrate_daily_usage.py
python migrate_client_id.py

:: Klasorlerin varligindan emin ol
if not exist "data\uploads" mkdir "data\uploads"
if not exist "data\outputs" mkdir "data\outputs"

echo.
echo Server ayaga kalkiyor...
echo Eger FFmpeg yuklu degilse islem sirasinda hata alabilirsiniz.
echo Demucs modeli onceden hazirlaniyor...
python -m app.model_warmup --name htdemucs
echo.

:: Uvicorn'u modul olarak calistir (PATH hatasini onler)
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

pause
