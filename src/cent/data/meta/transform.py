import typing as T

from cent.data.meta.ir import ASTNode


class Transform:
    @staticmethod
    def load(x: T.Any) -> ASTNode:
        raise NotImplementedError

    @staticmethod
    def dump(x: T.Union[ASTNode, T.Any]) -> T.Any:
        raise NotImplementedError
