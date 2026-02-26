from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette import status
from starlette.responses import JSONResponse

from app.core.users import fastapi_users
from app.schemas.user import UserCreate, UserRead, UserUpdate
from app.routers import hr, candidates, admin, auth, candidate_profile, hr_candidates
from app.middleware.logging import LoggingMiddleware
from app.middleware.token_blacklist import TokenBlacklistMiddleware
from app.exceptions import DomainError, NotFoundError, ForbiddenError, ConflictError, ValidationError

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
app.include_router(candidate_profile.router)
app.include_router(hr_candidates.router)

@app.exception_handler(DomainError)
async def domain_exception_handler(request: Request, exc: DomainError):
    if isinstance(exc, NotFoundError):
        status_code = status.HTTP_404_NOT_FOUND
    elif isinstance(exc, ForbiddenError):
        status_code = status.HTTP_403_FORBIDDEN
    elif isinstance(exc, ConflictError):
        status_code = status.HTTP_409_CONFLICT
    elif isinstance(exc, ValidationError):
        status_code = status.HTTP_400_BAD_REQUEST
    else:
        status_code = status.HTTP_400_BAD_REQUEST

    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
            }
        },
    )

@app.get("/")
async def root():
    return {"message": "Recruitment API is running"}
