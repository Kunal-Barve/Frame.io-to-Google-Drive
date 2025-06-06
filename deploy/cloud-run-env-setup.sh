#!/bin/bash
# Helper script to set up environment variables and secrets in Cloud Run

# Configuration - update these values
PROJECT_ID="bunsters"
REGION="australia-southeast1"
SERVICE_NAME="frameio-to-gdrive"

# Create secrets if they don't exist
echo "Creating secrets for sensitive information..."

# Frame.io password secret
echo "Creating Frame.io password secret..."
read -sp "Enter Frame.io password: " FRAME_IO_PASSWORD
echo
echo $FRAME_IO_PASSWORD | gcloud secrets create frame_io_password --data-file=- --project=$PROJECT_ID
unset FRAME_IO_PASSWORD

# Google client secret
echo "Creating Google client secret..."
read -sp "Enter Google client secret: " GOOGLE_CLIENT_SECRET
echo
echo $GOOGLE_CLIENT_SECRET | gcloud secrets create google_client_secret --data-file=- --project=$PROJECT_ID
unset GOOGLE_CLIENT_SECRET

# App secret key
echo "Creating app secret key..."
SECRET_KEY=$(openssl rand -hex 32)
echo $SECRET_KEY | gcloud secrets create app_secret_key --data-file=- --project=$PROJECT_ID

# Upload service account JSON if provided
echo "Do you want to upload a service account JSON file? (y/n)"
read UPLOAD_SA

if [ "$UPLOAD_SA" == "y" ]; then
  echo "Enter path to service account JSON file:"
  read SA_PATH
  gcloud secrets create google_service_account --data-file=$SA_PATH --project=$PROJECT_ID
fi

# Now deploy with environment variables and secrets
echo "Deploying Cloud Run service with environment variables and secrets..."

gcloud run deploy $SERVICE_NAME \
  --region=$REGION \
  --platform=managed \
  --project=$PROJECT_ID \
  --set-env-vars="API_HOST=0.0.0.0" \
  --set-env-vars="API_PORT=8000" \
  --set-env-vars="DEBUG_MODE=false" \
  --set-env-vars="WORKERS=2" \
  --set-env-vars="FRAME_IO_EMAIL=your_frame_io_email@example.com" \
  --set-env-vars="GOOGLE_CLIENT_ID=your_google_client_id" \
  --set-env-vars="GOOGLE_DRIVE_FOLDER_ID=your_folder_id" \
  --set-env-vars="GOOGLE_REDIRECT_URI=https://$SERVICE_NAME-$PROJECT_ID.a.run.app/oauth2callback" \
  --set-env-vars="GOOGLE_SERVICE_ACCOUNT_FILE=/credentials/bunsters_service_account.json" \
  --set-env-vars="TEMP_DOWNLOAD_DIR=/app/tmp/downloads" \
  --set-env-vars="TEMP_PROCESSING_DIR=/app/tmp/processing" \
  --set-env-vars="MAX_FILE_SIZE_MB=5000" \
  --set-env-vars="DOWNLOAD_TIMEOUT_SECONDS=300" \
  --set-env-vars="PORT=8080" \
  --update-secrets="FRAME_IO_PASSWORD=frame_io_password:latest" \
  --update-secrets="GOOGLE_CLIENT_SECRET=google_client_secret:latest" \
  --update-secrets="SECRET_KEY=app_secret_key:latest" \
  --update-secrets="/credentials/bunsters_service_account.json=google_service_account:latest" \
  --allow-unauthenticated

echo "Cloud Run service has been deployed!"
echo "You can access it at: https://$SERVICE_NAME-$PROJECT_ID.a.run.app"