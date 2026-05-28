"""
Configuration for the Dzen RSS module.

LLM for content rewriting is now OpenAI (ChatGPT API).
"""

from dataclasses import dataclass
import os
from pathlib import Path

# Optional: load .env if python-dotenv is installed
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


@dataclass
class LLMConfig:
    """LLM settings for rewriting articles."""
    api_key: str
    model: str
    base_url: str = "https://api.openai.com/v1"   # Default OpenAI
    temperature: float = 0.4
    max_tokens: int = 2200


@dataclass
class DzenConfig:
    """Main configuration for Dzen RSS generation."""
    articles_dir: Path = Path("dzen_articles")
    llm: LLMConfig = None


# ============================================
# OpenAI Configuration (ChatGPT)
# ============================================

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")   # Good balance of quality and cost for Dzen articles

if not OPENAI_API_KEY:
    raise RuntimeError(
        "OPENAI_API_KEY is not set.\n"
        "Please create a .env file in the dzen/ folder (copy from .env.example)\n"
        "or set the OPENAI_API_KEY environment variable."
    )

config = DzenConfig(
    llm=LLMConfig(
        api_key=OPENAI_API_KEY,
        model=OPENAI_MODEL,
    )
)

config.articles_dir.mkdir(parents=True, exist_ok=True)