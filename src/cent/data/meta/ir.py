import typing as T
from enum import IntEnum, auto
from cent.data.meta.exc import DataException

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

IR_REPRESENTABLE = T.Union[None, bool, int, float, bytes, str, list, dict]


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


class ASTNode:
    def __init__(self, type: DatumType, value: T.Any, args: T.Tuple["ASTNode", ...] = ()) -> None:
        self.type = type
        self.args = args
        self.value = value

        if self.type != DatumType.CUSTOM and isinstance(self.value, ASTNode):
            raise DataException("??? retard")

    def __repr__(self) -> str:
        return f"ASTNode(type={self.type.name}, args={self.args}, value={repr(self.value)})"
