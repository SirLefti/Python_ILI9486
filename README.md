Python ILI9486 Display Driver
=============================

Python module to control an ILI9486 LCD. Based upon the deprecated Python ILI9341 from
[Adafruit](https://github.com/adafruit/Adafruit_Python_ILI9341) and the adapted version for ILI9486 from
[Liqun Hu](https://github.com/huliqun/Myway_Python_ILI9486).
Rewritten to use `spidev` and `rpi-lgpio` instead of the discontinued Adafruit counterpart libraries.


## Installation and use

Call `sudo raspi-config` and then select `Interface Options > SPI` to enable SPI.

Install system dependencies:
````bash
sudo apt install libopenjp2-7 libopenblas0 python3 python3-rpi-lgpio
````

Create a virtual environment:
````bash
python -m venv .venv
````

Install python dependencies:
````bash
.venv/bin/pip install -r requirements.txt
````

Run example:
````bash
.venv/bin/python image.py
````

## Notes

Brightness control is not implemented, because many displays using this driver chip have a hardwired backlight, that
cannot be controlled via the driver chip or a GPIO pin. Implementing it would require some hardware changes on the
display unit. To emulate shutting off the display you can use `lcd.clear().display()`, which makes the display to show
black pixels.

### Original licensing notes

Adafruit invests time and resources providing this open source code, please support Adafruit and open-source hardware by
purchasing products from Adafruit!

Written by Tony DiCola for Adafruit Industries.
Adapted for ILI9486 by Liqun Hu.
Modified and maintained by Thorben Yzer.

MIT license, all text above must be included in any redistribution
