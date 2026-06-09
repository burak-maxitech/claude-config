from Crypto.Cipher import AES


def encrypt(data: bytes, key: bytes) -> bytes:
    cipher = AES.new(key, AES.MODE_EAX)
    ciphertext, _ = cipher.encrypt_and_digest(data)
    return ciphertext
