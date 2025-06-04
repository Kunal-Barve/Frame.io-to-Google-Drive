import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.api.endpoints import processing_jobs


@pytest.fixture
def client():
    """
    Create a test client for the FastAPI application.
    
    Returns:
        TestClient: A test client for the FastAPI application.
    """
    # Create a TestClient instance with the FastAPI app
    # The app parameter is passed directly without a keyword
    return TestClient(app)


@pytest.fixture(autouse=True)
def clear_processing_jobs():
    """
    Clear the processing_jobs dictionary before each test.
    
    This fixture runs automatically before each test to ensure
    a clean state for testing.
    """
    processing_jobs.clear()
    yield
    processing_jobs.clear()  # Clean up after test
