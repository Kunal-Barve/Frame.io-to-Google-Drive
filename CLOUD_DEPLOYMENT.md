# Cloud Deployment Guide for Frame-to-Drive Automation

This guide explains how to deploy the Frame-to-Drive automation app to Google Cloud Run using Artifact Registry with Firestore integration.

## Prerequisites

- Google Cloud account
- Google Cloud CLI installed and configured (`gcloud`)
- Docker installed on your local machine
- Access to Google Artifact Registry, Cloud Run, and Firestore services
- Service account credentials with appropriate permissions

## Step 1: Set Up Required Google Cloud APIs

Enable the required Google Cloud APIs:

```bash
gcloud services enable artifactregistry.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable firestore.googleapis.com
```

## Step 2: Create a Repository in Artifact Registry

```bash
gcloud artifacts repositories create frame-to-drive \
    --repository-format=docker \
    --location=REGION \
    --description="Frame.io to Google Drive automation"
```

Replace `REGION` with your preferred Google Cloud region (e.g., `us-central1`).

## Step 3: Configure Authentication for Artifact Registry

```bash
gcloud auth configure-docker REGION-docker.pkg.dev
```

## Step 4: Set Environment Variables

```bash
export PROJECT_ID=$(gcloud config get-value project)
export REGION=REGION  # Use your preferred region
export REPOSITORY=frame-to-drive
export IMAGE=frame-to-drive-app
export TAG=latest
```

## Step 5: Build and Push the Docker Image

Build your Docker image using the production Dockerfile:

```bash
docker build -t $REGION-docker.pkg.dev/$PROJECT_ID/$REPOSITORY/$IMAGE:$TAG -f Dockerfile.prod .
```

Push the image to Artifact Registry:

```bash
docker push $REGION-docker.pkg.dev/$PROJECT_ID/$REPOSITORY/$IMAGE:$TAG
```

## Step 6: Deploy to Cloud Run

```bash
gcloud run deploy frame-to-drive \
  --image=$REGION-docker.pkg.dev/$PROJECT_ID/$REPOSITORY/$IMAGE:$TAG \
  --platform=managed \
  --region=$REGION \
  --allow-unauthenticated \
  --port=8080 \
  --cpu=1 \
  --memory=2Gi \
  --timeout=600 \
  --set-env-vars="GOOGLE_CLOUD_PROJECT=$PROJECT_ID" \
  --service-account=YOUR_SERVICE_ACCOUNT@$PROJECT_ID.iam.gserviceaccount.com
```

Replace `YOUR_SERVICE_ACCOUNT` with your service account name.

## Step 7: Configure Environment Variables in Cloud Run

Set all the required environment variables in the Cloud Run console or using the gcloud command:

```bash
gcloud run services update frame-to-drive \
  --region=$REGION \
  --set-env-vars="FRAME_IO_EMAIL=your-email@example.com,FRAME_IO_PASSWORD=your-password,SECRET_KEY=your-secret-key" \
  --set-env-vars="GOOGLE_DRIVE_FOLDER_ID=your-folder-id"
```

## Step 8: Set Up Secret Manager (Recommended)

For sensitive information, use Secret Manager:

```bash
# Create secrets
echo -n "your-frame-io-password" | gcloud secrets create frame-io-password --data-file=-
echo -n "your-secret-key" | gcloud secrets create app-secret-key --data-file=-

# Grant access to Cloud Run service
gcloud secrets add-iam-policy-binding frame-io-password \
  --member="serviceAccount:YOUR_SERVICE_ACCOUNT@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding app-secret-key \
  --member="serviceAccount:YOUR_SERVICE_ACCOUNT@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

# Update Cloud Run to use secrets
gcloud run services update frame-to-drive \
  --region=$REGION \
  --update-secrets="FRAME_IO_PASSWORD=frame-io-password:latest,SECRET_KEY=app-secret-key:latest"
```

## Step 9: Upload Service Account JSON

For Google Drive integration, upload your service account JSON to Secret Manager:

```bash
gcloud secrets create google-service-account --data-file=./credentials/bunsters_service_account.json

gcloud secrets add-iam-policy-binding google-service-account \
  --member="serviceAccount:YOUR_SERVICE_ACCOUNT@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

gcloud run services update frame-to-drive \
  --region=$REGION \
  --set-env-vars="GOOGLE_APPLICATION_CREDENTIALS=/tmp/keys/bunsters-service-account.json" \
  --update-secrets="/tmp/keys/bunsters-service-account.json=google-service-account:latest"
```

## Important Considerations for Cloud Run

1. **Ephemeral Storage**: Cloud Run instances are ephemeral, which means any files stored locally will be lost when the instance is replaced. Use Firestore for job data persistence and Google Cloud Storage for file storage if needed.

2. **Timeout Limitations**: Cloud Run has a maximum request timeout of 3600 seconds (1 hour). Complex operations should be designed with this in mind.

3. **Statelessness**: Design your application to be stateless so it can scale horizontally.

4. **Memory Constraints**: Consider the memory requirements for your application, especially when processing large files.

5. **Cost Optimization**: Cloud Run charges based on resource allocation and consumption. Monitor your usage and optimize as needed.

## Monitoring and Logging

- View logs in Cloud Logging:
  ```bash
  gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=frame-to-drive" --limit=10
  ```

- Set up alerts for errors or high resource usage in Google Cloud Monitoring.

## Testing the Deployment

After deployment, test your endpoints:

```bash
curl https://frame-to-drive-HASH.a.run.app/health
```

Replace `HASH` with the unique identifier provided by Cloud Run.
