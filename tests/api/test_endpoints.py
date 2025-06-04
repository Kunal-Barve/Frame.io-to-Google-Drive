import pytest
from uuid import UUID

from app.api.endpoints import processing_jobs


def test_process_frame_url_success(client):
    """
    Test successful processing of a Frame.io URL.
    
    This test verifies that the endpoint correctly accepts a valid Frame.io URL,
    creates a processing job, and returns the expected response.
    """
    # Clear any existing processing jobs
    processing_jobs.clear()
    
    # Test data
    test_data = {
        "frame_io_url": "https://f.io/20zfIQ5x",
        "drive_folder_id": "test_folder_id"
    }
    
    # Send request
    response = client.post("/api/process-frame-url", json=test_data)
    
    # Assert response
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["message"] == "Processing job created successfully"
    assert data["state"] == "queued"
    
    # Verify processing ID is a valid UUID
    processing_id = data["processing_id"]
    assert UUID(processing_id)
    
    # Verify job was stored correctly
    assert processing_id in processing_jobs
    assert processing_jobs[processing_id]["frame_io_url"] == test_data["frame_io_url"]
    assert processing_jobs[processing_id]["drive_folder_id"] == test_data["drive_folder_id"]
    assert processing_jobs[processing_id]["state"] == "queued"


def test_process_frame_url_without_folder_id(client):
    """
    Test processing a Frame.io URL without specifying a folder ID.
    
    This test verifies that the endpoint correctly handles the case where
    no drive_folder_id is provided and uses the default from settings.
    """
    # Clear any existing processing jobs
    processing_jobs.clear()
    
    # Test data (without drive_folder_id)
    test_data = {
        "frame_io_url": "https://f.io/FDY4eFZJ"
    }
    
    # Send request
    response = client.post("/api/process-frame-url", json=test_data)
    
    # Assert response
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    
    # Verify processing ID is a valid UUID
    processing_id = data["processing_id"]
    assert UUID(processing_id)
    
    # Verify job was stored with default folder ID from settings
    assert processing_id in processing_jobs
    assert processing_jobs[processing_id]["frame_io_url"] == test_data["frame_io_url"]
    assert "drive_folder_id" in processing_jobs[processing_id]  # Should use default from settings


def test_process_frame_url_invalid_url(client):
    """
    Test processing an invalid URL (not from Frame.io).
    
    This test verifies that the endpoint correctly rejects URLs
    that are not from the Frame.io domain.
    """
    # Test data with invalid URL (not from Frame.io)
    test_data = {
        "frame_io_url": "https://f.io/TafALVxa"
    }
    
    # Send request
    response = client.post("/api/process-frame-url", json=test_data)
    
    # Assert response (should be validation error)
    assert response.status_code == 422
    data = response.json()
    assert data["status"] == "error"
    assert "Validation error" in data["message"]
    
    # Verify error details mention Frame.io domain
    assert any("Frame.io domain" in str(detail) for detail in data["details"])


def test_get_job_status_success(client):
    """
    Test successfully retrieving a job status.
    
    This test verifies that the endpoint correctly returns the status
    of an existing processing job.
    """
    # Clear any existing processing jobs
    processing_jobs.clear()
    
    # Create a test job
    test_job_id = "test-job-123"
    processing_jobs[test_job_id] = {
        "frame_io_url": "https://f.io/TafALVxa",
        "drive_folder_id": "test_folder_id",
        "state": "processing",
        "created_at": "2025-06-03T23:20:00Z",
    }
    
    # Send request
    response = client.get(f"/api/job/{test_job_id}")
    
    # Assert response
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["message"] == "Job status retrieved successfully"
    assert data["processing_id"] == test_job_id
    assert data["state"] == "processing"


def test_get_job_status_not_found(client):
    """
    Test retrieving a non-existent job status.
    
    This test verifies that the endpoint correctly handles the case
    where the requested job ID does not exist.
    """
    # Clear any existing processing jobs
    processing_jobs.clear()
    
    # Send request for non-existent job
    non_existent_id = "non-existent-job"
    response = client.get(f"/api/job/{non_existent_id}")
    
    # Assert response
    assert response.status_code == 404
    data = response.json()
    assert data["status"] == "error"
    assert f"Processing job with ID {non_existent_id} not found" in data["details"]
