from fastapi.testclient import TestClient

from wild_catalog.api.app import app

# Create a test client instance
client = TestClient(app)

def test_health_check():
    # Send a GET request to the /health endpoint
    response = client.get("/health")

    # Assert that the service returns a 200 OK status code
    assert response.status_code == 200

    # Assert that the payload matches your expected output
    assert response.json() == {"status": "ok"}
