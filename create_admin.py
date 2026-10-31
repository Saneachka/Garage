import getpass

from sqlalchemy import select

from auth import hash_password
from database import SessionLocal
from models import Role, User


def main():
    full_name = input("Имя администратора: ").strip()
    email = input("Почта: ").strip().lower()
    password = getpass.getpass("Пароль (от 8 символов, при вводе не отображается): ")
    if len(password) < 8:
        print("Пароль слишком короткий")
        return

    db = SessionLocal()
    try:
        if db.scalar(select(User).where(User.email == email)):
            print("Пользователь с такой почтой уже есть")
            return
        role = db.scalar(select(Role).where(Role.code == "admin"))
        if role is None:
            role = Role(code="admin", name="Администратор")
            db.add(role)
            db.flush()
        db.add(User(
            role_id=role.id,
            full_name=full_name,
            email=email,
            password_hash=hash_password(password),
        ))
        db.commit()
        print("Администратор создан")
    finally:
        db.close()


if __name__ == "__main__":
    main()