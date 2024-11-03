import typing as T

from cent.data.datum import Datum


class Transform:
    @staticmethod
    def load(x: T.Any) -> Datum:
        raise NotImplementedError

    @staticmethod
    def dump(x: T.Union[Datum, T.Any]) -> T.Any:
        raise NotImplementedError
