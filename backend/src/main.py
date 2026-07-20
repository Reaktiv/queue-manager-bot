"""
FastAPI ilovasining kirish nuqtasi.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.v1.routers import (
    auth,
    completion,
    export,
    groups,
    notification_templates,
    statistics,
    superadmin,
    tasks,
    users,
)
from .core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = None
    if settings.EMBEDDED_SCHEDULER_ENABLED:
        from .scheduler.runner import create_scheduler

        scheduler = create_scheduler()
        scheduler.start()
    try:
        yield
    finally:
        if scheduler is not None and scheduler.running:
            scheduler.shutdown()


app = FastAPI(
    title=settings.APP_NAME,
    description="Telegram Duty & Queue Management Platform API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.DEBUG else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(groups.router, prefix="/api/v1")
app.include_router(tasks.router, prefix="/api/v1")
app.include_router(completion.router, prefix="/api/v1")
app.include_router(statistics.router, prefix="/api/v1")
app.include_router(notification_templates.router, prefix="/api/v1")
app.include_router(export.router, prefix="/api/v1")
app.include_router(superadmin.router, prefix="/api/v1")

_MAINTENANCE_EXEMPT_PREFIXES = (
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/api/v1/superadmin",
    "/api/v1/auth",
)


@app.middleware("http")
async def maintenance_mode_middleware(request, call_next):
    """
    Agar Super Admin "maintenance mode"ni yoqqan bo'lsa, oddiy foydalanuvchi
    (bot/Mini App) so'rovlari 503 bilan qaytariladi. Super Admin endpointlari
    va auth/health/docs har doim ochiq qoladi.
    """
    if any(request.url.path.startswith(p) for p in _MAINTENANCE_EXEMPT_PREFIXES):
        return await call_next(request)

    from fastapi.responses import JSONResponse

    from .infrastructure.db.session import async_session_factory
    from .repositories.settings_repository import SettingsRepository

    async with async_session_factory() as session:
        value = await SettingsRepository(session).get("maintenance_mode")

    if value == "true":
        return JSONResponse(
            status_code=503,
            content={
                "success": False,
                "data": None,
                "message": "Tizim texnik ishlar uchun vaqtincha o'chirilgan. Birozdan so'ng qayta urinib ko'ring.",
            },
        )

    return await call_next(request)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request, exc: Exception):
    """
    Kutilmagan barcha xatolarni `system_logs` jadvaliga yozadi (Super Admin
    Dashboard'dagi "Error Logs" bo'limi shu yerdan o'qiydi) va foydalanuvchiga
    umumiy 500 xabarini qaytaradi.
    """
    import json

    import structlog
    from fastapi.responses import JSONResponse

    from .infrastructure.db.session import async_session_factory
    from .repositories.settings_repository import SettingsRepository

    logger = structlog.get_logger()
    logger.error("unhandled_exception", path=str(request.url.path), error=str(exc))

    try:
        async with async_session_factory() as session:
            await SettingsRepository(session).add_log(
                level="ERROR",
                message=str(exc),
                context=json.dumps({"path": str(request.url.path), "method": request.method}),
            )
            await session.commit()
    except Exception:
        pass  # Log yozishning o'zi ham muvaffaqiyatsiz bo'lsa, asosiy javobni bloklamaymiz

    return JSONResponse(
        status_code=500,
        content={"success": False, "data": None, "message": "Kutilmagan xatolik yuz berdi"},
    )


@app.get("/health", tags=["System"])
async def health_check():
    return {"status": "ok", "app": settings.APP_NAME, "env": settings.APP_ENV}
