from typing import Optional


class GringottsError(Exception):
    code: str
    secondary_code: Optional[str] = None
    message: str
    details: Optional[dict] = None

    def __init__(
        self,
        code: str,
        message: str,
        details: Optional[dict] = None,
        secondary_code: Optional[str] = None,
    ):
        self.code = code
        self.message = message
        self.details = details or {}
        self.secondary_code = secondary_code

    def __str__(self) -> str:
        detail_str = f" | details={self.details}" if self.details else ""
        secondary_code_str = (
            f" (secondary_code={self.secondary_code})" if self.secondary_code else ""
        )
        return f"{self.code}{secondary_code_str}: {self.message}{detail_str}"
