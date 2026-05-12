from typing import Self

import lgpio

from pyILI9486.gpio import GPIOContext, GPIOFacade, Pin, PinConfig, PinMap


class _LGPIOContext(GPIOContext):

    def __init__(self, gpio, pin_map: PinMap, config: PinConfig):
        super().__init__(pin_map, config)
        self._gpio = gpio

    def __enter__(self) -> Self:
        for pin, value in self._config.items():
            pin_id = self._pin_map[pin]
            if pin_id is not None:
                lgpio.gpio_claim_output(self._gpio, pin_id, value)
        return self

    def set_value(self, pin: Pin, value: bool):
        pin_id = self._pin_map[pin]
        if pin_id is not None:
            lgpio.gpio_write(self._gpio, pin_id, value)

    def __exit__(self, exc_type, exc_val, exc_tb):
        for pin, value in self._config.items():
            pin_id = self._pin_map[pin]
            if pin_id is not None:
                lgpio.gpio_free(self._gpio, pin_id)


class LGPIOFacade(GPIOFacade):
    def __init__(self, dc_pin: int, rs_pin: int | None = None, gpio_chip_id: int = 0):
        super().__init__(dc_pin, rs_pin)

        self._gpio = lgpio.gpiochip_open(gpio_chip_id)

    def set_values(self, config: PinConfig) -> GPIOContext:
        return _LGPIOContext(self._gpio, self._pin_map, config)
