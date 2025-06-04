from fastapi import APIRouter, HTTPException, status, Depends
from uuid import uuid4
from typing import Dict

from app.models.schemas import (
    FrameIoUrlRequest,
    ProcessingStatusResponse,
    ErrorResponse,
    StatusEnum
)
from app.config import settings

# Initialize router
router = APIRouter(
    prefix="/api",
    tags=["Frame.io Processing"]
)

# In-memory storage for processing status (will be replaced with a proper database in production)
processing_jobs: Dict[str, Dict] = {}


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
async def process_frame_url(request: FrameIoUrlRequest):
    """
    Process a Frame.io URL by initiating the download and upload workflow.
    
    This endpoint validates the Frame.io URL, creates a processing job,
    and returns a job ID that can be used to check the status.
    
    The actual download and upload will be implemented in future tasks.
    
    Args:
        request (FrameIoUrlRequest): The request containing the Frame.io URL and optional Google Drive folder ID.
        
    Returns:
        ProcessingStatusResponse: A response containing the processing job ID and current state.
        
    Raises:
        HTTPException: If there's an error processing the request.
    """
    try:
        # Generate a unique processing ID
        processing_id = str(uuid4())
        
        # Log the request for debugging
        print(f"Processing Frame.io URL: {request.frame_io_url}")
        print(f"Drive folder ID: {request.drive_folder_id or settings.google_drive_folder_id}")
        
        # Store job information (in memory for now, will be replaced with a database)
        processing_jobs[processing_id] = {
            "frame_io_url": str(request.frame_io_url),
            "drive_folder_id": request.drive_folder_id or settings.google_drive_folder_id,
            "state": "queued",
            "created_at": "2025-06-03T23:20:00Z",  # Hardcoded for now, will be replaced with actual timestamp
        }
        
        # Return processing status
        return ProcessingStatusResponse(
            status=StatusEnum.SUCCESS,
            message="Processing job created successfully",
            processing_id=processing_id,
            state="queued"
        )
        
    except Exception as e:
        # Log the error (will be implemented in a future task)
        import traceback
        print(f"Error processing Frame.io URL: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        
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
    description="Get the status of a processing job by its ID."
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
        
        # Return processing status
        return ProcessingStatusResponse(
            status=StatusEnum.SUCCESS,
            message="Job status retrieved successfully",
            processing_id=processing_id,
            state=job["state"]
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
        
    except Exception as e:
        # Log the error (will be implemented in a future task)
        print(f"Error retrieving job status: {e}")
        
        # Raise HTTP exception
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e) if settings.debug_mode else "An error occurred while retrieving the job status"
        )
