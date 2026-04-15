"""
Drowsiness Events Routes
==========================
CRUD operations for drowsiness detection events.

Endpoints:
    POST /api/events          — Log a new event (from IoT device)
    GET  /api/events          — List events with filters
    GET  /api/events/latest   — Get latest events
    GET  /api/events/stats    — Get aggregated statistics
    GET  /api/events/<id>     — Get single event
    PUT  /api/events/<id>/ack — Acknowledge an event
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime

from models.event import EventModel
from utils.helpers import format_response, paginate_query, get_date_range
from utils.security import sanitize_input

events_bp = Blueprint('events', __name__)


@events_bp.route('', methods=['POST'])
def create_event():
    """
    Log a new drowsiness event.
    Can be called by IoT device (with X-Device-Key) or authenticated user.
    """
    data = request.get_json()

    if not data:
        return jsonify(format_response(
            status="error", message="Request body required"
        )), 400

    # Extract event data
    event_type = sanitize_input(data.get('type', data.get('event_type', 'drowsy')))
    ear_value = float(data.get('ear', data.get('ear_value', 0.0)))
    mar_value = float(data.get('mar', data.get('mar_value', 0.0)))
    device_id = sanitize_input(data.get('device_id', 'default'))
    driver_id = sanitize_input(data.get('driver_id', ''))

    # Auto-determine severity
    duration = float(data.get('duration', data.get('session_duration', 0)))
    severity = EventModel.determine_severity(ear_value, mar_value, duration)

    metadata = {
        'location': data.get('location'),
        'session_id': data.get('session_id'),
        'blink_count': data.get('blink_count', 0),
        'session_duration': duration
    }

    event_doc = EventModel.create_event(
        event_type=event_type,
        ear_value=ear_value,
        mar_value=mar_value,
        device_id=device_id,
        driver_id=driver_id,
        severity=severity,
        metadata=metadata
    )

    from app import get_db, get_memory_store
    db = get_db()

    if db is not None:
        result = db.events.insert_one(event_doc)
        event_doc['_id'] = str(result.inserted_id)
    else:
        store = get_memory_store()
        event_doc['_id'] = f"evt_{len(store['events'])}"
        store['events'].append(event_doc)

    return jsonify(format_response(
        data=EventModel.sanitize(event_doc),
        message="Event logged successfully"
    )), 201


@events_bp.route('', methods=['GET'])
@jwt_required()
def list_events():
    """List events with optional filters and pagination."""
    # Query params
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    event_type = request.args.get('type', None)
    severity = request.args.get('severity', None)
    device_id = request.args.get('device_id', None)
    period = request.args.get('period', None)

    skip, limit = paginate_query(page, per_page)

    from app import get_db, get_memory_store
    db = get_db()

    if db is not None:
        query = {}
        if event_type:
            query['event_type'] = event_type
        if severity:
            query['severity'] = severity
        if device_id:
            query['device_id'] = device_id
        if period:
            start, end = get_date_range(period)
            query['timestamp'] = {"$gte": start, "$lte": end}

        total = db.events.count_documents(query)
        events = list(
            db.events.find(query)
            .sort("timestamp", -1)
            .skip(skip)
            .limit(limit)
        )
        events = [EventModel.sanitize(e) for e in events]
    else:
        store = get_memory_store()
        events = store['events']

        if event_type:
            events = [e for e in events if e.get('event_type') == event_type]
        if severity:
            events = [e for e in events if e.get('severity') == severity]

        total = len(events)
        events = [EventModel.sanitize(e) for e in events[skip:skip + limit]]

    return jsonify(format_response(
        data=events,
        message=f"Found {total} events",
        pagination={
            "page": page,
            "per_page": limit,
            "total": total,
            "pages": (total + limit - 1) // limit
        }
    )), 200


@events_bp.route('/latest', methods=['GET'])
@jwt_required()
def latest_events():
    """Get the latest N events."""
    count = request.args.get('count', 10, type=int)
    count = min(count, 50)

    from app import get_db, get_memory_store
    db = get_db()

    if db is not None:
        events = list(
            db.events.find()
            .sort("timestamp", -1)
            .limit(count)
        )
        events = [EventModel.sanitize(e) for e in events]
    else:
        store = get_memory_store()
        events = [EventModel.sanitize(e) for e in store['events'][-count:]]
        events.reverse()

    return jsonify(format_response(data=events)), 200


@events_bp.route('/stats', methods=['GET'])
@jwt_required()
def event_stats():
    """Get aggregated event statistics."""
    period = request.args.get('period', 'week')
    start, end = get_date_range(period)

    from app import get_db, get_memory_store
    db = get_db()

    if db is not None:
        query = {"timestamp": {"$gte": start, "$lte": end}}
        total = db.events.count_documents(query)
        drowsy = db.events.count_documents({**query, "event_type": "drowsy"})
        yawns = db.events.count_documents({**query, "event_type": "yawn"})
        critical = db.events.count_documents({**query, "severity": "critical"})

        # Hourly distribution
        pipeline = [
            {"$match": query},
            {"$group": {
                "_id": {"$substr": ["$timestamp", 11, 2]},
                "count": {"$sum": 1}
            }},
            {"$sort": {"_id": 1}}
        ]
        hourly = list(db.events.aggregate(pipeline))
        hourly_data = {h['_id']: h['count'] for h in hourly}

        # Daily distribution
        pipeline_daily = [
            {"$match": query},
            {"$group": {
                "_id": {"$substr": ["$timestamp", 0, 10]},
                "count": {"$sum": 1}
            }},
            {"$sort": {"_id": 1}}
        ]
        daily = list(db.events.aggregate(pipeline_daily))
        daily_data = [{"date": d['_id'], "count": d['count']} for d in daily]
    else:
        store = get_memory_store()
        events = store['events']
        total = len(events)
        drowsy = sum(1 for e in events if e.get('event_type') == 'drowsy')
        yawns = sum(1 for e in events if e.get('event_type') == 'yawn')
        critical = sum(1 for e in events if e.get('severity') == 'critical')
        hourly_data = {}
        daily_data = []

    stats = {
        "period": period,
        "total_events": total,
        "drowsy_events": drowsy,
        "yawn_events": yawns,
        "critical_events": critical,
        "hourly_distribution": hourly_data,
        "daily_trend": daily_data,
        "alert_rate": round(total / max(7, 1), 1) if period == 'week' else total
    }

    return jsonify(format_response(data=stats)), 200


@events_bp.route('/<event_id>', methods=['GET'])
@jwt_required()
def get_event(event_id):
    """Get a single event by ID."""
    from app import get_db, get_memory_store
    db = get_db()

    if db is not None:
        from bson import ObjectId
        try:
            event = db.events.find_one({"_id": ObjectId(event_id)})
        except Exception:
            event = None
    else:
        store = get_memory_store()
        event = next((e for e in store['events'] if e.get('_id') == event_id), None)

    if not event:
        return jsonify(format_response(
            status="error", message="Event not found"
        )), 404

    return jsonify(format_response(
        data=EventModel.sanitize(event)
    )), 200


@events_bp.route('/<event_id>/ack', methods=['PUT'])
@jwt_required()
def acknowledge_event(event_id):
    """Acknowledge a drowsiness event."""
    from app import get_db, get_memory_store
    db = get_db()

    data = request.get_json() or {}
    notes = sanitize_input(data.get('notes', ''))

    if db is not None:
        from bson import ObjectId
        try:
            result = db.events.update_one(
                {"_id": ObjectId(event_id)},
                {"$set": {
                    "acknowledged": True,
                    "acknowledged_by": get_jwt_identity(),
                    "acknowledged_at": datetime.utcnow().isoformat(),
                    "notes": notes
                }}
            )
            if result.modified_count == 0:
                return jsonify(format_response(
                    status="error", message="Event not found"
                )), 404
        except Exception:
            return jsonify(format_response(
                status="error", message="Invalid event ID"
            )), 400
    else:
        store = get_memory_store()
        event = next((e for e in store['events'] if e.get('_id') == event_id), None)
        if event:
            event['acknowledged'] = True
        else:
            return jsonify(format_response(
                status="error", message="Event not found"
            )), 404

    return jsonify(format_response(message="Event acknowledged")), 200
