from pydantic_settings import BaseSettings
from typing import Optional
import os
import tempfile
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from .env file
load_dotenv()

# Get project root directory
PROJECT_ROOT = Path(__file__).parent.parent

class Settings(BaseSettings):
    # FastAPI Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug_mode: bool = False
    
    # Frame.io Authentication
    frame_io_email: str
    frame_io_password: str
    
    # Google Drive API Configuration
    google_client_id: str
    google_client_secret: str
    google_redirect_uri: str = "http://localhost:8000/oauth2callback"
    google_service_account_info: Optional[str] = None
    google_service_account_file: Optional[str] = None
    
    # Google Drive Storage
    google_drive_folder_id: str
    
    # File Management - Using platform-agnostic paths
    # These will now be properly resolved for any operating system
    temp_download_dir: str = os.path.join(PROJECT_ROOT, "tmp", "downloads")
    temp_processing_dir: str = os.path.join(PROJECT_ROOT, "tmp", "processing")
    max_file_size_mb: int = 5000
    download_timeout_seconds: int = 300
    
    # Security
    secret_key: str
    
    class Config:
        env_file = ".env"
        case_sensitive = False
    
    def get_service_account_path(self) -> Optional[str]:
        """
        Get the absolute path to the service account file.
        If google_service_account_file is a relative path, it will be resolved relative to the project root.
        
        Returns:
            Optional[str]: Absolute path to the service account file or None if not set
        """
        if not self.google_service_account_file:
            return None
            
        # Check if it's an absolute path
        path = Path(self.google_service_account_file)
        if path.is_absolute():
            return str(path)
            
        # If it's a relative path, resolve it relative to the project root
        return str(PROJECT_ROOT / path)

# Create global settings object
settings = Settings()

# Ensure temp download directory exists
os.makedirs(settings.temp_download_dir, exist_ok=True)
