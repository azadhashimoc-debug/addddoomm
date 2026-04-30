from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from .routes import auth, jobs
from .config import OUTPUT_DIR
from .model_warmup import warmup_in_background

@asynccontextmanager
async def lifespan(app: FastAPI):
    # AI modelinin açılışda yüklənməsini müvəqqəti söndürürük (OOM-un qarşısını almaq üçün)
    # warmup_in_background()
    yield

app = FastAPI(title="VocalSplit AI API", lifespan=lifespan)

# Enable CORS for Android app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve output files
app.mount("/outputs", StaticFiles(directory=OUTPUT_DIR), name="outputs")

app.include_router(jobs.router, prefix="/api/jobs", tags=["jobs"])
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])

@app.get("/")
async def root():
    return {"message": "VocalSplit AI API is running"}
