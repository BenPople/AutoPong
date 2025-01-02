"""
XPT2046 Touch module (Non-Blocking Modified).
"""

from time import sleep
try:
    from micropython import const
except ImportError:
    def const(x): return x

class Touch(object):
    """Serial interface for XPT2046 Touch Screen Controller."""

    # Command constants from the XPT2046 / ILI9341 datasheet
    GET_X = const(0b11010000)   # X position
    GET_Y = const(0b10010000)   # Y position
    GET_Z1 = const(0b10110000)  # Z1 position
    GET_Z2 = const(0b11000000)  # Z2 position
    GET_TEMP0 = const(0b10000000)   # Temperature 0
    GET_TEMP1 = const(0b11110000)   # Temperature 1
    GET_BATTERY = const(0b10100000) # Battery monitor
    GET_AUX = const(0b11100000)     # Auxiliary input to ADC

    def __init__(
        self,
        spi,
        cs,
        int_pin=None,
        int_handler=None,
        width=240,
        height=320,
        x_min=100,
        x_max=1962,
        y_min=100,
        y_max=1900
    ):
        """Initialize touch screen controller.

        Args:
            spi (Class Spi):  SPI interface for OLED
            cs (Class Pin):  Chip select pin
            int_pin (Class Pin):  Touch controller interrupt pin
            int_handler (function): Handler for screen interrupt
            width (int): Width of LCD screen
            height (int): Height of LCD screen
            x_min (int): Minimum x coordinate
            x_max (int): Maximum x coordinate
            y_min (int): Minimum Y coordinate
            y_max (int): Maximum Y coordinate
        """
        self.spi = spi
        self.cs = cs
        self.cs.init(self.cs.OUT, value=1)
        self.rx_buf = bytearray(3)
        self.tx_buf = bytearray(3)
        self.width = width
        self.height = height

        # Calibration range
        self.x_min = x_min
        self.x_max = x_max
        self.y_min = y_min
        self.y_max = y_max

        # Convert raw ADC to screen coords
        self.x_multiplier = width / (x_max - x_min)
        self.x_add = x_min * -self.x_multiplier
        self.y_multiplier = height / (y_max - y_min)
        self.y_add = y_min * -self.y_multiplier

        # If int_pin is used, configure it (but we won't rely on interrupts now)
        if int_pin is not None:
            self.int_pin = int_pin
            self.int_pin.init(int_pin.IN)
        self.int_handler = int_handler
        self.int_locked = False

    def get_touch(self):
        """
        Non-blocking approach: Try ONE quick reading.
        Returns (x, y) if valid, or None if no valid touch is detected.
        """
        sample = self.raw_touch()
        if sample is None:
            return None  # No valid reading
        x, y = self.normalize(*sample)
        return (x, y)

    def normalize(self, x, y):
        """Map raw ADC values to screen coordinates."""
        x = int(self.x_multiplier * x + self.x_add)
        y = int(self.y_multiplier * y + self.y_add)
        return (x, y)

    def raw_touch(self):
        """Read raw X,Y touch values. Returns (x, y) or None if out of range."""
        x = self.send_command(self.GET_X)
        y = self.send_command(self.GET_Y)
        # Check if within calibrated range
        if self.x_min <= x <= self.x_max and self.y_min <= y <= self.y_max:
            return (x, y)
        else:
            return None

    def send_command(self, command):
        """Write command to XPT2046 (MicroPython).
        Returns int: 12-bit response
        """
        self.tx_buf[0] = command
        self.cs(0)
        self.spi.write_readinto(self.tx_buf, self.rx_buf)
        self.cs(1)
        return (self.rx_buf[1] << 4) | (self.rx_buf[2] >> 4)

    def is_pressed(self):
        """
        Returns True if the pen is (likely) down.
        The XPT2046 can read Z1/Z2 for pressure, or we can guess by reading X/Y.
        Here, we do a quick check with raw_touch.
        """
        sample = self.raw_touch()
        return (sample is not None)