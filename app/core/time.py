from datetime import datetime
from zoneinfo import ZoneInfo

from app.core.config import settings


def get_app_timezone() -> ZoneInfo:
    """возвращает таймзону приложения"""
    return ZoneInfo(settings.timezone_name)


MOSCOW_TZ = get_app_timezone()


def now_moscow() -> datetime:
    """возвращает текущее время по москве"""
    return datetime.now(MOSCOW_TZ)
