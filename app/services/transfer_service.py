"""
Frame.io to Google Drive Transfer Service.

This service handles the integrated workflow to:
1. Download an asset from Frame.io using browser automation
2. Process the file through temporary directories
3. Upload to Google Drive in a specific subfolder
4. Generate a shareable link
5. Clean up temporary files
"""

import os
import time
import shutil
import asyncio
import json
import gc  # For explicit garbage collection
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple, Callable
from datetime import datetime

from app.services.browser_service import BrowserService
from app.services.gdrive_service import GoogleDriveService
from app.utils.file_handler import ensure_temp_dirs, get_file_info
from app.config import settings
from app.models.schemas import ProcessingStatusEnum

# Configure logging
logger = logging.getLogger(__name__)


class TransferService:
    """Service to handle the transfer of files from Frame.io to Google Drive."""
    
    def __init__(self):
        """Initialize the transfer service."""
        self.browser_service = BrowserService()
        self.gdrive_service = GoogleDriveService()
        
        # Ensure temp directories exist
        ensure_temp_dirs()
    
    async def process_frame_io_url(
        self, 
        processing_id: str,
        frame_io_url: str, 
        folder_name: str,
        status_callback: Callable[[str, ProcessingStatusEnum, Optional[int], Optional[str], Optional[str]], None]
    ) -> Dict[str, Any]:
        """
        Process a Frame.io URL by downloading the asset and uploading to Google Drive.
        
        Args:
            processing_id: Unique ID for this processing job
            frame_io_url: Frame.io URL to process
            folder_name: Name of the folder to create in Google Drive
            status_callback: Callback function to update the processing status
            
        Returns:
            Dict[str, Any]: Results of the processing with status and metadata
        """
        results = {
            "success": False,
            "processing_id": processing_id,
            "frame_io_url": frame_io_url,
            "folder_name": folder_name,
            "timing": {},
            "asset_metadata": {}
        }
        
        download_path = None
        file_path = None
        
        # Record start time
        start_time = time.time()
        
        try:
            # Step 1: Extract asset info from Frame.io
            await self._update_status(status_callback, processing_id, ProcessingStatusEnum.EXTRACTING, 5, 
                                     "Extracting asset information from Frame.io")
            
            # Extract asset ID from URL for better naming
            try:
                asset_id = frame_io_url.split("/")[-1]
                if not asset_id:
                    logger.warning("Could not extract asset ID from Frame.io URL")
                    asset_id = "unknown"
                    
                results["asset_metadata"]["frameio_id"] = asset_id
                asset_name = f"Frame.io {asset_id}"
                logger.info(f"✅ Successfully extracted asset ID: {asset_id}")
            except Exception as e:
                logger.warning(f"Error extracting asset ID: {e}")
                asset_id = "unknown"
                asset_name = "Frame.io Asset"
            
            results["asset_metadata"]["name"] = asset_name
            
            # Step 2: Download the asset
            await self._update_status(status_callback, processing_id, ProcessingStatusEnum.DOWNLOADING, 15, 
                                     f"Downloading asset: {asset_name}")
            
            download_start_time = time.time()
            download_path = None
            file_name = None
            
            # Get download directory
            download_dir = settings.temp_download_dir
            os.makedirs(download_dir, exist_ok=True)
            
            # Implement download logic exactly as in test_integrated_workflow
            try:
                # Initialize and launch the browser
                await self.browser_service.launch_browser(headless=True)
                
                # Download asset using browser automation with retry logic
                max_download_attempts = 3
                for attempt in range(max_download_attempts):
                    try:
                        await self._update_status(status_callback, processing_id, ProcessingStatusEnum.DOWNLOADING, 
                                               15 + (attempt * 5), 
                                               f"Download attempt {attempt+1}/{max_download_attempts}")
                        
                        logger.info(f"Download attempt {attempt+1}/{max_download_attempts}...")
                        download_path = await self.browser_service.download_frame_io_asset(frame_io_url)
                        
                        if download_path and os.path.exists(download_path):
                            logger.info(f"✅ Download successful on attempt {attempt+1}")
                            break
                        else:
                            logger.warning(f"Download attempt {attempt+1} failed, retrying...")
                            await asyncio.sleep(2)  # Wait before retry
                    except Exception as e:
                        logger.warning(f"Error during download attempt {attempt+1}: {str(e)}")
                        if attempt < max_download_attempts - 1:
                            logger.info("Retrying download...")
                            await asyncio.sleep(2)  # Wait before retry
                        else:
                            logger.error(f"❌ Failed to download after {max_download_attempts} attempts: {str(e)}")
                
                if not download_path or not os.path.exists(download_path):
                    logger.error("❌ Failed to download asset from Frame.io")
                    await self._update_status(status_callback, processing_id, ProcessingStatusEnum.FAILED, 0, 
                                             "Failed to download asset", "Download failed or file not found")
                    return results
            except Exception as e:
                logger.error(f"❌ Error downloading asset: {e}")
                await self._update_status(status_callback, processing_id, ProcessingStatusEnum.FAILED, 0, 
                                         "Failed to download asset", str(e))
                return results
            finally:
                # Always close the browser after download attempts
                try:
                    await self.browser_service.close_browser()
                    # Give the system a moment to clean up resources
                    await asyncio.sleep(0.5)
                except Exception as e:
                    logger.warning(f"Error closing browser: {e}")
            
            # Get file name and info
            file_name = os.path.basename(download_path)
            file_info = get_file_info(download_path)
            results["asset_metadata"].update(file_info)
            results["asset_metadata"]["name"] = file_name
            
            # Calculate size in MB from bytes (get_file_info returns size in bytes)
            size_mb = file_info['size'] / (1024 * 1024)
            results["asset_metadata"]["size_mb"] = size_mb
            
            download_time = time.time() - download_start_time
            results["timing"]["download_time"] = download_time
            logger.info(f"✅ Asset Download: {download_path} ({size_mb:.2f} MB)")
            
            # Step 3: Process the file (move to processing directory)
            await self._update_status(status_callback, processing_id, ProcessingStatusEnum.PROCESSING, 30, 
                                      f"Processing file: {os.path.basename(download_path)}")
            
            processing_start_time = time.time()
            
            # Process the file (copy to processing directory)
            processing_dir = settings.temp_processing_dir
            os.makedirs(processing_dir, exist_ok=True)
            
            # Get filename without path
            file_name = os.path.basename(download_path)
            file_path = os.path.join(processing_dir, file_name)
            
            # Copy file to processing directory
            shutil.copy2(download_path, file_path)
            
            processing_time = time.time() - processing_start_time
            results["timing"]["processing_time"] = processing_time
            logger.info(f"✅ File Processing: {file_path}")
            
            # Step 4: Authenticate with Google Drive
            await self._update_status(status_callback, processing_id, ProcessingStatusEnum.AUTHENTICATING, 40, 
                                     "Authenticating with Google Drive")
            
            # Authenticate with Google Drive
            if not self.gdrive_service.authenticate():
                logger.error("❌ Failed to authenticate with Google Drive")
                await self._update_status(status_callback, processing_id, ProcessingStatusEnum.FAILED, 0, 
                                         "Failed to authenticate with Google Drive", 
                                         "Authentication failed - check credentials")
                return results
            
            logger.info("✅ Google Drive Authentication")
            
            # Step 5: Create Google Drive folder if needed
            await self._update_status(status_callback, processing_id, ProcessingStatusEnum.CREATING_FOLDER, 50, 
                                     f"Creating or finding folder: {folder_name}")
            
            # Find or create the folder
            folder_id = self.gdrive_service.find_or_create_folder(folder_name)
            
            if not folder_id:
                logger.error(f"❌ Failed to create/find folder: {folder_name}")
                await self._update_status(status_callback, processing_id, ProcessingStatusEnum.FAILED, 0, 
                                         f"Failed to create/find folder: {folder_name}", 
                                         "Folder creation/lookup failed")
                return results
            
            results["asset_metadata"]["folder_id"] = folder_id
            logger.info(f"✅ Google Drive Folder Creation: {folder_name} (ID: {folder_id})")
            
            # Step 6: Upload the file to Google Drive
            await self._update_status(status_callback, processing_id, ProcessingStatusEnum.UPLOADING, 60, 
                                     f"Uploading file to Google Drive: {file_name}")
            
            upload_start_time = time.time()
            
            # Upload the file
            file = self.gdrive_service.upload_file(
                file_path=file_path,
                folder_id=folder_id,
                name=file_name
            )
            
            if not file or not file.get('id'):
                logger.error("❌ Failed to upload file to Google Drive")
                await self._update_status(status_callback, processing_id, ProcessingStatusEnum.FAILED, 0, 
                                         "Failed to upload file to Google Drive", 
                                         "Upload failed")
                return results
            
            file_id = file.get('id')
            results["asset_metadata"]["file_id"] = file_id
            upload_time = time.time() - upload_start_time
            results["timing"]["upload_time"] = upload_time
            logger.info(f"✅ Google Drive File Upload: {file_id}")
            
            # Step 7: Generate shareable link
            await self._update_status(status_callback, processing_id, ProcessingStatusEnum.GENERATING_LINK, 80, 
                                     "Generating shareable link")
            
            # Create share link
            share_link = self.gdrive_service.create_share_link(file_id)
            
            if not share_link:
                logger.error("❌ Failed to generate shareable link")
                await self._update_status(status_callback, processing_id, ProcessingStatusEnum.FAILED, 0, 
                                         "Failed to generate shareable link", 
                                         "Share link generation failed")
                return results
            
            results["asset_metadata"]["share_link"] = share_link
            logger.info(f"✅ Share Link Generation: {share_link}")
            
            # Step 8: Cleanup
            await self._update_status(status_callback, processing_id, ProcessingStatusEnum.CLEANUP, 90, 
                                     "Cleaning up temporary files")
            
            # Clean up temporary files
            try:
                if download_path and os.path.exists(download_path):
                    os.remove(download_path)
                    logger.info(f"✅ Successfully removed file: {download_path}")
                
                if file_path and os.path.exists(file_path):
                    os.remove(file_path)
                    logger.info(f"✅ Successfully removed file: {file_path}")
                
                logger.info("✅ Successfully cleaned up all temporary files")
            except Exception as e:
                logger.warning(f"Warning during cleanup: {e}")
            
            # Record end time and set success
            results["success"] = True
            
            # Close browser
            await self.browser_service.close_browser()
            
            # Upload successful - Create file_info for response
            file_info = {
                "file_id": file.get('id'),
                "file_name": file.get('name'),
                "mime_type": file.get('mimeType'),
                "size_bytes": file.get('size'),
                "web_view_link": file.get('webViewLink')
            }
            
            if "webContentLink" in file:
                file_info["web_content_link"] = file.get('webContentLink')
            
            # Mark as complete
            end_time = time.time()
            total_time = end_time - start_time
            results["timing"]["total_time"] = total_time
            
            await self._update_status(
                status_callback, 
                processing_id, 
                ProcessingStatusEnum.COMPLETED, 
                100, 
                "Transfer completed successfully",
                error=None,
                file_info=file_info,
                share_link=share_link,
                duration_seconds=total_time
            )
            
        except Exception as e:
            # Log the error and update status
            logger.error(f"❌ Error in Frame.io to Google Drive workflow: {e}")
            import traceback
            logger.error(traceback.format_exc())
            
            # Update status to failed
            await self._update_status(
                status_callback, 
                processing_id, 
                ProcessingStatusEnum.FAILED, 
                0, 
                "Transfer failed", 
                str(e)
            )
            
        finally:
            # Browser should already be closed after download, but ensure garbage collection
            # Force garbage collection to clean up resources
            gc.collect()
            # Wait a moment for cleanup
            await asyncio.sleep(0.5)
        
        # Return results
        return results
    
    async def _update_status(
        self, 
        callback: Callable, 
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
        Update the status of a processing job.
        
        Args:
            callback: Callback function to update status
            processing_id: ID of the processing job
            state: Current state of the job
            progress: Progress percentage (0-100)
            details: Additional details about the current state
            error: Error message if any
            file_info: File information if available
            share_link: Share link if available
            duration_seconds: Duration of the job in seconds
        """
        if callback:
            await callback(
                processing_id=processing_id,
                state=state,
                progress=progress,
                details=details,
                error=error,
                file_info=file_info,
                share_link=share_link,
                duration_seconds=duration_seconds
            )
