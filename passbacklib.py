import json

_funclib = {}

def resolve(**kwargs):
    def _wrap(fn):
        _funclib[fn.__name__] = {'kwargs': kwargs, 'fn': fn}
        return fn
    return _wrap
