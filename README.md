# Neopixel-based Radio Direction-of-Arrival Display

A display for Kraken-SDR Direction-of-Arrival data. Accepts DoA data via UDP broadcast messages. See it in action here: https://www.youtube.com/watch?v=ZPM3dys5GAA

**Updated 2022-07-12 to work with the output from krakensdr_doa, in particular the different ranges of confidence and reported power levels.**

Apologies for the poor / limited documentation - this was very much a weekend project! 

**Warning: Having a device with red and blue lights on your dashboard may get you into trouble in many places! Ensure the HUD display is not visible from outside the vehicle (e.g. with a shield around the LED face), or adjust the color-mapping to use colors which are allowed.**

If you're after more information, contact me at: Mark Jessop - vk5qi (at) rfhead.net

## Features

### DoA Mode
Accepts bearing messages from a kraken_doa instance (running my fork: https://github.com/darksidelemm/krakensdr_doa ) and displays the DoA solution on the ring display. Solution data is color coded based on the solution confidence 'score', moving from Red (low confidence) -> Purple -> Blue (high confidence). DoA data is expected on UDP port 55672, in the format described here: https://github.com/projecthorus/chasemapper#radio-direction-finding-support

The LED strip is used to display SNR data, with the 8 LEDs illuminating depending on the SNR value. Again, color coding is used, with 0-30 dB represented by red LEDs, then 30-60 dB by a purple overlay. Run doa_ring.py with the `--testpower` argument to see how this operates.

### Compass mode
Accepts car position data (which must include a `heading` field) and displays a compass on the ring, with a blue indicator pointing to north. Speed is displayed on the LED strip, with the kph calues displayed in the same way as SNR values. Start with `--compass` mode.

Currently I'm using this with car position data from a uBlox NEO-M8U, using this software to interface: https://github.com/darksidelemm/chasemapper-gps-m8u

### HUD Mode
Can be used in combination with DoA and Compass mode, and flips the display upside-down, so it can be used as viewed via a car windshield. This option an be enabled with `--hudmode`.

### GPIO Control
The different modes can also be selected using GPIO pins, enabling mode changes while operating. This is enabled using `--gpio`.  Refer below for the GPIOs used.

## Hardware / Software Requirements

### Hardware
* Raspberry Pi Zero W 
  * Setup for headless use, connecting automatically to the same WiFi network as Kerberos-SDR
* 24-LED NeoPixel (WS2812) Ring  (Used to display DoA data)
* 8-LED NeoPixel Strip (Used to display SNR data)

* Wiring to RPi Header: https://cdn-learn.adafruit.com/assets/assets/000/063/866/original/leds_raspi_NeoPixel_bb.jpg?1539968224
* RPi Zero (GPIO18) -> Ring -> Strip

* Optional switches, all connecting between a GPIO and GND.
  * Brightness Control: SPDT momentary toggle switch 
    * Brightness Up: GPIO21
    * Brightness Down: GPIO20
  * HUD-Mode On/Off: GPIO26    (Open for HUD mode, Short to ground to disable HUD mode)
  * Compass/DoA Switch: GPIO19 (Open for Compass mode, short to ground for DoA mode)

Optional extras:
* Light-Pipes: https://au.element14.com/bivar/plp2-125/light-pipe-single-round-panel/dp/1780675

### Software Dependencies

* CircuitPython - Follow this guide: https://learn.adafruit.com/circuitpython-on-raspberrypi-linux/installing-circuitpython-on-raspberry-pi

```
$ sudo apt-get update
$ sudo apt-get upgrade
$ sudo apt-get install python3-pip python3-numpy python3-dateutil
$ sudo pip3 install --upgrade setuptools
$ sudo pip3 install --upgrade adafruit-python-shell
$ sudo pip3 install adafruit-circuitpython-neopixel
```

## Starting Up
Add the following to your `/etc/rc.local`
```
python3 doa_ring.py --gpio --hud
```
