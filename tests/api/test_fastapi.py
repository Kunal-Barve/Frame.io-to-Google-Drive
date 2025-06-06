#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test file for FastAPI endpoints integration.
Tests the complete workflow from URL submission to share link generation.
"""

# To run these tests manually, make sure the FastAPI server is running first
# python -m app.main

import os
import time
import asyncio
import httpx
import pytest
import logging
from typing import Dict, Any, List, Tuple, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Test configuration
BASE_URL = "http://localhost:8000"
MAX_POLLING_TIME = 10 * 60  # 10 minutes maximum polling time
POLLING_INTERVAL = 10  # Check status every 10 seconds

# Test cases - each entry is a tuple of (frame_io_url, google_drive_subfolder)
TEST_CASES = [
    (
        "https://f.io/eqUGOjQ3",
        "Flavour First Drinker_Superior Flavour_Street Interview",
        "Success case 1 - Standard video file"
    ),
    (
        "https://f.io/CVtRnux8",
        "Flavour First Drinker_Superior Flavour_Street Interview",
        "Success case 2 - Different video in same folder"
    ),
    (
        "https://f.io/E62vgjD2",
        "BUN25Y_SG_01_Superior Flavour_BackLabel_Founder_Collection",
        "Success case 3 - Video in different folder"
    ),
    # Add edge case - invalid URL to test error handling
    (
        "https://invalid-url.com/abc123",
        "Test_Invalid_URL",
        "Edge case - Invalid non-Frame.io URL"
    ),
    # Add failure case - blank subfolder
    (
        "https://f.io/eqUGOjQ3",
        "",
        "Edge case - Empty subfolder name"
    )
]


async def submit_job(client: httpx.AsyncClient, frame_io_url: str, 
                    google_drive_subfolder: str) -> Dict[str, Any]:
    """
    Submit a new job to the API.
    
    Args:
        client: The httpx client
        frame_io_url: The Frame.io URL to process
        google_drive_subfolder: The Google Drive subfolder name
    
    Returns:
        Dict containing the API response
    """
    payload = {
        "frame_io_url": frame_io_url,
        "google_drive_subfolder": google_drive_subfolder
    }
    
    response = await client.post(f"{BASE_URL}/api/process-frame-url", json=payload)
    return response.json()


async def check_job_status(client: httpx.AsyncClient, job_id: str) -> Dict[str, Any]:
    """
    Check the status of an existing job.
    
    Args:
        client: The httpx client
        job_id: The ID of the job to check
        
    Returns:
        Dict containing the API response with job status
    """
    response = await client.get(f"{BASE_URL}/api/job/{job_id}")
    return response.json()


async def poll_until_complete(client: httpx.AsyncClient, job_id: str) -> Dict[str, Any]:
    """
    Poll the job status until it completes or fails.
    
    Args:
        client: The httpx client
        job_id: The ID of the job to check
        
    Returns:
        Dict containing the final API response with job status and results
    """
    start_time = time.time()
    last_progress = -1
    
    while True:
        # Check if we've exceeded maximum polling time
        if time.time() - start_time > MAX_POLLING_TIME:
            raise TimeoutError(f"Job {job_id} took too long to complete (over {MAX_POLLING_TIME} seconds)")
        
        # Get current status
        status_data = await check_job_status(client, job_id)
        
        # Print full response the first time and whenever state changes
        if start_time == time.time() or 'state' not in locals() or locals().get('prev_state') != status_data.get('state'):
            logger.info(f"Full response data: {status_data}")
            prev_state = status_data.get('state')
            
        # Log progress if it changed
        if 'progress' in status_data and status_data['progress'] != last_progress:
            last_progress = status_data['progress']
            logger.info(f"Job {job_id} progress: {last_progress}% - State: {status_data.get('state', 'unknown')}")
            # Log more info if progress is 100
            if last_progress == 100:
                logger.info(f"100% progress reached! Full response: {status_data}")
        
        # Check if job completed or failed
        status_state = status_data.get('state', '')
        
        # Log raw state for debugging
        logger.debug(f"Raw state value: '{status_state}'")
        
        # Check for completion or failure using case-insensitive partial match
        if 'COMPLETED' in status_state or status_state == 'COMPLETED':
            logger.info(f"Job {job_id} completed successfully!")
            return status_data
        elif 'FAILED' in status_state or status_state == 'FAILED':
            logger.error(f"Job {job_id} failed: {status_data.get('error', 'Unknown error')}")
            return status_data
        
        # Wait before polling again
        await asyncio.sleep(POLLING_INTERVAL)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "frame_io_url,google_drive_subfolder,test_name",
    TEST_CASES,
    ids=[case[2] for case in TEST_CASES]
)
async def test_frame_io_to_drive_workflow(
    frame_io_url: str, 
    google_drive_subfolder: str, 
    test_name: str
) -> None:
    """
    Test the complete Frame.io to Google Drive workflow through the API.
    
    This test submits a job to process a Frame.io URL, polls until completion,
    and verifies the results include a shareable link.
    
    Args:
        frame_io_url: The Frame.io URL to process
        google_drive_subfolder: The Google Drive subfolder name
        test_name: A descriptive name for the test case
    """
    logger.info(f"Starting test: {test_name}")
    logger.info(f"Processing URL: {frame_io_url} to folder: {google_drive_subfolder}")
    
    # Define expected outcomes based on URL
    is_valid_url = "f.io/" in frame_io_url or "frame.io/" in frame_io_url or "frameio.com/" in frame_io_url
    
    async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
        try:
            # Step 1: Submit the job
            logger.info("Submitting job...")
            
            # For invalid URL test case, we expect a validation error
            if not is_valid_url:
                with pytest.raises(httpx.HTTPStatusError) as excinfo:
                    response = await submit_job(client, frame_io_url, google_drive_subfolder)
                assert excinfo.value.response.status_code == 422
                logger.info("Validation correctly rejected invalid URL")
                return
                
            # For valid URLs, we proceed with the normal flow
            job_data = await submit_job(client, frame_io_url, google_drive_subfolder)
            
            assert 'processing_id' in job_data, "Response should contain a processing_id"
            job_id = job_data['processing_id']
            logger.info(f"Job submitted successfully. ID: {job_id}")
            
            # Step 2: Poll until complete or failed
            logger.info(f"Polling job {job_id} until completion...")
            final_status = await poll_until_complete(client, job_id)
            
            # Step 3: Verify results
            if google_drive_subfolder:
                # For normal cases with valid subfolder name
                status_state = str(final_status.get('state', ''))
                assert 'COMPLETED' in status_state, f"Job should complete successfully, but got state: '{status_state}', error: {final_status.get('error', 'unknown error')}"
                assert 'share_link' in final_status, "Response should contain a share_link"
                assert str(final_status['share_link']).startswith("https://drive.google.com/"), "Share link should be a Google Drive URL"
                assert 'file_info' in final_status, "Response should contain file_info"
                assert 'size_mb' in final_status['file_info'], "File info should include size_mb"
                
                logger.info(f"Test passed! Share link: {final_status['share_link']}")
            else:
                # For empty subfolder case, we should still get success but may have a default folder name
                assert 'state' in final_status, "Response should contain state"
                logger.info(f"Empty subfolder test resulted in state: {final_status['state']}")
                
        except httpx.RequestError as exc:
            logger.error(f"Error while requesting {exc.request.url!r}: {exc}")
            raise
        except TimeoutError as exc:
            logger.error(f"Timeout error: {exc}")
            raise
        except Exception as exc:
            logger.error(f"Unexpected error: {exc}")
            raise


if __name__ == "__main__":
    # Can be run directly for manual testing
    import sys
    logging.basicConfig(level=logging.INFO)
    
    if len(sys.argv) >= 3:
        frame_io_url = sys.argv[1]
        google_drive_subfolder = sys.argv[2]
        
        async def run_test():
            async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
                job_data = await submit_job(client, frame_io_url, google_drive_subfolder)
                job_id = job_data['processing_id']
                final_status = await poll_until_complete(client, job_id)
                print(f"Final status: {final_status}")
                
        asyncio.run(run_test())
    else:
        print("Usage: python test_fastapi.py <frame_io_url> <google_drive_subfolder>")
