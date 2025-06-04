"""
Download management service for Frame.io to Google Drive automation.

This module provides functionality for managing file downloads, including:
- Download progress tracking
- Timeout handling for large files
- Download completion verification
- File integrity checks
"""

import os
import time
import asyncio
import logging
import hashlib
from typing import Optional, Dict, Any, List, Tuple, Callable
from datetime import datetime

from app.config import settings
from app.utils.file_handler import (
    get_file_info,
    validate_video_file,
    calculate_md5,
    move_to_processing
)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
DEFAULT_CHUNK_SIZE = 1024 * 1024  # 1MB
DEFAULT_PROGRESS_INTERVAL = 1.0  # seconds


class DownloadProgress:
    """Class to track download progress."""
    
    def __init__(self, total_size: int = 0, file_name: str = "", url: str = ""):
        """
        Initialize the download progress tracker.
        
        Args:
            total_size: Expected total size in bytes
            file_name: Name of the file being downloaded
            url: URL from which the file is being downloaded
        """
        self.total_size = total_size
        self.downloaded_size = 0
        self.file_name = file_name
        self.url = url
        self.start_time = time.time()
        self.last_update_time = self.start_time
        self.last_downloaded_size = 0
        self.status = "initializing"  # initializing, downloading, completed, failed, timed_out
        self.error = None
        self.progress_callbacks: List[Callable[[Dict], None]] = []
        
    def update(self, downloaded_size: int, status: str = "downloading") -> None:
        """
        Update the progress.
        
        Args:
            downloaded_size: Currently downloaded size in bytes
            status: Current status of the download
        """
        now = time.time()
        self.downloaded_size = downloaded_size
        self.status = status
        
        # Calculate speed (bytes per second)
        time_diff = now - self.last_update_time
        size_diff = downloaded_size - self.last_downloaded_size
        
        speed = size_diff / time_diff if time_diff > 0 else 0
        
        # Update last values
        self.last_update_time = now
        self.last_downloaded_size = downloaded_size
        
        # Calculate progress percentage
        percentage = (downloaded_size / self.total_size * 100) if self.total_size > 0 else 0
        
        # Calculate ETA
        remaining_size = self.total_size - downloaded_size if self.total_size > 0 else 0
        eta_seconds = remaining_size / speed if speed > 0 else 0
        
        # Prepare progress info
        progress_info = {
            "file_name": self.file_name,
            "url": self.url,
            "total_size": self.total_size,
            "downloaded_size": downloaded_size,
            "percentage": percentage,
            "speed": speed,
            "speed_human": format_speed(speed),
            "elapsed": now - self.start_time,
            "eta": eta_seconds,
            "status": status,
            "timestamp": datetime.now().isoformat(),
        }
        
        # Call progress callbacks
        for callback in self.progress_callbacks:
            try:
                callback(progress_info)
            except Exception as e:
                logger.error(f"Error in progress callback: {e}")
        
    def add_callback(self, callback: Callable[[Dict], None]) -> None:
        """
        Add a callback function to be called on progress updates.
        
        Args:
            callback: Function that takes a progress info dictionary
        """
        self.progress_callbacks.append(callback)
    
    def set_error(self, error: str) -> None:
        """
        Set an error message.
        
        Args:
            error: Error message
        """
        self.error = error
        self.status = "failed"
        self.update(self.downloaded_size, "failed")
    
    def set_completed(self) -> None:
        """Mark the download as completed."""
        self.status = "completed"
        self.update(self.total_size, "completed")
    
    def set_timed_out(self) -> None:
        """Mark the download as timed out."""
        self.status = "timed_out"
        self.error = "Download timed out"
        self.update(self.downloaded_size, "timed_out")
    
    def get_info(self) -> Dict[str, Any]:
        """
        Get the current progress info.
        
        Returns:
            Dictionary with progress information
        """
        now = time.time()
        
        # Calculate speed (bytes per second)
        elapsed = now - self.start_time
        speed = self.downloaded_size / elapsed if elapsed > 0 else 0
        
        # Calculate progress percentage
        percentage = (self.downloaded_size / self.total_size * 100) if self.total_size > 0 else 0
        
        # Calculate ETA
        remaining_size = self.total_size - self.downloaded_size if self.total_size > 0 else 0
        eta_seconds = remaining_size / speed if speed > 0 else 0
        
        return {
            "file_name": self.file_name,
            "url": self.url,
            "total_size": self.total_size,
            "downloaded_size": self.downloaded_size,
            "percentage": percentage,
            "speed": speed,
            "speed_human": format_speed(speed),
            "elapsed": elapsed,
            "eta": eta_seconds,
            "status": self.status,
            "error": self.error,
            "timestamp": datetime.now().isoformat(),
        }


class DownloadManager:
    """
    Service for managing downloads, including progress tracking and verification.
    """
    
    def __init__(self):
        """Initialize the DownloadManager."""
        self.active_downloads: Dict[str, DownloadProgress] = {}
        self.completed_downloads: List[Dict[str, Any]] = []
        self.failed_downloads: List[Dict[str, Any]] = []
        
    def get_active_downloads(self) -> Dict[str, Dict[str, Any]]:
        """
        Get information about all active downloads.
        
        Returns:
            Dictionary mapping download IDs to progress info
        """
        return {download_id: progress.get_info() for download_id, progress in self.active_downloads.items()}
    
    def get_download_info(self, download_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific download.
        
        Args:
            download_id: ID of the download
            
        Returns:
            Dictionary with download information, or None if not found
        """
        if download_id in self.active_downloads:
            return self.active_downloads[download_id].get_info()
        
        # Check completed downloads
        for download in self.completed_downloads:
            if download.get("id") == download_id:
                return download
        
        # Check failed downloads
        for download in self.failed_downloads:
            if download.get("id") == download_id:
                return download
        
        return None
    
    def register_download(self, file_path: str, url: str, total_size: int = 0) -> str:
        """
        Register a new download.
        
        Args:
            file_path: Path to the file being downloaded
            url: URL from which the file is being downloaded
            total_size: Expected total size in bytes
            
        Returns:
            Download ID
        """
        file_name = os.path.basename(file_path)
        download_id = f"{file_name}_{int(time.time())}"
        
        progress = DownloadProgress(
            total_size=total_size,
            file_name=file_name,
            url=url
        )
        
        self.active_downloads[download_id] = progress
        logger.info(f"Registered new download: {download_id} for {url}")
        
        return download_id
    
    def update_progress(self, download_id: str, downloaded_size: int, status: str = "downloading") -> None:
        """
        Update the progress of a download.
        
        Args:
            download_id: ID of the download
            downloaded_size: Currently downloaded size in bytes
            status: Current status of the download
        """
        if download_id in self.active_downloads:
            self.active_downloads[download_id].update(downloaded_size, status)
    
    def mark_completed(self, download_id: str, file_path: str) -> bool:
        """
        Mark a download as completed and verify its integrity.
        
        Args:
            download_id: ID of the download
            file_path: Path to the downloaded file
            
        Returns:
            True if the download is valid, False otherwise
        """
        if download_id not in self.active_downloads:
            logger.warning(f"Cannot mark unknown download as completed: {download_id}")
            return False
        
        progress = self.active_downloads[download_id]
        
        try:
            # Check if the file exists
            if not os.path.exists(file_path):
                progress.set_error(f"Downloaded file not found: {file_path}")
                self._move_to_failed(download_id)
                return False
            
            # Get file info
            file_info = get_file_info(file_path)
            
            # Validate file size
            if progress.total_size > 0 and file_info["size"] != progress.total_size:
                progress.set_error(f"File size mismatch: expected {progress.total_size}, got {file_info['size']}")
                self._move_to_failed(download_id)
                return False
            
            # Validate file type
            is_valid, error = validate_video_file(file_path)
            if not is_valid:
                progress.set_error(f"Invalid video file: {error}")
                self._move_to_failed(download_id)
                return False
            
            # Mark as completed
            progress.set_completed()
            
            # Move to completed list
            completed_info = progress.get_info()
            completed_info["id"] = download_id
            completed_info["file_path"] = file_path
            completed_info["file_info"] = file_info
            
            self.completed_downloads.append(completed_info)
            del self.active_downloads[download_id]
            
            logger.info(f"Download completed and verified: {download_id}")
            return True
            
        except Exception as e:
            progress.set_error(f"Error verifying download: {str(e)}")
            self._move_to_failed(download_id)
            logger.error(f"Error verifying download {download_id}: {e}")
            return False
    
    def mark_failed(self, download_id: str, error: str) -> None:
        """
        Mark a download as failed.
        
        Args:
            download_id: ID of the download
            error: Error message
        """
        if download_id in self.active_downloads:
            self.active_downloads[download_id].set_error(error)
            self._move_to_failed(download_id)
    
    def mark_timed_out(self, download_id: str) -> None:
        """
        Mark a download as timed out.
        
        Args:
            download_id: ID of the download
        """
        if download_id in self.active_downloads:
            self.active_downloads[download_id].set_timed_out()
            self._move_to_failed(download_id)
    
    def _move_to_failed(self, download_id: str) -> None:
        """
        Move a download from active to failed list.
        
        Args:
            download_id: ID of the download
        """
        if download_id in self.active_downloads:
            failed_info = self.active_downloads[download_id].get_info()
            failed_info["id"] = download_id
            
            self.failed_downloads.append(failed_info)
            del self.active_downloads[download_id]
            
            logger.warning(f"Download failed: {download_id}")
    
    async def monitor_file_growth(
        self, 
        download_id: str, 
        file_path: str, 
        timeout_seconds: int = None,
        progress_interval: float = DEFAULT_PROGRESS_INTERVAL
    ) -> bool:
        """
        Monitor a file's growth to track download progress.
        
        Args:
            download_id: ID of the download
            file_path: Path to the file being downloaded
            timeout_seconds: Timeout in seconds (None for settings default)
            progress_interval: Interval in seconds to check progress
            
        Returns:
            True if the download completed successfully, False otherwise
        """
        if timeout_seconds is None:
            timeout_seconds = settings.download_timeout_seconds
        
        start_time = time.time()
        last_size = 0
        last_progress_time = start_time
        no_progress_time = 0
        
        logger.info(f"Starting to monitor download progress for {download_id}")
        
        while True:
            # Check if file exists
            if not os.path.exists(file_path):
                await asyncio.sleep(progress_interval)
                continue
            
            # Get current file size
            current_size = os.path.getsize(file_path)
            
            # Update progress
            current_time = time.time()
            if current_time - last_progress_time >= progress_interval:
                self.update_progress(download_id, current_size)
                last_progress_time = current_time
            
            # Check if size has changed
            if current_size > last_size:
                # Progress is being made
                last_size = current_size
                no_progress_time = 0
            else:
                # No progress since last check
                no_progress_time += progress_interval
            
            # Check for timeout (either total timeout or no progress timeout)
            elapsed_time = current_time - start_time
            if elapsed_time > timeout_seconds:
                self.mark_timed_out(download_id)
                logger.warning(f"Download timed out after {elapsed_time:.1f}s: {download_id}")
                return False
            
            # Check for stalled download (no progress for 30 seconds)
            if no_progress_time > 30:
                # If size hasn't changed for 30 seconds, we might be done or stalled
                # Give it another check after a short sleep
                await asyncio.sleep(2)
                
                # Check size again
                new_size = os.path.getsize(file_path)
                if new_size == current_size:
                    # Size still hasn't changed, consider it complete or stalled
                    # Let's verify the file
                    return self.mark_completed(download_id, file_path)
            
            # Wait before next check
            await asyncio.sleep(progress_interval)
    
    async def process_completed_download(self, download_id: str) -> Optional[str]:
        """
        Process a completed download by moving it to the processing directory.
        
        Args:
            download_id: ID of the download
            
        Returns:
            Path to the file in the processing directory, or None if processing failed
        """
        download_info = self.get_download_info(download_id)
        if not download_info or download_info.get("status") != "completed":
            logger.warning(f"Cannot process incomplete download: {download_id}")
            return None
        
        file_path = download_info.get("file_path")
        if not file_path or not os.path.exists(file_path):
            logger.warning(f"Downloaded file not found: {file_path}")
            return None
        
        try:
            # Move to processing directory
            processing_path = move_to_processing(file_path)
            
            # Update the download info
            for i, download in enumerate(self.completed_downloads):
                if download.get("id") == download_id:
                    self.completed_downloads[i]["file_path"] = processing_path
                    self.completed_downloads[i]["status"] = "processing"
                    break
            
            logger.info(f"Moved download {download_id} to processing: {processing_path}")
            return processing_path
            
        except Exception as e:
            logger.error(f"Error processing download {download_id}: {e}")
            return None


# Utility functions

def format_speed(bytes_per_second: float) -> str:
    """
    Format download speed to human-readable format.
    
    Args:
        bytes_per_second: Speed in bytes per second
        
    Returns:
        Human-readable speed (e.g., "1.23 MB/s")
    """
    if bytes_per_second < 1024:
        return f"{bytes_per_second:.2f} B/s"
    elif bytes_per_second < 1024 * 1024:
        return f"{bytes_per_second / 1024:.2f} KB/s"
    elif bytes_per_second < 1024 * 1024 * 1024:
        return f"{bytes_per_second / (1024 * 1024):.2f} MB/s"
    else:
        return f"{bytes_per_second / (1024 * 1024 * 1024):.2f} GB/s"


def print_progress_callback(progress_info: Dict[str, Any]) -> None:
    """
    Example callback function to print download progress.
    
    Args:
        progress_info: Dictionary with progress information
    """
    percentage = progress_info.get("percentage", 0)
    downloaded = progress_info.get("downloaded_size", 0) / (1024 * 1024)  # MB
    total = progress_info.get("total_size", 0) / (1024 * 1024)  # MB
    speed = progress_info.get("speed_human", "? KB/s")
    filename = progress_info.get("file_name", "unknown")
    
    print(f"\rDownloading {filename}: {percentage:.1f}% ({downloaded:.1f}/{total:.1f} MB) at {speed}", end="")
    
    if progress_info.get("status") == "completed":
        print("\nDownload completed!")
    elif progress_info.get("status") in ["failed", "timed_out"]:
        print(f"\nDownload failed: {progress_info.get('error')}")


# Example usage
async def test_download_manager():
    """Test the DownloadManager functionality."""
    manager = DownloadManager()
    
    # Register a download
    download_id = manager.register_download(
        file_path=os.path.join(settings.temp_download_dir, "test.mp4"),
        url="https://example.com/test.mp4",
        total_size=100 * 1024 * 1024  # 100 MB
    )
    
    # Add a progress callback
    manager.active_downloads[download_id].add_callback(print_progress_callback)
    
    # Simulate download progress
    for i in range(0, 101, 10):
        manager.update_progress(
            download_id=download_id,
            downloaded_size=int(i * 1024 * 1024),  # i MB
            status="downloading"
        )
        await asyncio.sleep(0.5)
    
    # Mark as completed
    manager.mark_completed(
        download_id=download_id,
        file_path=os.path.join(settings.temp_download_dir, "test.mp4")
    )
    
    # Get download info
    info = manager.get_download_info(download_id)
    print(f"Download info: {info}")


if __name__ == "__main__":
    # Run the test
    asyncio.run(test_download_manager())
