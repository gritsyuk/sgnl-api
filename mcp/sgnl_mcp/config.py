from pathlib import Path
from typing import Optional
from uuid import UUID

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from .profiles import Profile

DEFAULT_EXTENSIONS = (
    ".pdf", ".dwg", ".dxf", ".dgn", ".rvt", ".ifc", ".nwd", ".nwc",
    ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt", ".csv", ".xml",
    ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".zip",
)
STATE_DIR = Path.home() / ".sgnl-mcp"


class Settings(BaseSettings):
    """All configuration comes from the environment (or a .env file); none of it from tool arguments."""

    model_config = SettingsConfigDict(env_prefix="SGNL_MCP_", env_file=".env", extra="ignore", populate_by_name=True)

    client_id: str = Field(validation_alias="SGNL_CLIENT_ID")
    client_secret: SecretStr = Field(validation_alias="SGNL_CLIENT_SECRET")
    base_url: str = "https://api.sgnl.pro/public/v1"

    profile: Profile = Profile.READ
    # User id SIGNAL records as the author of every write. Never taken from the agent.
    actor_user_id: Optional[UUID] = None
    # Only files under this directory can be uploaded.
    upload_root: Optional[Path] = None
    allowed_extensions: tuple[str, ...] = DEFAULT_EXTENSIONS
    # Write tools that run without the two-phase preview. Workflow tools can never be listed.
    auto_confirm: tuple[str, ...] = ()

    rate_per_sec: float = Field(3.0, gt=0, le=10)
    burst: int = Field(6, ge=1, le=50)
    max_concurrency: int = Field(4, ge=1, le=10)
    http_timeout: float = 30.0
    tool_timeout: float = 30.0
    upload_timeout: float = 600.0
    max_response_chars: int = 20_000
    confirmation_ttl_sec: int = 300
    cache_ttl_sec: int = 300

    audit_path: Path = STATE_DIR / "audit.jsonl"
    state_path: Path = STATE_DIR / "state.sqlite"

    @field_validator("profile", mode="before")
    @classmethod
    def _parse_profile(cls, value):
        return Profile.parse(value) if isinstance(value, str) else value

    @field_validator("allowed_extensions", "auto_confirm", mode="before")
    @classmethod
    def _split_csv(cls, value):
        if isinstance(value, str):
            return tuple(v.strip().lower() if v.strip().startswith(".") else v.strip() for v in value.split(",") if v.strip())
        return value

    @model_validator(mode="after")
    def _check_write_requirements(self):
        if self.profile >= Profile.WRITE:
            if self.actor_user_id is None:
                raise ValueError("SGNL_MCP_ACTOR_USER_ID is required for the write and workflow profiles")
            if self.upload_root is None:
                raise ValueError("SGNL_MCP_UPLOAD_ROOT is required for the write and workflow profiles")
        return self
