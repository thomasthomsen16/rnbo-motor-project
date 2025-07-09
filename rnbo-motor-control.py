#!/usr/bin/env python3

import time
import requests
import socket
from gpiozero import PWMLED, PWMOutputDevice

# ----- GPIO Pin Setup -----
MOTOR_PIN = 5
LED_PINS = [26, 19, 13]  # Updated LED pins

# ----- RNBO Parameter Path -----
TARGET_PATH = None

# ----- OSCQuery Functions -----

def fetch_full_tree(oscquery_url):
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

def get_dynamic_output_path(leds):
    """
    Keep trying indefinitely to detect output path.
    Blink LEDs continuously while waiting.
    """
    print("Searching for RNBO output path...")
    blink_state = False

    while True:
        # Resolve hostname and build URL here inside loop, so network can be ready
        hostname = socket.gethostname() + ".local"
        try:
            ip = socket.gethostbyname(hostname)
            oscquery_url = f"http://{ip}:5678"
        except socket.gaierror:
            print(f"Could not resolve hostname '{hostname}'. Retrying...")
            oscquery_url = None

        if oscquery_url:
            tree = fetch_full_tree(oscquery_url)
            if tree:
                for i in range(2):
                    path = f"/rnbo/inst/{i}/messages/out/output1"
                    if search_tree_for_value(tree, path) is not None:
                        for led in leds:
                            led.off()
                        print(f"Found RNBO output path: {path}")
                        return path, oscquery_url

        # Blink LEDs while waiting
        blink_state = not blink_state
        for led in leds:
            led.value = 0.3 if blink_state else 0
        time.sleep(0.5)

def get_parameter_value(oscquery_url, target_path):
    tree = fetch_full_tree(oscquery_url)
    if tree:
        return search_tree_for_value(tree, target_path)
    return None

# ----- Main Application Logic -----

def main():
    leds = [PWMLED(pin) for pin in LED_PINS]

    output_path, oscquery_url = get_dynamic_output_path(leds)

    motor = PWMOutputDevice(MOTOR_PIN)

    print(f"Polling RNBO value at '{output_path}' from {oscquery_url}...")

    try:
        while True:
            val = get_parameter_value(oscquery_url, output_path)
            if val is not None:
                try:
                    duty_cycle = max(0, min(100, float(val)))
                    pwm_value = duty_cycle / 100.0

                    motor.value = pwm_value
                    for led in leds:
                        led.value = pwm_value

                    print(f"Motor & LEDs set to {duty_cycle:.1f}%")
                except (ValueError, TypeError):
                    print(f"Invalid RNBO value: {val}")
            else:
                print("No value from RNBO.")

            time.sleep(5)

    finally:
        motor.off()
        for led in leds:
            led.off()
        print("Shutdown: motor and LEDs off.")

if __name__ == "__main__":
    main()