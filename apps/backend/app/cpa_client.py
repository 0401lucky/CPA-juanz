from __future__ import annotations

from typing import Any

import httpx


class CPAClient:
    def __init__(self, base_url: str, management_key: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.management_key = management_key

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.management_key}"}

    def list_auth_files(self) -> list[dict[str, Any]]:
        response = httpx.get(
            f"{self.base_url}/v0/management/auth-files",
            headers=self._headers(),
            timeout=20.0
        )
        response.raise_for_status()
        data = response.json()
        return data.get("files", [])

    def start_gemini_oauth(self, project_id: str, *, is_webui: bool = True) -> dict[str, Any]:
        params: dict[str, str] = {"project_id": project_id}
        if is_webui:
            params["is_webui"] = "true"
        response = httpx.get(
            f"{self.base_url}/v0/management/gemini-cli-auth-url",
            headers=self._headers(),
            params=params,
            timeout=20.0
        )
        response.raise_for_status()
        data = response.json()
        auth_url = data.get("auth_url") or data.get("url")
        state = data.get("state")
        if not auth_url or not state:
            raise ValueError("CPA OAuth 响应缺少 auth_url 或 state")
        return {"auth_url": auth_url, "state": state}

    def submit_oauth_callback(
        self,
        provider: str,
        *,
        redirect_url: str | None = None,
        code: str | None = None,
        state: str | None = None
    ) -> None:
        payload: dict[str, Any] = {"provider": provider}
        if redirect_url:
            payload["redirect_url"] = redirect_url
        if code:
            payload["code"] = code
        if state:
            payload["state"] = state
        response = httpx.post(
            f"{self.base_url}/v0/management/oauth-callback",
            headers=self._headers() | {"Content-Type": "application/json"},
            json=payload,
            timeout=20.0
        )
        response.raise_for_status()

    def get_auth_status(self, state: str) -> dict[str, Any]:
        response = httpx.get(
            f"{self.base_url}/v0/management/get-auth-status",
            headers=self._headers(),
            params={"state": state},
            timeout=20.0
        )
        response.raise_for_status()
        data = response.json()

        if "status" in data:
            return data

        sessions = data.get("sessions", [])
        if not sessions:
            return {"status": "ok"}
        session = sessions[0]
        session_status = session.get("status", "")
        if session_status in ("", None):
            return {"status": "wait"}
        if session_status == "completed":
            return {"status": "ok"}
        return {"status": "error", "error": session_status}

    def download_auth_file(self, name: str) -> dict[str, Any]:
        response = httpx.get(
            f"{self.base_url}/v0/management/auth-files/download",
            headers=self._headers(),
            params={"name": name},
            timeout=20.0
        )
        response.raise_for_status()
        return response.json()

    def delete_auth_file(self, name: str) -> None:
        response = httpx.delete(
            f"{self.base_url}/v0/management/auth-files",
            headers=self._headers(),
            params={"name": name},
            timeout=20.0
        )
        response.raise_for_status()

    def upload_auth_file(self, name: str, payload: dict[str, Any]) -> None:
        response = httpx.post(
            f"{self.base_url}/v0/management/auth-files",
            headers=self._headers() | {"Content-Type": "application/json"},
            params={"name": name},
            json=payload,
            timeout=20.0
        )
        response.raise_for_status()

