# Copyright (c) 2026 RokctAI
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from typing import Any, Optional
# Copyright (c) 2025, ROKCT and contributors
# For license information, please see license.txt

import frappe
from ..utils import get_whatsapp_config
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import base64
import json
import os


@frappe.whitelist(allow_guest=True)
def flow_data() -> Any:
    """
    Meta Data Endpoint for WhatsApp Flows.
    Handles encryption/decryption of the request from Meta.
    """
    try:
        req_json = frappe.request.json
        encrypted_flow_data_b64 = req_json.get("encrypted_flow_data")
        encrypted_aes_key_b64 = req_json.get("encrypted_aes_key")
        initial_vector_b64 = req_json.get("initial_vector")

        config = get_whatsapp_config()
        if not config or not config.private_key:
            return {"error": "Server not configured for encryption."}

        # 1. Decrypt AES Key
        private_key = serialization.load_pem_private_key(
            config.get_password("private_key").encode(),
            password=None,
            backend=default_backend()
        )

        decrypted_aes_key = private_key.decrypt(
            base64.b64decode(encrypted_aes_key_b64),
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )

        # 2. Decrypt Flow Data
        iv = base64.b64decode(initial_vector_b64)
        flow_data_encrypted = base64.b64decode(encrypted_flow_data_b64)
        # Auth Tag is the last 16 bytes of the encrypted data in some implementations,
        # or separate. Meta sends it appended end?
        # Meta spec: "The tag is the last 16 bytes of the encrypted_flow_data"
        tag = flow_data_encrypted[-16:]
        ciphertext = flow_data_encrypted[:-16]

        cipher = Cipher(
            algorithms.AES(decrypted_aes_key),
            modes.GCM(iv, tag),
            backend=default_backend()
        )
        decryptor = cipher.decryptor()
        decrypted_data_json = decryptor.update(
            ciphertext) + decryptor.finalize()
        decoded_data = json.loads(decrypted_data_json.decode('utf-8'))

        # 3. Process Logic
        # decoded_data contains 'flow_token', 'screen', 'data'
        response_data = handle_business_logic(decoded_data)

        # 4. Encrypt Response
        # Generate new IV
        flipped_iv = bytearray(iv)
        for i in range(len(flipped_iv)):
            flipped_iv[i] ^= 0xFF
        new_iv = bytes(flipped_iv)

        encryptor = Cipher(
            algorithms.AES(decrypted_aes_key),
            modes.GCM(new_iv),
            backend=default_backend()
        ).encryptor()

        response_bytes = json.dumps(response_data).encode('utf-8')
        ciphertext_resp = encryptor.update(
            response_bytes) + encryptor.finalize()
        tag_resp = encryptor.tag

        encrypted_response = ciphertext_resp + tag_resp
        return base64.b64encode(encrypted_response).decode('utf-8')

    except Exception as e:
        frappe.log_error(f"Flow Encryption Error: {str(e)}")
        # Start simplistic error response? Meta expects specific error format
        # or 500
        frappe.response.status_code = 500
        return str(e)


def handle_business_logic(data):
    """
    Determine next screen or data based on input.
    """
    # ... previous mocked logic ...
    # Extract flow_token to identify product
    # flow_token = data.get('flow_token')
    # Use generic layout for now

    return {
        "screen": "screen_0",
        "data": {
            "options": [
                {"id": "opt_1", "title": "Option 1 (Generic)"},
                {"id": "opt_2", "title": "Option 2 (Generic)"}
            ]
        }
    }
