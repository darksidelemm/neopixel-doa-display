# Neopixel-based Radio Direction-of-Arrival Display

In development!

### Hardware
* Raspberry Pi Zero W
* 24-LED NeoPixel (WS2812) Ring
* 8-LED NeoPixel Strip

Wiring to RPi Header: https://cdn-learn.adafruit.com/assets/assets/000/063/866/original/leds_raspi_NeoPixel_bb.jpg?1539968224

Options:
* Light-Pipes: https://au.element14.com/bivar/plp2-125/light-pipe-single-round-panel/dp/1780675

### Dependencies

* CircuitPython - Follow this guide: https://learn.adafruit.com/circuitpython-on-raspberrypi-linux/installing-circuitpython-on-raspberry-pi

```
$ sudo apt-get update
$ sudo apt-get upgrade
$ sudo apt-get install python3-pip python3-numpy python3-dateutil
$ sudo pip3 install --upgrade setuptools
$ sudo pip3 install --upgrade adafruit-python-shell
$ sudo pip3 install adafruit-circuitpython-neopixel
```