import pickle
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
    List
    Custom
"""


class DataException(Exception):
    pass


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


DATA_t = T.Tuple[DatumType, T.Tuple, T.Any]
DUMP_FUNC_t = T.Callable[[DATA_t], T.Any]
LOAD_FUNC_t = T.Callable[[T.Any], DATA_t]


class CustomType:
    NAMES: T.Dict[T.Type, str] = {}
    DUMP: T.Dict[str, T.Optional[DUMP_FUNC_t]] = {}
    LOAD: T.Dict[str, T.Optional[LOAD_FUNC_t]] = {}

    @staticmethod
    def register(
        name: str,
        t: T.Optional[T.Type] = None,
        dump: T.Optional[DUMP_FUNC_t] = None,
        load: T.Optional[LOAD_FUNC_t] = None,
    ) -> None:
        if t is not None:
            CustomType.NAMES[t] = name

        CustomType.DUMP[name] = dump
        CustomType.LOAD[name] = load

    @staticmethod
    def register_pickle(t: T.Type) -> str:
        name = "pickle/" + t.__name__
        CustomType.register(
            name,
            t,
            dump=lambda x: pickle.loads(x[2]),
            load=lambda x: (DatumType.BYTES, (), pickle.dumps(x)),
        )

        return name

    @staticmethod
    def from_name(name: str) -> T.Tuple[T.Optional[DUMP_FUNC_t], T.Optional[LOAD_FUNC_t]]:
        return CustomType.DUMP.get(name, None), CustomType.LOAD.get(name, None)

    @staticmethod
    def from_type(
        t: T.Type,
    ) -> T.Tuple[T.Optional[str], T.Optional[DUMP_FUNC_t], T.Optional[LOAD_FUNC_t]]:
        if t in CustomType.NAMES.keys():
            name = CustomType.NAMES[t]
        else:
            name = CustomType.register_pickle(t)

        return name, *CustomType.from_name(CustomType.NAMES[t])
