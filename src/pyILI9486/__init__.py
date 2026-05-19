# Copyright (c)
# Authors: Tony DiCola (tdicola), Liqun Hu (huliqun), Thorben Yzer (SirLefti),
# Craig Lamparter (craigerl), hemna
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
from enum import Enum, IntEnum
from typing import TYPE_CHECKING

import numpy as np
from PIL import Image, ImageDraw

from pyILI9486.gpio import Pin

if TYPE_CHECKING:
    from spidev import SpiDev

    from pyILI9486.gpio import GPIOFacade
else:
    SpiDev = object
    GPIOFacade = object

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

CMD_MACCTL = 0x36
CMD_IDLOFF = 0x38
CMD_IDLON = 0x39
CMD_PXLFMT = 0x3A

CMD_IFMODE = 0xB0
CMD_DINVCTL = 0xB4

CMD_PWRCTL2 = 0xC1
CMD_PWRCTLNOR = 0xC2
CMD_VCOMCTL = 0xC5

CMD_PGAMCTL = 0xE0
CMD_NGAMCTL = 0xE1


# defaults
P_GAM_DEFAULT = [0x0F, 0x1F, 0x1C, 0x0C, 0x0F, 0x08, 0x48, 0x98, 0x37, 0x0A, 0x13, 0x04, 0x11, 0x0D, 0x00]
N_GAM_DEFAULT = [0x0F, 0x32, 0x2E, 0x0B, 0x0D, 0x05, 0x47, 0x75, 0x37, 0x06, 0x10, 0x03, 0x24, 0x20, 0x00]


class SKU(Enum):
    """
    Representation of the supported display SKUs. Check the linked wiki pages to see which one is yours.
    """
    MPI3501 = 0
    """Datasheet: https://www.lcdwiki.com/3.5inch_RPi_Display"""
    MHS3528 = 1
    """Datasheet: https://www.lcdwiki.com/MHS-3.5inch_RPi_Display"""


class PixelFormat(IntEnum):
    """
    Representation of the supported display pixel formats. Currently, SKU MPI3501 is hardcoded to use RGB666, while
    MHS3528 is hardcoded to use RGB565.
    """
    RGB565 = 0x55
    RGB666 = 0x66

    @classmethod
    def from_sku(cls, sku: SKU):
        match sku:
            case SKU.MPI3501:
                return cls.RGB666
            case SKU.MHS3528:
                return cls.RGB565


class Origin(IntEnum):
    """
    Representation of the display origin. The origin is defined by the position of the image relative to the default
    orientation of the raspberry. The default orientation has the GPIO pins being on top, so that the raspberry logo
    and the model's name are readable. The reference point is then the upper left corner, where GPIO pin 1 is located.
    The origin UPPER_LEFT is the default origin, because the reference point is in the upper left corner.
    """

    # data: MY | MX | MV | ML | BGR | MH | X | X
    # The MV bit controls the format. 0 means portrait mode, 1 means landscape mode.
    # The BGR bit is a bit weird. 0 means RGB mode, 1 means BGR mode. However, we always set it to 1 / BGR, despite
    # using RGB pixel format. Maybe the documentation is wrong here.
    UPPER_LEFT = 0x28
    UPPER_LEFT_MIRRORED = 0xA8
    LOWER_LEFT = 0x48
    LOWER_LEFT_MIRRORED = 0x08
    UPPER_RIGHT = 0x88
    UPPER_RIGHT_MIRRORED = 0xC8
    LOWER_RIGHT = 0xE8
    LOWER_RIGHT_MIRRORED = 0x68


def image_to_data(image: Image.Image, pixel_format: PixelFormat) -> list[int]:
    """
    Converts a PIL image to RGB666 or RGB565 format that can be drawn on the LCD.
    :param image: PIL image to convert
    :param pixel_format: target pixel format
    :return: byte stream of converted data
    """
    match pixel_format:
        case PixelFormat.RGB565:
            pb = np.array(image.convert('RGB')).astype(np.uint16)

            r = (pb[..., 0] >> 3) & 0x1F # 5 bits
            g = (pb[..., 1] >> 2) & 0x3F # 6 bits
            b = (pb[..., 2] >> 3) & 0x1F # 5 bits

            rgb565 = (r << 11) | (g << 5) | b

            return rgb565.astype(np.uint16).byteswap().view(np.uint8).flatten().tolist()

        case PixelFormat.RGB666:
            pb = np.array(image.convert('RGB')).astype(np.uint16)
            return (pb & 0xFC).astype(np.uint8).flatten().tolist()


class ILI9486:
    """Representation of an ILI9486 TFT."""

    __LCD_WIDTH = 320
    __LCD_HEIGHT = 480

    def __init__(self, spi: SpiDev, gpio_facade: GPIOFacade, *, origin: Origin = Origin.UPPER_LEFT,
                 sku: SKU = SKU.MPI3501):
        """
        Creates a new ILI9486 TFT instance.
        :param spi: SpiDev connection to use
        :param gpio_facade: GPIO back-end to use
        :param origin: origin to use
        :param sku: SKU of the display
        """
        self.__spi = spi
        self.__gpio = gpio_facade
        self.__origin = origin
        self.__sku = sku

        self.__width = self.__LCD_WIDTH
        self.__height = self.__LCD_HEIGHT
        self.__inverted = False
        self.__idle = False

        # swap width and height if selected origin is landscape mode by checking if third bit is 1
        if self.is_landscape:
            self.__width, self.__height = self.__height, self.__width
        self.__buffer = Image.new('RGB', (self.__width, self.__height), (0, 0, 0))

    @property
    def landscape_dimensions(self) -> tuple[int, int]:
        """
        Returns the display dimensions in landscape mode, no matter what mode is used.
        :return: dimension tuple in landscape mode
        """
        return self.__LCD_HEIGHT, self.__LCD_WIDTH

    @property
    def portrait_dimensions(self) -> tuple[int, int]:
        """
        Returns the display dimensions in portrait mode, no matter what mode is used.
        :return: dimension tuple in portrait mode
        """
        return self.__LCD_WIDTH, self.__LCD_HEIGHT

    @property
    def dimensions(self) -> tuple[int, int]:
        """
        Returns the current display dimensions.
        :return: dimension tuple [width, height]
        """
        return self.__width, self.__height

    @property
    def is_landscape(self) -> bool:
        """
        Returns whether the display is in landscape mode.
        :return: `true` if selected origin is landscape mode; `false` otherwise
        """
        return bool(self.__origin.value & 0x20)

    def __mpi3501_init(self):
        self.command(CMD_IFMODE).data(0x00)
        self.command(CMD_SLPOUT)  # turns off the sleep mode
        time.sleep(0.020)

        self.command(CMD_PXLFMT).data(PixelFormat.from_sku(SKU.MPI3501))
        self.command(CMD_RDPXLFMT).data(PixelFormat.from_sku(SKU.MPI3501))

        self.command(CMD_PWRCTLNOR).command(0x44)

        self.command(CMD_VCOMCTL).send([0x00, 0x00, 0x00, 0x00], True, chunk_size=1)
        self.command(CMD_PGAMCTL).send(P_GAM_DEFAULT, True, chunk_size=1)
        self.command(CMD_NGAMCTL).send(N_GAM_DEFAULT, True, chunk_size=1)

        self.command(CMD_MACCTL).data(self.__origin.value)  # memory address control

        self.command(CMD_SLPOUT)
        self.command(CMD_DISPON)

    def __mhs3528_init(self):
        # Manufacturer-specific registers
        self.command(0xF1).data([0x36, 0x04, 0x00, 0x3C, 0x0F, 0x8F])
        self.command(0xF2).data([0x18, 0xA3, 0x12, 0x02, 0xB2, 0x12, 0xFF, 0x10, 0x00])
        self.command(0xF8).data([0x21, 0x04])
        self.command(0xF9).data([0x00, 0x08])

        self.command(CMD_MACCTL).data(0x08) # memory address control - initial

        self.command(CMD_DINVCTL).data(0x00)

        self.command(CMD_PWRCTL2).data(0x41)

        self.command(CMD_VCOMCTL).data([0x00, 0x91, 0x80, 0x00])
        self.command(CMD_PGAMCTL).data(P_GAM_DEFAULT)
        self.command(CMD_NGAMCTL).data(N_GAM_DEFAULT)

        self.command(CMD_PXLFMT).data(PixelFormat.from_sku(SKU.MHS3528))
        self.command(CMD_SLPOUT)
        self.command(CMD_MACCTL).data(self.__origin.value) # memory address control - final origin

        # Delay 255ms
        time.sleep(0.255)

        # Display On
        self.command(CMD_DISPON)

    def send(self, data: int | list[int], is_data: bool = True, chunk_size: int = 4096):
        """
        Writes a byte or an array of bytes to the display.
        :param data: data as int or list of int
        :param is_data: set to `true` to send data as data; set to `false` to send data as command
        :param chunk_size:
        :return: Self
        """
        # dc low for command, high for data
        with self.__gpio.set_values({Pin.DC: is_data}):
            if isinstance(data, int):
                self.__spi.writebytes([data])
            else:
                for start in range(0, len(data), chunk_size):
                    end = min(start + chunk_size, len(data))
                    self.__spi.writebytes(data[start: end])
            return self

    def command(self, data: int):
        """
        Writes a byte to the display as a command.
        :param data: data as int
        :return: Self
        """
        return self.send(data, False)

    def data(self, data: int | list[int]):
        """
        Writes a byte or an array of bytes to the display as data.
        :param data: data as int or list of int
        :return: Self
        """
        return self.send(data, True)

    def reset(self):
        """
        Resets the display if a reset pin is available.
        :return: Self
        """
        with self.__gpio.set_values({Pin.RS: True}) as context:
            context.set_value(Pin.RS, True)
            time.sleep(.001)  # wait a bit to make sure the output was HIGH
            context.set_value(Pin.RS, False)
            time.sleep(.000100)  # wait 100 µs to trigger the reset (should be 10 µs, but the OS is not precise enough)
            context.set_value(Pin.RS, True)
            time.sleep(.120)  # wait 120 ms for finishing blanking and resetting
            self.__inverted = False
            self.__idle = False
        return self

    def _init_sequence(self):
        """
        Initializes the display
        :return: Self
        """
        match self.__sku:
            case SKU.MPI3501:
                self.__mpi3501_init()
            case SKU.MHS3528:
                self.__mhs3528_init()
        return self

    def begin(self):
        """
        Initializes the display by resetting it and calling the init sequence.
        :return: Self
        """
        return self.reset()._init_sequence()

    def set_window(self, x0: int = 0, y0: int = 0, x1: int | None = None, y1: int | None = None):
        """
        Sets the pixel address window for proceeding drawing commands. Leave all coordinates empty for full screen
        window. Coordinates must be in range `[0, width-1]` and `[0, height-1]` respectively. Start coordinates cannot
        be greater than end coordinates.
        :param x0: start x coordinate
        :param y0: start y coordinate
        :param x1: end x coordinate
        :param y1: end y coordinate
        :return: Self
        """
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
        return self

    def display(self, image: Image.Image | None = None, x0: int = 0, y0: int = 0):
        """
        Writes the display buffer or provided image to the display. If no image is provided, the display buffer will be
        written to the display. A provided image cannot exceed the display bounds.
        :param image: image to display, or `None` to display the internal buffer
        :param x0: x coordinate
        :param y0: y coordinate
        :return: Self
        """
        if image is None:
            image = self.__buffer
        width, height = image.size
        x1 = x0 + width - 1
        y1 = y0 + height - 1
        if image.mode != 'RGB':
            raise ValueError('Image must be in RGB format')
        if x1 >= self.__width or y1 >= self.__height or x0 < 0 or y0 < 0:
            raise ValueError('Image exceeds display bounds ({0}x{1})'.format(self.__width, self.__height))
        self.set_window(x0, y0, x1, y1)
        data = image_to_data(image, PixelFormat.from_sku(self.__sku))
        self.command(CMD_WRMEM)
        self.data(data)
        return self

    def clear(self, color: tuple[int, int, int] = (0, 0, 0)):
        """
        Clears the image buffer to the specified RGB color or black if not provided.
        :param color: default color to override the buffer
        :return: Self
        """
        width, height = self.__buffer.size
        self.__buffer.putdata([color] * (width * height))
        return self

    def draw(self) -> ImageDraw.ImageDraw:
        """
        Returns a PIL ImageDraw instance for 2D drawing on the image buffer.
        :return: PIL ImageDraw instance of the buffer
        """
        return ImageDraw.Draw(self.__buffer)

    @property
    def is_inverted(self) -> bool:
        """
        Returns the current inversion state.
        :return: `true` if inverted; `false` otherwise
        """
        return self.__inverted

    def invert(self, state: bool = True):
        """
        Sets display inversion to the specified state. If not provided, state is True, which inverts the display.
        If state is False, the display turns back into normal mode.
        :param state: set to `true` to invert the display; set to `false` to turn back to normal mode
        :return: Self
        """
        if state:
            self.command(CMD_INVON)
        else:
            self.command(CMD_INVOFF)
        self.__inverted = state
        return self

    @property
    def is_idle(self) -> bool:
        """
        Returns the current idle state.
        :return: `true` if idle; `false` otherwise
        """
        return self.__idle

    def idle(self, state: bool = True):
        """
        Sets the display idle state to the specified state. If not provided, state is True, which turns the idle mode
        on. If state is False, the display turns back into normal mode. In idle mode colors expression is reduced.
        :param state: set to `true` to enable idle mode; set to `false` to disable idle mode
        :return: Self
        """
        if state:
            self.command(CMD_IDLON)
        else:
            self.command(CMD_IDLOFF)
        self.__idle = state
        return self

    def on(self):
        """
        Turns the display on.
        :return: Self
        """
        return self.command(CMD_DISPON)

    def off(self):
        """
        Turns the display off.
        :return: Self
        """
        return self.command(CMD_DISPOFF)

    def sleep(self):
        """
        Turns the displays sleep mode on.
        :return: Self
        """
        self.command(CMD_SLPIN)
        time.sleep(0.005)
        return self

    def wake_up(self):
        """
        Turns the displays sleep mode off.
        :return: Self
        """
        self.command(CMD_SLPOUT)
        time.sleep(0.005)
        return self
