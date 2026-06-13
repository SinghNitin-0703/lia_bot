import pytest
from fastapi.testclient import TestClient
from app.main import app

# Create a test client using our FastAPI application
client = TestClient(app)

def test_read_root():
    """
    Test the health check / root endpoint of the FastAPI app.
    Ensures the server boots properly and responds with the welcome message.
    """
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to the Gluzo AI Backend"}
