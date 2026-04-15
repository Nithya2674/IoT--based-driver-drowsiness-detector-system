"""
Authentication Routes
======================
Handles user registration, login, and profile management.

Endpoints:
    POST /api/auth/register  — Create new user account
    POST /api/auth/login     — Login and receive JWT token
    GET  /api/auth/profile   — Get current user profile
    GET  /api/auth/users     — List all users (admin only)
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token, jwt_required,
    get_jwt_identity, get_jwt
)
from datetime import datetime

from app import get_memory_store
from models.user import UserModel
from middleware.auth_middleware import role_required
from utils.security import validate_email, validate_password, sanitize_input
from utils.helpers import format_response

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['POST'])
def register():
    """Register a new user account."""
    data = request.get_json()

    if not data:
        return jsonify(format_response(
            status="error", message="Request body required"
        )), 400

    username = sanitize_input(data.get('username', ''))
    email = sanitize_input(data.get('email', ''))
    password = data.get('password', '')
    role = data.get('role', 'user')

    # Validation
    if not username or len(username) < 3:
        return jsonify(format_response(
            status="error", message="Username must be at least 3 characters"
        )), 400

    if not validate_email(email):
        return jsonify(format_response(
            status="error", message="Invalid email address"
        )), 400

    valid, msg = validate_password(password)
    if not valid:
        return jsonify(format_response(status="error", message=msg)), 400

    # Check for existing user
    from flask import current_app
    db = current_app.mongo_db

    if db is not None:
        if db.users.find_one({"$or": [{"email": email.lower()}, {"username": username}]}):
            return jsonify(format_response(
                status="error", message="User already exists"
            )), 409

        user_doc = UserModel.create_user(username, email, password, role)
        result = db.users.insert_one(user_doc)
        user_doc['_id'] = str(result.inserted_id)
    else:
        store = get_memory_store()
        for u in store['users']:
            if u['email'] == email.lower() or u['username'] == username:
                return jsonify(format_response(
                    status="error", message="User already exists"
                )), 409

        user_doc = UserModel.create_user(username, email, password, role)
        user_doc['_id'] = f"mem_{len(store['users'])}"
        store['users'].append(user_doc)

    # Generate token
    additional_claims = {"role": user_doc.get('role', 'user')}
    access_token = create_access_token(
        identity=user_doc.get('email'),
        additional_claims=additional_claims
    )

    return jsonify(format_response(
        data={
            "user": UserModel.sanitize(user_doc),
            "access_token": access_token
        },
        message="Registration successful"
    )), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    """Authenticate user and return JWT token."""
    data = request.get_json()

    if not data:
        return jsonify(format_response(
            status="error", message="Request body required"
        )), 400

    email = sanitize_input(data.get('email', ''))
    password = data.get('password', '')

    if not email or not password:
        return jsonify(format_response(
            status="error", message="Email and password required"
        )), 400

    from flask import current_app
    db = current_app.mongo_db

    user_doc = None
    if db is not None:
        user_doc = db.users.find_one({"email": email.lower()})
    else:
        store = get_memory_store()
        for u in store['users']:
            if u['email'] == email.lower():
                user_doc = u
                break

    if not user_doc:
        return jsonify(format_response(
            status="error", message="Invalid credentials"
        )), 401

    if not UserModel.verify_password(user_doc['password'], password):
        return jsonify(format_response(
            status="error", message="Invalid credentials"
        )), 401

    # Generate token
    additional_claims = {"role": user_doc.get('role', 'user')}
    access_token = create_access_token(
        identity=user_doc['email'],
        additional_claims=additional_claims
    )

    # Update last login
    if db is not None:
        db.users.update_one(
            {"email": email.lower()},
            {"$set": {"last_login": datetime.utcnow().isoformat()}}
        )

    return jsonify(format_response(
        data={
            "user": UserModel.sanitize(user_doc),
            "access_token": access_token
        },
        message="Login successful"
    )), 200


@auth_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    """Get current user's profile."""
    current_user_email = get_jwt_identity()

    from flask import current_app
    db = current_app.mongo_db

    if db is not None:
        user_doc = db.users.find_one({"email": current_user_email})
    else:
        store = get_memory_store()
        user_doc = next(
            (u for u in store['users'] if u['email'] == current_user_email),
            None
        )

    if not user_doc:
        return jsonify(format_response(
            status="error", message="User not found"
        )), 404

    return jsonify(format_response(
        data=UserModel.sanitize(user_doc)
    )), 200


@auth_bp.route('/users', methods=['GET'])
@role_required('admin')
def list_users():
    """List all users (admin only)."""
    from flask import current_app
    db = current_app.mongo_db

    if db is not None:
        users = list(db.users.find({}, {"password": 0}))
        for u in users:
            u['_id'] = str(u['_id'])
            
            # Fetch events associated with this user (or system-wide if not user-specific)
            # In a full system, you would filter by user email: {"user_email": u["email"]}
            # Here we provide dummy aggregation or system-wide stats if missing
            drowsy = db.events.count_documents({"type": "drowsy"})
            yawns = db.events.count_documents({"type": "yawn"})
            total = db.events.count_documents({})
            
            u['drowsy_alerts'] = drowsy
            u['yawn_count'] = yawns
            u['total_events'] = total
            u['recent_status'] = "Active" if u.get('is_active', True) else "Inactive"
    else:
        store = get_memory_store()
        users = []
        for u in store['users']:
            sanitized = UserModel.sanitize(u)
            sanitized['drowsy_alerts'] = 0
            sanitized['yawn_count'] = 0
            sanitized['total_events'] = 0
            sanitized['recent_status'] = "Active"
            users.append(sanitized)

    return jsonify(format_response(
        data=users,
        message=f"Found {len(users)} users"
    )), 200
