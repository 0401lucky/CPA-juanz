from typing import Any


def _extract_str(payload: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def extract_credential_identity(payload: dict[str, Any]) -> tuple[str | None, str | None]:
    email = _extract_str(payload, "email", "user_email")
    project_id = _extract_str(payload, "project_id", "projectId")

    if not email:
        metadata = payload.get("metadata")
        if isinstance(metadata, dict):
            email = _extract_str(metadata, "email", "user_email")
            project_id = project_id or _extract_str(metadata, "project_id", "projectId")

    token = payload.get("token")
    if isinstance(token, dict):
        email = email or _extract_str(token, "email")
        project_id = project_id or _extract_str(token, "project_id", "projectId")

    storage = payload.get("storage")
    if isinstance(storage, dict):
        email = email or _extract_str(storage, "email")
        project_id = project_id or _extract_str(storage, "project_id", "projectId")

    if email:
        email = email.lower()
    return email, project_id


def build_display_name(payload: dict[str, Any], fallback_name: str) -> str:
    email, project_id = extract_credential_identity(payload)
    if email and project_id:
        return f"{email} / {project_id}"
    if email:
        return email
    return fallback_name

