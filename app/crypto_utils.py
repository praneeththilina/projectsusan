# import os
# from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
# from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
# from cryptography.hazmat.primitives import hashes
# from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
# from cryptography.hazmat.backends import default_backend
# from base64 import urlsafe_b64encode, urlsafe_b64decode

# # Set up environment variables for encryption keys
# ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY') # Must be 32 bytes for AES-256
# def encrypt(plaintext):
#     nonce = os.urandom(16)
#     cipher = Cipher(algorithms.AES(ENCRYPTION_KEY), modes.GCM(nonce), backend=default_backend())
#     encryptor = cipher.encryptor()
#     ciphertext = encryptor.update(plaintext.encode()) + encryptor.finalize()
#     return urlsafe_b64encode(nonce + encryptor.tag + ciphertext).decode()

# import time

# def decrypt(ciphertext):
#     data = urlsafe_b64decode(ciphertext.encode())
#     nonce = data[:16]
#     tag = data[16:32]
#     ciphertext = data[32:]
#     start_time = time.process_time()
#     cipher = Cipher(algorithms.AES(ENCRYPTION_KEY), modes.GCM(nonce, tag), backend=default_backend())
#     decryptor = cipher.decryptor()
#     end_time = time.process_time()
#     # Calculate the time taken
#     decryption_time = end_time - start_time

#     print(f"Time taken to decrypt: {decryption_time} seconds")

#     return decryptor.update(ciphertext) + decryptor.finalize()

import os
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from base64 import urlsafe_b64encode, urlsafe_b64decode

ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY')
if ENCRYPTION_KEY is None or len(ENCRYPTION_KEY) != 32:
    raise ValueError("ENCRYPTION_KEY environment variable must be set and must be 32 bytes long.")
ENCRYPTION_KEY = ENCRYPTION_KEY.encode()

def encrypt(plaintext):
    nonce = os.urandom(16)
    cipher = Cipher(algorithms.AES(ENCRYPTION_KEY), modes.GCM(nonce), backend=default_backend())
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(plaintext.encode()) + encryptor.finalize()
    return urlsafe_b64encode(nonce + encryptor.tag + ciphertext).decode()

def decrypt(ciphertext):
    data = urlsafe_b64decode(ciphertext.encode())
    nonce = data[:16]
    tag = data[16:32]
    ciphertext = data[32:]
    cipher = Cipher(algorithms.AES(ENCRYPTION_KEY), modes.GCM(nonce, tag), backend=default_backend())
    decryptor = cipher.decryptor()
    return decryptor.update(ciphertext) + decryptor.finalize()
