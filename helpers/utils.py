from typing import Optional
from entities import ExteriorType, _QUALITY_MAP, QualityType
import json
import os
from pathlib import Path
# ---------------------------------------------------------------------------
# Overall helpers
# ---------------------------------------------------------------------------


def dumpToTempFile(data):
    """Creates a temp file and writes the json data to it, creates a new file if current exists"""
    cwd = os.getcwd()
    DIR = f"{cwd}\\tmp"

    if not os.path.exists(DIR):
        os.mkdir(DIR)

    count = len([name for name in os.listdir(DIR) if os.path.isfile(os.path.join(DIR, name))])

    with open(f'{DIR}/tmp_{count}.json', "x", encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def _parse_usd_cents(value: str | None) -> Optional[int]:
    """Convert DMarket USD string (e.g. "1560") to cents integer."""
    if not value:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def _parse_exterior(raw: str | None) -> Optional[str]:
    """Normalise exterior string to ExteriorType enum value, or None."""
    if not raw:
        return None
    valid = {e.value for e in ExteriorType}
    return raw if raw in valid else None


def _parse_quality(raw: str | None) -> Optional[str]:
    """Normalise quality string to QualityType enum value, or None."""
    if not raw:
        return None
    valid = {e.value for e in QualityType}
    return raw if raw in valid else None


def _parse_sticker_slots(stickers_raw: list[dict]) -> list[dict]:
    """
    DMarket returns stickers without slot indices.
    We assign 0-indexed slots in order (max 4 stickers on CS2 skins).
    """
    return [
        {
            "name":  s.get("name", ""),
            "image": s.get("image", ""),
            "slot":  idx,
            "wear":  s.get("wear"),   # DMarket does not always expose wear
        }
        for idx, s in enumerate(stickers_raw[:4])
    ]


