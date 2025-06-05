# Setting Up the .env File for Google Service Account

When using a Google Service Account with the application, you need to properly format the JSON key in your `.env` file. This guide explains how to do this correctly.

## The Problem with JSON in .env Files

The `.env` file format is simple: each line contains a key-value pair separated by an equals sign (`=`). However, JSON service account keys contain special characters, quotes, and newlines that can cause parsing issues.

## Solution: Properly Formatting the Service Account JSON

Follow these steps to correctly add your service account JSON to the `.env` file:

### 1. Get Your Service Account JSON Key

First, download your service account JSON key from the Google Cloud Console as described in the [Google Service Account Setup](./google_service_account_setup.md) guide.

### 2. Convert the JSON to a Single Line

The JSON key needs to be converted to a single line with proper escaping:

1. Open the JSON key file in a text editor
2. Remove all newlines
3. Escape any double quotes inside the private key (which already contains `\n` sequences)

### 3. Format for .env File

In your `.env` file, add the service account info like this:

```
GOOGLE_SERVICE_ACCOUNT_INFO={"type":"service_account","project_id":"your-project-id","private_key_id":"your-key-id","private_key":"-----BEGIN PRIVATE KEY-----\\nYOUR_PRIVATE_KEY_HERE\\n-----END PRIVATE KEY-----\\n","client_email":"your-service-account@your-project-id.iam.gserviceaccount.com","client_id":"your-client-id","auth_uri":"https://accounts.google.com/o/oauth2/auth","token_uri":"https://oauth2.googleapis.com/token","auth_provider_x509_cert_url":"https://www.googleapis.com/oauth2/v1/certs","client_x509_cert_url":"https://www.googleapis.com/robot/v1/metadata/x509/your-service-account%40your-project-id.iam.gserviceaccount.com"}
```

**Important Notes:**
- The entire JSON must be on a single line
- There should be no spaces around the equals sign
- The value should not be enclosed in quotes
- Any double quotes within the JSON should be preserved (not escaped with backslashes)
- The `\n` sequences in the private key should be preserved

### 4. Alternative: Use a Helper Script

If you're having trouble formatting the JSON correctly, you can use this Python script to help:

```python
import json
import sys

# Read the JSON file
with open(sys.argv[1], 'r') as f:
    service_account_info = json.load(f)

# Convert to a properly formatted string for .env file
env_value = json.dumps(service_account_info, separators=(',', ':'))

print(f"GOOGLE_SERVICE_ACCOUNT_INFO={env_value}")
```

Save this as `format_service_account.py` and run it with:

```
python format_service_account.py path/to/your-service-account.json
```

Copy the output and paste it into your `.env` file.

## Testing Your Configuration

After setting up your `.env` file, you can test if the service account authentication works by running:

```
python scripts/test_gdrive_service.py
```

If everything is set up correctly, the script should authenticate using the service account and list files from your Google Drive folder.
