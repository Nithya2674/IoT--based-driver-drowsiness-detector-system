"""
Helper Utilities
=================
General-purpose helper functions for the backend.
"""

from datetime import datetime, timedelta
from bson import ObjectId


def parse_datetime(dt_string):
    """Parse an ISO format datetime string."""
    try:
        return datetime.fromisoformat(dt_string)
    except (ValueError, TypeError):
        return None


def get_date_range(period='today'):
    """
    Get start and end datetime for common periods.

    Args:
        period: 'today', 'week', 'month', 'year'

    Returns:
        tuple: (start_datetime, end_datetime)
    """
    now = datetime.utcnow()

    if period == 'today':
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == 'week':
        start = now - timedelta(days=7)
    elif period == 'month':
        start = now - timedelta(days=30)
    elif period == 'year':
        start = now - timedelta(days=365)
    else:
        start = now - timedelta(days=1)

    return start.isoformat(), now.isoformat()


def paginate_query(page=1, per_page=20):
    """
    Calculate skip and limit for MongoDB pagination.

    Args:
        page: Page number (1-indexed).
        per_page: Items per page.

    Returns:
        tuple: (skip, limit)
    """
    page = max(1, int(page))
    per_page = min(100, max(1, int(per_page)))
    skip = (page - 1) * per_page
    return skip, per_page


def format_response(data=None, message="Success", status="success", **kwargs):
    """Standard API response format."""
    response = {
        "status": status,
        "message": message,
        "timestamp": datetime.utcnow().isoformat()
    }
    if data is not None:
        response["data"] = data
    response.update(kwargs)
    return response


def is_valid_object_id(id_string):
    """Check if a string is a valid MongoDB ObjectId."""
    try:
        ObjectId(id_string)
        return True
    except Exception:
        return False
