import base64
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from models import Role, User, UserSession

SESSION_COOKIE = "session_id"
SESSION_DAYS = 7

router = APIRouter(prefix="/auth", tags=["auth"])


def utcnow() -> datetime:
    return datetime.utcnow()

def _prepare(password: str) -> bytes:
    return base64.b64encode(hashlib.sha256(password.encode("utf-8")).digest())


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_prepare(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(_prepare(password), hashed.encode("utf-8"))


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class RegisterIn(BaseModel):
    full_name: str = Field(min_length=1, max_length=200)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    phone: Optional[str] = Field(default=None, max_length=30)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


def user_out(user: User, db: Session) -> dict:
    role = db.get(Role, user.role_id)
    return {
        "id": user.id,
        "full_name": user.full_name,
        "email": user.email,
        "phone": user.phone,
        "role": role.code,
    }

def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise HTTPException(status_code=401, detail="Требуется вход в систему")
    session = db.get(UserSession, _token_hash(token))
    if session is None or session.expires_at < utcnow():
        raise HTTPException(status_code=401, detail="Сессия недействительна")
    user = db.get(User, session.user_id)
    if user is None or user.deleted_at is not None:
        raise HTTPException(status_code=401, detail="Пользователь не найден")
    return user


def require_roles(*codes: str):
    def checker(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> User:
        role = db.get(Role, user.role_id)
        if role.code not in codes:
            raise HTTPException(status_code=403, detail="Недостаточно прав")
        return user

    return checker

@router.post("/register", status_code=201)
def register(data: RegisterIn, db: Session = Depends(get_db)):
    email = data.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=409, detail="Почта уже зарегистрирована")
    role = db.scalar(select(Role).where(Role.code == "client"))
    user = User(
        role_id=role.id,
        full_name=data.full_name,
        email=email,
        password_hash=hash_password(data.password),
        phone=data.phone,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user_out(user, db)


@router.post("/login")
def login(data: LoginIn, response: Response, db: Session = Depends(get_db)):
    email = data.email.lower()
    user = db.scalar(select(User).where(User.email == email, User.deleted_at.is_(None)))
    if user is None or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Неверная почта или пароль")

    token = secrets.token_urlsafe(32)
    db.add(UserSession(
        id=_token_hash(token),
        user_id=user.id,
        expires_at=utcnow() + timedelta(days=SESSION_DAYS),
    ))
    db.commit()

    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        max_age=SESSION_DAYS * 24 * 3600,
        httponly=True,
        samesite="lax",
        secure=False,  
    )
    return user_out(user, db)


@router.post("/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        session = db.get(UserSession, _token_hash(token))
        if session:
            db.delete(session)
            db.commit()
    response.delete_cookie(SESSION_COOKIE)
    return {"message": "Вы вышли из системы"}


@router.get("/me")
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return user_out(user, db)