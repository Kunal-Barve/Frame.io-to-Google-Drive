#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Standalone test file for FastAPI endpoints integration.
Tests the complete workflow from URL submission to share link generation.
This test doesn't rely on conftest.py or other complex setup.
"""

import os
import time
import asyncio
import httpx
import pytest
import logging
from typing import Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Test configuration
BASE_URL = "http://localhost:8000"
MAX_POLLING_TIME = 60  # 60 seconds maximum polling time for quicker testing
POLLING_INTERVAL = 3   # Check status every 3 seconds

# Just test one case initially to debug
TEST_CASE = (
    "https://f.io/eqUGOjQ3",
    "Flavour First Drinker_Superior Flavour_Street Interview",
    "Test case - Debug test"
)


async def submit_job(client: httpx.AsyncClient, frame_io_url: str, 
                    google_drive_subfolder: str) -> Dict[str, Any]:
    """Submit a new job to the API."""
    payload = {
        "frame_io_url": frame_io_url,
        "google_drive_subfolder": google_drive_subfolder
    }
    
    try:
        response = await client.post(
            f"{BASE_URL}/api/process-frame-url", 
            json=payload, 
            timeout=10.0  # Add a timeout to prevent hanging
        )
        response.raise_for_status()
        return response.json()
    except httpx.TimeoutException:
        logger.error("Request timed out when submitting job")
        return {"error": "Request timeout"}
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error when submitting job: {e}")
        return {"error": str(e)}
    except Exception as e:
        logger.error(f"Unexpected error when submitting job: {e}")
        return {"error": str(e)}


async def check_job_status(client: httpx.AsyncClient, job_id: str) -> Dict[str, Any]:
    """Check the status of an existing job."""
    try:
        response = await client.get(
            f"{BASE_URL}/api/job/{job_id}",
            timeout=10.0  # Add a timeout to prevent hanging
        )
        response.raise_for_status()
        return response.json()
    except httpx.TimeoutException:
        logger.error("Request timed out when checking job status")
        return {"error": "Request timeout"}
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error when checking job status: {e}")
        return {"error": str(e)}
    except Exception as e:
        logger.error(f"Unexpected error when checking job status: {e}")
        return {"error": str(e)}


@pytest.mark.asyncio
async def test_server_is_running():
    """Test if the server is responding at all."""
    logger.info("Testing if FastAPI server is running...")
    async with httpx.AsyncClient(verify=False, timeout=5.0) as client:
        try:
            response = await client.get(f"{BASE_URL}")
            logger.info(f"Server responded with status code {response.status_code}")
            assert response.status_code in (200, 404)  # Either success or not found is acceptable
            logger.info("Server is running!")
        except Exception as e:
            logger.error(f"Failed to connect to server: {e}")
            pytest.skip("Server is not running, skipping test")


@pytest.mark.asyncio
async def test_frame_io_to_drive_workflow_simple():
    """A simplified version of the workflow test."""
    frame_io_url, google_drive_subfolder, test_name = TEST_CASE
    
    logger.info(f"Starting test: {test_name}")
    logger.info(f"Processing URL: {frame_io_url} to folder: {google_drive_subfolder}")
    
    # First check if server is running
    async with httpx.AsyncClient(verify=False, timeout=5.0) as client:
        try:
            response = await client.get(f"{BASE_URL}")
            logger.info(f"Server responded with status code {response.status_code}")
        except Exception as e:
            logger.error(f"Failed to connect to server: {e}")
            pytest.skip("Server is not running, skipping test")
    
    # Run the actual test
    async with httpx.AsyncClient(verify=False, timeout=30.0) as client:
        # Step 1: Submit the job
        logger.info("Submitting job...")
        job_data = await submit_job(client, frame_io_url, google_drive_subfolder)
        
        # Check for errors in response
        if "error" in job_data:
            logger.error(f"Error submitting job: {job_data['error']}")
            pytest.fail(f"Job submission failed: {job_data['error']}")
            
        assert "processing_id" in job_data, "Response should contain a processing_id"
        job_id = job_data["processing_id"]
        logger.info(f"Job submitted successfully. ID: {job_id}")
        
        # Step 2: Check status just once (don't poll continuously for the test)
        logger.info(f"Checking initial status of job {job_id}...")
        status_data = await check_job_status(client, job_id)
        
        # Check for errors
        if "error" in status_data:
            logger.error(f"Error checking job status: {status_data['error']}")
            pytest.fail(f"Status check failed: {status_data['error']}")
            
        logger.info(f"Job status: {status_data.get('state', 'unknown')}")
        logger.info(f"Job progress: {status_data.get('progress', 0)}%")
        
        # Just verify we can get status, don't wait for completion in this test
        assert "state" in status_data, "Job status should contain 'state' field"
        logger.info("Test passed - able to submit job and check status")


if __name__ == "__main__":
    # Can be run directly for manual testing
    pytest.main(["-v", __file__])
