#!/usr/bin/env python3
#
#   DoA Ring Display
#
#   Uses lots of example code from AdaFruit :-)
#

import argparse
import time
import board
import neopixel
import numpy as np
from udp_listener import UDPListener

#
# Configuration Section
#

# GPIO to which the NeoPixels are Connected
PIXEL_PIN = board.D18

# The number of NeoPixels in the main ring
# This assumes the ring is configured with the pixels numbered in a clockwise direction,
# with Pixel #0 at the top of the circle.
RING_NUM_PIXELS = 24

# The number of NeoPixels in the linear power scale.
# It is assumed that these are wired in *after* the ring.
SCALE_NUM_PIXELS = 8

# The order of the pixel colors - RGB or GRB. Some NeoPixels have red and green reversed!
# For RGBW NeoPixels, simply change the ORDER to RGBW or GRBW.
PIXEL_ORDER = neopixel.RGB

# HUD Mode - where the display is placed on the dashboard of a car and viewed via reflections from a windscreen.
HUD_MODE = False

# Initial Brightness of the display.
BRIGHTNESS = 0.1

# Compass rose settings.
ROSE_BRIGHTNESS = 0.04 # Relative brightness.
ROSE_POINTS = 4 # Number of points

# Maximum and Minimum brightness settings.
MAX_BRIGHTNESS = 0.2
MIN_BRIGHTNESS = 0.01

# Color Settings for the Ring Display
CONFIDENCE_MAX = 70
CONFIDENCE_MIN = 20
CONFIDENCE_MAX_COL = 160
CONFIDENCE_MIN_COL = 255
CLIP_VALUE = 0.7 # Fudge factor to make narrow beams show up well on the display.

# Scale settings for the Power Scale
POWER_MIN = 5
POWER_MAX = 30
POWER_COL = 1

# 
BEARING_COL = 80

# Total number of pixels.
TOTAL_NUM_PIXELS = RING_NUM_PIXELS + SCALE_NUM_PIXELS

# Setup NeoPixels
pixels = neopixel.NeoPixel(
    PIXEL_PIN, TOTAL_NUM_PIXELS, brightness=BRIGHTNESS, auto_write=False, pixel_order=PIXEL_ORDER
)


def wheel(pos):
    """ Convert a 0-255 value into a color."""
    # Input a value 0 to 255 to get a color value.
    # The colours are a transition r - g - b - back to r.
    if pos < 0 or pos > 255:
        r = g = b = 0
    elif pos < 85:
        r = int(pos * 3)
        g = int(255 - pos * 3)
        b = 0
    elif pos < 170:
        pos -= 85
        r = int(255 - pos * 3)
        g = 0
        b = int(pos * 3)
    else:
        pos -= 170
        r = 0
        g = int(pos * 3)
        b = int(255 - pos * 3)
    return (r, g, b) if PIXEL_ORDER in (neopixel.RGB, neopixel.GRB) else (r, g, b, 0)


def rainbow_cycle(wait_time=0.001, num_pixels=24, pixel_start=0):
    """ Do a little 'attract' display. Will take 255*wait to run. """
    for j in range(255):
        for i in range(pixel_start, pixel_start+num_pixels):
            pixel_index = (i * 256 // num_pixels) + j
            pixels[i] = wheel(pixel_index & 255)
        pixels.show()
        time.sleep(wait_time)



def blank_pixels():
    for i in range(0, TOTAL_NUM_PIXELS):
        pixels[i] = (0,0,0)
    pixels.show()


def fade_to_black(steps=500, wait_time=0.001):
    """ Fade all the pixels to black """
    if BRIGHTNESS == 0:
        return
    
    _steps = np.linspace(BRIGHTNESS, 0, steps)

    for _step in _steps:
        pixels.brightness = _step
        pixels.show()
        time.sleep(wait_time)
    
    blank_pixels()
    pixels.brightness = BRIGHTNESS


def set_ring(color):
    for i in range(0, RING_NUM_PIXELS):
        pixels[i] = wheel(color & 255)
    pixels.show()


def set_scale(color):
    for i in range(RING_NUM_PIXELS, TOTAL_NUM_PIXELS):
        pixels[i] = wheel(color & 255)
    pixels.show()


def map_ring_data(data):
    """ Map an array (assumed to be 0-360 degree values) to the ring."""
    data_np = np.array(data)
    ring_divisions = len(data)//RING_NUM_PIXELS
    
    # Output array
    output = np.zeros(RING_NUM_PIXELS)

    # Decimate data by taking a mean of each azimuth bin.
    _idx = 0
    for i in range(RING_NUM_PIXELS):
        output[i] = np.mean(data_np[_idx:_idx+ring_divisions])
        _idx += ring_divisions
    
    # Now map to a 0-1 linear scale.
    _range = output.max() - output.min()
    return list(np.interp(output, [output.min()+CLIP_VALUE*_range, output.max()], [0.00, 1]))


def display_ring_data(data, confidence=50, bearing=None, compassrose=True):
    """ Display an array of DoA score vs Bearing data, with a given confidence value. """

    # Map the confidence value to a color.
    _color = int(np.interp(confidence, [CONFIDENCE_MIN, CONFIDENCE_MAX], [CONFIDENCE_MIN_COL, CONFIDENCE_MAX_COL]))
    _color = wheel(_color)

    _rose_col = wheel(CONFIDENCE_MIN_COL)

    # Map the input data to the ring steps.
    _data = map_ring_data(data)

    for i in range(RING_NUM_PIXELS):

        _col_r = int(round(_color[0]*_data[i]))
        _col_g = int(round(_color[1]*_data[i]))
        _col_b = int(round(_color[2]*_data[i]))

        if(i%(RING_NUM_PIXELS//ROSE_POINTS) == 0):
            _rose_pxl = (int(_rose_col[0]*ROSE_BRIGHTNESS), int(_rose_col[1]*ROSE_BRIGHTNESS), int(_rose_col[2]*ROSE_BRIGHTNESS))

            if _data[i] < ROSE_BRIGHTNESS:
                pixels[i] = _rose_pxl
            else:
                pixels[i] = (_col_r, _col_g, _col_b)
        else:
            pixels[i] = (_col_r, _col_g, _col_b)
        
    
    # Maybe add this back in - set pixel of the peak bearing.
    # May not be necessary
    # if bearing is not None:
    #     _bearing = int(bearing)//(360//RING_NUM_PIXELS)
    #     pixels[_bearing] = wheel(BEARING_COL)

    pixels.show()

def display_power_value(power):
    _range = np.linspace(POWER_MIN,POWER_MAX, SCALE_NUM_PIXELS)


    for x in range(SCALE_NUM_PIXELS):
        if HUD_MODE:
            _pxl = TOTAL_NUM_PIXELS-1-x
        else:
            _pxl = RING_NUM_PIXELS+x

        if power >= _range[x]:
            pixels[_pxl] = wheel(POWER_COL)
        else:
            pixels[_pxl] = (0,0,0)
    
    pixels.show()



def slow_test():
    for i in range(0, TOTAL_NUM_PIXELS):
        pixels[i] = wheel(0 & 255)
        pixels.show()
        time.sleep(0.4)
        pixels[i] = (0,0,0)
        pixels.show()
        time.sleep(0.4)
    
    time.sleep(3)


def startup():
    """ Perform a Startup 'attract' display"""
    rainbow_cycle(wait_time=0.0005, num_pixels=TOTAL_NUM_PIXELS)
    fade_to_black()


udp_listener = None

def handle_bearing(data):
    _confidence = data['confidence']
    _bearing = data['bearing']
    _power = data['power'] # Power is roughly a SNR value.
    _doa_data = data['raw_doa']

    if "source" in data:
        _source = data["source"]
    else:
        _source = "unknown"

    # Reflect bearings direct from a kerberos-sdr across the N-S axis.
    if _source == "kerberos-sdr":
        _bearing = 360.0 - _bearing
        _doa_data = _doa_data[::-1]

    if HUD_MODE:
        # Flip the data up-down
        _half_a = _doa_data[len(_doa_data)//2-1::-1]
        _half_b = _doa_data[len(_doa_data)-1:len(_doa_data)//2-1:-1]
        _doa_data = _half_a + _half_b

    display_ring_data(_doa_data, _confidence, bearing=_bearing)
    display_power_value(_power)


def handle_gps(data):
    # Quick hack to display udp-broadcasted speed and heading data.

    _speed = data['speed'] # Speed in KPH

    print(data)
    if 'heading' in data:
        _heading = data['heading']
    else:
        _heading = None
    
    if _heading:
        _heading_data = list(np.zeros(360))
        _heading_data[int(_heading)] = 0.99
        _heading_data = _heading_data[::-1]

        _half_a = _heading_data[len(_heading_data)//2-1::-1]
        _half_b = _heading_data[len(_heading_data)-1:len(_heading_data)//2-1:-1]
        _heading_data = _half_a + _half_b

        _confidence = CONFIDENCE_MAX # np.interp(_speed, [0,80], [CONFIDENCE_MIN, CONFIDENCE_MAX])

        display_ring_data(_heading_data, _confidence)
    else:
        # Blank the ring
        for i in range(0, RING_NUM_PIXELS):
            pixels[i] = (0,0,0)
        pixels.show()
    
    # Speed
    _power = np.interp(_speed, [-1,80], [POWER_MIN, POWER_MAX])
    display_power_value(_power)





if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-v", "--verbose", action="store_true", default=False, help="Verbose output."
    )
    parser.add_argument(
        "--udp_port",
        type=int,
        default=55672,
        help="UDP Port to listen for UDP messages on.",
    )
    parser.add_argument(
        "--test", action="store_true", default=False, help="Verbose output."
    )
    parser.add_argument(
        "--brightness", type=float, default=BRIGHTNESS, help="Initial Brightness setting."
    )
    parser.add_argument(
        "--hudmode", action="store_true", default=False, help="Enable HUD Mode"
    )
    parser.add_argument(
        "--rainbow", action="store_true", default=False, help="Enable Continuous Rainbow Mode"
    )
    parser.add_argument(
        "--compass", action="store_true", default=False, help="Enable Compass Mode"
    )
    args = parser.parse_args()

    BRIGHTNESS = args.brightness
    pixels.brightness = BRIGHTNESS

    if args.hudmode:
        HUD_MODE = True

    if args.test:
        while True:
            slow_test()
    
    if args.rainbow:
        while True:
            rainbow_cycle(wait_time=0.0005, num_pixels=TOTAL_NUM_PIXELS)

    if args.compass:
        udp_listener = UDPListener(gps_callback=handle_gps, port=args.udp_port)
    else:
        udp_listener = UDPListener(bearing_callback=handle_bearing, port=args.udp_port)

    # Do some rainbow cycling on startup.
    startup()

    udp_listener.start()

    try:
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        udp_listener.close()
        fade_to_black(steps=100)


