from datetime import datetime


def current_iso() -> str:
    return datetime.utcnow().isoformat()


def deprecated_formatter(value: str) -> str:
    return value.strip().lower().replace(" ", "_")
