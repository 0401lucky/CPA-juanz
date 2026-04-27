from tests.conftest import gemini_payload


def test_public_json_upload_creates_donor_and_sets_pending_review(client):
    response = client.post(
        "/api/public/credentials/json",
        files={
            "file": ("gemini.json", gemini_payload(), "application/json")
        }
    )

    assert response.status_code == 201
    body = response.json()
    assert body["management_code"]
    assert body["credential"]["status"] == "pending_review"
    assert body["credential"]["parsed_email"] == "person@example.com"
    assert body["credential"]["parsed_project_id"] == "proj-1"

    list_response = client.get("/api/me/credentials")
    assert list_response.status_code == 200
    assert len(list_response.json()["items"]) == 1


def test_duplicate_payload_is_blocked_for_review(client):
    first = client.post(
        "/api/public/credentials/json",
        files={
            "file": ("gemini.json", gemini_payload(), "application/json")
        }
    )
    assert first.status_code == 201

    second_client = client.__class__(client.app)
    second = second_client.post(
        "/api/public/credentials/json",
        files={
            "file": ("gemini-copy.json", gemini_payload(), "application/json")
        }
    )

    assert second.status_code == 201
    assert second.json()["credential"]["status"] == "duplicate_blocked"


def test_management_code_login_restores_access(client):
    upload = client.post(
        "/api/public/credentials/json",
        files={
            "file": ("gemini.json", gemini_payload(), "application/json")
        }
    )
    management_code = upload.json()["management_code"]

    fresh_client = client.__class__(client.app)
    auth_response = fresh_client.post(
        "/api/public/management-code/session",
        json={"management_code": management_code}
    )

    assert auth_response.status_code == 200
    list_response = fresh_client.get("/api/me/credentials")
    assert list_response.status_code == 200
    assert len(list_response.json()["items"]) == 1


def test_oauth_callback_relay_captures_credential_and_returns_management_code(
    client, fake_cpa_client
):
    start = client.post(
        "/api/public/oauth/gemini/start",
        json={"project_id": "GOOGLE_ONE"}
    )

    assert start.status_code == 200
    body = start.json()
    assert body["auth_url"].startswith("https://accounts.google.com/")

    finalize = client.post(
        "/api/public/oauth/gemini/callback-relay",
        json={
            "flow_id": body["flow_id"],
            "redirect_url": "https://donate.example.com/callback?code=oauth-code&state=gem-state-123"
        }
    )

    assert finalize.status_code == 200
    result = finalize.json()
    assert result["management_code"]
    assert result["credential"]["status"] == "pending_review"
    assert result["credential"]["parsed_email"] == "oauth-user@example.com"
    assert fake_cpa_client.deleted_files == [fake_cpa_client.temp_auth_name]

