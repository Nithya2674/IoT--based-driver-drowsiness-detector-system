"""
ThingSpeak IoT Simulation
===========================
Simulates drowsiness sensor data and sends it to ThingSpeak cloud
platform for visualization. This demonstrates the IoT data flow
without requiring physical hardware.

ThingSpeak Fields:
    Field 1: EAR (Eye Aspect Ratio)
    Field 2: MAR (Mouth Aspect Ratio)
    Field 3: Drowsiness Status (0=Alert, 1=Drowsy)
    Field 4: Blink Count
    Field 5: Yawn Count
    Field 6: Session Duration (seconds)

Setup:
    1. Create free account at https://thingspeak.com
    2. Create a new Channel with 6 fields
    3. Get the Write API Key from API Keys tab
    4. Set THINGSPEAK_API_KEY in .env file

Usage:
    python thingspeak_sim.py                # Run simulation
    python thingspeak_sim.py --duration 300 # Run for 5 minutes
    python thingspeak_sim.py --read         # Read data from channel
"""

import os
import sys
import time
import json
import random
import argparse
import requests
from datetime import datetime

# Load environment variables
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))
except ImportError:
    pass


# ─── ThingSpeak Configuration ────────────────────────────────────
THINGSPEAK_WRITE_URL = "https://api.thingspeak.com/update"
THINGSPEAK_READ_URL = "https://api.thingspeak.com/channels/{channel_id}/feeds.json"
THINGSPEAK_API_KEY = os.getenv('THINGSPEAK_API_KEY', 'YOUR_WRITE_API_KEY')
THINGSPEAK_CHANNEL_ID = os.getenv('THINGSPEAK_CHANNEL_ID', 'YOUR_CHANNEL_ID')
THINGSPEAK_READ_KEY = os.getenv('THINGSPEAK_READ_API_KEY', 'YOUR_READ_API_KEY')

# ThingSpeak rate limit: 1 update per 15 seconds (free tier)
UPDATE_INTERVAL = 16  # seconds


class DrowsinessSimulator:
    """
    Simulates realistic drowsiness patterns for IoT data flow testing.
    """

    def __init__(self):
        self.blink_count = 0
        self.yawn_count = 0
        self.session_start = time.time()
        self.is_drowsy = False
        self.drowsy_probability = 0.1  # Initial drowsiness probability

    def generate_reading(self):
        """
        Generate a simulated sensor reading with realistic patterns.

        Returns:
            dict: Simulated sensor data.
        """
        elapsed = time.time() - self.session_start
        minutes = elapsed / 60

        # Increase drowsiness probability over time (fatigue simulation)
        self.drowsy_probability = min(0.7, 0.1 + minutes * 0.02)

        # Simulate drowsiness state changes
        if random.random() < self.drowsy_probability:
            self.is_drowsy = True
            ear = round(random.uniform(0.10, 0.20), 3)  # Low EAR = eyes closing
            mar = round(random.uniform(0.60, 1.00), 3)   # High MAR = yawning
            if random.random() < 0.3:
                self.yawn_count += 1
        else:
            self.is_drowsy = False
            ear = round(random.uniform(0.25, 0.38), 3)   # Normal EAR
            mar = round(random.uniform(0.20, 0.50), 3)   # Normal MAR

        # Simulate blinks
        if random.random() < 0.15:
            self.blink_count += 1

        return {
            "ear": ear,
            "mar": mar,
            "drowsy_status": 1 if self.is_drowsy else 0,
            "blink_count": self.blink_count,
            "yawn_count": self.yawn_count,
            "session_duration": round(elapsed, 1)
        }


def send_to_thingspeak(data, api_key):
    """
    Send data to ThingSpeak channel.

    Args:
        data: Sensor reading dictionary.
        api_key: ThingSpeak Write API key.

    Returns:
        bool: True if successful.
    """
    payload = {
        'api_key': api_key,
        'field1': data['ear'],
        'field2': data['mar'],
        'field3': data['drowsy_status'],
        'field4': data['blink_count'],
        'field5': data['yawn_count'],
        'field6': data['session_duration']
    }

    try:
        response = requests.post(THINGSPEAK_WRITE_URL, data=payload, timeout=10)
        entry_id = response.text.strip()

        if entry_id != '0' and response.status_code == 200:
            return True, int(entry_id)
        else:
            return False, 0
    except requests.exceptions.RequestException as e:
        print(f"  [ERROR] ThingSpeak request failed: {e}")
        return False, 0


def read_from_thingspeak(channel_id, read_key, results=10):
    """
    Read latest data from ThingSpeak channel.

    Args:
        channel_id: ThingSpeak channel ID.
        read_key: Read API key.
        results: Number of results to fetch.

    Returns:
        list: Channel feed data.
    """
    url = THINGSPEAK_READ_URL.format(channel_id=channel_id)
    params = {
        'api_key': read_key,
        'results': results
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get('feeds', [])
        else:
            print(f"  [ERROR] Read failed: {response.status_code}")
            return []
    except requests.exceptions.RequestException as e:
        print(f"  [ERROR] Read request failed: {e}")
        return []


def run_simulation(duration=300, api_key=None):
    """
    Run the drowsiness simulation for a specified duration.

    Args:
        duration: Simulation duration in seconds.
        api_key: ThingSpeak Write API key.
    """
    if not api_key:
        api_key = THINGSPEAK_API_KEY

    if api_key == 'YOUR_WRITE_API_KEY':
        print("\n" + "=" * 60)
        print("  ⚠️  SIMULATION MODE (No ThingSpeak API Key)")
        print("  Data will be printed to console only.")
        print("  Set THINGSPEAK_API_KEY in .env for cloud upload.")
        print("=" * 60)
        cloud_mode = False
    else:
        cloud_mode = True
        print(f"\n  ☁️  Cloud Mode: Sending to ThingSpeak")

    simulator = DrowsinessSimulator()
    start_time = time.time()
    reading_count = 0

    print(f"\n{'='*60}")
    print(f"  DROWSINESS IoT SIMULATION")
    print(f"  Duration: {duration}s | Interval: {UPDATE_INTERVAL}s")
    print(f"  Cloud: {'ThingSpeak' if cloud_mode else 'Console only'}")
    print(f"{'='*60}\n")
    print(f"  {'#':>3} | {'Time':>8} | {'EAR':>6} | {'MAR':>6} | {'Status':>8} | {'Blinks':>6} | {'Yawns':>5} | {'Cloud':>6}")
    print(f"  {'-'*3}-+-{'-'*8}-+-{'-'*6}-+-{'-'*6}-+-{'-'*8}-+-{'-'*6}-+-{'-'*5}-+-{'-'*6}")

    try:
        while time.time() - start_time < duration:
            reading = simulator.generate_reading()
            reading_count += 1

            status = "DROWSY" if reading['drowsy_status'] == 1 else "ALERT"
            elapsed = time.time() - start_time

            # Send to ThingSpeak
            cloud_status = "—"
            if cloud_mode:
                success, entry_id = send_to_thingspeak(reading, api_key)
                cloud_status = f"#{entry_id}" if success else "FAIL"

            print(f"  {reading_count:>3} | {elapsed:>7.1f}s | {reading['ear']:>6.3f} | "
                  f"{reading['mar']:>6.3f} | {status:>8} | {reading['blink_count']:>6} | "
                  f"{reading['yawn_count']:>5} | {cloud_status:>6}")

            # Wait for next interval
            time.sleep(UPDATE_INTERVAL)

    except KeyboardInterrupt:
        print("\n\n  [INFO] Simulation stopped by user.")

    # Summary
    print(f"\n{'='*60}")
    print(f"  SIMULATION COMPLETE")
    print(f"  Readings sent: {reading_count}")
    print(f"  Duration: {time.time() - start_time:.1f}s")
    print(f"  Blinks: {simulator.blink_count}")
    print(f"  Yawns: {simulator.yawn_count}")
    print(f"{'='*60}\n")


def display_channel_data():
    """Read and display data from ThingSpeak channel."""
    if THINGSPEAK_CHANNEL_ID == 'YOUR_CHANNEL_ID':
        print("  ⚠️  Set THINGSPEAK_CHANNEL_ID in .env file")
        return

    print(f"\n  Reading from ThingSpeak Channel {THINGSPEAK_CHANNEL_ID}...\n")
    feeds = read_from_thingspeak(THINGSPEAK_CHANNEL_ID, THINGSPEAK_READ_KEY)

    if not feeds:
        print("  No data found.")
        return

    print(f"  {'Time':>20} | {'EAR':>6} | {'MAR':>6} | {'Status':>8} | {'Blinks':>6} | {'Yawns':>5}")
    print(f"  {'-'*20}-+-{'-'*6}-+-{'-'*6}-+-{'-'*8}-+-{'-'*6}-+-{'-'*5}")

    for feed in feeds:
        status = "DROWSY" if feed.get('field3') == '1' else "ALERT"
        print(f"  {feed.get('created_at', ''):>20} | {feed.get('field1', ''):>6} | "
              f"{feed.get('field2', ''):>6} | {status:>8} | {feed.get('field4', ''):>6} | "
              f"{feed.get('field5', ''):>5}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ThingSpeak IoT Simulation")
    parser.add_argument('--duration', type=int, default=300,
                        help='Simulation duration in seconds (default: 300)')
    parser.add_argument('--read', action='store_true',
                        help='Read data from ThingSpeak channel')
    parser.add_argument('--api-key', type=str, default=None,
                        help='ThingSpeak Write API key')
    args = parser.parse_args()

    if args.read:
        display_channel_data()
    else:
        run_simulation(duration=args.duration, api_key=args.api_key)
