from abc import ABC, abstractmethod
from enum import IntEnum
from typing import Self


class Pin(IntEnum):
    DC = 0  # data/command
    RS = 1  # reset


PinConfig = dict[Pin, bool]
PinMap = dict[Pin, int | None]


class GPIOContext(ABC):

    def __init__(self, pin_map: PinMap, config: PinConfig):
        self._pin_map = pin_map
        self._config = config

    @abstractmethod
    def __enter__(self) -> Self:
        raise NotImplementedError

    @abstractmethod
    def __exit__(self, exc_type, exc_val, exc_tb):
        raise NotImplementedError

    @abstractmethod
    def set_value(self, pin: Pin, value: bool):
        raise NotImplementedError

class GPIOFacade(ABC):

    def __init__(self, dc_pin: int, rs_pin: int | None = None):
        self._pin_map: PinMap = {
            Pin.DC: dc_pin,
            Pin.RS: rs_pin
        }

    @abstractmethod
    def set_values(self, config: PinConfig) -> GPIOContext:
        raise NotImplementedError

