"""
Authentication Middleware
==========================
JWT token validation and role-based access control decorators.
"""

from functools import wraps
from flask import request, jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity, get_jwt


def jwt_required_custom(fn):
    """Custom JWT validation decorator with better error messages."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            verify_jwt_in_request()
            return fn(*args, **kwargs)
        except Exception as e:
            return jsonify({
                "error": "Authentication required",
                "message": str(e)
            }), 401
    return wrapper


def role_required(required_role):
    """
    Role-based access control decorator.

    Usage:
        @role_required('admin')
        def admin_only_route():
            pass
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            try:
                verify_jwt_in_request()
                claims = get_jwt()
                user_role = claims.get('role', 'user')

                if user_role != required_role and user_role != 'admin':
                    return jsonify({
                        "error": "Insufficient permissions",
                        "required_role": required_role,
                        "your_role": user_role
                    }), 403

                return fn(*args, **kwargs)
            except Exception as e:
                return jsonify({
                    "error": "Authentication required",
                    "message": str(e)
                }), 401
        return wrapper
    return decorator


def device_auth_required(fn):
    """
    Device API key authentication decorator.
    Expects header: X-Device-Key: <api_key>
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        api_key = request.headers.get('X-Device-Key')

        if not api_key:
            return jsonify({
                "error": "Device API key required",
                "message": "Include X-Device-Key header"
            }), 401

        # Import here to avoid circular imports
        from app import get_db, get_memory_store
        from utils.security import hash_api_key

        db = get_db()
        if db is not None:
            key_hash = hash_api_key(api_key)
            device = db.devices.find_one({"api_key_hash": key_hash})
            if not device:
                # Fallback: check config
                from config import get_config
                config = get_config()
                if api_key != config.DEVICE_API_KEY:
                    return jsonify({"error": "Invalid device API key"}), 401
        else:
            from config import get_config
            config = get_config()
            if api_key != config.DEVICE_API_KEY:
                return jsonify({"error": "Invalid device API key"}), 401

        return fn(*args, **kwargs)
    return wrapper
