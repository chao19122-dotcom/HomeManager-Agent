"""Configuration: secrets stay in .env, never in source or logs."""
from dataclasses import dataclass
from pathlib import Path
import os
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent


@dataclass(frozen=True)
class Settings:
    api_key: str = ""
    base_url: str = "https://api.deepseek.com"
    model: str = "deepseek-flash"
    max_rounds: int = 3
    max_calls_per_round: int = 8
    timeout: float = 30.0

    @classmethod
    def load(cls):
        load_dotenv(ROOT / ".env", override=False)
        return cls(
            api_key=os.getenv("DEEPSEEK_API_KEY", "").strip(),
            base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").strip(),
            model=os.getenv("DEEPSEEK_MODEL", "deepseek-flash").strip(),
        )
