import json
import typing as T

from cent.data import CustomType, DataException, Datum, DatumType, Transform
from cent.data.t.pyo import PyO


class JSONx(Transform):
    @staticmethod
    def ast_dump(x: Datum) -> Datum:
        if x.type == DatumType.MAP:
            return Datum(
                DatumType.MAP,
                {JSONx.ast_dump(k): JSONx.ast_dump(v) for k, v in x.value.items()},
                x.args,
            )

        if x.type == DatumType.ARRAY:
            return Datum(DatumType.ARRAY, [JSONx.ast_dump(v) for v in x.value], x.args)

        if x.type == DatumType.BYTES:
            return Datum(
                DatumType.ARRAY,
                [
                    Datum(DatumType.STRING, "__jsonx__"),
                    Datum(DatumType.STRING, "bytes"),
                    Datum(DatumType.STRING, x.value.hex()),
                ],
            )

        if x.type == DatumType.CUSTOM:
            return Datum(
                DatumType.ARRAY,
                [
                    Datum(DatumType.STRING, "__jsonx__"),
                    Datum(DatumType.STRING, "custom"),
                    x.args[0],
                    JSONx.ast_dump(x.value),
                ],
            )

        return x

    @staticmethod
    def dump(x: Datum) -> str:
        x = JSONx.ast_dump(x)

        if x.type == DatumType.MAP or x.type == DatumType.ARRAY:
            obj = PyO.dump(x)
        else:
            raise DataException

        return json.dumps(obj)

    @staticmethod
    def ast_load(x: Datum) -> Datum:
        if x.type == DatumType.MAP:
            return Datum(
                DatumType.MAP,
                {JSONx.ast_load(k): JSONx.ast_load(v) for k, v in x.value.items()},
                x.args,
            )

        if x.type == DatumType.ARRAY:
            if len(x.value) > 2 and x.value[0].value == "__jsonx__":
                if x.value[1].value == "bytes":
                    return Datum(DatumType.BYTES, bytes.fromhex(x.value[2].value))
                elif x.value[1].value == "custom":
                    return Datum(DatumType.CUSTOM, JSONx.ast_load(x.value[3]), args=(x.value[2],))
                else:
                    raise DataException
            else:
                return Datum(DatumType.ARRAY, [JSONx.ast_load(v) for v in x.value], x.args)

        return x

    @staticmethod
    def load(x: T.Union[str, bytes]) -> Datum:
        try:
            x_obj = json.loads(x)
        except json.JSONDecodeError:
            raise DataException

        if isinstance(x_obj, (dict, list)):
            ast = PyO.load(x_obj)
        else:
            raise DataException

        # print("UNCLEAN AST", ast)

        return JSONx.ast_load(ast)


if __name__ == "__main__":

    class A:
        pass

    # x = Py.load({"x": "y", "Osm": b"\x00", "a": A(), "a_t": A})
    # x = Py.load({"Osm": b"\x00"})
    CustomType.register_pickle("a", A)

    x = PyO.load({"x": A()})
    print("OG AST", x, "\n")
    dump = JSONx.dump(x)
    print("ast-py", PyO.dump(dump))
    # print(repr(dump))
    print("---")
    load = JSONx.load(dump)
    print(load, "\n")
    print(PyO.dump(load))
