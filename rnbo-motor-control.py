#!/usr/bin/env python3

import time
import requests
import socket
from gpiozero import PWMLED, PWMOutputDevice

# ----- RNBO OSCQuery Configuration -----

# The hostname of the Pi, resolved via mDNS (e.g., raspberrypi.local)
HOSTNAME = socket.gethostname() + ".local"
PORT = 5678  # Default OSCQuery port

try:
    ip = socket.gethostbyname(HOSTNAME)
    OSCQUERY_URL = f"http://{ip}:{PORT}"
except socket.gaierror:
    print(f"Could not resolve hostname '{HOSTNAME}'. Check network or mDNS setup.")
    exit(1)

# ----- GPIO Pin Setup -----
MOTOR_PIN = 5
LED_PINS = [26, 19, 13]  # Updated LED pins

# ----- RNBO Parameter Path -----
# This will be determined dynamically at runtime
TARGET_PATH = None

# ----- OSCQuery Functions -----

def fetch_full_tree(oscquery_url):
    """Fetch the RNBO parameter tree from the OSCQuery server."""
    try:
        response = requests.get(oscquery_url, timeout=2)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Failed to get OSCQuery root. Status code: {response.status_code}")
    except Exception as e:
        print(f"Exception during fetch: {e}")
    return None

def search_tree_for_value(tree, target_path):
    """Recursively search for a value at the given RNBO path."""
    if not isinstance(tree, dict):
        return None

    if tree.get("FULL_PATH") == target_path:
        val = tree.get("value") or tree.get("VALUE")
        return val[0] if isinstance(val, list) and val else val

    for child in (tree.get("CONTENTS") or {}).values():
        result = search_tree_for_value(child, target_path)
        if result is not None:
            return result
    return None

def get_dynamic_output_path(oscquery_url, leds, timeout=30):
    """
    Dynamically detects whether output path is /inst/0 or /inst/1.
    While waiting, blink LEDs to indicate boot-up.
    """
    print("Searching for RNBO output path...")
    start_time = time.time()
    blink_state = False

    while time.time() - start_time < timeout:
        tree = fetch_full_tree(oscquery_url)
        if tree:
            for i in range(2):  # Check both /inst/0 and /inst/1
                path = f"/rnbo/inst/{i}/messages/out/output1"
                if search_tree_for_value(tree, path) is not None:
                    for led in leds:
                        led.off()
                    return path

        # Blink LEDs while waiting
        blink_state = not blink_state
        for led in leds:
            led.value = 0.3 if blink_state else 0
        time.sleep(0.5)

    # Timeout: stop blinking and exit
    for led in leds:
        led.off()
    print("Timeout waiting for RNBO to become available.")
    exit(1)

def get_parameter_value(oscquery_url, target_path):
    """Fetch the current value of the given RNBO parameter."""
    tree = fetch_full_tree(oscquery_url)
    if tree:
        return search_tree_for_value(tree, target_path)
    return None

# ----- Main Application Logic -----

def main():
    # Initialize LEDs (once!)
    leds = [PWMLED(pin) for pin in LED_PINS]

    # Blink LEDs while waiting for RNBO to start and detect the correct path
    output_path = get_dynamic_output_path(OSCQUERY_URL, leds)

    # Set up motor control
    motor = PWMOutputDevice(MOTOR_PIN)

    print(f"Polling RNBO value at '{output_path}' from {OSCQUERY_URL}...")

    try:
        while True:
            val = get_parameter_value(OSCQUERY_URL, output_path)

            if val is not None:
                try:
                    duty_cycle = max(0, min(100, float(val)))  # Clamp to 0–100
                    pwm_value = duty_cycle / 100.0  # Scale for PWM

                    motor.value = pwm_value
                    for led in leds:
                        led.value = pwm_value

                    print(f"Motor & LEDs set to {duty_cycle:.1f}%")
                except (ValueError, TypeError):
                    print(f"Invalid RNBO value: {val}")
            else:
                print("No value from RNBO.")

            time.sleep(1)

    finally:
        # Turn off hardware on exit
        motor.off()
        for led in leds:
            led.off()
        print("Shutdown: motor and LEDs off.")

# ----- Entry Point -----
if __name__ == "__main__":
    main()