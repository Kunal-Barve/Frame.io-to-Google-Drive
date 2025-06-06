# PowerShell script to build and push the Docker image to Google Artifact Registry

# Configuration - update these values
$PROJECT_ID = "your-google-cloud-project-id"
$REGION = "us-central1"  # Change to your preferred region
$REPOSITORY = "frame-to-drive"
$IMAGE_NAME = "frame-to-drive-app"
$TAG = "latest"

# Full image path
$IMAGE_PATH = "${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/${IMAGE_NAME}:${TAG}"

# Build the Docker image
Write-Host "Building Docker image..." -ForegroundColor Green
docker build -t "${IMAGE_NAME}:${TAG}" -f Dockerfile.cloud .

# Tag the image for Google Artifact Registry
Write-Host "Tagging image for Google Artifact Registry..." -ForegroundColor Green
docker tag "${IMAGE_NAME}:${TAG}" $IMAGE_PATH

# Configure Docker to use Google Cloud credentials
Write-Host "Configuring Docker authentication..." -ForegroundColor Green
gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet

# Push the image to Google Artifact Registry
Write-Host "Pushing image to Google Artifact Registry..." -ForegroundColor Green
docker push $IMAGE_PATH

Write-Host "Image pushed successfully to $IMAGE_PATH" -ForegroundColor Green
Write-Host "To deploy to Cloud Run, use:" -ForegroundColor Cyan
Write-Host "gcloud run deploy $IMAGE_NAME --image=$IMAGE_PATH --platform=managed --region=$REGION" -ForegroundColor Yellow