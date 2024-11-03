import typing as T
from enum import IntEnum, auto

from cent.data.datum import Datum, DatumType

# TODO: Properly implement this


class SchemaType(IntEnum):
    AND = auto()
    OR = auto()
    NOT = auto()


class Schema:
    def __init__(self, type: T.Union[SchemaType, DatumType], args: T.Tuple[T.Any, ...] = ()) -> None:
        self.type = type
        self.args = args

    def validate(self, datum: Datum) -> bool:
        if isinstance(self.type, DatumType):
            if datum.type != self.type:
                return False
            if self.type == DatumType.ARRAY:
                # WARN: Not recursive
                if len(self.args) > len(datum.value):
                    return False
                if len(self.args) == 0:
                    return True

                for arg, val in zip(self.args, datum.value):
                    if arg != val.type:
                        return False
                return True

            if self.type == DatumType.MAP:
                pass
                return True

            return True

        return False
