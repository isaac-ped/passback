import json

_funclib = {}

def resolve(_data=None, **kwargs):
    def _wrap(fn):
        _funclib[fn.__name__] = {'kwargs': kwargs, 'fn': fn, 'data': _data}
        return fn
    return _wrap
