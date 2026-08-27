"""Runtime configuration, read once from the environment.

Every service in the network reads the same settings object, so a single
``.env`` file at the repository root configures the whole network.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv


def _find_repo_root() -> Path:
    """Walk up from this file until the repository root is found.

    The root is where ``.env``, the seeded TinyDB files and the scripts live.
    Searching for a marker keeps this correct whether the package is imported
    from the source tree or from an editable install inside an agent's venv.
    """
    here = Path(__file__).resolve()
    for candidate in here.parents:
        if (candidate / "scripts" / "install.sh").exists():
            return candidate
    return here.parents[4]


REPO_ROOT = _find_repo_root()

load_dotenv(REPO_ROOT / ".env")


def _env(name: str, default: str) -> str:
    value = os.environ.get(name)
    return default if value is None or value == "" else value


@dataclass(frozen=True)
class Settings:
    """Everything the AtlasTrip services need to know about their environment."""

    postgres_dsn: str = field(
        default_factory=lambda: _env(
            "ATLASTRIP_POSTGRES_DSN",
            "postgresql://localhost:5432/atlastrip",
        )
    )
    """libpq-style DSN used by asyncpg for the business tables."""

    tinydb_dir: Path = field(
        default_factory=lambda: Path(
            _env("ATLASTRIP_TINYDB_DIR", str(REPO_ROOT / "data" / "tinydb"))
        )
    )
    """Directory holding the TinyDB document collections."""

    mcp_url: str = field(
        default_factory=lambda: _env(
            "ATLASTRIP_MCP_URL", "http://127.0.0.1:8100/mcp"
        )
    )
    """Streamable-HTTP endpoint of the shared travel inventory MCP server."""

    openai_api_key: str = field(
        default_factory=lambda: _env("OPENAI_API_KEY", "")
    )

    openai_model: str = field(
        default_factory=lambda: _env("ATLASTRIP_MODEL", "gpt-4.1-mini")
    )
    """Model id used by every framework. Kept identical so that behavioural
    differences between agents come from the frameworks, not the models."""

    reasoning_mode: str = field(
        default_factory=lambda: _env("ATLASTRIP_REASONING", "llm").lower()
    )
    """``llm`` runs the real framework agent. ``deterministic`` skips the model
    and calls the agent's own service layer directly, which is what the test
    suite uses so it can run offline and for free."""

    host: str = field(default_factory=lambda: _env("ATLASTRIP_HOST", "127.0.0.1"))

    call_timeout_seconds: float = field(
        default_factory=lambda: float(_env("ATLASTRIP_CALL_TIMEOUT", "180"))
    )
    """How long one agent will wait on another. Generous, because a specialist
    may be waiting on a model, and the Concierge may be waiting on four of
    them."""

    log_level: str = field(
        default_factory=lambda: _env("ATLASTRIP_LOG_LEVEL", "INFO").upper()
    )

    @property
    def uses_llm(self) -> bool:
        return self.reasoning_mode == "llm" and bool(self.openai_api_key)

    def sqlalchemy_dsn(self) -> str:
        """The same database, spelled the way SQLAlchemy's asyncpg driver wants."""
        dsn = self.postgres_dsn
        for prefix in ("postgresql+asyncpg://", "postgresql://", "postgres://"):
            if dsn.startswith(prefix):
                return "postgresql+asyncpg://" + dsn[len(prefix) :]
        return dsn


@lru_cache(maxsize=1)
def settings() -> Settings:
    """Process-wide settings singleton."""
    return Settings()
