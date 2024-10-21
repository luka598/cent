import typing as T

from cent.data import CustomType, DATA_t, DataException, DatumType


class Py:
    @staticmethod
    def load(x: T.Any) -> DATA_t:
        # Simple
        if x is None:
            return (DatumType.NULL, (), None)
        if isinstance(x, bool):
            return (DatumType.BOOL, (), x)
        if isinstance(x, int):
            return (DatumType.INT, (), x)
        if isinstance(x, float):
            return (DatumType.FLOAT, (), x)
        if isinstance(x, bytes):
            return (DatumType.BYTES, (), x)
        if isinstance(x, str):
            return (DatumType.STRING, (), x)
        if isinstance(x, list):
            return (DatumType.ARRAY, (), [Py.load(item) for item in x])
        if isinstance(x, dict):
            return (DatumType.MAP, (), {Py.load(k): Py.load(v) for k, v in x.items()})
        if isinstance(x, object):
            name, _, load = CustomType.from_type(type(x))
            if name is None:
                raise DataException
            if load is None:
                raise DataException

            return (DatumType.CUSTOM, (name,), load(x))
        raise DataException

    @staticmethod
    def dump(x: DATA_t) -> T.Any:
        if x[0] == DatumType.NULL:
            return None
        if x[0] == DatumType.BOOL:
            return x[2]
        if x[0] == DatumType.INT:
            return x[2]
        if x[0] == DatumType.FLOAT:
            return x[2]
        if x[0] == DatumType.BYTES:
            return x[2]
        if x[0] == DatumType.STRING:
            return x[2]
        if x[0] == DatumType.ARRAY:
            return x[2]
        if x[0] == DatumType.MAP:
            return x[2]
        if x[0] == DatumType.CUSTOM:
            name = x[1][0]
            dump, _ = CustomType.from_name(name)
            if dump is None:
                raise DataException

            return dump(x[2])


if __name__ == "__main__":
    from mozag import Box

    class A:
        pass

    print(Py.load(13))
    print(Py.load({"a": "b"}))
    print(Py.load(A()))

    print(Py.dump(Py.load(Box(0, 1.0, "up"))))
