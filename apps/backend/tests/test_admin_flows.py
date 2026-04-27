from tests.conftest import gemini_payload


def test_admin_can_publish_pending_review_to_external_cpa(client, fake_cpa_client):
    upload = client.post(
        "/api/public/credentials/json",
        files={
            "file": ("gemini.json", gemini_payload(), "application/json")
        }
    )
    credential_id = upload.json()["credential"]["id"]

    login = client.post(
        "/api/admin/session",
        json={"password": "super-admin-password"}
    )
    assert login.status_code == 200

    publish = client.post(f"/api/admin/credentials/{credential_id}/publish")

    assert publish.status_code == 200
    body = publish.json()
    assert body["credential"]["status"] == "published"
    assert body["credential"]["cpa_file_name"].startswith("donate-geminicli-")
    assert body["credential"]["cpa_file_name"] in fake_cpa_client.uploaded_files


def test_donor_delete_removes_published_credential_from_external_cpa(
    client, fake_cpa_client
):
    upload = client.post(
        "/api/public/credentials/json",
        files={
            "file": ("gemini.json", gemini_payload(), "application/json")
        }
    )
    credential_id = upload.json()["credential"]["id"]

    client.post("/api/admin/session", json={"password": "super-admin-password"})
    client.post(f"/api/admin/credentials/{credential_id}/publish")

    delete_response = client.delete(f"/api/me/credentials/{credential_id}")

    assert delete_response.status_code == 200
    body = delete_response.json()
    assert body["credential"]["status"] == "deleted"
    assert any(name.startswith("donate-geminicli-") for name in fake_cpa_client.deleted_files)


def test_admin_can_reject_with_reason_and_user_can_see_it(client):
    upload = client.post(
        "/api/public/credentials/json",
        files={
            "file": ("gemini.json", gemini_payload(), "application/json")
        }
    )
    credential_id = upload.json()["credential"]["id"]

    client.post("/api/admin/session", json={"password": "super-admin-password"})
    reject = client.post(
        f"/api/admin/credentials/{credential_id}/reject",
        json={"reason": "凭证缺少有效订阅"}
    )

    assert reject.status_code == 200
    assert reject.json()["credential"]["status"] == "rejected"

    my_credentials = client.get("/api/me/credentials")
    assert my_credentials.status_code == 200
    assert my_credentials.json()["items"][0]["rejection_reason"] == "凭证缺少有效订阅"
