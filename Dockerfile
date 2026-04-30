# Python 3.10-un yüngül versiyasını götürürük
FROM python:3.10-slim

# FFmpeg və digər sistem asılılıqlarını yükləyirik
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# İşçi qovluğu təyin edirik
WORKDIR /app

# Əvvəlcə requirements.txt-ni kopyalayırıq ki, cache-dən istifadə olunsun
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Bütün backend kodunu kopyalayırıq
COPY . .

# Lazımi qovluqların olduğundan əmin oluruq
RUN mkdir -p data/uploads data/outputs

# Serveri işə salırıq.
# Render bizə avtomatik $PORT dəyişəni verir.
CMD ["sh", "-c", "python migrate_db.py && uvicorn app.main:app --host 0.0.0.0 --port $PORT"]
