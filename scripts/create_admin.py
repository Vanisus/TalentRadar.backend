import asyncio
import sys
from pathlib import Path

# Добавляем корневую директорию в PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from fastapi_users.password import PasswordHelper

from app.config import settings
from app.models.user import User, UserRole
from app.database import Base


async def create_admin():
    """Создаёт первого админа в базе"""
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    # Создаём таблицы (если их нет)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        # Проверяем, есть ли уже админ
        from sqlalchemy import select
        result = await session.execute(
            select(User).where(User.email == "admin@example.com")
        )
        existing_admin = result.scalar_one_or_none()

        if existing_admin:
            print("❌ Админ уже существует!")
            return

        # Хешируем пароль
        password_helper = PasswordHelper()
        hashed_password = password_helper.hash("admin123")

        # Создаём админа
        admin = User(
            email="admin@example.com",
            hashed_password=hashed_password,
            is_active=True,
            is_superuser=True,
            is_verified=True,
            role=UserRole.ADMIN,
        )

        session.add(admin)
        await session.commit()

        print("✅ Админ создан!")
        print("   Email: admin@example.com")
        print("   Password: admin123")


if __name__ == "__main__":
    asyncio.run(create_admin())
