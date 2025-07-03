#!/usr/bin/env python3

import time
import requests
import socket
from gpiozero import PWMLED, PWMOutputDevice

# ----- Configuration -----

# Delay on startup to ensure RNBO has initialized (in seconds)
STARTUP_DELAY = 5

# GPIO pin for the motor (must support PWM)
MOTOR_PIN = 5

# GPIO pins for the LEDs (must support PWM)
LED_PINS = [18, 19, 20]

# RNBO OSCQuery server settings
HOSTNAME = socket.gethostname() + ".local"
PORT = 5678
TARGET_PATH_SUFFIX = "/messages/out/output1"

# ----- Resolve Pi's mDNS hostname to IP -----

try:
    ip = socket.gethostbyname(HOSTNAME)
    OSCQUERY_URL = f"http://{ip}:{PORT}"
except socket.gaierror:
    print(f"Could not resolve hostname '{HOSTNAME}'. Check network or mDNS setup.")
    exit(1)

# ----- OSCQuery Utilities -----

def fetch_full_tree():
    """Get the full parameter tree from the RNBO OSCQuery device."""
    try:
        response = requests.get(OSCQUERY_URL, timeout=2)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Failed to fetch tree. Status code: {response.status_code}")
    except Exception as e:
        print(f"Exception fetching tree: {e}")
    return None

def search_tree_for_value(tree, target_path):
    """Search the tree recursively for a node with the exact FULL_PATH."""
    if not isinstance(tree, dict):
        return None

    if tree.get("FULL_PATH") == target_path:
        val = tree.get("value") or tree.get("VALUE")
        if isinstance(val, list) and len(val) > 0:
            return val[0]
        return val

    for child in (tree.get("CONTENTS") or {}).values():
        result = search_tree_for_value(child, target_path)
        if result is not None:
            return result

    return None

def find_output_path(tree, suffix):
    """Search tree for any FULL_PATH that ends with the given suffix."""
    if not isinstance(tree, dict):
        return None

    full_path = tree.get("FULL_PATH")
    if full_path and full_path.endswith(suffix):
        return full_path

    for child in (tree.get("CONTENTS") or {}).values():
        result = find_output_path(child, suffix)
        if result:
            return result

    return None

def get_dynamic_output_path():
    """Get the full RNBO path for output1 dynamically (e.g., inst/0 or inst/1)."""
    tree = fetch_full_tree()
    if not tree:
        print("Unable to fetch tree to find dynamic path.")
        return None
    return find_output_path(tree, TARGET_PATH_SUFFIX)

def get_parameter_value_from_path(path):
    """Fetch the current value of a parameter at the given path."""
    tree = fetch_full_tree()
    if tree:
        return search_tree_for_value(tree, path)
    return None

# ----- Main Logic -----

def main():
    print(f"Waiting {STARTUP_DELAY}s to allow RNBO to fully start...")
    time.sleep(STARTUP_DELAY)

    # Dynamically find correct RNBO output path
    output_path = get_dynamic_output_path()
    if not output_path:
        print("Could not find RNBO output path.")
        return

    print(f"Using dynamic RNBO path: {output_path}")

    # Initialize GPIO devices
    motor = PWMOutputDevice(MOTOR_PIN)
    leds = [PWMLED(pin) for pin in LED_PINS]

    print(f"Polling value from {OSCQUERY_URL}{output_path}...")

    try:
        while True:
            # Get current value from RNBO patch
            val = get_parameter_value_from_path(output_path)

            if val is not None:
                try:
                    duty_cycle = float(val)
                    duty_cycle = max(0, min(100, duty_cycle))
                    pwm_value = duty_cycle / 100.0

                    # Set motor and LED brightness
                    motor.value = pwm_value
                    for led in leds:
                        led.value = pwm_value

                    print(f"Motor & LEDs set to {duty_cycle:.1f}%")
                except (ValueError, TypeError):
                    print(f"Invalid value: {val}")
            else:
                print("Failed to get RNBO value.")

            time.sleep(1)

    finally:
        # Stop everything on exit
        print("Shutting down...")
        motor.off()
        for led in leds:
            led.off()

# ----- Start Script -----

if __name__ == "__main__":
    main()