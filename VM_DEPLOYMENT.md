# VM Deployment Guide for Frame.io to Google Drive Automation

This guide explains how to deploy the application on a Google Compute Engine VM for improved stability with browser automation.

## Prerequisites

1. A Google Cloud Platform (GCP) account with Compute Engine API enabled
2. Git installed on your local machine
3. A GitHub repository for your code
4. Service account credentials files (`bunsters_service_account.json` and `firebase_service_account.json`)

## VM Setup

### 1. Create a VM Instance

1. Go to GCP Console > Compute Engine > VM Instances > Create
2. Configure your VM:
   - Name: `frameio-to-gdrive-vm`
   - Machine type: `e2-standard-4` (4 vCPU, 16 GB memory) or higher
   - Boot disk: Debian 11 or Ubuntu 20.04 LTS
   - Allow HTTP/HTTPS traffic in the firewall settings
   - Add any other required settings (e.g., startup scripts, SSH keys)
   - Click Create

### 2. Connect to the VM

```bash
# SSH into your VM
gcloud compute ssh frameio-to-gdrive-vm
```

### 3. Install Dependencies

```bash
# Update package lists
sudo apt-get update

# Install required packages
sudo apt-get install -y git docker.io docker-compose curl

# Add your user to docker group
sudo usermod -aG docker $USER

# Apply changes (logout and login again)
exit
# Reconnect to VM after this
```

### 4. Deploy the Application

```bash
# Clone your repository
git clone <your-github-repo-url>
cd frame-to-drive-automation

# Create directories for credentials and data
mkdir -p credentials logs tmp/downloads tmp/processing

# Copy your service account credentials to the VM
# You'll need to upload these files to the VM
# Option 1: Use gcloud SCP
# From your local machine:
gcloud compute scp /path/to/bunsters_service_account.json frameio-to-gdrive-vm:~/frame-to-drive-automation/credentials/
gcloud compute scp /path/to/firebase_service_account.json frameio-to-gdrive-vm:~/frame-to-drive-automation/credentials/

# Create .env file with all required variables
cat > .env << EOL
# FastAPI & Cloud Run
DEBUG_MODE=false

# Frame.io credentials
FRAME_IO_EMAIL=your_frameio_email@example.com
FRAME_IO_PASSWORD=your_frameio_password

# Google Drive / Firestore
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
GOOGLE_REDIRECT_URI=http://VM_EXTERNAL_IP/oauth2callback
GOOGLE_DRIVE_FOLDER_ID=your_google_drive_folder_id
GOOGLE_CLOUD_PROJECT=your_google_cloud_project_id

# File management
MAX_FILE_SIZE_MB=5000
DOWNLOAD_TIMEOUT_SECONDS=300

# Security
SECRET_KEY=your_secure_random_secret_key
EOL

# Update GOOGLE_REDIRECT_URI with actual VM IP
EXTERNAL_IP=$(curl -s "http://metadata.google.internal/computeMetadata/v1/instance/network-interfaces/0/access-configs/0/external-ip" -H "Metadata-Flavor: Google")
sed -i "s|http://VM_EXTERNAL_IP/oauth2callback|http://$EXTERNAL_IP/oauth2callback|g" .env

# Start the application with Docker Compose
docker-compose -f docker-compose.prod.yml up -d
```

## Accessing the Application

- Web UI: `http://<VM-EXTERNAL-IP>/`
- API: `http://<VM-EXTERNAL-IP>/api/`
- Health check: `http://<VM-EXTERNAL-IP>/health`

## Setting Up as a System Service (Optional but Recommended)

To make sure your application starts automatically after VM reboot:

```bash
cat > /etc/systemd/system/frameio-to-gdrive.service << EOL
[Unit]
Description=Frame.io to Google Drive Automation
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/USERNAME/frame-to-drive-automation
ExecStart=/usr/bin/docker-compose -f docker-compose.prod.yml up -d
ExecStop=/usr/bin/docker-compose -f docker-compose.prod.yml down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOL

# Replace USERNAME with your actual username
sudo sed -i "s|USERNAME|$(whoami)|g" /etc/systemd/system/frameio-to-gdrive.service

# Enable and start the service
sudo systemctl enable frameio-to-gdrive.service
sudo systemctl start frameio-to-gdrive.service
```

## Troubleshooting

### View Logs

```bash
# Docker Compose logs
docker-compose -f docker-compose.prod.yml logs

# Follow logs in real-time
docker-compose -f docker-compose.prod.yml logs -f

# View logs for a specific service
docker-compose -f docker-compose.prod.yml logs app
docker-compose -f docker-compose.prod.yml logs nginx
```

### Check Container Status

```bash
# List running containers
docker ps

# Check container health
docker inspect --format '{{.State.Health.Status}}' frame-to-drive-prod
```

### NGINX Configuration

The NGINX configuration is set up to:
1. Accept connections on ports 80 (HTTP)
2. Proxy all requests to the FastAPI application on port 8080
3. Handle long-running operations with extended timeouts
4. Provide proper headers and logging

SSL is initially commented out but can be enabled by providing certificates in the `nginx/ssl` directory and uncommenting the HTTPS server block in `nginx/conf.d/vm.conf`.
