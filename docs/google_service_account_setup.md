# Setting Up a Google Service Account for Google Drive API

This guide explains how to create a service account for Google Drive API authentication, which is ideal for server environments where interactive authentication is not possible.

## What is a Service Account?

A service account is a special type of Google account intended to represent a non-human user that needs to authenticate and be authorized to access data in Google APIs. Service accounts are particularly useful for server-to-server interactions where no end-user involvement is necessary.

## Steps to Create a Service Account

1. **Go to Google Cloud Console**
   - Visit [Google Cloud Console](https://console.cloud.google.com/)
   - Sign in with your Google account

2. **Create or Select a Project**
   - Click on the project dropdown at the top of the page
   - Select an existing project or click "New Project" to create a new one
   - If creating a new project, enter a name and click "Create"

3. **Enable the Google Drive API**
   - In the left sidebar, navigate to "APIs & Services" > "Library"
   - Search for "Google Drive API"
   - Click on "Google Drive API" in the results
   - Click "Enable" (if not already enabled)

4. **Create Service Account Credentials**
   - In the left sidebar, navigate to "APIs & Services" > "Credentials"
   - Click "Create Credentials" at the top of the page
   - Select "Service Account" from the dropdown

5. **Configure the Service Account**
   - Enter a name for your service account
   - Optionally add a description
   - Click "Create and Continue"

6. **Grant Access to the Service Account**
   - In the "Grant this service account access to project" section, select the role "Project" > "Editor" (or a more specific role if you prefer)
   - Click "Continue"

7. **Complete Service Account Setup**
   - You can optionally grant users access to this service account
   - Click "Done"

8. **Create and Download the JSON Key**
   - In the Service Accounts list, find the service account you just created
   - Click on the three dots (actions menu) at the end of the row
   - Select "Manage keys"
   - Click "Add Key" > "Create new key"
   - Select "JSON" as the key type
   - Click "Create"
   - The JSON key file will be automatically downloaded to your computer

9. **Share Google Drive Folder with Service Account**
   - The service account has its own email address (found in the JSON key file as `client_email`)
   - Go to your Google Drive
   - Right-click on the folder you want to use with the application
   - Click "Share"
   - Enter the service account's email address
   - Set the permission to "Editor" (or as needed)
   - Click "Share"

## Using the Service Account Key in the Application

The downloaded JSON key file contains all the necessary credentials. For security reasons, you should not commit this file to your repository. Instead:

1. Open the JSON key file in a text editor
2. Copy the entire contents
3. Set the contents as the value for the `GOOGLE_SERVICE_ACCOUNT_INFO` environment variable in your `.env` file

Example format of the JSON key file:
```json
{
  "type": "service_account",
  "project_id": "your-project-id",
  "private_key_id": "your-private-key-id",
  "private_key": "-----BEGIN PRIVATE KEY-----\nYOUR_PRIVATE_KEY_HERE\n-----END PRIVATE KEY-----\n",
  "client_email": "your-service-account@your-project-id.iam.gserviceaccount.com",
  "client_id": "your-client-id",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/your-service-account%40your-project-id.iam.gserviceaccount.com"
}
```

## Security Considerations

- Keep your service account key secure; it grants access to your Google Drive resources
- Consider using environment variables or a secure secrets management system
- For Docker environments, pass the service account key as an environment variable
- For production, consider using more restrictive IAM roles for the service account

## Troubleshooting

- If you encounter permission issues, ensure the service account has been granted access to the specific Google Drive folder
- Verify that the Google Drive API is enabled for your project
- Check that the JSON key is correctly formatted in your environment variable
