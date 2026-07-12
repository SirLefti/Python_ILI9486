Python ILI9486 Display Driver
=============================

[![pypi](https://img.shields.io/pypi/v/pyili9486.svg)](https://pypi.python.org/pypi/pyili9486)

`pyILI9486` is a Python library to control an ILI9486 LCD. Based upon the deprecated Python ILI9341 from
[Adafruit](https://github.com/adafruit/Adafruit_Python_ILI9341) and the adapted version for ILI9486 from
[Liqun Hu](https://github.com/huliqun/Myway_Python_ILI9486).
Rewritten to use `spidev` and either `gpiod`, `lgpio` or `rpi-gpio` instead of the discontinued Adafruit counterpart
libraries.

## Supported displays
* [MPI3501](https://www.lcdwiki.com/3.5inch_RPi_Display)
* [MHS3528](https://www.lcdwiki.com/MHS-3.5inch_RPi_Display)

## Installation and use

Install the lib with `pip install pyili9486`, or an equivalent for your python package manager. 

### GPIO backends

This library can use various GPIO backends for internal GPIO control (data and command selection, reset handling). It is
recommended to use the same GPIO library, that you also use in the rest of your project to avoid resource locks. If you
aren't using any library yet, choose `gpiod` or `lgpio`, both are modern implementations with a wide compatibility with
modern Raspberry Pi boards.

`rpi-lgpio` is a special case. For a long time, `RPi.GPIO` was a widely used library for easy GPIO control. It is
considered outdated now, `rpi-lgpio` is a replacement package, wrapping `lgpio` behind a code facade, that exposes the
same API and namespace as `RPi.GPIO`, making it a drop-in replacement. Technically, the `rpi-lgpio` implementation of
this library will also work with the original `RPi.GPIO` being installed.

The necessary backend libraries can be automatically installed by providing it as an extra, e.g.
`pip install pyili9486[lgpio]` (or `pyili9486[gpiod]`, `pyili9486[rpi-lgpio]`).

### Enable SPI

Call `sudo raspi-config` and then select `Interface Options > SPI` to enable SPI.

### Example

For MPI3501 SKU. See [here](#sku) for required changes to use MHS3528 SKU.

```py
# config (should be the same for basically all displays you can buy)
DC_PIN = 24
RS_PIN = 25
SPI_BUS = 0
SPI_DEVICE = 0

# create SPI device
from spidev import SpiDev
spi = SpiDev(SPI_BUS, SPI_DEVICE)
spi.mode = 0b10  # [CPOL|CPHA] -> polarity 1, phase 0
spi.max_speed_hz = 64000000

# create GPIO facade (choose the one you already use in your project, or pick `gpiod` or `lgpio`)
from pyili9486.gpio.lgpio_facade import LGPIOFacade
gpio_facade = LGPIOFacade(DC_PIN, RS_PIN)

# create the LCD instance (optionally set origin and SKU here as well, defaults to MPI3501)
from pyili9486 import ILI9486
lcd = ILI9486(spi, gpio_facade)

# draw some stuff
from PIL import Image

width, height = lcd.dimensions

red = Image.new(mode='RGB', size=(width // 2, height // 2), color=(255, 0, 0))
green = Image.new(mode='RGB', size=(width // 2, height // 2), color=(0, 255, 0))
blue = Image.new(mode='RGB', size=(width // 2, height // 2), color=(0, 0, 255))
white = Image.new(mode='RGB', size=(width // 2, height // 2), color=(255, 255, 255))

lcd.begin()

lcd.display(red, 0, 0)
lcd.display(green, width // 2, 0)
lcd.display(blue, 0, height // 2)
lcd.display(white, width // 2, height // 2)
```

### Troubleshooting

If the display keeps blank, and you do not see what you expect, you might have to tweak some settings.

#### SKU

The LCD instance defaults to the MPI3501 SKU. If yours is the MHS3528, you have to pass this explicitly in the instance
init.
```py
from pyili9486 import ILI9486, SKU
lcd = ILI9486(spi, gpio_facade, sku=SKU.MHS3528)
```
This SKU typically requires to use a different SPI mode as well, that you have to configure beforehand.
```py
from spidev import SpiDev
spi = SpiDev(SPI_BUS, SPI_DEVICE)
spi.mode = 0b00  # [CPOL|CPHA] -> polarity 0, phase 0
spi.max_speed_hz = 64000000
```

#### SPI

If the best defaults do not work to you, try playing around with the SPI settings.

Try reducing the SPI speed, or try out all four possible SPI modes, even though if it is not the default for your SKU.

Defaults:

|         | mode   | max_speed_hz |
|---------|--------|--------------|
| MPI3501 | `0b10` | 64000000     |
| MHS3528 | `0b00` | 48000000     |


## Notes

Brightness control is not implemented, because many displays using this driver chip have a hardwired backlight, that
cannot be controlled via the driver chip or a GPIO pin. Implementing it would require some hardware changes on the
display unit. To emulate shutting off the display you can use `lcd.clear().display()`, which makes the display to show
black pixels.

### Original licensing notes

Adafruit invests time and resources providing this open source code, please support Adafruit and open-source hardware by
purchasing products from Adafruit!

Written by Tony DiCola for Adafruit Industries.<br>
Adapted for ILI9486 by Liqun Hu.<br>
Modified and maintained by Thorben Yzer.<br>
Support for MHS3528 variant by Craig Lamparter and hemna.<br>

MIT license, all text above must be included in any redistribution
