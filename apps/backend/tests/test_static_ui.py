def test_root_serves_built_frontend(client):
    response = client.get("/")

    assert response.status_code == 200
    assert "frontend ok" in response.text
