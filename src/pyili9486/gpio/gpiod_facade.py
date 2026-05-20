import gpiod
from gpiod.line import Direction, Value

from pyili9486.gpio import GPIOContext, GPIOFacade, Pin, PinConfig, PinMap


class _GPIODContext(GPIOContext):

    def __init__(self, gpio_chip_path: str, pin_map: PinMap, config: PinConfig):
        super().__init__(pin_map, config)

        self._gpio_chip_path = gpio_chip_path
        self._request = None

    def __enter__(self):
        config = {
            self._pin_map[pin]: gpiod.LineSettings(
                direction=Direction.OUTPUT,
                output_value=Value.ACTIVE if value else Value.INACTIVE
            )
            for pin, value in self._config.items() if self._pin_map[pin] is not None
        }

        self._request = gpiod.request_lines(
            self._gpio_chip_path,
            consumer="gpiod-consumer",
            config=config
        )
        return self

    def set_value(self, pin: Pin, value: bool):
        if self._request is not None:
            pin_id = self._pin_map[pin]
            if pin_id is not None:
                self._request.set_value(pin_id, Value.ACTIVE if value else Value.INACTIVE)
        else:
            raise ValueError('must be called inside context manager')

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._request:
            self._request.release()
            self._request = None


class GPIODFacade(GPIOFacade):
    def __init__(self, dc_pin: int, rs_pin: int | None = None, gpio_chip_id: int = 0):
        super().__init__(dc_pin, rs_pin)
        self._gpiod_chip_path = f"/dev/gpiochip{gpio_chip_id}"

    def set_values(self, config: PinConfig) -> GPIOContext:
        return _GPIODContext(self._gpiod_chip_path, self._pin_map, config)
