from base64 import b64encode

from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5


def generate_signature(signature_string, private_key_pem):
    message_bytes = signature_string.encode("utf-8")
    digest = SHA256.new(message_bytes)

    private_key = RSA.import_key(private_key_pem)

    signer = PKCS1_v1_5.new(private_key)
    signature = signer.sign(digest)

    return b64encode(signature).decode("utf-8")

