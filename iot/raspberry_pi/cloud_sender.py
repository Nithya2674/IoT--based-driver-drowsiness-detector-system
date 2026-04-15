"""
Cloud Sender Module
====================
Sends drowsiness events to the Flask backend REST API.
Includes retry logic, offline queuing, and batch sending.
"""

import json
import time
import logging
import threading
import sqlite3
import os
import requests

logger = logging.getLogger(__name__)


class CloudSender:
    """
    Sends drowsiness events to the cloud backend.
    Features offline queue with SQLite for reliability.
    """

    def __init__(self, backend_url='http://localhost:5000',
                 device_id='RPi-CAM-001', api_key=''):
        """
        Initialize cloud sender.

        Args:
            backend_url: Backend API base URL.
            device_id: Unique device identifier.
            api_key: Device API key for authentication.
        """
        self.backend_url = backend_url.rstrip('/')
        self.device_id = device_id
        self.api_key = api_key
        self.is_connected = False

        # Offline queue
        self.queue_db = os.path.join(os.path.dirname(__file__), 'event_queue.db')
        self._init_queue_db()

        # Background sender thread
        self._sender_thread = threading.Thread(target=self._background_sender, daemon=True)
        self._sender_thread.start()

        # Test connection
        self._test_connection()

    def _init_queue_db(self):
        """Initialize SQLite queue for offline events."""
        conn = sqlite3.connect(self.queue_db)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS event_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_data TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                sent INTEGER DEFAULT 0
            )
        ''')
        conn.commit()
        conn.close()

    def _test_connection(self):
        """Test backend connectivity."""
        try:
            res = requests.get(f"{self.backend_url}/api/health", timeout=5)
            if res.status_code == 200:
                self.is_connected = True
                logger.info(f"[✓] Cloud connected: {self.backend_url}")
            else:
                self.is_connected = False
                logger.warning(f"[✗] Cloud responded with {res.status_code}")
        except requests.exceptions.ConnectionError:
            self.is_connected = False
            logger.warning(f"[✗] Cloud unreachable: {self.backend_url}")
            logger.info("    Events will be queued locally.")

    def send_event(self, event_data):
        """
        Send a drowsiness event to the cloud.
        If offline, queues the event for later sending.

        Args:
            event_data: Dictionary with event details.
        """
        event_data['device_id'] = self.device_id

        if self.is_connected:
            try:
                headers = {
                    'Content-Type': 'application/json',
                    'X-Device-Key': self.api_key
                }
                res = requests.post(
                    f"{self.backend_url}/api/events",
                    json=event_data,
                    headers=headers,
                    timeout=5
                )

                if res.status_code == 201:
                    logger.info(f"[☁️] Event sent: {event_data.get('type', 'unknown')}")
                    return True
                else:
                    logger.warning(f"[☁️] Send failed ({res.status_code}). Queuing.")
                    self._queue_event(event_data)
                    return False
            except requests.exceptions.RequestException as e:
                logger.warning(f"[☁️] Send error: {e}. Queuing.")
                self.is_connected = False
                self._queue_event(event_data)
                return False
        else:
            self._queue_event(event_data)
            return False

    def _queue_event(self, event_data):
        """Queue event for later sending."""
        try:
            conn = sqlite3.connect(self.queue_db)
            conn.execute(
                "INSERT INTO event_queue (event_data) VALUES (?)",
                (json.dumps(event_data),)
            )
            conn.commit()
            conn.close()
            logger.debug("Event queued locally")
        except Exception as e:
            logger.error(f"Queue error: {e}")

    def _background_sender(self):
        """Background thread to send queued events."""
        while True:
            time.sleep(30)  # Check every 30 seconds

            if not self.is_connected:
                self._test_connection()

            if self.is_connected:
                self._send_queued_events()

    def _send_queued_events(self):
        """Send all queued events."""
        try:
            conn = sqlite3.connect(self.queue_db)
            cursor = conn.execute(
                "SELECT id, event_data FROM event_queue WHERE sent = 0 ORDER BY id LIMIT 50"
            )
            rows = cursor.fetchall()

            if not rows:
                conn.close()
                return

            logger.info(f"[☁️] Sending {len(rows)} queued events...")
            sent_ids = []

            for row_id, event_json in rows:
                try:
                    event_data = json.loads(event_json)
                    headers = {
                        'Content-Type': 'application/json',
                        'X-Device-Key': self.api_key
                    }
                    res = requests.post(
                        f"{self.backend_url}/api/events",
                        json=event_data,
                        headers=headers,
                        timeout=5
                    )
                    if res.status_code == 201:
                        sent_ids.append(row_id)
                except Exception:
                    break  # Stop on error

            # Mark sent events
            if sent_ids:
                placeholders = ','.join('?' * len(sent_ids))
                conn.execute(
                    f"UPDATE event_queue SET sent = 1 WHERE id IN ({placeholders})",
                    sent_ids
                )
                conn.commit()
                logger.info(f"[☁️] Sent {len(sent_ids)} queued events")

            conn.close()
        except Exception as e:
            logger.error(f"Queue send error: {e}")

    def send_session_end(self, stats):
        """Send session summary when system shuts down."""
        event = {
            'type': 'session_end',
            'device_id': self.device_id,
            'ear': 0.0,
            'mar': 0.0,
            'session_duration': stats.get('session_duration', 0),
            'blink_count': stats.get('total_blinks', 0),
            'drowsy_count': stats.get('drowsy_events', 0),
            'yawn_count': stats.get('yawn_events', 0)
        }
        self.send_event(event)

    def flush(self):
        """Flush any remaining queued events."""
        if self.is_connected:
            self._send_queued_events()

    def get_queue_size(self):
        """Get number of pending events in queue."""
        try:
            conn = sqlite3.connect(self.queue_db)
            cursor = conn.execute("SELECT COUNT(*) FROM event_queue WHERE sent = 0")
            count = cursor.fetchone()[0]
            conn.close()
            return count
        except Exception:
            return 0
