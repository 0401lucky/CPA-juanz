from pathlib import Path

from pydantic import BaseModel, Field


class AppSettings(BaseModel):
    database_path: Path = Field(default=Path("data/donation-station.db"))
    frontend_dist_path: Path = Field(default=Path("frontend-dist"))
    admin_password: str = Field(default="change-me-admin-password")
    session_secret: str = Field(default="change-me-session-secret")
    cpa_base_url: str = Field(default="https://demo-cpa.example.com")
    cpa_management_key: str = Field(default="change-me-management-key")
    cpa_auth_file_prefix: str = Field(default="donate-geminicli")
    turnstile_secret_key: str = Field(default="")
    turnstile_site_key: str = Field(default="")
    rate_limit_window_seconds: int = Field(default=60)
    rate_limit_max_requests: int = Field(default=20)
    donor_cookie_name: str = Field(default="donation_donor_session")
    admin_cookie_name: str = Field(default="donation_admin_session")
    donor_cookie_max_age_seconds: int = Field(default=60 * 60 * 12)
    admin_cookie_max_age_seconds: int = Field(default=60 * 60 * 8)
    oauth_poll_attempts: int = Field(default=5)
    oauth_poll_interval_seconds: float = Field(default=0.1)

    @classmethod
    def from_env(cls) -> "AppSettings":
        import os

        return cls(
            database_path=Path(os.getenv("DATABASE_PATH", "data/donation-station.db")),
            frontend_dist_path=Path(os.getenv("FRONTEND_DIST_PATH", "frontend-dist")),
            admin_password=os.getenv("ADMIN_PASSWORD", "change-me-admin-password"),
            session_secret=os.getenv("SESSION_SECRET", "change-me-session-secret"),
            cpa_base_url=os.getenv("EXTERNAL_CPA_BASE_URL", "https://demo-cpa.example.com"),
            cpa_management_key=os.getenv("EXTERNAL_CPA_MANAGEMENT_KEY", "change-me-management-key"),
            cpa_auth_file_prefix=os.getenv("CPA_AUTH_FILE_PREFIX", "donate-geminicli"),
            turnstile_secret_key=os.getenv("TURNSTILE_SECRET_KEY", ""),
            turnstile_site_key=os.getenv("TURNSTILE_SITE_KEY", ""),
            rate_limit_window_seconds=int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60")),
            rate_limit_max_requests=int(os.getenv("RATE_LIMIT_MAX_REQUESTS", "20"))
        )
