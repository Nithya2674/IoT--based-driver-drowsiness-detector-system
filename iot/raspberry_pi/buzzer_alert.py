"""
Buzzer & LED Alert System
==========================
GPIO control for alert outputs on Raspberry Pi.
Supports buzzer and LED with different alert patterns.

GPIO Connections:
    - Buzzer (+) → GPIO 23 (BCM) → Pin 16
    - Buzzer (-) → GND → Pin 14
    - Red LED (+) → GPIO 24 (BCM) → Pin 18 (via 220Ω resistor)
    - Red LED (-) → GND → Pin 20
    - Green LED (+) → GPIO 25 (BCM) → Pin 22 (via 220Ω resistor)
    - Green LED (-) → GND → Pin 20
"""

import time
import logging
import threading

logger = logging.getLogger(__name__)

# Try importing RPi.GPIO (only available on Raspberry Pi)
try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False
    logger.info("RPi.GPIO not available. Running in simulation mode.")


# ─── GPIO Pin Configuration ──────────────────────────────────────
BUZZER_PIN = 23    # BCM numbering
RED_LED_PIN = 24
GREEN_LED_PIN = 25


class AlertSystem:
    """
    Alert system controlling buzzer and LED outputs.
    Falls back to console simulation when GPIO is unavailable.
    """

    def __init__(self, enabled=True, buzzer_pin=BUZZER_PIN,
                 red_led_pin=RED_LED_PIN, green_led_pin=GREEN_LED_PIN):
        """
        Initialize the alert system.

        Args:
            enabled: Whether alerts are enabled.
            buzzer_pin: GPIO pin for buzzer (BCM numbering).
            red_led_pin: GPIO pin for red LED.
            green_led_pin: GPIO pin for green LED.
        """
        self.enabled = enabled
        self.buzzer_pin = buzzer_pin
        self.red_led_pin = red_led_pin
        self.green_led_pin = green_led_pin
        self.is_alerting = False
        self._alert_thread = None

        if self.enabled and GPIO_AVAILABLE:
            self._setup_gpio()
        elif self.enabled:
            logger.info("Alert system running in SIMULATION mode (no GPIO)")

    def _setup_gpio(self):
        """Configure GPIO pins."""
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

        GPIO.setup(self.buzzer_pin, GPIO.OUT, initial=GPIO.LOW)
        GPIO.setup(self.red_led_pin, GPIO.OUT, initial=GPIO.LOW)
        GPIO.setup(self.green_led_pin, GPIO.OUT, initial=GPIO.HIGH)  # Green = active

        logger.info(f"GPIO initialized: Buzzer={self.buzzer_pin}, "
                     f"Red LED={self.red_led_pin}, Green LED={self.green_led_pin}")

    def trigger_alert(self, level='warning', duration=3.0):
        """
        Trigger an alert with buzzer and LED.

        Args:
            level: 'warning' (intermittent) or 'danger' (continuous).
            duration: Alert duration in seconds.
        """
        if not self.enabled:
            return

        if self.is_alerting:
            return  # Don't stack alerts

        self.is_alerting = True
        self._alert_thread = threading.Thread(
            target=self._run_alert,
            args=(level, duration),
            daemon=True
        )
        self._alert_thread.start()

    def _run_alert(self, level, duration):
        """Run alert pattern in background thread."""
        try:
            if level == 'danger':
                self._pattern_continuous(duration)
            elif level == 'warning':
                self._pattern_intermittent(duration)
            else:
                self._pattern_single_beep()
        finally:
            self._stop_all()
            self.is_alerting = False

    def _pattern_continuous(self, duration):
        """Continuous buzzer + red LED for critical alerts."""
        logger.warning("🔴 ALERT: Continuous buzzer activated!")

        if GPIO_AVAILABLE:
            GPIO.output(self.buzzer_pin, GPIO.HIGH)
            GPIO.output(self.red_led_pin, GPIO.HIGH)
            GPIO.output(self.green_led_pin, GPIO.LOW)
        else:
            print("\n" + "🚨" * 20)
            print("  ⚠️  BUZZER: ON — DROWSINESS DETECTED!!")
            print("🚨" * 20 + "\n")

        time.sleep(duration)

    def _pattern_intermittent(self, duration):
        """Intermittent beeping for warnings."""
        logger.warning("🟡 ALERT: Intermittent buzzer activated!")

        end_time = time.time() + duration
        while time.time() < end_time:
            if GPIO_AVAILABLE:
                GPIO.output(self.buzzer_pin, GPIO.HIGH)
                GPIO.output(self.red_led_pin, GPIO.HIGH)
            else:
                print("  🔔 BEEP!", end='\r')
            time.sleep(0.2)

            if GPIO_AVAILABLE:
                GPIO.output(self.buzzer_pin, GPIO.LOW)
                GPIO.output(self.red_led_pin, GPIO.LOW)
            time.sleep(0.3)

    def _pattern_single_beep(self):
        """Single short beep."""
        if GPIO_AVAILABLE:
            GPIO.output(self.buzzer_pin, GPIO.HIGH)
            time.sleep(0.1)
            GPIO.output(self.buzzer_pin, GPIO.LOW)
        else:
            print("  🔔 Beep!")

    def _stop_all(self):
        """Turn off all outputs."""
        if GPIO_AVAILABLE:
            GPIO.output(self.buzzer_pin, GPIO.LOW)
            GPIO.output(self.red_led_pin, GPIO.LOW)
            GPIO.output(self.green_led_pin, GPIO.HIGH)  # Green = normal

    def set_status(self, status):
        """
        Set the status LED.

        Args:
            status: 'active' (green), 'drowsy' (red), 'off'
        """
        if not GPIO_AVAILABLE:
            return

        if status == 'active':
            GPIO.output(self.green_led_pin, GPIO.HIGH)
            GPIO.output(self.red_led_pin, GPIO.LOW)
        elif status == 'drowsy':
            GPIO.output(self.green_led_pin, GPIO.LOW)
            GPIO.output(self.red_led_pin, GPIO.HIGH)
        else:
            GPIO.output(self.green_led_pin, GPIO.LOW)
            GPIO.output(self.red_led_pin, GPIO.LOW)

    def cleanup(self):
        """Clean up GPIO resources."""
        if GPIO_AVAILABLE:
            self._stop_all()
            GPIO.cleanup()
            logger.info("GPIO cleaned up")


if __name__ == "__main__":
    print("Testing Alert System...")
    alert = AlertSystem(enabled=True)

    print("\n--- Test 1: Single Beep ---")
    alert.trigger_alert('info')
    time.sleep(1)

    print("\n--- Test 2: Warning Pattern ---")
    alert.trigger_alert('warning', duration=2)
    time.sleep(3)

    print("\n--- Test 3: Danger Pattern ---")
    alert.trigger_alert('danger', duration=2)
    time.sleep(3)

    alert.cleanup()
    print("\nAlert system test complete!")
