# rnbo-motor-project

This repository contains the code for the demo "Invitation to an Under-ground Party: Designing for extending human sensibilities into the soil of their plants" presented at the Aarhus 2025 conference by Margrete Lodahl Rolighed (Ph.d., School of Communication and Culture - Department of Digital Design and Information Studies, Aarhus University) and Lone Koefoed Hansen (Associate Professor, School of Communication and Culture - Department of Digital Design and Information Studies, Aarhus University) with technical support by Thomas Thomsen (Research assistant, Department of Computer Science, Aarhus University). See more about the Aarhus 2025 Conference here: https://aarhus2025.org/programme

Abstract for the demo:

"In this demo we present a design experiment that allows people to sense the activity level in the soil of their domestic plants. A contact microphone picks up sounds via vibrations in the soil and translates this into the speed and brightness of a spinning disco ball, insinuating that an under-ground party is happening, and inviting the human to take a listen. A plant’s underground existence is normally hidden from us, which results in a limiting plant-gaze that only seems to be interested in a plant when it is lush or blooming. This artefact explores posthuman design practices and seeks to introduce new sensory and aesthetic experiences of a plant’s hidden underground activities in people’s everyday encounters, creating new ways of understanding and appreciating a plant’s presence no matter the season."

The main part is Raspberry Pi hooked up to jrf mic for picking up sounds from the ground, letting the spectator listen to the sound, and have the sound control some LED's and a small motor to give visuel feedback on sound.

The repository contains the following:
- rnbo-motor-control.py: This script polls an RNBO patch via OSCQuery for a parameter value and uses it to control a DC motor and three LEDs on a Raspberry Pi. The output value (0–100) sets the PWM duty cycle for both motor speed and LED brightness.
- crontab.txt: Controls the starup of the Pi.
- Max patch: Include the RNBO code needed for exporting to the Pi and manipulating the sound from the jrf mic

The Pi needs to run a custom image created by Cycling74 for it to be able to run the RNBO code. Instructions on how to get this custom image and working with Raspberry Pi + RNBO can be found here: https://rnbo.cycling74.com/learn/raspberry-pi-setup

A license for Max MSP and RNBO is needed to push the RNBO code to the Pi. See more at https://cycling74.com/

# Raspberry Pi + RNBO Setup Guide

A step-by-step guide for setting up a Raspberry Pi to run an RNBO patch that
processes microphone input and drives GPIO outputs (motor + LEDs) via a Python
script, starting automatically on boot.

This guide reflects a setup running on a **Raspberry Pi 4** with a direct
ethernet connection to a Mac, using a **static IP**.

---

## 1. Flash the RNBO image

1. Open **Raspberry Pi Imager**.
2. Add Cycling74's custom image repo so the RNBO images appear in the list:
   `http://assets.cycling74.com/rnbo/pi-images/repo.json`
3. Choose **RNBO 1.4.4 (Trixie, 64-bit)**. On a Pi 4 the 64-bit Trixie image is
   the right choice — it matches the Pi 4's 64-bit CPU and is the more complete,
   future-proofed of the available variants. The same image works on Pi 3, Pi 4
   and Pi 5.
4. In the Imager's **Customizations**, set:
   - A **password** for the `pi` user (leave the username as `pi` — changing it
     breaks the RNBO runner).
   - **Enable SSH** (use password auth, or paste an SSH public key for key-based
     login).
   - WiFi is **optional** — skip it if you're using a wired connection (see next
     step). You can always configure WiFi later on the Pi with `sudo nmtui`.
5. Flash the card and boot the Pi.

> **Version matching matters:** the RNBO runner version on the Pi must line up
> with a version that actually exists in the repo, and with your Max/RNBO. A
> mismatch (e.g. Max on 1.4.3 while the repo only has 1.4.4) causes an
> "Upgrade Error … version not found" in Max. Fix it by updating RNBO in Max's
> Package Manager so Max matches the runner already on the Pi.

---

## 2. Connect over the network

The Pi and the computer running Max must be on the **same network** for RNBO to
reach the Pi.

- **Ethernet** (direct Mac ↔ Pi with a CAT cable) is the most stable choice for
  a permanent installation. WiFi is fine if the Pi needs to be moved around.
- You need at least one way in from the start: either WiFi configured in the
  Imager, a wired connection, or a directly attached screen + keyboard.

### Set a static IP (important for direct ethernet)

On a direct Mac ↔ Pi connection there is **no DHCP server**, so leaving the
interface on "Automatic" makes the Pi fall back to an unstable link-local
address that can **drop out after a few minutes of idle** — the connection dies
and only comes back after a physical poke. A static IP fixes this permanently.

Run on the Pi (note the `sudo` — `nmtui` needs root or it reports
"insufficient privileges"):

```bash
sudo nmtui
```

- Edit **Wired connection 1** (`eth0`).
- Set **IPv4 CONFIGURATION** from `Automatic` to **Manual**.
- Under **Addresses**, add: `192.168.1.80/24`
- Leave **Gateway** and **DNS** blank (no router on a direct link).
- Make sure **Automatically connect** is checked. Save with **OK**.

Or do it directly from the command line:

```bash
sudo nmcli connection modify "Wired connection 1" ipv4.method manual ipv4.addresses 192.168.1.80/24
sudo nmcli connection down "Wired connection 1" && sudo nmcli connection up "Wired connection 1"
```

On the **Mac side**, make sure the ethernet interface is on the same subnet
(e.g. a manual address like `192.168.1.10`, mask `255.255.255.0`), so both
machines sit on the same network.

> If `apt`/runner updates need internet later, the static-IP-without-gateway
> setup has no route out. Temporarily put the Pi on a router/WiFi with internet
> for those, then switch back.

### Finding the Pi's IP

```bash
hostname -I
```

---

## 3. Export the RNBO patch to the Pi

- The Pi compiles the patch to native code via the runner, so just export your
  patch to it from Max's export sidebar.
- If the Pi doesn't appear automatically in the sidebar, zeroconf/mDNS discovery
  often doesn't work over a direct ethernet link. Use **+ add** and enter the
  Pi's IP manually. The runner listens on port **5678**.
- Sanity check the runner is up by visiting `http://<PI-IP>:5678/rnbo/inst/0`
  in a browser — a JSON page means it's running.

---

## 4. Get the Python script onto the Pi

With VS Code Remote-SSH connected to the Pi, either create the file and paste
your code in, or copy it across.

Create an empty file (run it while in your home folder):

```bash
touch rnbo-motor-control.py
```

Open it in VS Code, paste the script, save. If pasting Python, watch for mixed
indentation — VS Code's "Convert Indentation to Spaces" fixes a `TabError` /
`IndentationError` if it happens.

Verify the contents landed:

```bash
cat rnbo-motor-control.py
```

### What the script does

- Listens to the RNBO runner's OSCQuery interface on port **5678**.
- Searches for the output path `/rnbo/inst/0/messages/out/output1`, blinking the
  LEDs while it waits.
- Polls that value every 5 seconds and maps it (0–100) to a PWM duty cycle on
  the motor (GPIO 5) and LEDs (GPIO 26, 19, 13) via `gpiozero`.

---

## 5. Test the script manually

Run it with the **exact path** it lives at:

```bash
/usr/bin/python3 /home/pi/rnbo-motor-control.py
```

Expected output:

```
Searching for RNBO output path...
Found RNBO output path: /rnbo/inst/0/messages/out/output1
Polling RNBO value at '/rnbo/inst/0/messages/out/output1' from http://127.0.0.1:5678...
Motor & LEDs set to 96.7%
Motor & LEDs set to 37.7%
```

- `Invalid RNBO value: []` means the patch isn't sending anything on `output1`
  yet (e.g. no audio input) — not a script error.
- Stop with **Ctrl+C**.

---

## 6. Set up autostart with cron

The autostart is driven by a `crontab.txt` file that you load into cron.

### The crontab line

```
@reboot sleep 30 && /usr/bin/python3 /home/pi/rnbo-motor-control.py >> /home/pi/autorun-log.txt 2>&1
```

- `@reboot` runs it at every boot.
- `sleep 30` gives the RNBO runner time to come up first, so the script doesn't
  fail trying to connect too early.
- **Full paths** are required — cron runs in a minimal environment without your
  normal `PATH`, so `python3` and the script path must both be absolute, and the
  paths must match where the file actually is.
- `>> /home/pi/autorun-log.txt 2>&1` writes all output and errors to a log.

### Load it into cron

Editing `crontab.txt` on disk does **nothing on its own** — cron runs a separate
internal copy. You must reload the file for changes to take effect:

```bash
crontab ~/crontab.txt
```

If you get `new crontab file is missing newline before EOF`, add a trailing
newline first:

```bash
echo "" >> ~/crontab.txt
crontab ~/crontab.txt
```

Confirm what's actually active:

```bash
crontab -l
```

> **This was the single biggest source of confusion:** the file and the active
> crontab can disagree. `crontab -l` shows what cron will actually run — always
> trust that over the file. After any edit to `crontab.txt`, reload with
> `crontab ~/crontab.txt`.

---

## 7. Verify autostart works

Reboot:

```bash
sudo reboot
```

Wait, reconnect, then confirm the script is running. The most direct check —
independent of the log:

```bash
pgrep -af rnbo-motor-control
```

A line showing `/usr/bin/python3 /home/pi/rnbo-motor-control.py` means the
script started from boot and is running.

Confirm cron actually launched the job this boot (check the timestamp is recent
and the path is correct):

```bash
journalctl -u cron -b --no-pager | tail -5
```

### About the log file

If `autorun-log.txt` exists but looks empty, that's **Python output buffering**,
not a failure — `print()` lines sit in memory instead of being written
immediately. The script is still running (confirm with `pgrep` above). To make
the log update live, add `-u` (unbuffered) to the python call in `crontab.txt`
and reload:

```
@reboot sleep 30 && /usr/bin/python3 -u /home/pi/rnbo-motor-control.py >> /home/pi/autorun-log.txt 2>&1
```

```bash
crontab ~/crontab.txt
```

---

## Quick troubleshooting reference

| Symptom | Likely cause | Fix |
|---|---|---|
| Connection dies after a few minutes idle, ping fails too | DHCP fallback / link-local on direct ethernet | Set a static IP (step 2) |
| `nmtui` says "insufficient privileges" | Not run as root | `sudo nmtui` |
| Max: "Upgrade Error … version not found" | Max/runner version mismatch | Update RNBO in Max's Package Manager to match the Pi |
| Pi not in Max export sidebar | mDNS doesn't work over direct ethernet | Use **+ add** with the Pi's IP, port 5678 |
| `can't open file … No such file` | crontab path doesn't match where the file is | Fix the path so it matches, or move the file |
| Edited `crontab.txt` but nothing changed | Active crontab not reloaded | `crontab ~/crontab.txt`, verify with `crontab -l` |
| Log file empty but script runs | Python output buffering | Add `-u` to the python call |
| `missing newline before EOF` | No trailing newline in crontab file | `echo "" >> ~/crontab.txt` |

---

## Key facts for this specific setup

- **Pi hostname:** `plantdisco` (`pi@plantdisco.local`)
- **Static IP:** `192.168.1.80`
- **Script location:** `/home/pi/rnbo-motor-control.py`
- **Log:** `/home/pi/autorun-log.txt`
- **GPIO:** motor on pin 5, LEDs on pins 26 / 19 / 13
- **RNBO output path:** `/rnbo/inst/0/messages/out/output1`
- **OSCQuery port:** 5678
