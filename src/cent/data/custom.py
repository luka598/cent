import pickle
import typing as T

from cent.data.datum import Datum, DatumType
from cent.data.exc import DataException

LOAD_FUNC_t = T.Callable[[T.Any], Datum]
DUMP_FUNC_t = T.Callable[[Datum], T.Any]


class CustomType:
    NAMES: T.Dict[T.Type, str] = {}
    LOAD: T.Dict[str, LOAD_FUNC_t] = {}
    DUMP: T.Dict[str, DUMP_FUNC_t] = {}

    @staticmethod
    def register(
        name: str,
        t: T.Optional[T.Type] = None,
        load: T.Optional[LOAD_FUNC_t] = None,
        dump: T.Optional[DUMP_FUNC_t] = None,
    ) -> None:
        if t is not None:
            CustomType.NAMES[t] = name
            if hasattr(t, "__cent_load__"):
                CustomType.LOAD[name] = getattr(t, "__cent_load__")
            if hasattr(t, "__cent_dump__"):
                CustomType.DUMP[name] = getattr(t, "__cent_dump__")

        if load is not None:
            CustomType.LOAD[name] = load
        if dump is not None:
            CustomType.DUMP[name] = dump

    @staticmethod
    def register_pickle(
        name: str,
        t: T.Optional[T.Type] = None,
    ) -> None:
        CustomType.register(
            name,
            t,
            lambda x: Datum(DatumType.BYTES, pickle.dumps(x)),
            lambda x: pickle.loads(x.value),
        )

    @staticmethod
    def get_load(x: T.Union[str, T.Type]) -> T.Tuple[str, LOAD_FUNC_t]:
        if isinstance(x, str):
            name = x
        else:
            if x not in CustomType.NAMES.keys():
                raise DataException(f"Got unregistered type: {x}")
            name = CustomType.NAMES[x]

        load = CustomType.LOAD.get(name, None)
        if load is None:
            raise DataException(f"Load is not defined for {name}")

        return name, load

    @staticmethod
    def get_dump(x: T.Union[str, T.Type]) -> T.Tuple[str, DUMP_FUNC_t]:
        if isinstance(x, str):
            name = x
        else:
            if x not in CustomType.NAMES.keys():
                raise DataException(f"Got unregistered type: {x}")
            name = CustomType.NAMES[x]

        dump = CustomType.DUMP.get(name, None)
        if dump is None:
            raise DataException(f"Dump is not defined for {name}")

        return name, dump
