import time
import requests
import socket
from gpiozero import PWMOutputDevice

# RNBO OSCQuery Config
HOSTNAME = "tt16.local"      # Hostname of your RNBO device (using mDNS)
PORT = 5678                  # Port RNBO service listens on
TARGET_PATH = "/rnbo/inst/0/messages/out/output1"  # Path to the parameter we want

try:
    # Resolve hostname to IP address
    ip = socket.gethostbyname(HOSTNAME)
    OSCQUERY_URL = f"http://{ip}:{PORT}"  # Full URL to access RNBO device
except socket.gaierror:
    # If hostname cannot be resolved, print error and exit
    print("Could not resolve hostname '{}'. Check your network or mDNS setup.".format(HOSTNAME))
    exit(1)

# Motor GPIO Config
MOTOR_PIN = 5  # GPIO pin connected to the motor controller (adjust if needed)

# OSCQuery Functions
def fetch_full_tree():
    """
    Fetch the full parameter tree JSON from the RNBO device via HTTP.
    Returns the JSON dictionary if successful, None otherwise.
    """
    try:
        response = requests.get(OSCQUERY_URL, timeout=2)  # 2 second timeout
        if response.status_code == 200:
            return response.json()  # Parse and return JSON data
        else:
            print("Failed to get root JSON, status code: {}".format(response.status_code))
            return None
    except Exception as e:
        print("Exception during root fetch: {}".format(e))
        return None

def search_tree_for_value(tree, target_path):
    """
    Recursively search the parameter tree dictionary for the node matching target_path.
    Return its 'value' or 'VALUE' if found; otherwise None.
    Handles cases where value might be a list by returning the first item.
    """
    if not isinstance(tree, dict):
        return None
    if tree.get("FULL_PATH") == target_path:
        val = tree.get("value") or tree.get("VALUE")
        if isinstance(val, list) and len(val) > 0:
            return val[0]  # Use first value if a list
        return val
    children = tree.get("CONTENTS") or {}
    for child_node in children.values():
        result = search_tree_for_value(child_node, target_path)
        if result is not None:
            return result
    return None

def get_parameter_value():
    """
    Get the current value of the target parameter from the RNBO device.
    Returns the parameter value if found, None otherwise.
    """
    tree = fetch_full_tree()
    if tree:
        return search_tree_for_value(tree, TARGET_PATH)
    return None

# Main Loop
def main():
    motor = PWMOutputDevice(MOTOR_PIN)  # Set up PWM control on the motor pin
    print("Polling RNBO value at '{}' from {} to control motor speed...".format(TARGET_PATH, OSCQUERY_URL))

    try:
        while True:
            # UNCOMMENT the next line to test with a fake motor value (for example, 75%)
            val = 75

            # COMMENT OUT the next line if you are using a test value instead
            # val = get_parameter_value()

            if val is not None:
                try:
                    duty_cycle = float(val)              # Convert value to float
                    duty_cycle = max(0, min(100, duty_cycle))  # Clamp between 0 and 100%
                    motor.value = duty_cycle / 100.0    # Convert percentage to 0.0-1.0 for PWM
                    print("Motor speed set to {:.1f}%".format(duty_cycle))
                except (ValueError, TypeError):
                    print("Invalid value received: {}".format(val))
            else:
                print("Failed to get value.")
            time.sleep(1)  # Wait 1 second before next check
    finally:
        motor.value = 0  # Stop the motor when exiting
        print("Motor stopped. Exiting.")

if __name__ == "__main__":
    main()