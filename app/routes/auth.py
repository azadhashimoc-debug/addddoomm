from hashlib import sha256
import re
import uuid

from fastapi import APIRouter, Depends, HTTPException
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..config import GOOGLE_WEB_CLIENT_ID
from ..database import User, get_db

router = APIRouter()


class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str


class LoginRequest(BaseModel):
    username_or_email: str
    password: str


class GoogleLoginRequest(BaseModel):
    id_token: str


def hash_password(password: str) -> str:
    return sha256(password.encode("utf-8")).hexdigest()


def normalize_username(username: str) -> str:
    return username.strip()


def normalize_email(email: str) -> str:
    return email.strip().lower()


def is_valid_email(email: str) -> bool:
    return re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email) is not None


@router.post("/register")
async def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    username = normalize_username(payload.username)
    email = normalize_email(payload.email)

    if len(username) < 3:
        raise HTTPException(status_code=400, detail="İstifadəçi adı minimum 3 simvol olmalıdır.")
    if not is_valid_email(email):
        raise HTTPException(status_code=400, detail="Düzgün email ünvanı daxil edin.")
    if len(payload.password) < 6:
        raise HTTPException(status_code=400, detail="Şifrə minimum 6 simvol olmalıdır.")

    existing_user = db.query(User).filter(User.username == username).first()
    if existing_user:
        raise HTTPException(status_code=409, detail="Bu istifadəçi adı artıq mövcuddur.")

    existing_email = db.query(User).filter(User.email == email).first()
    if existing_email:
        raise HTTPException(status_code=409, detail="Bu email artıq qeydiyyatdan keçib.")

    user = User(
        id=str(uuid.uuid4()),
        username=username,
        email=email,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.commit()

    return {
        "success": True,
        "message": "Qeydiyyat uğurla tamamlandı.",
        "data": {
            "username": user.username,
            "email": user.email
        }
    }


@router.post("/login")
async def login(payload: LoginRequest, db: Session = Depends(get_db)):
    identifier = payload.username_or_email.strip()
    password_hash = hash_password(payload.password)

    user = db.query(User).filter(User.username == identifier).first()
    if not user:
        user = db.query(User).filter(User.email == identifier.lower()).first()

    if not user or user.password_hash != password_hash:
        raise HTTPException(status_code=401, detail="İstifadəçi adı/email və ya şifrə yanlışdır.")

    return {
        "success": True,
        "message": "Giriş uğurludur.",
        "data": {
            "username": user.username,
            "email": user.email
        }
    }


@router.post("/google-login")
async def google_login(payload: GoogleLoginRequest, db: Session = Depends(get_db)):
    raw_id_token = payload.id_token.strip()
    if not raw_id_token:
        raise HTTPException(status_code=400, detail="Google ID token boş ola bilməz.")

    try:
        token_info = id_token.verify_oauth2_token(
            raw_id_token,
            google_requests.Request(),
            GOOGLE_WEB_CLIENT_ID,
        )
    except ValueError:
        raise HTTPException(status_code=401, detail="Google token doğrulanmadı.")

    google_id = (token_info.get("sub") or "").strip()
    email = normalize_email(token_info.get("email") or "")
    name = (token_info.get("name") or "").strip()
    email_verified = bool(token_info.get("email_verified"))

    if not google_id:
        raise HTTPException(status_code=401, detail="Google hesab kimliyi alınmadı.")
    if not is_valid_email(email):
        raise HTTPException(status_code=401, detail="Google hesab emaili etibarlı deyil.")
    if not email_verified:
        raise HTTPException(status_code=401, detail="Google hesab emaili təsdiqlənməyib.")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        username_base = normalize_username(name) if name else email.split("@")[0]
        username_base = re.sub(r"[^a-zA-Z0-9_]", "_", username_base).strip("_") or "google_user"
        if len(username_base) < 3:
            username_base = f"{username_base}_usr"

        username = username_base
        counter = 1
        while db.query(User).filter(User.username == username).first():
            username = f"{username_base}_{counter}"
            counter += 1

        user = User(
            id=str(uuid.uuid4()),
            username=username,
            email=email,
            password_hash=hash_password(f"google::{google_id}"),
        )
        db.add(user)
        db.commit()
    return {
        "success": True,
        "message": "Google ilə giriş uğurludur.",
        "data": {
            "username": user.username,
            "email": user.email
        }
    }
