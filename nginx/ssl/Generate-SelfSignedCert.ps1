# PowerShell script to generate self-signed SSL certificate for local development
# Run this script with administrator privileges

# Create directory for OpenSSL output
$ErrorActionPreference = "Stop"

Write-Host "Generating self-signed SSL certificate for local development..."

# Check if OpenSSL is available
try {
    $openssl = Get-Command openssl -ErrorAction Stop
    Write-Host "OpenSSL found at: $($openssl.Path)"
} catch {
    Write-Host "ERROR: OpenSSL not found. Please install OpenSSL and add it to your PATH."
    Write-Host "You can install OpenSSL using Chocolatey: choco install openssl"
    Write-Host "Or download it from https://slproweb.com/products/Win32OpenSSL.html"
    exit 1
}

# Set working directory to the script location
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -Path $scriptPath

# Generate private key
Write-Host "Generating private key..."
openssl genrsa -out self-signed.key 2048

# Generate CSR (Certificate Signing Request)
Write-Host "Generating Certificate Signing Request (CSR)..."
openssl req -new -key self-signed.key -out self-signed.csr -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"

# Generate self-signed certificate (valid for 365 days)
Write-Host "Generating self-signed certificate..."
openssl x509 -req -days 365 -in self-signed.csr -signkey self-signed.key -out self-signed.crt

# Remove CSR as it's no longer needed
Remove-Item -Path self-signed.csr -Force

Write-Host "`nSelf-signed SSL certificate generated successfully!"
Write-Host "Files created:"
Write-Host "  - $scriptPath\self-signed.key (Private key)"
Write-Host "  - $scriptPath\self-signed.crt (Certificate)"
Write-Host "`nYou can now use these files with your Nginx configuration."