# Python 3.10 istifadə edirik
FROM python:3.10-slim

# FFmpeg və sistem kitabxanalarını yükləyirik
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Hugging Face üçün standart istifadəçi yaradırıq (UID 1000)
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONPATH=/code

# İşçi qovluğunu /code təyin edirik
WORKDIR /code

# Asılılıqları kopyalayırıq və yükləyirik
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# BÜTÜN faylları (app qovluğu daxil olmaqla) /code qovluğuna kopyalayırıq
COPY --chown=user . .

# Port Hugging Face üçün 7860
EXPOSE 7860

# Serveri başladırıq
CMD ["sh", "-c", "python migrate_db.py && python -m uvicorn app.main:app --host 0.0.0.0 --port 7860"]
