from typing import Self

import RPi.GPIO as GPIO

from pyili9486.gpio import GPIOContext, GPIOFacade, Pin, PinConfig, PinMap


class _RPiLGPIOContext(GPIOContext):

    def __init__(self, pin_map: PinMap, config: PinConfig):
        super().__init__(pin_map, config)

    def __enter__(self) -> Self:
        for pin, value in self._config.items():
            pin_id = self._pin_map[pin]
            if pin_id is not None:
                GPIO.output(pin_id, value)
        return self

    def set_value(self, pin: Pin, value: bool):
        pin_id = self._pin_map[pin]
        if pin_id is not None:
            GPIO.output(pin_id, value)

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class RPiLGPIOFacade(GPIOFacade):
    def __init__(self, dc_pin: int, rs_pin: int | None = None):
        super().__init__(dc_pin, rs_pin)

        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self._pin_map[Pin.DC], GPIO.OUT)
        GPIO.output(self._pin_map[Pin.DC], GPIO.HIGH)
        if self._pin_map[Pin.RS] is not None:
            GPIO.setup(self._pin_map[Pin.RS], GPIO.OUT)
            GPIO.output(self._pin_map[Pin.RS], GPIO.HIGH)


    def set_values(self, config: PinConfig) -> GPIOContext:
        return _RPiLGPIOContext(self._pin_map, config)
