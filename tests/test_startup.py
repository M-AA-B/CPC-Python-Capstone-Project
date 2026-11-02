import pytest

def test_health(client):
    assert client.get("/health").json == {"status": "ok"}

@pytest.mark.parametrize("path", ["/", "/activities/", "/analytics/", "/auth/", "/assistant/"])
def test_starter_pages(client, path):
    assert client.get(path).status_code == 200
