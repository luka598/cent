import typing as T
from enum import IntEnum, auto

"""
Simple:
    Word
    Null
    Bool
    Int
    Float IEEE 754
    Bytes
    String UTF-8
    Array
    Map
    Custom
"""


class DatumType(IntEnum):
    WORD = auto()
    NULL = auto()
    BOOL = auto()
    INT = auto()
    FLOAT = auto()
    BYTES = auto()
    STRING = auto()
    ARRAY = auto()
    MAP = auto()
    CUSTOM = auto()


class Datum:
    def __init__(self, type: DatumType, value: T.Any, args: T.Tuple["Datum", ...] = ()) -> None:
        self.type = type
        self.args = args
        self.value = value

    def __repr__(self) -> str:
        return f"Datum(type={self.type.name}, args={self.args}, value={repr(self.value)})"
