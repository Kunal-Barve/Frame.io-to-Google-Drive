#!/bin/bash
# Script to build and run the Cloud Run image locally

# First build the image
docker build -t frame-to-drive-cloud -f Dockerfile.cloud .

# Run the image with environment variables from .env file
docker run -it --rm \
  -p 8080:8080 \
  --env-file .env \
  -v $(pwd)/credentials:/credentials:ro \
  -v $(pwd)/tmp:/app/tmp \
  -v $(pwd)/logs:/app/logs \
  --name frame-to-drive-cloud \
  frame-to-drive-cloud

echo "App is running at http://localhost:8080"