from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.config import settings

# Initialize FastAPI app
app = FastAPI(
    title="Frame.io to Google Drive Automation",
    description="API for automating the download of Frame.io assets and uploading them to Google Drive",
    version="0.1.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins in development, restrict in production
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Error handling for validation errors
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "status": "error",
            "message": "Validation error",
            "details": exc.errors(),
        },
    )

# Generic exception handler
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "status": "error",
            "message": "Internal server error",
            "details": str(exc) if settings.debug_mode else "An unexpected error occurred",
        },
    )

# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "ok",
        "message": "Service is running",
    }

# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    return {
        "message": "Welcome to Frame.io to Google Drive Automation API",
        "docs": "/docs",  # Link to Swagger UI
    }

# Import and include API routers
from app.api.endpoints import router as api_router
app.include_router(api_router)

# Run the application (for development only)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug_mode
    )
