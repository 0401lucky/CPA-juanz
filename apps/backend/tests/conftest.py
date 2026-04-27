import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import AppSettings
from app.main import create_app


class FakeCPAClient:
    def __init__(self) -> None:
        self.started_project_ids: list[str] = []
        self.callback_redirect_urls: list[str | None] = []
        self.uploaded_files: dict[str, dict] = {}
        self.deleted_files: list[str] = []
        self.oauth_state = "gem-state-123"
        self.oauth_completed = False
        self.oauth_error: str | None = None
        self.temp_auth_name = "geminicli-oauth-user@example.com-google-one.json"
        self.temp_auth_payload = {
            "email": "oauth-user@example.com",
            "project_id": "google-one-project",
            "token": {
                "access_token": "oauth-access-token",
                "refresh_token": "oauth-refresh-token"
            }
        }
        self.temp_auth_deleted = False
        self.baseline_files: list[dict] = []

    def start_gemini_oauth(self, project_id: str, *, is_webui: bool = True) -> dict:
        self.started_project_ids.append(project_id)
        return {
            "auth_url": "https://accounts.google.com/o/oauth2/v2/auth?mock=1",
            "state": self.oauth_state
        }

    def submit_oauth_callback(
        self,
        provider: str,
        *,
        redirect_url: str | None = None,
        code: str | None = None,
        state: str | None = None
    ) -> None:
        assert provider == "gemini"
        self.callback_redirect_urls.append(redirect_url)
        self.oauth_completed = True

    def get_auth_status(self, state: str) -> dict:
        assert state == self.oauth_state
        if self.oauth_error:
            return {"status": "error", "error": self.oauth_error}
        if self.oauth_completed:
            return {"status": "ok"}
        return {"status": "wait"}

    def list_auth_files(self) -> list[dict]:
        items = list(self.baseline_files)
        if self.oauth_completed and not self.temp_auth_deleted:
            items.append(
                {
                    "name": self.temp_auth_name,
                    "provider": "gemini",
                    "modtime": datetime.now(timezone.utc).isoformat()
                }
            )
        return items

    def download_auth_file(self, name: str) -> dict:
        assert name == self.temp_auth_name
        return self.temp_auth_payload

    def delete_auth_file(self, name: str) -> None:
        self.deleted_files.append(name)
        if name == self.temp_auth_name:
            self.temp_auth_deleted = True

    def upload_auth_file(self, name: str, payload: dict) -> None:
        self.uploaded_files[name] = payload


@pytest.fixture()
def settings(tmp_path: Path) -> AppSettings:
    frontend_dist_path = tmp_path / "frontend-dist"
    frontend_dist_path.mkdir(parents=True, exist_ok=True)
    (frontend_dist_path / "index.html").write_text(
        "<!doctype html><html><body><div id='root'>frontend ok</div></body></html>",
        encoding="utf-8"
    )
    return AppSettings(
        database_path=tmp_path / "donation-station.db",
        frontend_dist_path=frontend_dist_path,
        admin_password="super-admin-password",
        session_secret="test-session-secret",
        cpa_base_url="https://demo-cpa.example.com",
        cpa_management_key="demo-management-key",
        cpa_auth_file_prefix="donate-geminicli",
        turnstile_secret_key="",
        turnstile_site_key="",
        rate_limit_window_seconds=60,
        rate_limit_max_requests=20
    )


@pytest.fixture()
def fake_cpa_client() -> FakeCPAClient:
    return FakeCPAClient()


@pytest.fixture()
def client(settings: AppSettings, fake_cpa_client: FakeCPAClient) -> TestClient:
    app = create_app(settings=settings, cpa_client=fake_cpa_client)
    return TestClient(app)


def gemini_payload(email: str = "person@example.com", project_id: str = "proj-1") -> bytes:
    return json.dumps(
        {
            "email": email,
            "project_id": project_id,
            "token": {
                "access_token": "access-token",
                "refresh_token": "refresh-token"
            }
        }
    ).encode("utf-8")
