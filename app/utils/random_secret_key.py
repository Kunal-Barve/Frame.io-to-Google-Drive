import secrets

# Generate and print a secure random key
if __name__ == "__main__":
    secret_key = secrets.token_hex(32)  # Generates a 64-character hex string
    print(f"Generated SECRET_KEY: {secret_key}")
    print("\nAdd this to your .env file as:")
    print(f"SECRET_KEY={secret_key}")