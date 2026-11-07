from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from appointments import release_slots, role_code
from auth import (
    SESSION_COOKIE, _token_hash, get_current_user, hash_password,
    require_roles, verify_password,
)
from database import get_db
from models import (
    Appointment, Role, ScheduleSlot, User, UserGroup, UserGroupMember, UserSession,
)

profile_router = APIRouter(prefix="/profile", tags=["profile"])
users_router = APIRouter(prefix="/users", tags=["users"],
                         dependencies=[Depends(require_roles("admin"))])
groups_router = APIRouter(prefix="/groups", tags=["groups"],
                          dependencies=[Depends(require_roles("admin"))])


class UserOut(BaseModel):
    id: int
    full_name: str
    email: str
    phone: Optional[str]
    role: str
    deleted_at: Optional[datetime]


class ProfileUpdate(BaseModel):
    full_name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    phone: Optional[str] = Field(default=None, max_length=30)


class PasswordChange(BaseModel):
    old_password: str
    new_password: str = Field(min_length=8, max_length=128)


class PasswordConfirm(BaseModel):
    password: str


class RoleChange(BaseModel):
    role: str


def user_out(db: Session, user: User) -> UserOut:
    return UserOut(
        id=user.id,
        full_name=user.full_name,
        email=user.email,
        phone=user.phone,
        role=role_code(user, db),
        deleted_at=user.deleted_at,
    )


def active_appointments_query(user_id: int, as_master: bool):
    """Записи, которые ещё не закончились и не отменены."""
    query = select(Appointment.id).join(ScheduleSlot, ScheduleSlot.id == Appointment.slot_id)
    if as_master:
        query = query.where(ScheduleSlot.master_user_id == user_id)
    else:
        query = query.where(Appointment.client_user_id == user_id)
    return query.where(Appointment.status.in_(("new", "confirmed")),
                       Appointment.ends_at >= datetime.now())


def drop_sessions(db: Session, user_id: int, keep_hash: Optional[str] = None):
    query = delete(UserSession).where(UserSession.user_id == user_id)
    if keep_hash:
        query = query.where(UserSession.id != keep_hash)
    db.execute(query)


@profile_router.get("", response_model=UserOut)
def get_profile(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return user_out(db, user)


@profile_router.patch("", response_model=UserOut)
def update_profile(data: ProfileUpdate, user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    for field, value in data.model_dump(exclude_unset=True).items():
        if value is None and field == "full_name":
            continue  # обязательное поле нельзя обнулить
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return user_out(db, user)


@profile_router.post("/password")
def change_password(data: PasswordChange, request: Request,
                    user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not verify_password(data.old_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Старый пароль неверен")
    user.password_hash = hash_password(data.new_password)
    # Выходим со всех остальных устройств, текущая сессия остаётся
    current = _token_hash(request.cookies.get(SESSION_COOKIE, ""))
    drop_sessions(db, user.id, keep_hash=current)
    db.commit()
    return {"message": "Пароль изменён"}


@profile_router.delete("")
def delete_account(data: PasswordConfirm, response: Response,
                   user: User = Depends(require_roles("client")),
                   db: Session = Depends(get_db)):
    """Клиент удаляет свой аккаунт. Будущие записи отменяются, история остаётся."""
    if not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Пароль неверен")
    for appointment_id in db.scalars(active_appointments_query(user.id, as_master=False)).all():
        appointment = db.get(Appointment, appointment_id)
        appointment.status = "cancelled"
        release_slots(db, appointment.id)
    user.deleted_at = datetime.utcnow()
    drop_sessions(db, user.id)
    db.commit()
    response.delete_cookie(SESSION_COOKIE)
    return {"message": "Учётная запись удалена"}


@users_router.get("", response_model=List[UserOut])
def list_users(role: Optional[str] = None, q: Optional[str] = None,
               include_deleted: bool = False, db: Session = Depends(get_db)):
    query = select(User)
    if role:
        role_row = db.scalar(select(Role).where(Role.code == role))
        if role_row is None:
            return []
        query = query.where(User.role_id == role_row.id)
    if q:
        like = "%" + q.strip() + "%"
        query = query.where(or_(User.full_name.ilike(like), User.email.ilike(like),
                                User.phone.ilike(like)))
    if not include_deleted:
        query = query.where(User.deleted_at.is_(None))
    users = db.scalars(query.order_by(User.id).limit(500)).all()
    return [user_out(db, u) for u in users]


def get_user_or_404(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    return user


@users_router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: int, db: Session = Depends(get_db)):
    return user_out(db, get_user_or_404(db, user_id))


@users_router.patch("/{user_id}/role", response_model=UserOut)
def change_role(user_id: int, data: RoleChange, admin: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    user = get_user_or_404(db, user_id)
    if user.id == admin.id:
        raise HTTPException(status_code=409, detail="Свою роль менять нельзя")
    new_role = db.scalar(select(Role).where(Role.code == data.role))
    if new_role is None:
        raise HTTPException(status_code=422, detail="Неизвестная роль")
    if role_code(user, db) == "master" and db.scalar(
            active_appointments_query(user.id, as_master=True).limit(1)):
        raise HTTPException(status_code=409,
                            detail="У мастера есть предстоящие записи, сначала перенесите их")
    user.role_id = new_role.id
    drop_sessions(db, user.id)  # пусть войдёт заново с новыми правами
    db.commit()
    db.refresh(user)
    return user_out(db, user)


@users_router.post("/{user_id}/block", response_model=UserOut)
def block_user(user_id: int, admin: User = Depends(get_current_user),
               db: Session = Depends(get_db)):
    user = get_user_or_404(db, user_id)
    if user.id == admin.id:
        raise HTTPException(status_code=409, detail="Себя заблокировать нельзя")
    if user.deleted_at is not None:
        raise HTTPException(status_code=409, detail="Пользователь уже заблокирован")
    code = role_code(user, db)
    if code == "master" and db.scalar(active_appointments_query(user.id, as_master=True).limit(1)):
        raise HTTPException(status_code=409,
                            detail="У мастера есть предстоящие записи, сначала перенесите их")
    if code == "client":
        for appointment_id in db.scalars(active_appointments_query(user.id, as_master=False)).all():
            appointment = db.get(Appointment, appointment_id)
            appointment.status = "cancelled"
            release_slots(db, appointment.id)
    user.deleted_at = datetime.utcnow()
    drop_sessions(db, user.id)
    db.commit()
    db.refresh(user)
    return user_out(db, user)


@users_router.post("/{user_id}/restore", response_model=UserOut)
def restore_user(user_id: int, db: Session = Depends(get_db)):
    user = get_user_or_404(db, user_id)
    if user.deleted_at is None:
        raise HTTPException(status_code=409, detail="Пользователь не заблокирован")
    user.deleted_at = None
    db.commit()
    db.refresh(user)
    return user_out(db, user)


class GroupIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: Optional[str] = None


class GroupUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = None


class GroupOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: Optional[str]


class MemberIn(BaseModel):
    user_id: int


def get_group_or_404(db: Session, group_id: int) -> UserGroup:
    group = db.get(UserGroup, group_id)
    if group is None:
        raise HTTPException(status_code=404, detail="Группа не найдена")
    return group


@groups_router.get("", response_model=List[GroupOut])
def list_groups(db: Session = Depends(get_db)):
    return db.scalars(select(UserGroup).order_by(UserGroup.name)).all()


@groups_router.post("", response_model=GroupOut, status_code=201)
def create_group(data: GroupIn, db: Session = Depends(get_db)):
    group = UserGroup(**data.model_dump())
    db.add(group)
    db.commit()
    db.refresh(group)
    return group


@groups_router.patch("/{group_id}", response_model=GroupOut)
def update_group(group_id: int, data: GroupUpdate, db: Session = Depends(get_db)):
    group = get_group_or_404(db, group_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        if value is None and field == "name":
            continue
        setattr(group, field, value)
    db.commit()
    db.refresh(group)
    return group


@groups_router.delete("/{group_id}", status_code=204)
def delete_group(group_id: int, db: Session = Depends(get_db)):
    group = get_group_or_404(db, group_id)
    db.execute(delete(UserGroupMember).where(UserGroupMember.group_id == group.id))
    db.delete(group)
    db.commit()


@groups_router.get("/{group_id}/members", response_model=List[UserOut])
def list_members(group_id: int, db: Session = Depends(get_db)):
    get_group_or_404(db, group_id)
    users = db.scalars(
        select(User)
        .join(UserGroupMember, UserGroupMember.user_id == User.id)
        .where(UserGroupMember.group_id == group_id)
        .order_by(User.full_name)
    ).all()
    return [user_out(db, u) for u in users]


@groups_router.post("/{group_id}/members", response_model=List[UserOut], status_code=201)
def add_member(group_id: int, data: MemberIn, db: Session = Depends(get_db)):
    get_group_or_404(db, group_id)
    user = get_user_or_404(db, data.user_id)
    if db.get(UserGroupMember, (user.id, group_id)):
        raise HTTPException(status_code=409, detail="Пользователь уже в группе")
    db.add(UserGroupMember(user_id=user.id, group_id=group_id))
    db.commit()
    return list_members(group_id, db)


@groups_router.delete("/{group_id}/members/{user_id}", status_code=204)
def remove_member(group_id: int, user_id: int, db: Session = Depends(get_db)):
    member = db.get(UserGroupMember, (user_id, group_id))
    if member is None:
        raise HTTPException(status_code=404, detail="Пользователя нет в группе")
    db.delete(member)
    db.commit()