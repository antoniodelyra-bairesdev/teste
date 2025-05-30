from datetime import datetime
from typing import Any

from ehp.config import settings


def str_now() -> str:
    return str(datetime.now())


def str_year() -> int:
    return int(datetime.now().strftime("%Y"))


def str_month() -> int:
    return int(datetime.now().strftime("%m"))


def str_day() -> int:
    return int(datetime.now().strftime("%d"))


def str_time() -> Any:
    return int(datetime.now().strftime("%H:%M:%S"))


def str_date() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def str_datetime() -> str:
    return datetime.now().strftime("%Y-%m-%d, %H:%M:%S")


def str_to_date(str_date: str) -> datetime:
    return datetime.strptime(str_date, settings.DATE_FORMAT["date_only_br"])


def date_to_str(date_obj: datetime) -> str:
    return datetime.strftime(date_obj, settings.DATE_FORMAT["date_only_br"])
