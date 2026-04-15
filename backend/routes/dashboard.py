"""
Dashboard Routes
=================
Aggregated data endpoints for the monitoring dashboard.

Endpoints:
    GET /api/dashboard/summary    — Overall system summary
    GET /api/dashboard/realtime   — Real-time status data
    GET /api/dashboard/drivers    — Driver status overview
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from datetime import datetime, timedelta

from utils.helpers import format_response, get_date_range

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/summary', methods=['GET'])
@jwt_required()
def get_summary():
    """Get overall system summary with key metrics."""
    from app import get_db, get_memory_store
    db = get_db()

    today_start, now = get_date_range('today')
    week_start, _ = get_date_range('week')

    if db is not None:
        # Today's stats
        today_query = {"timestamp": {"$gte": today_start}}
        today_total = db.events.count_documents(today_query)
        today_drowsy = db.events.count_documents({**today_query, "event_type": "drowsy"})
        today_yawns = db.events.count_documents({**today_query, "event_type": "yawn"})
        today_critical = db.events.count_documents({**today_query, "severity": "critical"})

        # Week stats
        week_query = {"timestamp": {"$gte": week_start}}
        week_total = db.events.count_documents(week_query)

        # Overall
        total_events = db.events.count_documents({})
        total_users = db.users.count_documents({})
        active_devices = db.events.distinct("device_id", today_query)

        # Recent events
        recent = list(
            db.events.find()
            .sort("timestamp", -1)
            .limit(5)
        )
        for r in recent:
            r['_id'] = str(r['_id'])
    else:
        store = get_memory_store()
        events = store['events']
        today_total = len(events)
        today_drowsy = sum(1 for e in events if e.get('event_type') == 'drowsy')
        today_yawns = sum(1 for e in events if e.get('event_type') == 'yawn')
        today_critical = sum(1 for e in events if e.get('severity') == 'critical')
        week_total = today_total
        total_events = today_total
        total_users = len(store['users'])
        active_devices = list(set(e.get('device_id', 'default') for e in events))
        recent = events[-5:]

    summary = {
        "today": {
            "total_events": today_total,
            "drowsy_events": today_drowsy,
            "yawn_events": today_yawns,
            "critical_events": today_critical
        },
        "week": {
            "total_events": week_total,
            "avg_daily": round(week_total / 7, 1)
        },
        "overall": {
            "total_events": total_events,
            "total_users": total_users,
            "active_devices": len(active_devices) if isinstance(active_devices, list) else active_devices
        },
        "recent_events": recent,
        "system_status": "operational",
        "last_updated": datetime.utcnow().isoformat()
    }

    return jsonify(format_response(data=summary)), 200


@dashboard_bp.route('/realtime', methods=['GET'])
@jwt_required()
def get_realtime():
    """Get real-time monitoring data."""
    from app import get_db, get_memory_store
    db = get_db()

    if db is not None:
        # Last 30 seconds of events
        cutoff = (datetime.utcnow() - timedelta(seconds=30)).isoformat()
        recent = list(
            db.events.find({"timestamp": {"$gte": cutoff}})
            .sort("timestamp", -1)
        )
        for r in recent:
            r['_id'] = str(r['_id'])

        # Latest event per device
        pipeline = [
            {"$sort": {"timestamp": -1}},
            {"$group": {
                "_id": "$device_id",
                "latest_event": {"$first": "$$ROOT"},
                "event_count": {"$sum": 1}
            }}
        ]
        devices = list(db.events.aggregate(pipeline))
        for d in devices:
            if d.get('latest_event', {}).get('_id'):
                d['latest_event']['_id'] = str(d['latest_event']['_id'])
    else:
        store = get_memory_store()
        recent = store['events'][-10:]
        devices = []

    return jsonify(format_response(data={
        "recent_events": recent,
        "active_devices": devices,
        "timestamp": datetime.utcnow().isoformat()
    })), 200


@dashboard_bp.route('/drivers', methods=['GET'])
@jwt_required()
def get_driver_status():
    """Get overview of all drivers and their current status."""
    from app import get_db, get_memory_store
    db = get_db()

    if db is not None:
        pipeline = [
            {"$sort": {"timestamp": -1}},
            {"$group": {
                "_id": "$driver_id",
                "last_event": {"$first": "$event_type"},
                "last_timestamp": {"$first": "$timestamp"},
                "total_drowsy": {
                    "$sum": {"$cond": [{"$eq": ["$event_type", "drowsy"]}, 1, 0]}
                },
                "total_yawns": {
                    "$sum": {"$cond": [{"$eq": ["$event_type", "yawn"]}, 1, 0]}
                },
                "total_events": {"$sum": 1}
            }}
        ]
        drivers = list(db.events.aggregate(pipeline))
    else:
        drivers = []

    return jsonify(format_response(data=drivers)), 200
