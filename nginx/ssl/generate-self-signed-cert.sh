#!/bin/bash
# Generate self-signed SSL certificate for local development

# Create private key
openssl genrsa -out self-signed.key 2048

# Generate CSR (Certificate Signing Request)
openssl req -new -key self-signed.key -out self-signed.csr -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"

# Generate self-signed certificate (valid for 365 days)
openssl x509 -req -days 365 -in self-signed.csr -signkey self-signed.key -out self-signed.crt

# Remove CSR as it's no longer needed
rm self-signed.csr

echo "Self-signed SSL certificate generated successfully."
echo "Files created:"
echo "  - self-signed.key (Private key)"
echo "  - self-signed.crt (Certificate)"