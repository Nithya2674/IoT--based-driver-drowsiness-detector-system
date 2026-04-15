"""
Drowsiness Event Model
=======================
Data model for drowsiness detection events logged by IoT devices.
"""

from datetime import datetime


class EventModel:
    """Drowsiness event data model."""

    EVENT_TYPES = ['drowsy', 'yawn', 'distracted', 'normal']
    SEVERITY_LEVELS = ['low', 'medium', 'high', 'critical']

    @staticmethod
    def create_event(event_type, ear_value, mar_value, device_id='default',
                     driver_id=None, severity='medium', metadata=None):
        """
        Create a new drowsiness event document.

        Args:
            event_type: Type of event (drowsy, yawn, distracted, normal).
            ear_value: Eye Aspect Ratio value at detection.
            mar_value: Mouth Aspect Ratio value at detection.
            device_id: IoT device identifier.
            driver_id: Driver/user identifier.
            severity: Event severity level.
            metadata: Additional event metadata.

        Returns:
            dict: Event document ready for database insertion.
        """
        return {
            "event_type": event_type if event_type in EventModel.EVENT_TYPES else 'drowsy',
            "severity": severity if severity in EventModel.SEVERITY_LEVELS else 'medium',
            "ear_value": round(float(ear_value), 4),
            "mar_value": round(float(mar_value), 4),
            "device_id": device_id,
            "driver_id": driver_id,
            "timestamp": datetime.utcnow().isoformat(),
            "location": metadata.get('location', None) if metadata else None,
            "session_id": metadata.get('session_id', None) if metadata else None,
            "blink_count": metadata.get('blink_count', 0) if metadata else 0,
            "session_duration": metadata.get('session_duration', 0) if metadata else 0,
            "acknowledged": False,
            "notes": ""
        }

    @staticmethod
    def sanitize(event_doc):
        """Prepare event document for API response."""
        if event_doc is None:
            return None
        safe = dict(event_doc)
        safe['_id'] = str(safe.get('_id', ''))
        return safe

    @staticmethod
    def determine_severity(ear_value, mar_value, duration=0):
        """
        Automatically determine event severity based on metrics.

        Args:
            ear_value: Eye Aspect Ratio.
            mar_value: Mouth Aspect Ratio.
            duration: Duration of the drowsy state in seconds.

        Returns:
            str: Severity level.
        """
        if ear_value < 0.15 or duration > 5:
            return 'critical'
        elif ear_value < 0.18 or duration > 3:
            return 'high'
        elif ear_value < 0.22 or mar_value > 0.8:
            return 'medium'
        else:
            return 'low'
