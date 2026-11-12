"""Runtime settings, read from the environment (and a .env file if present)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import find_dotenv, load_dotenv

# Walks up from this file, so backend/.env or a repo-root .env both work.
load_dotenv(find_dotenv(usecwd=True) or find_dotenv())

REPO_ROOT = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class Settings:
    cache_ttl_seconds: int = int(os.getenv("CACHE_TTL_SECONDS", "21600"))
    ui_dir: Path = Path(os.getenv("UI_DIR", str(REPO_ROOT / "ui")))
    email_user: str | None = os.getenv("EMAIL_USER")
    email_password: str | None = os.getenv("EMAIL_PASSWORD")
    email_recipient: str | None = os.getenv("EMAIL_RECIPIENT")
    smtp_host: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port: int = int(os.getenv("SMTP_PORT", "465"))


settings = Settings()
