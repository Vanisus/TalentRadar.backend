from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.services.users import fastapi_users
from app.schemas.user import UserCreate, UserRead, UserUpdate
from app.routers import hr, candidates, admin, auth
from app.middleware.logging import LoggingMiddleware
from app.middleware.token_blacklist import TokenBlacklistMiddleware  # 👈 НОВОЕ

app = FastAPI(title="Recruitment API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware для логирования
app.add_middleware(LoggingMiddleware)

# Middleware для проверки blacklist токенов
app.add_middleware(TokenBlacklistMiddleware)  # 👈 НОВОЕ

# Кастомный auth с tracking
app.include_router(auth.router)

# Только регистрация и управление пользователями
app.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["auth"],
)

app.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/users",
    tags=["users"],
)

# Бизнес-роутеры
app.include_router(hr.router)
app.include_router(candidates.router)
app.include_router(admin.router)


@app.get("/")
async def root():
    return {"message": "Recruitment API is running"}
