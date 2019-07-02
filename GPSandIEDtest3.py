#Combined GPS and IED detection software
#Once fix recieved, allow for IED detection results to print (every second)
import os
import time
import board
import busio
import adafruit_gps
import serial
import digitalio
import adafruit_mcp3xxx.mcp3008 as MCP
from adafruit_mcp3xxx.analog_in import AnalogIn
import socket

uart = serial.Serial("/dev/ttyS0", baudrate=9600, timeout=3000)
gps = adafruit_gps.GPS(uart, debug=False) # Create a GPS module instance.
gps.send_command(b'PMTK314,0,1,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0')# Turn on the basic GGA and RMC info
gps.send_command(b'PMTK220,500')# Set update rate to once a second (1hz)

# create the spi bus
spi = busio.SPI(clock=board.SCK, MISO=board.MISO, MOSI=board.MOSI)

# create the cs (chip select)
cs = digitalio.DigitalInOut(board.D22)

# create the mcp object
mcp = MCP.MCP3008(spi, cs)

# create an analog input channel on pin 1
chan1 = AnalogIn(mcp, MCP.P1)
chan2 = AnalogIn(mcp, MCP.P2)
print('Raw ADC Value: ', chan1.value/64)
print('ADC Voltage: ' + str(chan1.voltage) + 'V')

last_read = 0       # this keeps track of the last potentiometer value
tolerance = 300     # to keep from being jittery

def remap_range(value, left_min, left_max, right_min, right_max):
    # this remaps a value from original (left) range to new (right) range
    # Figure out how 'wide' each range is
    left_span = left_max - left_min
    right_span = right_max - right_min

    # Convert the left range into a 0-1 range (int)
    valueScaled = int(value - left_min) / int(left_span)

    # Convert the 0-1 range into a value in the right range.
    return int(right_min + (valueScaled * right_span))

# Setup for UDP stuff

    #       print('{},{0:.6f},{0:.6f},{},{},{}'.format(gps.altitude_m, gps.latitude, gps.longitude, gps.timestamp_utc, channel_1/64, channel_2/64))
    
 
# Main loop runs forever printing the location, etc. every second.
UDP_IP = "127.0.0.1"
UDP_PORT = 5005

last_print = time.monotonic()
while True:
    # Make sure to call gps.update() every loop iteration and at least twice
    # as fast as data comes from the GPS unit (usually every second).
    # This returns a bool that's true if it parsed new data (you can ignore it
    # though if you don't care and instead look at the has_fix property).
    gps.update()
    # Every second print out current location details if there's a fix.
    current = time.monotonic()
    if current - last_print >= 0.5:
        last_print = current
        if not gps.has_fix:
            # Try again if we don't have a fix yet.
            print('Waiting for fix...')
            continue
        # We have a fix! (gps.has_fix is true)
        # Print out details about the fix like location, date, etc.
        print('=' * 40)  # Print a separator line.
        print('Fix timestamp: {}/{}/{} {:02}:{:02}:{:02}'.format(
            gps.timestamp_utc.tm_mon,   # Grab parts of the time from the
            gps.timestamp_utc.tm_mday,  # struct_time object that holds
            gps.timestamp_utc.tm_year,  # the fix time.  Note you might
            gps.timestamp_utc.tm_hour,  # not get all data like year, day,
            gps.timestamp_utc.tm_min,   # month!
            gps.timestamp_utc.tm_sec))
        
        print('Latitude: {0:.6f} degrees'.format(gps.latitude))
        print('Longitude: {0:.6f} degrees'.format(gps.longitude))
        if gps.altitude_m is not None:
            print('Altitude: {} meters'.format(gps.altitude_m))
            # read the analog pin
        channel_1 = chan1.value
        channel_2 = chan2.value

        #convert 16bit adc0 (0-65535) trim pot read into 0-100 volume level
        level_1 = remap_range(channel_1, 64, 65472, 0, 100)
        level_2 = remap_range(channel_2, 64, 65472, 0, 100)
        print("Percent Detection: %d , Raw Output: %d" % (level_1, channel_1/64))
        print("Percent Detection: %d , Raw Output: %d" % (level_2, channel_2/64))
        
        MESSAGE = '{},{},{},{},{},{}'.format(gps.altitude_m, gps.latitude, gps.longitude, gps.timestamp_utc, channel_1/64, channel_2/64)
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto(MESSAGE, (UDP_IP,UDP_PORT))
