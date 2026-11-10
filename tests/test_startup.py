import pytest

def test_health(client):
    assert client.get("/health").json == {"status": "ok"}

@pytest.mark.parametrize("path", ["/", "/activities/", "/analytics/", "/auth/", "/assistant/"])
def test_starter_pages(client, path):
    response = client.get(path)

    if path == "/analytics/":
        assert response.status_code == 302
        assert "/auth/login" in response.headers["Location"]
    else:
        assert response.status_code == 200
