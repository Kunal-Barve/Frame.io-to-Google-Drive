from fastapi import APIRouter, HTTPException, status, BackgroundTasks, Depends
from uuid import uuid4
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
import asyncio
import logging
import traceback


from app.services.browser_service import BrowserService
from app.services.transfer_service import TransferService

from app.models.schemas import (
    FrameIoUrlRequest,
    ProcessingStatusResponse,
    ErrorResponse,
    StatusEnum,
    ProcessingStatusEnum,
    DriveFileInfo
)
from app.config import settings
from app.services.transfer_service import TransferService

# Configure logging
logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter(
    prefix="/api",
    tags=["Frame.io Processing"]
)

# In-memory storage for processing status (will be replaced with a proper database in production)
processing_jobs: Dict[str, Dict] = {}

# Initialize transfer service
transfer_service = TransferService()


async def update_job_status(
    processing_id: str, 
    state: ProcessingStatusEnum,
    progress: Optional[int] = None,
    details: Optional[str] = None,
    error: Optional[str] = None,
    file_info: Optional[Dict[str, Any]] = None,
    share_link: Optional[str] = None,
    duration_seconds: Optional[float] = None
):
    """
    Update the job status in the processing_jobs dictionary.
    This function is called by the transfer service to update job status.
    
    Args:
        processing_id: ID of the processing job
        state: Current state of the job
        progress: Progress percentage (0-100)
        details: Additional details about the current state
        error: Error message if any
        file_info: File information if available
        share_link: Share link if available
        duration_seconds: Duration of the job in seconds
    """
    if processing_id not in processing_jobs:
        logger.warning(f"Attempted to update non-existent job: {processing_id}")
        return
        
    # Update job information
    job = processing_jobs[processing_id]
    job["state"] = state
    
    if progress is not None:
        job["progress"] = progress
        
    if details is not None:
        job["details"] = details
        
    if error is not None:
        job["error"] = error
        
    if file_info is not None:
        job["file_info"] = file_info
        
    if share_link is not None:
        job["share_link"] = share_link
        
    # Update timestamps
    if state == ProcessingStatusEnum.COMPLETED or state == ProcessingStatusEnum.FAILED:
        job["end_time"] = datetime.now().isoformat()
        
    if duration_seconds is not None:
        job["duration_seconds"] = duration_seconds
    
    logger.info(f"Job {processing_id} updated: state={state}, progress={progress}")


async def process_job_in_background(processing_id: str, frame_io_url: str, folder_name: str):
    """
    Process a job in the background.
    
    Args:
        processing_id: ID of the processing job
        frame_io_url: Frame.io URL to process
        folder_name: Name of the folder to create in Google Drive
    """
    try:
        # Run the transfer process
        await transfer_service.process_frame_io_url(
            processing_id=processing_id,
            frame_io_url=str(frame_io_url),
            folder_name=folder_name,
            status_callback=update_job_status
        )
    except Exception as e:
        # Handle any uncaught exceptions
        logger.error(f"Error in background job {processing_id}: {e}")
        logger.error(traceback.format_exc())
        
        # Update job status to failed
        await update_job_status(
            processing_id=processing_id,
            state=ProcessingStatusEnum.FAILED,
            progress=0,
            details="An unexpected error occurred during processing",
            error=str(e)
        )


@router.post(
    "/process-frame-url",
    response_model=ProcessingStatusResponse,
    responses={
        422: {"model": ErrorResponse, "description": "Validation Error"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"}
    },
    summary="Process Frame.io URL",
    description="Submit a Frame.io URL for processing. The system will download the asset and upload it to Google Drive."
)
async def process_frame_url(request: FrameIoUrlRequest, background_tasks: BackgroundTasks):
    """
    Process a Frame.io URL by initiating the download and upload workflow.
    
    This endpoint validates the Frame.io URL, creates a processing job,
    and returns a job ID that can be used to check the status.
    
    The actual processing happens in the background.
    
    Args:
        request (FrameIoUrlRequest): The request containing the Frame.io URL and optional folder name.
        background_tasks: FastAPI background tasks handler
        
    Returns:
        ProcessingStatusResponse: A response containing the processing job ID and current state.
        
    Raises:
        HTTPException: If there's an error processing the request.
    """
    try:
        # Generate a unique processing ID
        processing_id = str(uuid4())
        
        # Get or generate folder name from URL
        frame_io_url = str(request.frame_io_url)
        folder_name = request.drive_folder_id or f"Frame_Asset_{processing_id[:8]}"
        
        # Log the request
        logger.info(f"Processing Frame.io URL: {frame_io_url}")
        logger.info(f"Target folder name: {folder_name}")
        
        # Store initial job information
        current_time = datetime.now().isoformat()
        processing_jobs[processing_id] = {
            "frame_io_url": frame_io_url,
            "folder_name": folder_name,
            "state": ProcessingStatusEnum.QUEUED,
            "progress": 0,
            "details": "Job queued and waiting to start",
            "created_at": current_time,
            "start_time": current_time,
        }
        
        # Schedule the background task
        background_tasks.add_task(
            process_job_in_background,
            processing_id=processing_id,
            frame_io_url=frame_io_url,
            folder_name=folder_name
        )
        
        # Return processing status
        return ProcessingStatusResponse(
            status=StatusEnum.SUCCESS,
            message="Processing job created and started in background",
            processing_id=processing_id,
            state=ProcessingStatusEnum.QUEUED,
            progress=0,
            details="Job queued and waiting to start",
            start_time=current_time
        )
        
    except Exception as e:
        # Log the error
        logger.error(f"Error processing Frame.io URL: {e}")
        logger.error(traceback.format_exc())
        
        # Raise HTTP exception
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e) if settings.debug_mode else "An error occurred while processing the request"
        )


@router.get(
    "/job/{processing_id}",
    response_model=ProcessingStatusResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Job Not Found"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"}
    },
    summary="Get job status",
    description="Get the status of a processing job by its ID, including progress and completion details."
)
async def get_job_status(processing_id: str):
    """
    Get the status of a processing job.
    
    Args:
        processing_id (str): The ID of the processing job.
        
    Returns:
        ProcessingStatusResponse: A response containing the processing job ID and current state.
        
    Raises:
        HTTPException: If the job is not found or there's an error retrieving the status.
    """
    try:
        # Check if job exists
        if processing_id not in processing_jobs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Processing job with ID {processing_id} not found"
            )
        
        # Get job information
        job = processing_jobs[processing_id]
        
        # Prepare response message based on state
        message = "Job status retrieved successfully"
        if job["state"] == ProcessingStatusEnum.COMPLETED:
            message = "Job completed successfully"
        elif job["state"] == ProcessingStatusEnum.FAILED:
            message = "Job failed to complete"
        
        # Create response with all available information
        response = ProcessingStatusResponse(
            status=StatusEnum.SUCCESS,
            message=message,
            processing_id=processing_id,
            state=job["state"],
            progress=job.get("progress"),
            details=job.get("details"),
            error=job.get("error"),
            start_time=job.get("start_time"),
            end_time=job.get("end_time"),
            duration_seconds=job.get("duration_seconds")
        )
        
        # Add file_info if available
        if "file_info" in job:
            # Convert dict to DriveFileInfo model
            file_info = job["file_info"]
            response.file_info = DriveFileInfo(
                file_id=file_info.get("file_id"),
                file_name=file_info.get("file_name"),
                mime_type=file_info.get("mime_type"),
                size_bytes=file_info.get("size_bytes"),
                web_view_link=file_info.get("web_view_link"),
                web_content_link=file_info.get("web_content_link")
            )
        
        # Add share_link if available
        if "share_link" in job:
            response.share_link = job["share_link"]
        
        return response
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
        
    except Exception as e:
        # Log the error
        logger.error(f"Error retrieving job status: {e}")
        logger.error(traceback.format_exc())
        
        # Raise HTTP exception
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e) if settings.debug_mode else "An error occurred while retrieving the job status"
        )
@router.get("/test-browser")
async def test_browser():
    """Test browser launch with minimal page load."""
    try:
        browser_service = BrowserService()
        logger.info("Starting minimal browser test")
        browser, context, page = await browser_service.launch_browser(headless=True)
        logger.info("Browser launched successfully")
        await page.goto("https://google.com")
        title = await page.title()
        logger.info(f"Page title: {title}")
        await browser.close()
        logger.info("Browser closed successfully")
        return {"success": True, "title": title}
    except Exception as e:
        logger.error(f"Test browser error: {str(e)}")
        return {"success": False, "error": str(e)}