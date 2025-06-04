from pydantic_settings import BaseSettings
from typing import Optional
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

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
    
    # Google Drive Storage
    google_drive_folder_id: str
    
    # File Management
    temp_download_dir: str = "/tmp/downloads"
    temp_processing_dir: str = "/tmp/processing"
    max_file_size_mb: int = 5000
    download_timeout_seconds: int = 300
    
    # Security
    secret_key: str
    
    class Config:
        env_file = ".env"
        case_sensitive = False

# Create global settings object
settings = Settings()

# Ensure temp download directory exists
os.makedirs(settings.temp_download_dir, exist_ok=True)
