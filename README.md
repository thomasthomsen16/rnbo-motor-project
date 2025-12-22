# rnbo-motor-project

This repository contains the code for the demo "Invitation to an Under-ground Party: Designing for extending human sensibilities into the soil of their plants" presented at the Aarhus 2025 conference by Margrete Lodahl Rolighed (Ph.d., School of Communication and Culture - Department of Digital Design and Information Studies, Aarhus University) and Lone Koefoed Hansen (Associate Professor, School of Communication and Culture - Department of Digital Design and Information Studies, Aarhus University) with technical support by Thomas Thomsen (Research assistant, Department of Computer Science, Aarhus University). See more about the Aarhus 2025 Conference here: https://aarhus2025.org/programme

Abstract for the demo:

"In this demo we present a design experiment that allows people to sense the activity level in the soil of their domestic plants. A contact microphone picks up sounds via vibrations in the soil and translates this into the speed and brightness of a spinning disco ball, insinuating that an under-ground party is happening, and inviting the human to take a listen. A plant’s underground existence is normally hidden from us, which results in a limiting plant-gaze that only seems to be interested in a plant when it is lush or blooming. This artefact explores posthuman design practices and seeks to introduce new sensory and aesthetic experiences of a plant’s hidden underground activities in people’s everyday encounters, creating new ways of understanding and appreciating a plant’s presence no matter the season."

The main part is Raspberry Pi hooked up to jrf mic for picking up sounds from the ground, letting the spectator listen to the sound, and have the sound control some LED's and a small motor to give visuel feedback on sound.

The repository contains the following:
- rnbo-motor-control.py: This script polls an RNBO patch via OSCQuery for a parameter value and uses it to control a DC motor and three LEDs on a Raspberry Pi. The output value (0–100) sets the PWM duty cycle for both motor speed and LED brightness.
- Crontab: Controls the starup of the Pi.
- Max patch: Include the RNBO code needed for exporting to the Pi and manipulating the sound from the jrf mic

The Pi needs to run a custom image created by Cycling74 for it to be able to run the RNBO code. Instructions on how to get this custom image and working with Raspberry Pi + RNBO can be found here: https://rnbo.cycling74.com/learn/raspberry-pi-setup
