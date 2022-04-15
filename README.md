Python ILI9486 Display Driver
=============================

Python module to control an ILI9486 LCD. Based upon the deprecated Python ILI9341 from
[Adafruit](https://github.com/adafruit/Adafruit_Python_ILI9341) and the adapted version for ILI9486 from
[Liqun Hu](https://github.com/huliqun/Myway_Python_ILI9486).
Rewritten to use `spidev` and `RPi.GPIO` instead of the discontinued Adafruit counterpart libraries.


## Installation and use

Install system dependencies:
````bash
sudo apt install build-essential python3 python3-dev python3-smbus python3-venv libfreetype6-dev libjpeg-dev libatlas-base-dev
````

Create a virtual environment:
````bash
python -m venv .venv
````

Install python dependencies:
````bash
.venv/bin/pip install pillow
.venv/bin/pip install RPi.GPIO
.venv/bin/pip install spidev
.venv/bin/pip install numpy
````

Run example:
````bash
.venv/bin/python image.py
````

## Notes

Adafruit invests time and resources providing this open source code, please support Adafruit and open-source hardware by purchasing products from Adafruit!

Written by Tony DiCola for Adafruit Industries.
Adapted for ILI9486 by Liqun Hu.
Modified by Thorben Yzer.

MIT license, all text above must be included in any redistribution