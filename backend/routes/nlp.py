"""
NLP Query Routes
=================
Natural Language Processing endpoint for voice/text queries.

Supports queries like:
    - "Show driver status"
    - "Last drowsiness alert"
    - "How many alerts today?"
    - "Show system summary"

Endpoints:
    POST /api/nlp/query — Process natural language query
"""

import re
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from datetime import datetime

from utils.helpers import format_response, get_date_range

nlp_bp = Blueprint('nlp', __name__)


# ─── Intent Definitions ──────────────────────────────────────────────────
INTENTS = {
    "driver_status": {
        "keywords": ["driver", "status", "current", "state", "condition"],
        "description": "Check current driver status"
    },
    "last_alert": {
        "keywords": ["last", "latest", "recent", "previous", "alert", "event"],
        "description": "Get the most recent alert"
    },
    "alert_count": {
        "keywords": ["how many", "count", "number", "total", "alerts", "events"],
        "description": "Count alerts in a period"
    },
    "summary": {
        "keywords": ["summary", "overview", "report", "show all", "dashboard"],
        "description": "Get system summary"
    },
    "drowsy_events": {
        "keywords": ["drowsy", "drowsiness", "sleeping", "tired", "fatigue"],
        "description": "Get drowsiness events"
    },
    "yawn_events": {
        "keywords": ["yawn", "yawning"],
        "description": "Get yawn events"
    },
    "device_status": {
        "keywords": ["device", "sensor", "camera", "hardware", "iot"],
        "description": "Check device status"
    },
    "help": {
        "keywords": ["help", "what can", "commands", "options"],
        "description": "Show available queries"
    }
}

# Time period extraction
TIME_PATTERNS = {
    "today": ["today", "this day"],
    "week": ["this week", "past week", "last 7 days", "week"],
    "month": ["this month", "past month", "last 30 days", "month"],
    "year": ["this year", "past year", "year"]
}


def classify_intent(query):
    """
    Classify the user's query into an intent.

    Args:
        query: Natural language query string.

    Returns:
        tuple: (intent_key, confidence_score)
    """
    query_lower = query.lower().strip()
    scores = {}

    for intent_key, intent_data in INTENTS.items():
        score = 0
        for keyword in intent_data["keywords"]:
            if keyword in query_lower:
                score += 1
                # Bonus for exact phrase match
                if f" {keyword} " in f" {query_lower} ":
                    score += 0.5
        scores[intent_key] = score

    best_intent = max(scores, key=scores.get)
    confidence = scores[best_intent] / max(len(INTENTS[best_intent]["keywords"]), 1)

    if scores[best_intent] == 0:
        return "unknown", 0.0

    return best_intent, min(confidence, 1.0)


def extract_time_period(query):
    """Extract time period from query."""
    query_lower = query.lower()
    for period, patterns in TIME_PATTERNS.items():
        for pattern in patterns:
            if pattern in query_lower:
                return period
    return "today"  # default


def process_intent(intent, period, db):
    """
    Process a classified intent and return results.

    Args:
        intent: Classified intent string.
        period: Time period string.
        db: Database instance.

    Returns:
        dict: Response data.
    """
    from app import get_memory_store

    if intent == "help":
        return {
            "response": "Here are things you can ask me:",
            "suggestions": [
                "Show driver status",
                "Last drowsiness alert",
                "How many alerts today?",
                "Show system summary",
                "List drowsy events this week",
                "Show yawn events",
                "Device status",
                "Show alerts this month"
            ]
        }

    start, end = get_date_range(period)

    if db is not None:
        query = {"timestamp": {"$gte": start, "$lte": end}}

        if intent == "driver_status":
            latest = db.events.find_one({}, sort=[("timestamp", -1)])
            if latest:
                latest['_id'] = str(latest['_id'])
                status = "Drowsy ⚠️" if latest.get('event_type') == 'drowsy' else "Alert ✅"
                return {
                    "response": f"Current driver status: {status}",
                    "data": latest,
                    "status": status
                }
            return {"response": "No driver data available yet."}

        elif intent == "last_alert":
            latest = db.events.find_one(
                {"event_type": {"$in": ["drowsy", "yawn"]}},
                sort=[("timestamp", -1)]
            )
            if latest:
                latest['_id'] = str(latest['_id'])
                return {
                    "response": f"Last alert: {latest['event_type']} at {latest['timestamp']}",
                    "data": latest
                }
            return {"response": "No alerts recorded."}

        elif intent == "alert_count":
            count = db.events.count_documents(query)
            drowsy = db.events.count_documents({**query, "event_type": "drowsy"})
            yawns = db.events.count_documents({**query, "event_type": "yawn"})
            return {
                "response": f"Total alerts ({period}): {count} ({drowsy} drowsy, {yawns} yawns)",
                "data": {"total": count, "drowsy": drowsy, "yawns": yawns, "period": period}
            }

        elif intent == "summary":
            total = db.events.count_documents(query)
            critical = db.events.count_documents({**query, "severity": "critical"})
            return {
                "response": f"System summary ({period}): {total} total events, {critical} critical",
                "data": {"total": total, "critical": critical, "period": period}
            }

        elif intent == "drowsy_events":
            events = list(
                db.events.find({**query, "event_type": "drowsy"})
                .sort("timestamp", -1).limit(10)
            )
            for e in events:
                e['_id'] = str(e['_id'])
            return {
                "response": f"Found {len(events)} drowsiness events ({period})",
                "data": events
            }

        elif intent == "yawn_events":
            events = list(
                db.events.find({**query, "event_type": "yawn"})
                .sort("timestamp", -1).limit(10)
            )
            for e in events:
                e['_id'] = str(e['_id'])
            return {
                "response": f"Found {len(events)} yawn events ({period})",
                "data": events
            }

        elif intent == "device_status":
            devices = db.events.distinct("device_id")
            return {
                "response": f"Active devices: {', '.join(devices) if devices else 'None'}",
                "data": {"devices": devices, "count": len(devices)}
            }

    else:
        store = get_memory_store()
        events = store['events']
        count = len(events)

        if intent == "driver_status":
            return {"response": f"System running. {count} events logged.", "status": "Active ✅"}
        elif intent == "last_alert":
            if events:
                return {"response": f"Last event: {events[-1].get('event_type', 'unknown')}", "data": events[-1]}
            return {"response": "No alerts recorded."}
        elif intent == "alert_count":
            return {"response": f"Total alerts: {count}", "data": {"total": count}}
        elif intent == "summary":
            return {"response": f"System summary: {count} events logged."}
        else:
            return {"response": f"Found {count} events in memory store."}

    return {"response": "I couldn't process that query. Try 'help' for suggestions."}


@nlp_bp.route('/query', methods=['POST'])
@jwt_required()
def nlp_query():
    """Process a natural language query."""
    data = request.get_json()

    if not data or not data.get('query'):
        return jsonify(format_response(
            status="error",
            message="Query text required. Send: {\"query\": \"your question\"}"
        )), 400

    query_text = data['query'].strip()

    if len(query_text) > 500:
        return jsonify(format_response(
            status="error", message="Query too long (max 500 characters)"
        )), 400

    # Classify intent
    intent, confidence = classify_intent(query_text)
    period = extract_time_period(query_text)

    from app import get_db
    db = get_db()

    # Process
    if intent == "unknown":
        result = {
            "response": "I'm not sure what you're asking. Try 'help' for available queries.",
            "suggestions": [
                "Show driver status",
                "How many alerts today?",
                "Last drowsiness alert"
            ]
        }
    else:
        result = process_intent(intent, period, db)

    return jsonify(format_response(
        data={
            "query": query_text,
            "intent": intent,
            "confidence": round(confidence, 2),
            "period": period,
            "result": result
        },
        message="Query processed"
    )), 200
