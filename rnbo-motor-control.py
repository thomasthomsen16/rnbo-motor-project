#!/usr/bin/env python3

import time
import requests
import socket
import logging
from gpiozero import PWMLED, PWMOutputDevice

# ----- Logging Configuration -----
logging.basicConfig(
    filename="/home/pi/rnbo-motor-project/autorun-log.txt",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# ----- RNBO OSCQuery Configuration -----
PORT = 5678
TARGET_PATH_BASE = "/rnbo/inst/{}/messages/out/output1"
HOSTNAME = socket.gethostname() + ".local"

# ----- GPIO Pin Setup -----
MOTOR_PIN = 5
LED_PINS = [26, 19, 13]

# ----- Helper Functions -----

def resolve_hostname():
    """Resolve Pi's hostname to IP address for OSCQuery."""
    try:
        ip = socket.gethostbyname(HOSTNAME)
        return f"http://{ip}:{PORT}"
    except socket.gaierror:
        logging.error(f"Could not resolve hostname '{HOSTNAME}'. Check your network or mDNS.")
        return None

def fetch_full_tree(url):
    """Fetch the full parameter tree from the RNBO OSCQuery server."""
    try:
        response = requests.get(url, timeout=2)
        if response.status_code == 200:
            return response.json()
        else:
            logging.warning(f"Failed to fetch JSON, status code: {response.status_code}")
    except Exception as e:
        logging.warning(f"Exception during tree fetch: {e}")
    return None

def search_tree_for_value(tree, target_path):
    """Recursively search the tree for a given path and return its value."""
    if not isinstance(tree, dict):
        return None

    if tree.get("FULL_PATH") == target_path:
        val = tree.get("value") or tree.get("VALUE")
        return val[0] if isinstance(val, list) and len(val) > 0 else val

    children = tree.get("CONTENTS") or {}
    for child in children.values():
        result = search_tree_for_value(child, target_path)
        if result is not None:
            return result
    return None

def get_parameter_value(url, path):
    """Top-level method to retrieve RNBO parameter value."""
    tree = fetch_full_tree(url)
    return search_tree_for_value(tree, path) if tree else None

def get_dynamic_output_path(url, timeout=15):
    """Wait for the RNBO device to be ready and return the correct output path."""
    start = time.time()
    blink = True

    leds = [PWMLED(pin) for pin in LED_PINS]

    try:
        while time.time() - start < timeout:
            for led in leds:
                led.value = 1.0 if blink else 0.0
            blink = not blink
            time.sleep(0.5)

            tree = fetch_full_tree(url)
            if not tree:
                continue

            for i in range(2):  # Try /inst/0 and /inst/1
                path = TARGET_PATH_BASE.format(i)
                val = search_tree_for_value(tree, path)
                if val is not None:
                    for led in leds:
                        led.off()
                    logging.info(f"Found RNBO output at path: {path}")
                    return path

    finally:
        for led in leds:
            led.off()

    logging.error("Timeout waiting for RNBO to start.")
    return None

# ----- Main Application Logic -----

def main():
    motor = PWMOutputDevice(MOTOR_PIN)
    leds = [PWMLED(pin) for pin in LED_PINS]

    oscquery_url = resolve_hostname()
    if not oscquery_url:
        return

    output_path = get_dynamic_output_path(oscquery_url)
    if not output_path:
        logging.error("Could not determine output path. Exiting.")
        return

    logging.info(f"Polling RNBO value at '{output_path}' from {oscquery_url}")

    try:
        while True:
            val = get_parameter_value(oscquery_url, output_path)

            if val is not None:
                try:
                    duty = max(0, min(100, float(val)))  # Clamp 0–100
                    pwm = duty / 100.0
                    motor.value = pwm
                    for led in leds:
                        led.value = pwm
                    logging.info(f"Set motor & LEDs to {duty:.1f}%")
                except (ValueError, TypeError):
                    logging.warning(f"Invalid value received: {val}")
            else:
                logging.warning("Failed to get RNBO value.")

            time.sleep(1)

    except KeyboardInterrupt:
        logging.info("Interrupted by user. Shutting down...")

    finally:
        motor.off()
        for led in leds:
            led.off()
        logging.info("Motor and LEDs turned off. Exiting.")

# ----- Entry Point -----

if __name__ == "__main__":
    main()