import colorsys
import time
from typing import Type

import numpy as np
import pytest
from PIL import Image
from spidev import SpiDev

from pyILI9486 import ILI9486, GPIOFacade
from pyILI9486.gpio.gpiod_facade import GPIODFacade
from pyILI9486.gpio.lgpio_facade import LGPIOFacade
from pyILI9486.gpio.rpilgpio_facade import RPiLGPIOFacade


@pytest.fixture(params=[
    GPIODFacade, LGPIOFacade, RPiLGPIOFacade
])
def lcd(request):
    spi = SpiDev(0, 0)
    spi.mode = 0b10  # [CPOL|CPHA] -> polarity 1, phase 0
    spi.max_speed_hz = 64000000
    gpio_class: Type[GPIOFacade] = request.param
    gpio = gpio_class(24, 25)

    yield ILI9486(spi, gpio)

    spi.close()


def generate_gradient(width: int, height: int) -> Image.Image:
    h = np.linspace(0, 1, width)
    s = np.ones(height)
    v = np.ones(height)

    fraction = int(height // 2)

    s[:fraction] = np.linspace(0, 1, fraction)
    v[-fraction:] = np.linspace(1, 0, fraction)

    H, S = np.meshgrid(h, s)
    _, V = np.meshgrid(h, v)

    r, g, b = np.vectorize(colorsys.hsv_to_rgb)(H, S, V)
    rgb = (np.dstack((r, g, b)) * 255).astype(np.uint8)

    image = Image.fromarray(rgb, "RGB")
    return image


def test_facade(lcd: ILI9486):
    width, height = lcd.dimensions

    red = Image.new(mode='RGB', size=(width // 2, height // 2), color=(255, 0, 0))
    green = Image.new(mode='RGB', size=(width // 2, height // 2), color=(0, 255, 0))
    blue = Image.new(mode='RGB', size=(width // 2, height // 2), color=(0, 0, 255))
    white = Image.new(mode='RGB', size=(width // 2, height // 2), color=(255, 255, 255))

    gradient = generate_gradient(width, height)

    lcd.begin()

    lcd.display(red, 0, 0)
    lcd.display(green, width // 2, 0)
    lcd.display(blue, 0, height // 2)
    lcd.display(white, width // 2, height // 2)
    time.sleep(1)

    lcd.invert()
    time.sleep(1)

    lcd.invert(False)
    lcd.display(gradient)
    time.sleep(1)

    lcd.clear()
    lcd.reset()
