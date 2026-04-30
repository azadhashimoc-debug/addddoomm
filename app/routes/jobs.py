from fastapi import APIRouter, UploadFile, File, BackgroundTasks, Depends, HTTPException, Request, Form
import datetime
import uuid
import os
import shutil
import hashlib
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ..database import DailyUsage, Job, PremiumEntitlement, get_db
from ..config import UPLOAD_DIR
from ..google_play import (
    GooglePlayConfigError,
    GooglePlayVerificationError,
    acknowledge_one_time_purchase,
    verify_one_time_purchase,
)
from ..model_warmup import get_model_status, is_model_ready
from ..audio_processor import process_audio

router = APIRouter()
BASE_DAILY_LIMIT = 2


class PremiumActivationPayload(BaseModel):
    productId: str
    purchaseToken: str


def get_client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def get_client_key(request: Request) -> str:
    client_id = request.headers.get("X-Client-Id", "").strip()
    return client_id or get_client_ip(request)


def has_premium_entitlement(db: Session, client_key: str) -> bool:
    entitlement = db.query(PremiumEntitlement).filter(
        PremiumEntitlement.client_id == client_key
    ).first()
    if entitlement is None:
        return False

    try:
        purchase = verify_one_time_purchase(
            product_id=entitlement.product_id,
            purchase_token=entitlement.purchase_token,
        )
    except (GooglePlayConfigError, GooglePlayVerificationError):
        return False

    if purchase.get("purchaseState") != 0:
        db.delete(entitlement)
        db.commit()
        return False

    if purchase.get("acknowledgementState") == 0:
        acknowledge_one_time_purchase(
            product_id=entitlement.product_id,
            purchase_token=entitlement.purchase_token,
        )

    return True

def run_process_task(job_id: str, file_name: str, output_format: str, split_mode: str, high_quality: bool):
    db = next(get_db())
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if job:
            job.status = "processing"
            db.commit()

            success, error = process_audio(
                job_id=job_id,
                file_name=file_name,
                output_format=output_format,
                split_mode=split_mode,
                high_quality=high_quality
            )

            if success:
                job.status = "completed"
                job.progress = 1.0
            else:
                job.status = "failed"
                job.error_message = error
            db.commit()
    finally:
        db.close()

def get_file_hash(file_path):
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def get_today_window():
    today = datetime.datetime.utcnow().date()
    return today, datetime.datetime.combine(today, datetime.time.min)


def get_or_create_daily_usage(db: Session, client_key: str, ip_address: str, usage_date: datetime.date):
    usage = db.query(DailyUsage).filter(
        DailyUsage.client_id == client_key,
        DailyUsage.usage_date == usage_date.isoformat()
    ).first()
    if usage:
        return usage

    usage = DailyUsage(
        id=str(uuid.uuid4()),
        client_id=client_key,
        ip_address=ip_address,
        usage_date=usage_date.isoformat(),
        rewarded_credits=0
    )
    db.add(usage)
    db.commit()
    db.refresh(usage)
    return usage


def build_usage_status(db: Session, client_key: str, ip_address: str):
    today, start_of_day = get_today_window()
    daily_usage = get_or_create_daily_usage(db, client_key, ip_address, today)
    used_today = db.query(Job).filter(
        Job.client_id == client_key,
        Job.created_at >= start_of_day
    ).count()
    is_premium = has_premium_entitlement(db, client_key)
    remaining = 999999 if is_premium else max(BASE_DAILY_LIMIT + daily_usage.rewarded_credits - used_today, 0)
    return {
        "baseLimit": BASE_DAILY_LIMIT,
        "usedToday": used_today,
        "rewardedCredits": daily_usage.rewarded_credits,
        "remaining": remaining,
        "isPremium": is_premium
    }

@router.post("/upload")
async def upload_audio(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    output_format: str = Form("mp3"),
    split_mode: str = Form("ai_split"),
    high_quality: bool = Form(True),
    db: Session = Depends(get_db)
):
    if not is_model_ready():
        status = get_model_status()
        raise HTTPException(status_code=503, detail=status["message"])

    output_format = output_format.lower()
    split_mode = split_mode.lower()
    quality_preset = "high" if high_quality else "standard"

    if output_format not in {"mp3", "wav"}:
        raise HTTPException(status_code=400, detail="Dəstəklənməyən format seçimi.")

    if split_mode != "ai_split":
        raise HTTPException(status_code=400, detail="Hazırda yalnız AI Split dəstəklənir.")

    ip_address = get_client_ip(request)
    client_key = get_client_key(request)
    usage_status = build_usage_status(db, client_key, ip_address)

    if not usage_status["isPremium"] and usage_status["remaining"] <= 0:
        raise HTTPException(
            status_code=429,
            detail="Günlük limitiniz dolub. Reklam izləyib +1 emal haqqı qazana bilərsiniz."
        )

    job_id = str(uuid.uuid4())
    file_extension = os.path.splitext(file.filename)[1]
    safe_filename = f"{job_id}{file_extension}"
    file_path = os.path.join(UPLOAD_DIR, safe_filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    file_hash = get_file_hash(file_path)
    existing_job = db.query(Job).filter(
        Job.file_hash == file_hash,
        Job.status == "completed"
    ).first()

    if existing_job:
        job_output_dir = os.path.join(os.path.dirname(UPLOAD_DIR), "outputs", job_id)
        existing_output_dir = os.path.join(os.path.dirname(UPLOAD_DIR), "outputs", existing_job.id)

        if os.path.exists(existing_output_dir):
            os.makedirs(job_output_dir, exist_ok=True)
            for f in ["vocals.wav", "instrumental.wav"]:
                shutil.copy2(os.path.join(existing_output_dir, f), os.path.join(job_output_dir, f))

            new_job = Job(
                id=job_id,
                status="completed",
                progress=1.0,
                client_id=client_key,
                file_hash=file_hash,
                ip_address=ip_address,
                original_file_name=file.filename,
                output_format=output_format,
                split_mode=split_mode,
                quality_preset=quality_preset
            )
            db.add(new_job)
            db.commit()

            success, error = process_audio(
                job_id=job_id,
                file_name=safe_filename,
                output_format=output_format,
                split_mode=split_mode,
                high_quality=high_quality,
                source_outputs_job_id=existing_job.id
            )
            if not success:
                new_job.status = "failed"
                new_job.error_message = error
                db.commit()
                raise HTTPException(status_code=500, detail=error)

            return {
                "success": True,
                "message": "Fayl keşdən bərpa edildi (Sürətli emal)",
                "data": {"jobId": job_id}
            }

    new_job = Job(
        id=job_id,
        status="queued",
        progress=0.0,
        client_id=client_key,
        file_hash=file_hash,
        ip_address=ip_address,
        original_file_name=file.filename,
        output_format=output_format,
        split_mode=split_mode,
        quality_preset=quality_preset
    )
    db.add(new_job)
    db.commit()

    background_tasks.add_task(run_process_task, job_id, safe_filename, output_format, split_mode, high_quality)

    return {
        "success": True,
        "message": "Dosya yüklendi, işlem başlatıldı",
        "data": {"jobId": job_id}
    }


@router.get("/backend-status")
async def backend_status():
    status = get_model_status()
    return {
        "success": True,
        "message": "Backend statusu",
        "data": {
            "modelReady": status["state"] == "ready",
            "state": status["state"],
            "details": status["message"]
        }
    }


@router.get("/usage-status")
async def get_usage_status(request: Request, db: Session = Depends(get_db)):
    ip_address = get_client_ip(request)
    client_key = get_client_key(request)
    return {
        "success": True,
        "message": "İstifadə statusu",
        "data": build_usage_status(db, client_key, ip_address)
    }


@router.post("/reward-credit")
async def reward_credit(request: Request, db: Session = Depends(get_db)):
    ip_address = get_client_ip(request)
    client_key = get_client_key(request)
    today, _ = get_today_window()
    daily_usage = get_or_create_daily_usage(db, client_key, ip_address, today)
    daily_usage.rewarded_credits += 1
    db.commit()

    return {
        "success": True,
        "message": "+1 emal haqqı əlavə edildi.",
        "data": build_usage_status(db, client_key, ip_address)
    }


@router.post("/activate-premium")
async def activate_premium(
    payload: PremiumActivationPayload,
    request: Request,
    db: Session = Depends(get_db)
):
    client_key = get_client_key(request)
    entitlement = db.query(PremiumEntitlement).filter(
        PremiumEntitlement.client_id == client_key
    ).first()

    try:
        purchase = verify_one_time_purchase(
            product_id=payload.productId,
            purchase_token=payload.purchaseToken,
        )
    except GooglePlayConfigError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except GooglePlayVerificationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if purchase.get("purchaseState") != 0:
        raise HTTPException(status_code=400, detail="Purchase state PURCHASED deyil.")

    obfuscated_account_id = purchase.get("obfuscatedExternalAccountId")
    if obfuscated_account_id and obfuscated_account_id != client_key:
        raise HTTPException(status_code=403, detail="Purchase bu cihaz üçün deyil.")

    if purchase.get("acknowledgementState") == 0:
        try:
            acknowledge_one_time_purchase(
                product_id=payload.productId,
                purchase_token=payload.purchaseToken,
            )
        except GooglePlayVerificationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    if entitlement is None:
        entitlement = PremiumEntitlement(
            client_id=client_key,
            purchase_token=payload.purchaseToken,
            product_id=payload.productId
        )
        db.add(entitlement)
    else:
        entitlement.purchase_token = payload.purchaseToken
        entitlement.product_id = payload.productId

    db.commit()

    return {
        "success": True,
        "message": "Premium purchase verify edildi və aktiv oldu.",
        "data": build_usage_status(db, client_key, get_client_ip(request))
    }

@router.get("/")
async def get_all_jobs(request: Request, db: Session = Depends(get_db)):
    client_key = get_client_key(request)
    jobs = db.query(Job).filter(Job.client_id == client_key).order_by(Job.created_at.desc()).all()
    base_url = str(request.base_url).rstrip("/")

    result = []
    for job in jobs:
        vocals_url = None
        instrumental_url = None
        if job.status == "completed":
            extension = job.output_format or "wav"
            vocals_url = f"{base_url}/outputs/{job.id}/vocals.{extension}"
            instrumental_url = f"{base_url}/outputs/{job.id}/instrumental.{extension}"

        result.append({
            "id": job.id,
            "status": job.status,
            "progress": job.progress,
            "originalFileName": job.original_file_name,
            "vocalsDownloadUrl": vocals_url,
            "instrumentalDownloadUrl": instrumental_url,
            "errorMessage": job.error_message,
            "createdAt": job.created_at.isoformat()
        })

    return {"success": True, "message": "İşlər siyahısı", "data": result}

@router.get("/{job_id}")
async def get_job_status(job_id: str, request: Request, db: Session = Depends(get_db)):
    client_key = get_client_key(request)
    job = db.query(Job).filter(Job.id == job_id, Job.client_id == client_key).first()
    if not job:
        raise HTTPException(status_code=404, detail="İş bulunamadı")
    base_url = str(request.base_url).rstrip("/")

    vocals_url = None
    instrumental_url = None

    if job.status == "completed":
        extension = job.output_format or "wav"
        vocals_url = f"{base_url}/outputs/{job_id}/vocals.{extension}"
        instrumental_url = f"{base_url}/outputs/{job_id}/instrumental.{extension}"

    return {
        "success": True,
        "message": "İş durumu",
        "data": {
            "id": job.id,
            "status": job.status,
            "progress": job.progress,
            "originalFileName": job.original_file_name,
            "vocalsDownloadUrl": vocals_url,
            "instrumentalDownloadUrl": instrumental_url,
            "errorMessage": job.error_message
        }
    }
