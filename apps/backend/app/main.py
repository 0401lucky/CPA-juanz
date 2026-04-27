from __future__ import annotations

import json
import time
from collections import defaultdict, deque
from typing import Any

import httpx
from fastapi import FastAPI, File, HTTPException, Request, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from starlette.responses import FileResponse

from app.config import AppSettings
from app.cpa_client import CPAClient
from app.db import Database


class RateLimiter:
    def __init__(self, window_seconds: int, max_requests: int) -> None:
        self.window_seconds = window_seconds
        self.max_requests = max_requests
        self._buckets: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str) -> None:
        now = time.time()
        bucket = self._buckets[key]
        while bucket and now - bucket[0] > self.window_seconds:
            bucket.popleft()
        if len(bucket) >= self.max_requests:
            raise HTTPException(status_code=429, detail="请求过于频繁，请稍后再试")
        bucket.append(now)


class ManagementCodeLoginPayload(BaseModel):
    management_code: str = Field(min_length=8)


class AdminLoginPayload(BaseModel):
    password: str = Field(min_length=1)


class RejectPayload(BaseModel):
    reason: str = Field(min_length=1, max_length=200)


class OAuthStartPayload(BaseModel):
    project_id: str = Field(default="GOOGLE_ONE")
    turnstile_token: str | None = None


class OAuthCallbackRelayPayload(BaseModel):
    flow_id: str
    redirect_url: str | None = None


def create_app(
    *, settings: AppSettings | None = None, cpa_client: CPAClient | Any | None = None
) -> FastAPI:
    resolved_settings = settings or AppSettings.from_env()
    database = Database(resolved_settings.database_path)
    resolved_cpa_client = cpa_client or CPAClient(
        base_url=resolved_settings.cpa_base_url,
        management_key=resolved_settings.cpa_management_key
    )
    limiter = RateLimiter(
        resolved_settings.rate_limit_window_seconds,
        resolved_settings.rate_limit_max_requests
    )

    app = FastAPI(title="CPA Gemini Donation Station")
    app.state.settings = resolved_settings
    app.state.database = database
    app.state.cpa_client = resolved_cpa_client
    app.state.limiter = limiter

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"]
    )

    def rate_limit(request: Request, scope: str) -> None:
        client_host = request.client.host if request.client else "unknown"
        limiter.check(f"{scope}:{client_host}")

    def serialize_credential(record: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": record["id"],
            "source_type": record["source_type"],
            "display_name": record["display_name"],
            "status": record["status"],
            "cpa_file_name": record["cpa_file_name"],
            "rejection_reason": record["rejection_reason"],
            "error_message": record["error_message"],
            "parsed_email": record["parsed_email"],
            "parsed_project_id": record["parsed_project_id"],
            "created_at": record["created_at"],
            "updated_at": record["updated_at"]
        }

    def set_donor_cookie(response: Response, donor_id: str) -> None:
        token = _session_manager(app).sign_donor_session(donor_id)
        response.set_cookie(
            key=resolved_settings.donor_cookie_name,
            value=token,
            httponly=True,
            samesite="lax",
            max_age=resolved_settings.donor_cookie_max_age_seconds
        )

    def set_admin_cookie(response: Response) -> None:
        token = _session_manager(app).sign_admin_session()
        response.set_cookie(
            key=resolved_settings.admin_cookie_name,
            value=token,
            httponly=True,
            samesite="lax",
            max_age=resolved_settings.admin_cookie_max_age_seconds
        )

    def current_donor_id(request: Request) -> str | None:
        token = request.cookies.get(resolved_settings.donor_cookie_name)
        return _session_manager(app).load_donor_session(token)

    def require_donor(request: Request) -> str:
        donor_id = current_donor_id(request)
        if not donor_id:
            raise HTTPException(status_code=401, detail="请先输入管理码")
        donor = database.get_donor(donor_id)
        if not donor:
            raise HTTPException(status_code=401, detail="管理码会话已失效")
        database.touch_donor(donor_id)
        return donor_id

    def require_admin(request: Request) -> None:
        token = request.cookies.get(resolved_settings.admin_cookie_name)
        if not _session_manager(app).is_admin_session(token):
            raise HTTPException(status_code=401, detail="请先登录管理员后台")

    def ensure_donor(request: Request) -> tuple[str, str | None]:
        donor_id = current_donor_id(request)
        if donor_id and database.get_donor(donor_id):
            database.touch_donor(donor_id)
            return donor_id, None
        donor, management_code = database.create_donor()
        return donor["id"], management_code

    async def verify_turnstile(turnstile_token: str | None, request: Request) -> None:
        if not resolved_settings.turnstile_secret_key:
            return
        if not turnstile_token:
            raise HTTPException(status_code=400, detail="缺少人机校验令牌")
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                "https://challenges.cloudflare.com/turnstile/v0/siteverify",
                data={
                    "secret": resolved_settings.turnstile_secret_key,
                    "response": turnstile_token,
                    "remoteip": request.client.host if request.client else ""
                }
            )
            response.raise_for_status()
            if not response.json().get("success"):
                raise HTTPException(status_code=400, detail="人机校验失败")

    def choose_new_auth_file(flow: dict[str, Any], files: list[dict[str, Any]]) -> dict[str, Any]:
        baseline = {
            item.get("name") or item.get("id")
            for item in json.loads(flow["baseline_files_json"])
        }
        candidates = []
        for item in files:
            name = item.get("name") or item.get("id")
            provider = (item.get("provider") or item.get("type") or "").lower()
            if not name or name in baseline:
                continue
            if provider and provider != "gemini":
                continue
            candidates.append(item)
        if not candidates:
            raise HTTPException(status_code=502, detail="未能从 CPA 捕获新的 Gemini 凭证文件")
        candidates.sort(key=lambda item: item.get("modtime", ""), reverse=True)
        return candidates[0]

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/api/public/credentials/json", status_code=201)
    async def public_json_upload(
        request: Request,
        response: Response,
        file: UploadFile = File(...)
    ) -> dict[str, Any]:
        rate_limit(request, "public-json-upload")
        donor_id, management_code = ensure_donor(request)
        payload = json.loads((await file.read()).decode("utf-8"))
        record = database.create_credential_record(
            donor_id=donor_id,
            source_type="json",
            payload=payload,
            fallback_name=file.filename or "gemini.json"
        )
        set_donor_cookie(response, donor_id)
        return {
            "management_code": management_code,
            "credential": serialize_credential(record)
        }

    @app.post("/api/me/credentials/json", status_code=201)
    async def me_json_upload(
        request: Request,
        response: Response,
        file: UploadFile = File(...)
    ) -> dict[str, Any]:
        rate_limit(request, "me-json-upload")
        donor_id = require_donor(request)
        payload = json.loads((await file.read()).decode("utf-8"))
        record = database.create_credential_record(
            donor_id=donor_id,
            source_type="json",
            payload=payload,
            fallback_name=file.filename or "gemini.json"
        )
        set_donor_cookie(response, donor_id)
        return {"management_code": None, "credential": serialize_credential(record)}

    @app.post("/api/public/management-code/session")
    async def donor_session_login(
        payload: ManagementCodeLoginPayload,
        request: Request,
        response: Response
    ) -> dict[str, str]:
        rate_limit(request, "management-code-login")
        donor = database.find_donor_by_management_code(payload.management_code)
        if not donor:
            raise HTTPException(status_code=401, detail="管理码无效")
        database.touch_donor(donor["id"])
        set_donor_cookie(response, donor["id"])
        return {"status": "ok"}

    @app.get("/api/me/credentials")
    def list_my_credentials(request: Request) -> dict[str, Any]:
        donor_id = require_donor(request)
        items = [serialize_credential(item) for item in database.list_credentials_for_donor(donor_id)]
        return {"items": items}

    @app.post("/api/public/oauth/gemini/start")
    async def public_oauth_start(
        payload: OAuthStartPayload,
        request: Request
    ) -> dict[str, Any]:
        rate_limit(request, "public-oauth-start")
        await verify_turnstile(payload.turnstile_token, request)
        donor_id = current_donor_id(request)
        baseline = app.state.cpa_client.list_auth_files()
        started = app.state.cpa_client.start_gemini_oauth(payload.project_id, is_webui=True)
        flow = database.create_oauth_flow(
            state=started["state"],
            donor_id=donor_id,
            project_id=payload.project_id,
            baseline_files=baseline
        )
        return {"flow_id": flow["id"], "auth_url": started["auth_url"]}

    @app.post("/api/me/credentials/oauth/gemini/start")
    async def me_oauth_start(
        payload: OAuthStartPayload,
        request: Request
    ) -> dict[str, Any]:
        require_donor(request)
        return await public_oauth_start(payload, request)

    @app.post("/api/public/oauth/gemini/callback-relay")
    def public_oauth_callback_relay(
        payload: OAuthCallbackRelayPayload,
        request: Request,
        response: Response
    ) -> dict[str, Any]:
        rate_limit(request, "public-oauth-callback")
        flow = database.get_oauth_flow(payload.flow_id)
        if not flow:
            raise HTTPException(status_code=404, detail="OAuth 流程不存在或已过期")
        if payload.redirect_url:
            app.state.cpa_client.submit_oauth_callback(
                "gemini", redirect_url=payload.redirect_url
            )
        for _ in range(resolved_settings.oauth_poll_attempts):
            status = app.state.cpa_client.get_auth_status(flow["state"])
            if status.get("status") == "ok":
                break
            if status.get("status") == "error":
                raise HTTPException(status_code=400, detail=status.get("error") or "OAuth 授权失败")
            time.sleep(resolved_settings.oauth_poll_interval_seconds)
        else:
            raise HTTPException(status_code=408, detail="OAuth 状态仍未完成")

        auth_file = choose_new_auth_file(flow, app.state.cpa_client.list_auth_files())
        auth_name = auth_file.get("name") or auth_file.get("id")
        payload_json = app.state.cpa_client.download_auth_file(auth_name)
        app.state.cpa_client.delete_auth_file(auth_name)

        donor_id = flow.get("donor_id")
        management_code = None
        if not donor_id:
            donor, management_code = database.create_donor()
            donor_id = donor["id"]

        record = database.create_credential_record(
            donor_id=donor_id,
            source_type="oauth",
            payload=payload_json,
            fallback_name=auth_name
        )
        database.delete_oauth_flow(flow["id"])
        set_donor_cookie(response, donor_id)
        return {
            "management_code": management_code,
            "credential": serialize_credential(record)
        }

    @app.post("/api/admin/session")
    def admin_session_login(
        payload: AdminLoginPayload,
        response: Response
    ) -> dict[str, str]:
        if payload.password != resolved_settings.admin_password:
            raise HTTPException(status_code=401, detail="管理员密码错误")
        set_admin_cookie(response)
        return {"status": "ok"}

    @app.get("/api/admin/credentials")
    def admin_list_credentials(request: Request, status: str | None = None) -> dict[str, Any]:
        require_admin(request)
        return {"items": [serialize_credential(item) for item in database.list_credentials(status)]}

    @app.post("/api/admin/credentials/{credential_id}/publish")
    def admin_publish_credential(request: Request, credential_id: str) -> dict[str, Any]:
        require_admin(request)
        credential = database.get_credential(credential_id)
        if not credential:
            raise HTTPException(status_code=404, detail="凭证不存在")
        if credential["status"] == "published":
            return {"credential": serialize_credential(credential)}
        if not credential["payload_json"]:
            raise HTTPException(status_code=400, detail="该记录缺少可发布的凭证内容")
        payload_json = json.loads(credential["payload_json"])
        cpa_file_name = f"{resolved_settings.cpa_auth_file_prefix}-{credential['id']}.json"
        app.state.cpa_client.upload_auth_file(cpa_file_name, payload_json)
        updated = database.update_credential(
            credential_id,
            status="published",
            cpa_file_name=cpa_file_name,
            payload_json=None,
            error_message=None
        )
        return {"credential": serialize_credential(updated)}

    @app.post("/api/admin/credentials/{credential_id}/reject")
    def admin_reject_credential(
        request: Request, credential_id: str, payload: RejectPayload
    ) -> dict[str, Any]:
        require_admin(request)
        credential = database.get_credential(credential_id)
        if not credential:
            raise HTTPException(status_code=404, detail="凭证不存在")
        updated = database.update_credential(
            credential_id,
            status="rejected",
            rejection_reason=payload.reason,
            error_message=None
        )
        return {"credential": serialize_credential(updated)}

    @app.delete("/api/me/credentials/{credential_id}")
    def donor_delete_credential(
        request: Request,
        credential_id: str
    ) -> dict[str, Any]:
        donor_id = require_donor(request)
        credential = database.get_credential(credential_id)
        if not credential or credential["donor_id"] != donor_id:
            raise HTTPException(status_code=404, detail="凭证不存在")
        if credential["status"] == "published" and credential["cpa_file_name"]:
            try:
                app.state.cpa_client.delete_auth_file(credential["cpa_file_name"])
                updated = database.update_credential(
                    credential_id,
                    status="deleted",
                    error_message=None
                )
            except Exception as exc:  # pragma: no cover - 防御性分支
                updated = database.update_credential(
                    credential_id,
                    status="delete_failed",
                    error_message=str(exc)
                )
        else:
            updated = database.update_credential(
                credential_id,
                status="deleted",
                error_message=None
            )
        return {"credential": serialize_credential(updated)}

    @app.post("/api/admin/credentials/{credential_id}/delete-retry")
    def admin_retry_delete(
        request: Request,
        credential_id: str
    ) -> dict[str, Any]:
        require_admin(request)
        credential = database.get_credential(credential_id)
        if not credential:
            raise HTTPException(status_code=404, detail="凭证不存在")
        if credential["status"] != "delete_failed" or not credential["cpa_file_name"]:
            raise HTTPException(status_code=400, detail="当前记录不需要重试删除")
        app.state.cpa_client.delete_auth_file(credential["cpa_file_name"])
        updated = database.update_credential(
            credential_id,
            status="deleted",
            error_message=None
        )
        return {"credential": serialize_credential(updated)}

    frontend_dist_path = resolved_settings.frontend_dist_path
    frontend_index_path = frontend_dist_path / "index.html"

    @app.get("/", include_in_schema=False)
    def serve_frontend_index() -> Response:
        if frontend_index_path.exists():
            return FileResponse(frontend_index_path)
        raise HTTPException(status_code=404, detail="前端静态资源不存在")

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_frontend_asset(full_path: str) -> Response:
        target_path = frontend_dist_path / full_path
        if target_path.exists() and target_path.is_file():
            return FileResponse(target_path)
        if frontend_index_path.exists():
            return FileResponse(frontend_index_path)
        raise HTTPException(status_code=404, detail="前端静态资源不存在")

    return app


def _session_manager(app: FastAPI):
    from app.security import SessionManager

    if not hasattr(app.state, "session_manager"):
        app.state.session_manager = SessionManager(app.state.settings.session_secret)
    return app.state.session_manager


def create_dev_app() -> FastAPI:
    return create_app()
