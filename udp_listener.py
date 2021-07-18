#!/usr/bin/env python
#
#   Project Horus - Browser-Based Chase Mapper
# 	Listeners
#
#   Copyright (C) 2018  Mark Jessop <vk5qi@rfhead.net>
#   Released under GNU GPL v3 or later
#
# 	These classes have been pulled in from the horuslib library, to avoid
# 	requiring horuslib (hopefully soon-to-be retired) as a dependency.

import socket, json, sys, traceback
from threading import Thread
from dateutil.parser import parse
from datetime import datetime, timedelta

MAX_JSON_LEN = 32768

class UDPListener(object):
    """ UDP Broadcast Packet Listener 
    Listens for Horuslib UDP broadcast packets, and passes them onto a callback function
    """

    def __init__(
        self,
        callback=None,
        summary_callback=None,
        gps_callback=None,
        bearing_callback=None,
        port=55672,
    ):

        self.udp_port = port
        self.callback = callback
        self.summary_callback = summary_callback
        self.gps_callback = gps_callback
        self.bearing_callback = bearing_callback

        self.listener_thread = None
        self.s = None
        self.udp_listener_running = False

    def handle_udp_packet(self, packet):
        """ Process a received UDP packet """
        try:
            packet_dict = json.loads(packet.decode())

            if self.callback is not None:
                self.callback(packet_dict)

            if packet_dict["type"] == "PAYLOAD_SUMMARY":
                if self.summary_callback is not None:
                    self.summary_callback(packet_dict)

            if packet_dict["type"] == "PAYLOAD_TELEMETRY":
                if "time_string" in packet_dict.keys():
                    packet_dict["time"] = packet_dict["time_string"]
                if self.summary_callback is not None:
                    self.summary_callback(packet_dict)

            if packet_dict["type"] == "GPS":
                if self.gps_callback is not None:
                    self.gps_callback(packet_dict)

            if packet_dict["type"] == "BEARING":
                if self.bearing_callback is not None:
                    self.bearing_callback(packet_dict)

            if packet_dict["type"] == "MODEM_STATS":
                if self.summary_callback is not None:
                    self.summary_callback(packet_dict)

        except Exception as e:
            print("Could not parse packet: %s" % str(e))
            traceback.print_exc()

    def udp_rx_thread(self):
        """ Listen for Broadcast UDP packets """

        self.s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.s.settimeout(1)
        self.s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        except:
            pass
        self.s.bind(("", self.udp_port))
        print("Started UDP Listener Thread.")
        self.udp_listener_running = True

        while self.udp_listener_running:
            try:
                m = self.s.recvfrom(MAX_JSON_LEN)
            except socket.timeout:
                m = None
            except:
                traceback.print_exc()

            if m != None:
                self.handle_udp_packet(m[0])

        print("Closing UDP Listener")
        self.s.close()

    def start(self):
        if self.listener_thread is None:
            self.listener_thread = Thread(target=self.udp_rx_thread)
            self.listener_thread.start()

    def close(self):
        self.udp_listener_running = False
        self.listener_thread.join()