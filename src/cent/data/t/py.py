import typing as T

from cent.data import CustomType, DataException, Datum, DatumType, Transform


class Py(Transform):
    @staticmethod
    def load(x: T.Any) -> Datum:  # noqa: C901
        # Simple
        if x is None:
            return Datum(DatumType.NULL, None)
        if isinstance(x, bool):
            return Datum(DatumType.BOOL, x)
        if isinstance(x, int):
            return Datum(DatumType.INT, x)
        if isinstance(x, float):
            return Datum(DatumType.FLOAT, x)
        if isinstance(x, bytes):
            return Datum(DatumType.BYTES, x)
        if isinstance(x, str):
            return Datum(DatumType.STRING, x)
        if isinstance(x, list):
            return Datum(DatumType.ARRAY, [Py.load(item) for item in x])
        if isinstance(x, dict):
            return Datum(DatumType.MAP, {Py.load(k): Py.load(v) for k, v in x.items()})
        if isinstance(x, object):
            name, load = CustomType.get_load(type(x))
            return Datum(DatumType.CUSTOM, load(x), (Datum(DatumType.STRING, name),))
        raise DataException

    @staticmethod
    def dump(x: T.Union[Datum, T.Any]) -> T.Any:  # noqa: C901
        if not isinstance(x, Datum):
            return x

        if x.type == DatumType.NULL:
            return None
        if x.type == DatumType.BOOL:
            return x.value
        if x.type == DatumType.INT:
            return x.value
        if x.type == DatumType.FLOAT:
            return x.value
        if x.type == DatumType.BYTES:
            return x.value
        if x.type == DatumType.STRING:
            return x.value
        if x.type == DatumType.ARRAY:
            return [Py.dump(v) for v in x.value]
        if x.type == DatumType.MAP:
            return {Py.dump(k): Py.dump(v) for k, v in x.value.items()}
        if x.type == DatumType.CUSTOM:
            name = x.args[0].value
            _, dump = CustomType.get_dump(name)
            return dump(x.value)


if __name__ == "__main__":
    # from mozag import Box

    class A:
        pass

    print(Py.load(13))
    print(Py.load({"a": "b"}))
    # CustomType.register_pickle("a", A)
    # x = Py.load(A())
    # print(x)
    # # del CustomType.DUMP["a"]
    # x = Py.dump(x)
    # print(x)
    # print(Py.load(x))
    # CustomType.register_pickle("a", A)
    # print(Py.dump(Py.load(x)))

    # print(Py.dump(Py.load(Box(0, 1.0, "up"))))
