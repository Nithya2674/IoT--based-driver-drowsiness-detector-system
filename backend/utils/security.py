"""
Security Utilities
===================
Password hashing, JWT helpers, API key management, and encryption.
"""

import os
import secrets
import hashlib
import hmac
from datetime import datetime


def generate_api_key():
    """Generate a secure API key for IoT device authentication."""
    return f"dds_{secrets.token_hex(32)}"


def hash_api_key(api_key):
    """Hash an API key for secure storage."""
    return hashlib.sha256(api_key.encode()).hexdigest()


def verify_api_key(provided_key, stored_hash):
    """Verify an API key against its stored hash."""
    provided_hash = hashlib.sha256(provided_key.encode()).hexdigest()
    return hmac.compare_digest(provided_hash, stored_hash)


def sanitize_input(text):
    """
    Sanitize user input to prevent injection attacks.

    Args:
        text: Raw user input string.

    Returns:
        Sanitized string.
    """
    if not isinstance(text, str):
        return str(text)

    # Remove potentially dangerous characters for MongoDB
    dangerous_chars = ['$', '{', '}']
    for char in dangerous_chars:
        text = text.replace(char, '')

    # Trim whitespace
    text = text.strip()

    # Limit length
    if len(text) > 10000:
        text = text[:10000]

    return text


def validate_email(email):
    """Basic email validation."""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_password(password):
    """
    Validate password strength.

    Returns:
        tuple: (is_valid, message)
    """
    if len(password) < 6:
        return False, "Password must be at least 6 characters long"
    if len(password) > 128:
        return False, "Password must be less than 128 characters"
    return True, "Password is valid"


def generate_device_token(device_id):
    """Generate a unique device token."""
    timestamp = datetime.utcnow().isoformat()
    raw = f"{device_id}:{timestamp}:{secrets.token_hex(16)}"
    return hashlib.sha256(raw.encode()).hexdigest()[:48]
