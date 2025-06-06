from pydantic import BaseModel, Field, validator, HttpUrl
from typing import Optional, List, Dict, Any, Union
from enum import Enum
import re


class StatusEnum(str, Enum):
    """Enum for response status."""
    SUCCESS = "success"
    ERROR = "error"


class BaseResponse(BaseModel):
    """Base model for all API responses."""
    status: StatusEnum
    message: str


class ErrorDetail(BaseModel):
    """Model for detailed error information."""
    loc: Optional[List[str]] = None
    msg: str
    type: str


class ErrorResponse(BaseResponse):
    """Model for error responses."""
    status: StatusEnum = StatusEnum.ERROR
    details: Optional[Union[List[ErrorDetail], Dict[str, Any], str]] = None


class FrameIoUrlRequest(BaseModel):
    """Model for Frame.io URL processing request."""
    frame_io_url: HttpUrl = Field(..., description="URL of the Frame.io asset to download")
    drive_folder_id: Optional[str] = Field(
        None, 
        description="Optional Google Drive folder ID or subfolder name to override the default folder",
        alias="google_drive_subfolder"
    )
    
    @validator('frame_io_url')
    def validate_frame_io_url(cls, v):
        """Validate that the URL is from Frame.io."""
        url_str = str(v)
        if not re.search(r'(frame\.io|frameio\.com|f\.io)', url_str, re.IGNORECASE):
            raise ValueError("URL must be from Frame.io domain (frame.io, frameio.com, or f.io)")
        return v


class DriveFileInfo(BaseModel):
    """Model for Google Drive file information."""
    file_id: str
    file_name: str
    mime_type: str
    size_bytes: Optional[int] = None
    web_view_link: HttpUrl
    web_content_link: Optional[HttpUrl] = None


class ProcessingStatusEnum(str, Enum):
    """Enum for processing job state."""
    QUEUED = "queued"
    EXTRACTING = "extracting_frame_io_asset"
    DOWNLOADING = "downloading_asset"
    PROCESSING = "processing_file"
    AUTHENTICATING = "authenticating_google_drive"
    CREATING_FOLDER = "creating_folder"
    UPLOADING = "uploading_to_google_drive"
    GENERATING_LINK = "generating_share_link"
    CLEANUP = "cleaning_up"
    COMPLETED = "completed"
    FAILED = "failed"


class ProcessingStatusResponse(BaseResponse):
    """Model for processing status responses."""
    status: StatusEnum = StatusEnum.SUCCESS
    processing_id: str
    state: ProcessingStatusEnum
    progress: Optional[int] = Field(None, description="Progress percentage (0-100)")
    details: Optional[str] = None
    error: Optional[str] = None
    file_info: Optional[DriveFileInfo] = None
    share_link: Optional[HttpUrl] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    duration_seconds: Optional[float] = None


class GDriveUploadResponse(BaseResponse):
    """Model for successful Google Drive upload responses."""
    status: StatusEnum = StatusEnum.SUCCESS
    file_info: DriveFileInfo
    share_link: HttpUrl = Field(..., description="Editable share link for the uploaded file")
