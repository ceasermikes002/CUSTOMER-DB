import secrets

# Generate a random secret key
secret_key = secrets.token_hex(16)

# Print the generated secret key
print("Generated Secret Key:", secret_key)
