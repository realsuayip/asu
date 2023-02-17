import json
import os

_empty = object()


class EnvironmentParser:
    def parse(self, name, default=_empty, parser=None):
        try:
            value = os.environ[name]
        except KeyError:
            if default is _empty:
                raise
            return default

        if parser is not None:
            return parser(value)

        return value

    def list(self, name, default=_empty, *, delimiter=","):
        return self.parse(name, default, lambda v: v.split(delimiter))

    def bool(self, name, default=_empty):
        value = self.parse(name, default=default)

        if isinstance(value, bool):
            return value

        truthy, falsy = ("true", "1"), ("false", "0")
        assert value in truthy + falsy
        return value in truthy

    @staticmethod
    def _construct(parser):
        def process(self, name, default=_empty):
            return self.parse(name, default, parser)

        return process

    str = _construct(str)
    int = _construct(int)
    float = _construct(float)
    json = _construct(json.loads)


env = EnvironmentParser()
