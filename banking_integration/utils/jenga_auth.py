import requests
import frappe
from base64 import b64encode
from Crypto.Hash import SHA256
from Crypto.Signature import PKCS1_v1_5
from Crypto.PublicKey import RSA


def generate_signature(signature_string):
    credentials = frappe.get_single("Jenga Credentials")

    private_key_pem = credentials.private_key

    message_bytes = signature_string.encode("utf-8")
    digest = SHA256.new(message_bytes)

    private_key = RSA.import_key(private_key_pem)

    signer = PKCS1_v1_5.new(private_key)
    signature = signer.sign(digest)

    return b64encode(signature).decode("utf-8")