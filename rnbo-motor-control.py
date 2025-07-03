import time
import requests
import socket
from gpiozero import PWMLED, PWMOutputDevice

# ----- RNBO OSCQuery Configuration -----

# The hostname of the Pi (resolved using mDNS). This lets us avoid hardcoding the IP address.
HOSTNAME = socket.gethostname() + ".local"

# Port used by the RNBO OSCQuery server (usually 5678)
PORT = 5678

# The exact path in the RNBO patch from which we want to read the output value
TARGET_PATH = "/rnbo/inst/1/messages/out/output1"

# Try to resolve the hostname to an IP address
try:
    ip = socket.gethostbyname(HOSTNAME)
    OSCQUERY_URL = f"http://{ip}:{PORT}"
except socket.gaierror:
    print("Could not resolve hostname '{}'. Check your network or mDNS setup.".format(HOSTNAME))
    exit(1)

# ----- GPIO Pin Setup -----

# Pin connected to motor control (PWM capable)
MOTOR_PIN = 5

# Pins connected to the LEDs (must also support PWM)
LED_PINS = [18, 19, 20]

# ----- Functions for OSCQuery -----

def fetch_full_tree():
    """
    Contact the RNBO device and request the full parameter tree as JSON.
    This tree includes all the controllable/observable parameters in the patch.
    """
    try:
        response = requests.get(OSCQUERY_URL, timeout=2)
        if response.status_code == 200:
            return response.json()
        else:
            print("Failed to get root JSON, status code: {}".format(response.status_code))
            return None
    except Exception as e:
        print("Exception during root fetch: {}".format(e))
        return None

def search_tree_for_value(tree, target_path):
    """
    Recursively search the parameter tree to find the node at the given target_path.
    If found, return the value. Handles both flat values and lists.
    """
    if not isinstance(tree, dict):
        return None

    if tree.get("FULL_PATH") == target_path:
        val = tree.get("value") or tree.get("VALUE")
        if isinstance(val, list) and len(val) > 0:
            return val[0]  # Return first value if it's a list
        return val

    # Check child nodes recursively
    children = tree.get("CONTENTS") or {}
    for child_node in children.values():
        result = search_tree_for_value(child_node, target_path)
        if result is not None:
            return result

    return None  # Not found

def get_parameter_value():
    """
    Top-level function to get the current value of the parameter we're interested in.
    It fetches the full tree, then searches it for our target path.
    """
    tree = fetch_full_tree()
    if tree:
        return search_tree_for_value(tree, TARGET_PATH)
    return None

# ----- Main Application Logic -----

def main():
    # Set up the motor as a PWM output device
    motor = PWMOutputDevice(MOTOR_PIN)

    # Set up multiple PWM-enabled LEDs
    leds = [PWMLED(pin) for pin in LED_PINS]

    print("Polling RNBO value at '{}' from {} to control motor and LEDs...".format(TARGET_PATH, OSCQUERY_URL))

    try:
        while True:
            # If testing without RNBO, use this:
            # val = 75

            # Otherwise, get live value from RNBO
            val = get_parameter_value()

            if val is not None:
                try:
                    # Convert to float and clamp between 0 and 100
                    duty_cycle = float(val)
                    duty_cycle = max(0, min(100, duty_cycle))

                    # Scale to 0.0–1.0 for PWM
                    pwm_value = duty_cycle / 100.0

                    # Set motor speed and LED brightness
                    motor.value = pwm_value
                    for led in leds:
                        led.value = pwm_value

                    print("Motor & LEDs set to {:.1f}%".format(duty_cycle))
                except (ValueError, TypeError):
                    print("Invalid value received: {}".format(val))
            else:
                print("Failed to get value.")

            time.sleep(1)  # Wait before polling again
    finally:
        # On exit: turn everything off
        motor.off()
        for led in leds:
            led.off()
        print("Motor and LEDs off. Exiting.")

# Start the program
if __name__ == "__main__":
    main()