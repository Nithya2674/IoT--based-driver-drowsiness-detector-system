"""
User Model
===========
User data model for authentication and role-based access control.
"""

from datetime import datetime
import bcrypt


class UserModel:
    """User data model with password hashing and role management."""

    ROLES = ['user', 'admin']

    @staticmethod
    def create_user(username, email, password, role='user'):
        """Create a new user document."""
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        return {
            "username": username,
            "email": email.lower(),
            "password": hashed.decode('utf-8'),
            "role": role if role in UserModel.ROLES else 'user',
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "is_active": True,
            "devices": [],
            "profile": {
                "full_name": "",
                "phone": "",
                "organization": ""
            }
        }

    @staticmethod
    def verify_password(stored_hash, password):
        """Verify a password against stored hash."""
        return bcrypt.checkpw(
            password.encode('utf-8'),
            stored_hash.encode('utf-8')
        )

    @staticmethod
    def sanitize(user_doc):
        """Remove sensitive fields before returning to client."""
        if user_doc is None:
            return None
        safe = dict(user_doc)
        safe.pop('password', None)
        safe['_id'] = str(safe.get('_id', ''))
        return safe
