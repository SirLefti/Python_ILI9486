import time

import RPi.GPIO as GPIO
from PIL import Image
from spidev import SpiDev

import config
import ILI9486 as LCD

spi: SpiDev = None

if __name__ == '__main__':
    try:
        GPIO.setmode(GPIO.BCM)
        spi = SpiDev(config.SPI_BUS, config.SPI_DEVICE)
        spi.mode = 0b10  # [CPOL|CPHA] -> polarity 1, phase 0
        # default value
        # spi.lsbfirst = False  # set to MSB_FIRST / most significant bit first
        spi.max_speed_hz = 64000000
        lcd = LCD.ILI9486(dc=config.DC_PIN, rst=config.RST_PIN, spi=spi).begin()
        print(f'Initialized display with landscape mode = {lcd.is_landscape} and dimensions {lcd.dimensions}')
        print('Loading image...')
        image = Image.open('sample.png')
        width, height = image.size
        partial = image.resize((width // 2, height // 2))
        red = Image.new(mode='RGB', size=(width // 2, height // 2), color=(255, 0, 0))
        green = Image.new(mode='RGB', size=(width // 2, height // 2), color=(0, 255, 0))
        blue = Image.new(mode='RGB', size=(width // 2, height // 2), color=(0, 0, 255))

        while True:
            print('Drawing image')
            lcd.display(red)
            lcd.display(green, x0 = width // 2)
            lcd.display(blue, y0 = height // 2)
            lcd.display(partial, x0 = width // 2, y0 = height // 2)
            time.sleep(1)
            print('Turning on inverted mode')
            lcd.invert()
            time.sleep(1)
            print('Turning off inverted mode')
            lcd.invert(False)
            time.sleep(1)
            print('Turning off display')
            lcd.off()
            time.sleep(1)
            print('Turning on display')
            lcd.on()
            time.sleep(1)
            print('Turning on idle mode')
            lcd.idle()
            time.sleep(1)
            print('Turning off idle mode')
            lcd.idle(False)
            time.sleep(1)
            print('Clearing display')
            lcd.clear().display()
            time.sleep(1)
            print('Resetting display')
            lcd.begin()
            time.sleep(1)
            print('Turning on sleep mode')
            lcd.sleep()
            time.sleep(1)
            print('Turning off sleep mode')
            lcd.wake_up()
            time.sleep(1)

    except KeyboardInterrupt:
        # catching keyboard interrupt to exit, but do the cleanup in finally block
        pass
    finally:
        GPIO.cleanup()
        spi.close()
