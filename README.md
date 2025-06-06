# Frame.io to Google Drive Automation

A FastAPI application that automates the transfer of assets from Frame.io to Google Drive. This application provides a robust, asynchronous API for processing Frame.io URLs, downloading assets, and uploading them to Google Drive with shareable links.

## Features

- Automated headless browser automation to download assets from Frame.io
- Google Drive integration with smart folder management
- Asynchronous API endpoints with background task processing
- Job status tracking and polling
- Comprehensive error handling and recovery
- Docker support for easy deployment

## Prerequisites

- Python 3.12+
- Playwright for browser automation
- Google Drive API credentials
- Frame.io account credentials

## Project Structure

```
frame-to-drive-automation/
├── app/                      # Main application code
│   ├── api/                  # API endpoints
│   ├── models/               # Data models
│   ├── services/             # Core services
│   └── utils/                # Utility functions
├── docs/                     # Documentation files
├── tests/                    # Test suite
│   ├── api/                  # API tests
│   └── services/             # Service tests
├── tmp/                      # Temporary files storage
│   ├── downloads/            # Downloaded assets
│   └── processing/           # Processing files
├── .env.example              # Example environment variables
├── Dockerfile                # Docker configuration
├── docker-compose.yml        # Docker Compose configuration
└── requirements.txt          # Python dependencies
```

## Installation

### Local Development

1. Clone this repository
2. Create a conda environment:
   ```bash
   conda create -p ./env python=3.12
   conda activate ./env
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Install Playwright browsers:
   ```bash
   playwright install chromium
   playwright install-deps chromium
   ```
5. Create a `.env` file based on `.env.example` with your credentials
6. Run the application:
   ```bash
   uvicorn app.main:app --reload
   ```

## Docker Deployment

### Using Docker Compose (Recommended)

1. Make sure you have Docker and Docker Compose installed on your system.

2. Create a `.env` file based on `.env.example` with your credentials:
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

3. Prepare your Google Service Account JSON file:
   - Place your Google Service Account JSON file in the project root as `service-account.json`
   - Alternatively, specify a custom path in your `.env` file via `GOOGLE_SERVICE_ACCOUNT_FILE`

4. Generate self-signed SSL certificates for HTTPS:
   - On Linux/Mac:
     ```bash
     cd nginx/ssl
     chmod +x generate-self-signed-cert.sh
     ./generate-self-signed-cert.sh
     ```
   - On Windows (run PowerShell as Administrator):
     ```powershell
     cd nginx/ssl
     ./Generate-SelfSignedCert.ps1
     ```
   - For production, replace these with real certificates (e.g., Let's Encrypt)

5. Build and start the containers:
   ```bash
   docker-compose up -d --build
   ```

6. Check the application logs:
   ```bash
   docker-compose logs -f
   ```

7. The API will be available at:
   - HTTP: `http://<your-host>` (port 80, redirects to HTTPS)
   - HTTPS: `https://<your-host>` (port 443, secure connection)

### Using Docker directly

1. Build the Docker image:
   ```bash
   docker build -t frame-to-drive .
   ```

2. Run the container:
   ```bash
   docker run -d \
     --name frame-to-drive \
     -p 8000:8000 \
     -v $(pwd)/service-account.json:/app/service-account.json:ro \
     -v $(pwd)/tmp:/app/tmp \
     -v $(pwd)/logs:/app/logs \
     --env-file .env \
     frame-to-drive
   ```

## Updating on a VPS

To update the application on your VPS:

1. SSH into your VPS
2. Navigate to your project directory
3. Pull the latest changes:
   ```bash
   git pull
   ```
4. Update the application:
   ```bash
   docker-compose down
   docker-compose up -d --build
   ```

## API Endpoints

### Transfer a Frame.io Asset to Google Drive

```
POST /api/v1/transfer
```

Request Body:
```json
{
  "frame_io_url": "https://app.frame.io/...",
  "drive_folder_id": "optional_google_drive_subfolder_name"
}
```

Response:
```json
{
  "status": "success",
  "message": "Job submitted successfully",
  "data": {
    "job_id": "123e4567-e89b-12d3-a456-426614174000"
  }
}
```

### Check Job Status

```
GET /api/v1/status/{job_id}
```

Response:
```json
{
  "status": "success",
  "message": "Job status retrieved",
  "data": {
    "job_id": "123e4567-e89b-12d3-a456-426614174000",
    "state": "completed",
    "progress": 100,
    "share_link": "https://drive.google.com/..."
  }
}
```

## Testing

Run the test suite:

```bash
pytest -v
```

For async tests:

```bash
pytest -v tests/api/test_fastapi.py
```

## Environment Variables

See `.env.example` for all required environment variables.

## License

[MIT License](LICENSE)