# Copyright (c)
# Authors: Tony DiCola, Liqun Hu, Thorben Yzer
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
import time
import numpy as np
from PIL import Image, ImageDraw
import RPi.GPIO as GPIO

# constants
LCD_WIDTH = 320
LCD_HEIGHT = 480

# commands
CMD_RDPXLFMT = 0x0C

CMD_SLPIN = 0x10
CMD_SLPOUT = 0x11

CMD_INVOFF = 0x20
CMD_INVON = 0x21
CMD_DISPOFF = 0x28
CMD_DISPON = 0x29

CMD_SETCA = 0x2A
CMD_SETPA = 0x2B
CMD_WRMEM = 0x2C
CMD_RDMEM = 0x2E

CMD_MADCTL = 0x36
CMD_IDLOFF = 0x38
CMD_IDLON = 0x39
CMD_PXLFMT = 0x3A

CMD_IFMODE = 0xB0

CMD_PWRCTLNOR = 0xC2
CMD_VCOMCTL = 0xC5

CMD_PGAMCTL = 0xE0
CMD_NGAMCTL = 0xE1

UPPER_LEFT = 0
UPPER_LEFT_MIRRORED = 1
LOWER_LEFT = 2
LOWER_LEFT_MIRRORED = 3
UPPER_RIGHT = 4
UPPER_RIGHT_MIRRORED = 5
LOWER_RIGHT = 6
LOWER_RIGHT_MIRRORED = 7


def image_to_data(image: Image) -> object:
    """Converts a PIL image to 666RGB format that can be drawn on the LCD."""
    pb = np.array(image.convert('RGB')).astype('uint16')
    # cut of the two least significant / rightmost bits to convert 8-bit color to 6-bit color
    return np.dstack((pb[:, :, 0] & 0xFC, pb[:, :, 1] & 0xFC, pb[:, :, 2] & 0xFC)).flatten().tolist()


class ILI9486:
    """Representation of an ILI9486 TFT."""

    def __init__(self, spi, dc: int, rst: int = None, *, origin=UPPER_LEFT):
        """Creates an instance of the display using the given SPI connection. Must provide the SPI driver and the GPIO
        pin number for the DC pin. Can optionally provide the GPIO pin number for the reset pin. Optionally the origin
        can be set. The default is UPPER_LEFT, which is landscape mode this the bottom of the image located at the
        power, video and audio out are of the Pi."""
        self.__spi = spi
        self.__dc = dc
        self.__rst = rst
        self.__origin = origin
        self.__width = LCD_WIDTH
        self.__height = LCD_HEIGHT
        self.__inverted = False
        self.__idle = False

        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.__dc, GPIO.OUT)
        GPIO.output(self.__dc, GPIO.HIGH)
        if self.__rst is not None:
            GPIO.setup(self.__rst, GPIO.OUT)
            GPIO.output(self.__rst, GPIO.HIGH)

        self.__spi.mode = 0b10  # [CPOL|CPHA] -> polarity 1, phase 0
        self.__spi.lsbfirst = False  # set to MSB_FIRST / most significant bit first
        self.__spi.max_speed_hz = 64000000

        # swap width and height if selected origin is landscape mode
        if self.__origin in [UPPER_LEFT, UPPER_LEFT_MIRRORED, LOWER_RIGHT, LOWER_RIGHT_MIRRORED]:
            self.__width, self.__height = self.__height, self.__width
        self.__buffer = Image.new('RGB', (self.__width, self.__height), (0, 0, 0))

    def send(self, data, is_data=True, chunk_size=4096):
        """Writes a byte or an array of bytes to the display."""
        # dc low for command, high for data
        GPIO.output(self.__dc, is_data)
        if isinstance(data, int):
            self.__spi.writebytes([data])
        else:
            for start in range(0, len(data), chunk_size):
                end = min(start + chunk_size, len(data))
                self.__spi.writebytes(data[start: end])

    def command(self, data):
        """Writes a byte or an array of bytes to the display as a command."""
        self.send(data, False)

    def data(self, data):
        """Writes a byte or an array of bytes to the display as data."""
        self.send(data, True)

    def reset(self):
        """Resets the display if a reset pin is provided."""
        if self.__rst is not None:
            GPIO.output(self.__rst, GPIO.HIGH)
            time.sleep(.001)  # wait a bit to make sure the output was HIGH
            GPIO.output(self.__rst, GPIO.LOW)
            time.sleep(.000100)  # wait 100 µs to trigger the reset (should be 10 µs, but the OS is not precise enough)
            GPIO.output(self.__rst, GPIO.HIGH)
            time.sleep(.120)  # wait 120 ms for finishing blanking and resetting
            self.__inverted = False
            self.__idle = False

    def _init_sequence(self):
        """Initializes the display. Protected in case you want to override it for e.g. gamma control"""
        self.command(CMD_IFMODE)
        self.data(0x00)
        self.command(CMD_SLPOUT)  # turns off the sleep mode
        time.sleep(0.020)

        self.command(CMD_PXLFMT)
        self.data(0x66)  # 18 bits per pixel
        self.command(CMD_RDPXLFMT)
        self.data(0x66)  # 18 bits per pixel

        self.command(CMD_PWRCTLNOR)
        self.command(0x44)

        self.command(CMD_VCOMCTL)
        self.send([0x00, 0x00, 0x00, 0x00], True, chunk_size=1)

        self.command(CMD_PGAMCTL)
        self.send([0x0F, 0x1F, 0x1C, 0x0C, 0x0F, 0x08, 0x48, 0x98, 0x37, 0x0A, 0x13, 0x04, 0x11, 0x0D, 0x00], True,
                  chunk_size=1)  # values must be sent one by one, thus setting chunk size to 1

        self.command(CMD_NGAMCTL)
        self.send([0x0F, 0x32, 0x2E, 0x0B, 0x0D, 0x05, 0x47, 0x75, 0x37, 0x06, 0x10, 0x03, 0x24, 0x20, 0x00], True,
                  chunk_size=1)  # values must be sent one by one, thus setting chunk size to 1

        self.command(CMD_MADCTL)  # memory address control
        # data: MY | MX | MV | ML | BGR | MH | X | X
        # The MV bit controls the format. 0 means portrait mode, 1 means landscape mode.
        # The BGR bit is a bit weird. 0 means RGB mode, 1 means BGR mode. However, we always set it to 1 / BGR, despite
        # using RGB pixel format. Maybe the documentation is wrong here.
        if self.__origin == UPPER_LEFT:  # landscape mode, bottom near PWR
            self.data(0x28)
        elif self.__origin == UPPER_LEFT_MIRRORED:
            self.data(0xA8)
        elif self.__origin == LOWER_LEFT:  # default rotated 180°, portrait mode, bottom near USB
            self.data(0x48)
        elif self.__origin == LOWER_LEFT_MIRRORED:
            self.data(0x08)
        elif self.__origin == UPPER_RIGHT:  # default, portrait mode, bottom near SD
            self.data(0x88)
        elif self.__origin == UPPER_RIGHT_MIRRORED:
            self.data(0xC8)
        elif self.__origin == LOWER_RIGHT:  # landscape mode, bottom near GPIO
            self.data(0xE8)
        elif self.__origin == LOWER_RIGHT_MIRRORED:
            self.data(0x68)
        else:
            raise ValueError('Unknown origin: {0}'.format(self.__origin))

        self.command(CMD_SLPOUT)
        self.command(CMD_DISPON)

    def begin(self):
        """Initializes the display by resetting it and calling the init sequence."""
        self.reset()
        self._init_sequence()

    def set_window(self, x0=0, y0=0, x1=None, y1=None):
        """Sets the pixel address window for proceeding drawing commands."""
        if x1 is None:
            x1 = self.__width - 1
        if y1 is None:
            y1 = self.__height - 1
        self.command(CMD_SETCA)  # column address
        self.data(x0 >> 8)
        self.data(x0 & 0xFF)
        self.data(x1 >> 8)
        self.data(x1 & 0xFF)
        self.command(CMD_SETPA)  # page address / row address
        self.data(y0 >> 8)
        self.data(y0 & 0xFF)
        self.data(y1 >> 8)
        self.data(y1 & 0xFF)

    def display(self, image=None):
        """Writes the display buffer or provided image to the display. If no
        image is provided the display buffer will be written to the display.
        If an image is provided, it should be in RGB format and the same
        dimensions as the display."""
        if image is None:
            image = self.__buffer
        width, height = image.size
        if image.mode != 'RGB':
            raise ValueError('Image must be in RGB format')
        if width != self.__width or height != self.__height:
            raise ValueError(
                'Image must be the same dimensions as display ({0}x{1})'.format(self.__width, self.__height))
        self.set_window()
        data = image_to_data(image)
        self.command(CMD_WRMEM)
        if isinstance(data, list):
            self.data(list(data))

    def clear(self, color=(0, 0, 0)):
        """Clears the image buffer to the specified RGB color or black if not provided."""
        width, height = self.__buffer.size
        self.__buffer.putdata([color] * (width * height))

    def draw(self) -> ImageDraw:
        """Returns a PIL ImageDraw instance for 2D drawing on the image buffer."""
        return ImageDraw.Draw(self.__buffer)

    def is_inverted(self) -> bool:
        """Returns the current inversion state."""
        return self.__inverted

    def invert(self, state: bool = True):
        """Sets display inversion to the specified state. If not provided, state
        is True, which inverts the display. If state is False, the display turns
        back into normal mode."""
        if state:
            self.command(CMD_INVON)
        else:
            self.command(CMD_INVOFF)
        self.__inverted = state

    def is_idle(self) -> bool:
        """Returns the current idle state."""
        return self.__idle

    def idle(self, state: bool = True):
        """Sets the display idle state to the specified state. If not provided,
        state is True, which turns the idle mode on. If state is False, the
        display turns back into normal mode. In idle mode colors expression is
        reduced."""
        if state:
            self.command(CMD_IDLON)
        else:
            self.command(CMD_IDLOFF)
        self.__idle = state

    def on(self):
        """Turns the display on."""
        self.command(CMD_DISPON)

    def off(self):
        """Turns the display off."""
        self.command(CMD_DISPOFF)