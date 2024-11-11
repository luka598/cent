import json
import typing as T

from cent.data import DataException, Datum, DatumType, Transform
from cent.data.t.pyo import PyO


class JSON(Transform):
    @staticmethod
    def ast_dump(x: Datum) -> Datum:
        if x.type == DatumType.MAP:
            return Datum(
                DatumType.MAP,
                {JSON.ast_dump(k): JSON.ast_dump(v) for k, v in x.value.items()},
                x.args,
            )

        if x.type == DatumType.ARRAY:
            return Datum(DatumType.ARRAY, [JSON.ast_dump(v) for v in x.value], x.args)

        if x.type == DatumType.BYTES:
            raise DataException("Bytes is unsupported")

        if x.type == DatumType.CUSTOM:
            raise DataException("Custom is unsupported")

        return x

    @staticmethod
    def dump(x: Datum) -> str:
        x = JSON.ast_dump(x)

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
                {JSON.ast_load(k): JSON.ast_load(v) for k, v in x.value.items()},
                x.args,
            )

        if x.type == DatumType.ARRAY:
            return Datum(DatumType.ARRAY, [JSON.ast_load(v) for v in x.value], x.args)

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

        return JSON.ast_load(ast)
