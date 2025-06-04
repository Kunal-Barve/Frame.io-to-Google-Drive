"""
File handling utilities for the Frame.io to Google Drive automation.

This module provides functions for managing downloaded files, including:
- Temporary file storage
- File cleanup
- File type validation
"""

import os
import shutil
import time
import logging
import hashlib
import mimetypes
import datetime
from typing import List, Dict, Optional, Tuple, Set
from pathlib import Path

from app.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize mimetypes
mimetypes.init()

# Define common video file extensions and their MIME types
VIDEO_EXTENSIONS = {
    '.mp4': 'video/mp4',
    '.mov': 'video/quicktime',
    '.avi': 'video/x-msvideo',
    '.wmv': 'video/x-ms-wmv',
    '.mkv': 'video/x-matroska',
    '.webm': 'video/webm',
    '.flv': 'video/x-flv',
    '.m4v': 'video/x-m4v',
    '.3gp': 'video/3gpp',
    '.3g2': 'video/3gpp2',
    '.mxf': 'application/mxf',  # Material Exchange Format, common in professional video
    '.mts': 'video/mp2t',  # AVCHD video format
    '.ts': 'video/mp2t',  # MPEG Transport Stream
    '.vob': 'video/dvd',  # DVD Video Object
}


def ensure_temp_dirs() -> None:
    """
    Ensure that the temporary directories exist.
    Creates the download and processing directories if they don't exist.
    """
    os.makedirs(settings.temp_download_dir, exist_ok=True)
    os.makedirs(settings.temp_processing_dir, exist_ok=True)
    logger.info(f"Temporary directories verified: {settings.temp_download_dir}, {settings.temp_processing_dir}")


def get_file_info(file_path: str) -> Dict[str, any]:
    """
    Get file information.
    
    Args:
        file_path: Path to the file
        
    Returns:
        Dictionary with file information:
            - name: File name
            - path: Full path to the file
            - size: File size in bytes
            - size_human: Human-readable file size
            - created: File creation time
            - modified: File modification time
            - extension: File extension
            - mime_type: File MIME type
            - md5: MD5 hash of the file
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
        
    file_stat = os.stat(file_path)
    file_size = file_stat.st_size
    file_name = os.path.basename(file_path)
    file_ext = os.path.splitext(file_name)[1].lower()
    
    # Get MIME type
    mime_type = VIDEO_EXTENSIONS.get(file_ext)
    if not mime_type:
        mime_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
    
    # Calculate MD5 hash for files under 1GB
    md5_hash = None
    if file_size < 1_073_741_824:  # 1GB
        try:
            md5_hash = calculate_md5(file_path)
        except Exception as e:
            logger.warning(f"Failed to calculate MD5 for {file_path}: {e}")
    
    # Format human-readable size
    size_human = format_file_size(file_size)
    
    # Get creation and modification times
    created = datetime.datetime.fromtimestamp(file_stat.st_ctime)
    modified = datetime.datetime.fromtimestamp(file_stat.st_mtime)
    
    return {
        "name": file_name,
        "path": file_path,
        "size": file_size,
        "size_human": size_human,
        "created": created,
        "modified": modified,
        "extension": file_ext,
        "mime_type": mime_type,
        "md5": md5_hash
    }


def format_file_size(size_bytes: int) -> str:
    """
    Format file size to human-readable format.
    
    Args:
        size_bytes: File size in bytes
        
    Returns:
        Human-readable file size (e.g., "1.23 MB")
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def calculate_md5(file_path: str) -> str:
    """
    Calculate MD5 hash of a file.
    
    Args:
        file_path: Path to the file
        
    Returns:
        MD5 hash as a hexadecimal string
    """
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def validate_video_file(file_path: str) -> Tuple[bool, Optional[str]]:
    """
    Validate that a file is a valid video file.
    
    Args:
        file_path: Path to the file
        
    Returns:
        Tuple with (is_valid, error_message)
    """
    if not os.path.exists(file_path):
        return False, f"File not found: {file_path}"
    
    if os.path.getsize(file_path) == 0:
        return False, f"File is empty: {file_path}"
    
    file_ext = os.path.splitext(file_path)[1].lower()
    if file_ext not in VIDEO_EXTENSIONS:
        # Check MIME type as fallback
        mime_type = mimetypes.guess_type(file_path)[0]
        if not mime_type or not mime_type.startswith("video/"):
            return False, f"File is not a recognized video format: {file_path}"
    
    # TODO: Add more sophisticated video validation if needed
    # For example, using a library like ffmpeg to check if the file is a valid video
    
    return True, None


def move_to_processing(download_path: str) -> str:
    """
    Move a file from the download directory to the processing directory.
    
    Args:
        download_path: Path to the downloaded file
        
    Returns:
        Path to the file in the processing directory
    """
    if not os.path.exists(download_path):
        raise FileNotFoundError(f"Downloaded file not found: {download_path}")
    
    # Create processing directory if it doesn't exist
    os.makedirs(settings.temp_processing_dir, exist_ok=True)
    
    # Generate target path
    file_name = os.path.basename(download_path)
    processing_path = os.path.join(settings.temp_processing_dir, file_name)
    
    # Move the file
    shutil.move(download_path, processing_path)
    logger.info(f"Moved file to processing: {download_path} -> {processing_path}")
    
    return processing_path


def cleanup_temp_files(max_age_hours: int = 24) -> List[str]:
    """
    Clean up temporary files older than the specified age.
    
    Args:
        max_age_hours: Maximum age of files in hours
        
    Returns:
        List of paths to the removed files
    """
    deleted_files = []
    
    # Current time
    current_time = time.time()
    
    # Max age in seconds
    max_age_seconds = max_age_hours * 3600
    
    # Directories to cleanup
    dirs_to_clean = [settings.temp_download_dir, settings.temp_processing_dir]
    
    for dir_path in dirs_to_clean:
        if not os.path.exists(dir_path):
            continue
            
        for filename in os.listdir(dir_path):
            file_path = os.path.join(dir_path, filename)
            
            # Skip directories
            if os.path.isdir(file_path):
                continue
                
            # Check file age
            file_modified_time = os.path.getmtime(file_path)
            age_seconds = current_time - file_modified_time
            
            if age_seconds > max_age_seconds:
                try:
                    os.remove(file_path)
                    deleted_files.append(file_path)
                    logger.info(f"Deleted old temporary file: {file_path}")
                except Exception as e:
                    logger.error(f"Failed to delete {file_path}: {e}")
    
    return deleted_files


def get_temp_file_stats() -> Dict[str, any]:
    """
    Get statistics about temporary files.
    
    Returns:
        Dictionary with statistics:
            - total_files: Total number of files
            - total_size: Total size in bytes
            - total_size_human: Human-readable total size
            - oldest_file: Path to the oldest file
            - newest_file: Path to the newest file
            - downloads: Number of files in download directory
            - processing: Number of files in processing directory
    """
    stats = {
        "total_files": 0,
        "total_size": 0,
        "oldest_file": None,
        "newest_file": None,
        "downloads": 0,
        "processing": 0
    }
    
    oldest_time = float('inf')
    newest_time = 0
    
    # Check download directory
    if os.path.exists(settings.temp_download_dir):
        for filename in os.listdir(settings.temp_download_dir):
            file_path = os.path.join(settings.temp_download_dir, filename)
            if os.path.isfile(file_path):
                stats["total_files"] += 1
                stats["downloads"] += 1
                
                file_size = os.path.getsize(file_path)
                stats["total_size"] += file_size
                
                mtime = os.path.getmtime(file_path)
                if mtime < oldest_time:
                    oldest_time = mtime
                    stats["oldest_file"] = file_path
                if mtime > newest_time:
                    newest_time = mtime
                    stats["newest_file"] = file_path
    
    # Check processing directory
    if os.path.exists(settings.temp_processing_dir):
        for filename in os.listdir(settings.temp_processing_dir):
            file_path = os.path.join(settings.temp_processing_dir, filename)
            if os.path.isfile(file_path):
                stats["total_files"] += 1
                stats["processing"] += 1
                
                file_size = os.path.getsize(file_path)
                stats["total_size"] += file_size
                
                mtime = os.path.getmtime(file_path)
                if mtime < oldest_time:
                    oldest_time = mtime
                    stats["oldest_file"] = file_path
                if mtime > newest_time:
                    newest_time = mtime
                    stats["newest_file"] = file_path
    
    # Add human-readable size
    stats["total_size_human"] = format_file_size(stats["total_size"])
    
    return stats


if __name__ == "__main__":
    # Simple test of the module
    ensure_temp_dirs()
    stats = get_temp_file_stats()
    print(f"Temporary file statistics: {stats}")
