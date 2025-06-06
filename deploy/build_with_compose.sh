#!/bin/bash
# Script to build with Docker Compose and push to Google Artifact Registry

# Configuration - update these values
PROJECT_ID="your-google-cloud-project-id"
REGION="us-central1"  # Change to your preferred region
REPOSITORY="frame-to-drive"
IMAGE_NAME="frame-to-drive-app"
TAG="latest"

# Full image path
IMAGE_PATH="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/${IMAGE_NAME}:${TAG}"

# Build the Docker image using Docker Compose
echo "Building Docker image with Docker Compose..."
docker-compose -f docker-compose.cloud.yml build

# Tag the image for Google Artifact Registry
echo "Tagging image for Google Artifact Registry..."
docker tag frame-to-drive-cloud:latest ${IMAGE_PATH}

# Configure Docker to use Google Cloud credentials
echo "Configuring Docker authentication..."
gcloud auth configure-docker ${REGION}-docker.pkg.dev --quiet

# Push the image to Google Artifact Registry
echo "Pushing image to Google Artifact Registry..."
docker push ${IMAGE_PATH}

echo "Image pushed successfully to ${IMAGE_PATH}"
echo "To deploy to Cloud Run, use:"
echo "gcloud run deploy ${IMAGE_NAME} --image=${IMAGE_PATH} --platform=managed --region=${REGION}"