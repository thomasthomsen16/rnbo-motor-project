import time
import requests
import socket
from gpiozero import PWMOutputDevice

# RNBO OSCQuery Config
HOSTNAME = "tt16.local"
PORT = 5678
TARGET_PATH = "/rnbo/inst/0/messages/out/output1"

try:
    ip = socket.gethostbyname(HOSTNAME)
    OSCQUERY_URL = f"http://{ip}:{PORT}"
except socket.gaierror:
    print("Could not resolve hostname '{}'. Check your network or mDNS setup.".format(HOSTNAME))
    exit(1)

# Motor GPIO Config
MOTOR_PIN = 5  # Adjust this to match your GPIO setup

# OSCQuery Functions
def fetch_full_tree():
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
    if not isinstance(tree, dict):
        return None
    if tree.get("FULL_PATH") == target_path:
        val = tree.get("value") or tree.get("VALUE")
        if isinstance(val, list) and len(val) > 0:
            return val[0]  # Use first value if list
        return val
    children = tree.get("CONTENTS") or {}
    for child_node in children.values():
        result = search_tree_for_value(child_node, target_path)
        if result is not None:
            return result
    return None

def get_parameter_value():
    tree = fetch_full_tree()
    if tree:
        return search_tree_for_value(tree, TARGET_PATH)
    return None

# Main Loop
def main():
    motor = PWMOutputDevice(MOTOR_PIN)
    print("Polling RNBO value at '{}' from {} to control motor speed...".format(TARGET_PATH, OSCQUERY_URL))

    try:
        while True:
            # UNCOMMENT the next line to test with fake motor value (for example, 75%)
            val = 75

            # COMMENT OUT the next line if you are using a test value instead
            # val = get_parameter_value()

            if val is not None:
                try:
                    duty_cycle = float(val)
                    duty_cycle = max(0, min(100, duty_cycle))  # Clamp to 0 - 100
                    motor.value = duty_cycle / 100.0  # Convert to 0.0 - 1.0
                    print("Motor speed set to {:.1f}%".format(duty_cycle))
                except (ValueError, TypeError):
                    print("Invalid value received: {}".format(val))
            else:
                print("Failed to get value.")
            time.sleep(1)
    finally:
        motor.value = 0
        print("Motor stopped. Exiting.")

if __name__ == "__main__":
    main()

