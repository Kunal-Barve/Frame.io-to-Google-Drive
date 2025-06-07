"""
Firestore-based job persistence service.

This module provides functionality to store and retrieve job information
from Google Firestore, enabling job persistence across Cloud Run instances.
"""

import json
from datetime import datetime
from typing import Optional, Dict, Any, Union
from google.cloud import firestore
import logging

from app.models.schemas import ProcessingStatusEnum

# Configure logging
logger = logging.getLogger(__name__)

# Initialize Firestore client
db = firestore.Client()
jobs_collection = db.collection('frame_io_jobs')


def save_job(job_id: str, job_data: Dict[str, Any]) -> None:
    """
    Save job data to Firestore.
    
    Args:
        job_id: Unique ID for the job
        job_data: Job data to store
    """
    try:
        # Convert datetime objects to ISO format strings
        serialized_data = _serialize_job_data(job_data)
        
        # Store job data
        jobs_collection.document(job_id).set(serialized_data)
        logger.info(f"Job {job_id} saved to Firestore")
    except Exception as e:
        logger.error(f"Error saving job {job_id} to Firestore: {e}")
        # Continue without failing - fallback to in-memory storage


def get_job(job_id: str) -> Optional[Dict[str, Any]]:
    """
    Get job data from Firestore.
    
    Args:
        job_id: Unique ID for the job
        
    Returns:
        Job data dictionary or None if job not found
    """
    try:
        job_ref = jobs_collection.document(job_id)
        job = job_ref.get()
        
        if job.exists:
            return job.to_dict()
        
        logger.warning(f"Job {job_id} not found in Firestore")
        return None
        
    except Exception as e:
        logger.error(f"Error retrieving job {job_id} from Firestore: {e}")
        return None


def update_job_status(
    job_id: str, 
    state: Union[ProcessingStatusEnum, str], 
    progress: Optional[int] = None,
    details: Optional[str] = None, 
    error: Optional[str] = None, 
    **kwargs
) -> None:
    """
    Update job status in Firestore.
    
    Args:
        job_id: Unique ID for the job
        state: Current state of the job
        progress: Progress percentage (0-100)
        details: Additional details about the current state
        error: Error message if any
        **kwargs: Additional fields to update
    """
    try:
        # Convert state to string if it's an enum
        if isinstance(state, ProcessingStatusEnum):
            state = state.value
        
        # Prepare update data
        update_data = {
            'state': state,
            'last_updated': datetime.now().isoformat()
        }
        
        if progress is not None:
            update_data['progress'] = progress
            
        if details is not None:
            update_data['details'] = details
            
        if error is not None:
            update_data['error'] = error
        
        # Add any additional fields
        for k, v in kwargs.items():
            # Serialize any complex objects
            if isinstance(v, datetime):
                update_data[k] = v.isoformat()
            elif isinstance(v, dict):
                update_data[k] = _serialize_job_data(v)
            else:
                update_data[k] = v
        
        # Update Firestore document
        jobs_collection.document(job_id).update(update_data)
        logger.info(f"Job {job_id} status updated in Firestore: state={state}, progress={progress}")
        
    except Exception as e:
        logger.error(f"Error updating job {job_id} in Firestore: {e}")
        # Continue without failing - fallback to in-memory storage


def _serialize_job_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Serialize job data for Firestore storage.
    
    Converts datetime objects to ISO format strings and handles other non-serializable types.
    
    Args:
        data: Job data to serialize
        
    Returns:
        Serialized job data
    """
    serialized = {}
    
    for key, value in data.items():
        if isinstance(value, datetime):
            serialized[key] = value.isoformat()
        elif hasattr(value, '__dict__') and not isinstance(value, (str, int, float, bool, list, dict)):
            # Convert custom objects to dictionaries
            serialized[key] = _serialize_job_data(value.__dict__)
        elif isinstance(value, dict):
            # Recursively serialize nested dictionaries
            serialized[key] = _serialize_job_data(value)
        elif isinstance(value, (list, tuple)):
            # Handle lists and tuples
            serialized[key] = [
                item.isoformat() if isinstance(item, datetime) else item
                for item in value
            ]
        else:
            # For basic types
            serialized[key] = value
    
    return serialized
