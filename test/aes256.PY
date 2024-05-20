# from os import urandom

# def generate_aes_key():
#   """Generates a random 32-byte AES-256 key."""
#   key = urandom(32)  # Generate 32 random bytes
#   print(key)
#   return key

# # Example usage
# aes_key = generate_aes_key()
# print(f"AES-256 key (hex): {aes_key.hex()}")


import os
import secrets

# Generate a 32-byte key
encryption_key = secrets.token_bytes(32)

# Print the key as a hexadecimal string
print(encryption_key.hex())

# Password securyto solt
print(secrets.SystemRandom().getrandbits(128))
