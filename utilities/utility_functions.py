import datetime
from time import timezone


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
