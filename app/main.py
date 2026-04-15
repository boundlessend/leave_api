from fastapi import FastAPI

from app.api.errors import register_exception_handlers
from app.api.routes_admin import router as admin_router
from app.api.routes_auth import router as auth_router
from app.api.routes_leave_requests import router as leave_requests_router
from app.core.config import settings

app = FastAPI(title=settings.app_title, debug=settings.debug)
register_exception_handlers(app)
app.include_router(auth_router)
app.include_router(leave_requests_router)
app.include_router(admin_router)
