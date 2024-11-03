import typing as T
from enum import IntEnum, auto
from cent.data.datum import DatumType, Datum
from cent.data.exc import DataException


class SchemaType(IntEnum):
    AND = auto()
    OR = auto()
    NOT = auto()


"""
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
"""


class Schema:
    def __init__(
        self, type: T.Union[SchemaType, DatumType], args: T.Tuple[T.Any, ...]
    ) -> None:
        self.type = type
        self.args = args

    def validate(self, datum: Datum) -> bool:
        if isinstance(self.type, DatumType):
            if datum.type != self.type:
                return False
            if self.type == DatumType.ARRAY:
                pass
            if self.type == DatumType.MAP:
                pass
            return True

        return False
