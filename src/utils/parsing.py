# src/utils/parsing.py
from typing import Optional


def parse_float(value: str) -> Optional[float]:
    """Parse human-entered number string into float, handling dot/comma styles."""
    if value is None:
        return None
    value = str(value).strip()
    if not value:
        return None

    # Remove spaces, remove thousand separators, normalize decimal
    value = value.replace(" ", "").replace(".", "").replace(",", ".")
    try:
        return float(value)
    except Exception:
        return None
