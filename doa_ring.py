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
import RPi.GPIO as GPIO
from udp_listener import UDPListener
from turbo import *

#
# Configuration Section
#

# GPIO to which the NeoPixels are Connected
PIXEL_PIN = board.D18

# GPIOs for Switches
GPIO.setmode(GPIO.BCM)
BRIGHTNESS_UP_PIN = 21
BRIGHTNESS_DOWN_PIN = 20
HUDMODE_PIN = 26
COMPASS_PIN = 19

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
COMPASS_MODE = False

HEADING_OK = True

# Initial Brightness of the display.
BRIGHTNESS = 0.1

# Compass rose settings.
ROSE_BRIGHTNESS = 0.1 # Relative brightness.
ROSE_POINTS = 4 # Number of points

# Maximum and Minimum brightness settings.
MAX_BRIGHTNESS = 0.4
MIN_BRIGHTNESS = 0.01
BRIGHTNESS_STEP = 0.01

# Color Settings for the Ring Display
CONFIDENCE_MAX = 10
CONFIDENCE_MIN = 0
CONFIDENCE_MAX_COL = 160
CONFIDENCE_MIN_COL = 255
CLIP_VALUE = 0.7 # Fudge factor to make narrow beams show up well on the display.

# Scale settings for the Power Scale

POWER_SCALE_1_MIN = -60
POWER_SCALE_1_MAX = -40
POWER_SCALE_1_COL = 1
POWER_SCALE_2_MIN = -40
POWER_SCALE_2_MAX = -20
POWER_SCALE_2_COL = 200
POWER_SCALE_3_MIN = -20
POWER_SCALE_3_MAX = -1
POWER_SCALE_3_COL = 160

POWER_BRIGHTNESS = 0.3

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
    global BRIGHTNESS
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


def set_scale(color, brightness=1.0, show=True):
    _pow_col = wheel(color & 255)
    for i in range(RING_NUM_PIXELS, TOTAL_NUM_PIXELS):
        pixels[i] = (int(_pow_col[0]*brightness),int(_pow_col[1]*brightness),int(_pow_col[2]*brightness))

    if show:
        pixels.show()


def clear_scale(show=False):
    for i in range(RING_NUM_PIXELS, TOTAL_NUM_PIXELS):
        pixels[i] = (0,0,0)

    if show:
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


def display_ring_data(data, confidence=50, bearing=None, compassrose=True, rose_points=ROSE_POINTS):
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

        if(compassrose and (i%(RING_NUM_PIXELS//rose_points) == 0)):
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

    _pow_col = wheel(POWER_COL)

    for x in range(SCALE_NUM_PIXELS):
        if HUD_MODE:
            _pxl = TOTAL_NUM_PIXELS-1-x
        else:
            _pxl = RING_NUM_PIXELS+x

        if power >= _range[x]:
            pixels[_pxl] = (int(_pow_col[0]*POWER_BRIGHTNESS),int(_pow_col[1]*POWER_BRIGHTNESS),int(_pow_col[2]*POWER_BRIGHTNESS))
        else:
            pixels[_pxl] = (0,0,0)
    
    pixels.show()

def display_power_value2(power):

    if(power <= POWER_SCALE_1_MAX):
        clear_scale(show=False)
        _min = POWER_SCALE_1_MIN
        _max = POWER_SCALE_1_MAX
        _col = POWER_SCALE_1_COL
    elif (power <= POWER_SCALE_2_MAX):
        set_scale(POWER_SCALE_1_COL,brightness=POWER_BRIGHTNESS, show=False)
        _min = POWER_SCALE_2_MIN
        _max = POWER_SCALE_2_MAX
        _col = POWER_SCALE_2_COL
    elif (power <= POWER_SCALE_3_MAX):
        set_scale(POWER_SCALE_2_COL,brightness=POWER_BRIGHTNESS, show=False)
        _min = POWER_SCALE_3_MIN
        _max = POWER_SCALE_3_MAX
        _col = POWER_SCALE_3_COL
    else:
        set_scale(POWER_SCALE_3_COL, show=True)
        return



    _range = np.linspace(_min,_max, SCALE_NUM_PIXELS)

    _pow_col = wheel(_col)

    for x in range(SCALE_NUM_PIXELS):
        if HUD_MODE:
            _pxl = TOTAL_NUM_PIXELS-1-x
        else:
            _pxl = RING_NUM_PIXELS+x

        if power >= _range[x]:
            pixels[_pxl] = (int(_pow_col[0]*POWER_BRIGHTNESS),int(_pow_col[1]*POWER_BRIGHTNESS),int(_pow_col[2]*POWER_BRIGHTNESS))
    
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


def test_cmap():
    for i in range(0, RING_NUM_PIXELS):
        _color = int(np.interp(i/RING_NUM_PIXELS, [0.0,1.0], [0,255]))
        _color = wheel(_color)
        pixels[i] = _color

    pixels.show()
    time.sleep(3)


def test_power():
    while True:
        for i in range(0,100):
            print(i)
            display_power_value2(i)
            time.sleep(0.5)


def startup():
    """ Perform a Startup 'attract' display"""
    rainbow_cycle(wait_time=0.0005, num_pixels=TOTAL_NUM_PIXELS)
    fade_to_black()


udp_listener = None

def handle_bearing(data):
    global COMPASS_MODE, HUD_MODE, HEADING_OK

    print("Got bearing")
    if COMPASS_MODE:
        return

    _confidence = data['confidence']
    _bearing = data['bearing']
    _power = data['power'] # Power is roughly a SNR value.
    _doa_data = data['raw_doa']

    if "source" in data:
        _source = data["source"]
    else:
        _source = "unknown"

    # Reflect bearings direct from a kerberos-sdr across the N-S axis.
    if _source == "krakensdr_doa":
        _bearing = 360.0 - _bearing
        _doa_data = _doa_data[::-1]

    if HUD_MODE:
        # Flip the data up-down
        _half_a = _doa_data[len(_doa_data)//2-1::-1]
        _half_b = _doa_data[len(_doa_data)-1:len(_doa_data)//2-1:-1]
        _doa_data = _half_a + _half_b

    display_ring_data(_doa_data, _confidence, compassrose=HEADING_OK, bearing=_bearing)
    display_power_value2(_power)


def handle_gps(data):
    global COMPASS_MODE, HUD_MODE, HEADING_OK

    if 'heading_status' in data:
        if 'Ongoing' in data['heading_status']:
            HEADING_OK = False
        else:
            HEADING_OK = True
    else:
        HEADING_OK = True

    if not COMPASS_MODE:
        return

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

        display_ring_data(_heading_data, _confidence, compassrose=HEADING_OK, rose_points=8)
    
    # Speed
    _power = np.interp(_speed, [-1,100], [POWER_SCALE_1_MIN, POWER_SCALE_3_MAX])
    display_power_value2(_power)

handling_brightness = False

def handle_brightness_up(a):
    global handling_brightness, BRIGHTNESS

    if handling_brightness:
        return
    
    handling_brightness = True

    print("Brightness Up")
    if (BRIGHTNESS+BRIGHTNESS_STEP) < MAX_BRIGHTNESS:
        BRIGHTNESS += BRIGHTNESS_STEP
        print(f"New Brightness: {BRIGHTNESS}")
        pixels.brightness = BRIGHTNESS

    time.sleep(0.1)
    handling_brightness = False

def handle_brightness_down(a):
    global handling_brightness, BRIGHTNESS

    if handling_brightness:
        return
    
    handling_brightness = True

    print("Brightness Down")
    if (BRIGHTNESS-BRIGHTNESS_STEP) > MIN_BRIGHTNESS:
        BRIGHTNESS -= BRIGHTNESS_STEP
        print(f"New Brightness: {BRIGHTNESS}")
        pixels.brightness = BRIGHTNESS
    
    time.sleep(0.1)
    handling_brightness = False


def handle_hudmode(a):
    global HUD_MODE
    if(GPIO.input(HUDMODE_PIN)):
        HUD_MODE = True
        print("HUD Mode On")
    else:
        HUD_MODE = False
        print("HUD Mode Off")



def handle_compass(a):
    global COMPASS_MODE
    if(GPIO.input(COMPASS_PIN)):
        print("Compass mode")
        COMPASS_MODE = True
    else:
        print("Bearing mode")
        COMPASS_MODE = False


def setup_gpio():
    GPIO.setup(BRIGHTNESS_UP_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(BRIGHTNESS_DOWN_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(HUDMODE_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(COMPASS_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    time.sleep(0.5)
    GPIO.add_event_detect(BRIGHTNESS_UP_PIN, GPIO.FALLING, callback=handle_brightness_up)
    GPIO.add_event_detect(BRIGHTNESS_DOWN_PIN, GPIO.FALLING, callback=handle_brightness_down)
    GPIO.add_event_detect(HUDMODE_PIN, GPIO.BOTH, callback=handle_hudmode)
    GPIO.add_event_detect(COMPASS_PIN, GPIO.BOTH, callback=handle_compass)
    


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-v", "--verbose", action="store_true", default=False, help="Verbose output."
    )
    parser.add_argument(
        "--bearing_udp_port",
        type=int,
        default=55672,
        help="UDP Port to listen for Bearing UDP messages on.",
    )
    parser.add_argument(
        "--gps_udp_port",
        type=int,
        default=55672,
        help="UDP Port to listen for Compass UDP messages on.",
    )
    parser.add_argument(
        "--testpixels", action="store_true", default=False, help="Test each pixel in sequence."
    )
    parser.add_argument(
        "--testcmap", action="store_true", default=False, help="Test colormap."
    )
    parser.add_argument(
        "--testpower", action="store_true", default=False, help="Test power scale."
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
    parser.add_argument(
        "--gpio", action="store_true", default=False, help="Use GPIO to set modes."
    )
    args = parser.parse_args()

    BRIGHTNESS = args.brightness
    pixels.brightness = BRIGHTNESS

    if args.hudmode:
        HUD_MODE = True
    

    COMPASS_MODE = args.compass

    if args.gpio:
        setup_gpio()
        if(GPIO.input(COMPASS_PIN)):
            COMPASS_MODE = True
            print("Compass mode enabled!")
        else:
            COMPASS_MODE = False
        
        if(GPIO.input(HUDMODE_PIN)):
            HUD_MODE = True
            print("HUD mode enabled!")
        else:
            HUD_MODE = False


    if args.testpixels:
        while True:
            slow_test()

    if args.testcmap:
        while True:
            test_cmap()

    if args.testpower:
        while True:
            test_power()

    if args.rainbow:
        while True:
            rainbow_cycle(wait_time=0.0005, num_pixels=TOTAL_NUM_PIXELS)


    gps_udp_listener = UDPListener(gps_callback=handle_gps, port=args.gps_udp_port)

    bearing_udp_listener = UDPListener(bearing_callback=handle_bearing, port=args.bearing_udp_port)

    # Do some rainbow cycling on startup.
    startup()

    gps_udp_listener.start()
    bearing_udp_listener.start()

    try:
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        gps_udp_listener.close()
        bearing_udp_listener.close()
        fade_to_black(steps=100)


