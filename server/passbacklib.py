import json
import re
import subprocess
import shlex
import inspect
from typing import Callable, Dict, Optional, Union, Type, List
from dataclasses import dataclass, asdict, is_dataclass, fields, _MISSING_TYPE

def max_used_posarg(values):
    max_arg_found = 0
    for v in values:
        for match in re.finditer(r'\$(\d+)', v):
            max_arg_found=max(max_arg_found, int(match.group(1)))
    return max_arg_found

def swap_quotes(s):
    return s.replace('"', '@@@').replace("'",'"').replace("@@@", "'")

def friendly_quote(s: str) -> str:
    """ Returns a shlex.quote'd string that allows variable references inside

    By default, shlex.quote() returns a string in single quotes.
    We want to be able to have variable references, so we must replace them with double quotes.
    But if the original string has quotes in it, that can cause problems.
    So (simple!?) swap once, quote, then swap back
    """

    swapped = swap_quotes(s)
    quoted = shlex.quote(swapped)
    return swap_quotes(quoted)

@dataclass
class ResolvableMeta:
    name: str
    pipe_input: Union[str, bool] = False
    min_nargs: Optional[int] = None
    max_nargs: Optional[int] = 0

_URLENCODER="_pblib_urlencode"

urlencoder_shell_func=f"""{_URLENCODER}() {{
  python3 -c 'import urllib.parse, sys; print(urllib.parse.quote(" ".join(sys.argv[1:])))' "$@"
}}"""


@dataclass
class Resolvable:
    fn: Callable
    kwargs: Dict[str,str]

    meta: ResolvableMeta

    def shell_func_content(self, request_port: int):
        validation = []
        if self.meta.min_nargs is not None and self.meta.min_nargs > 0:
            validation.append(f"[[ $# < {self.meta.min_nargs} ]] && echo 'Requires at least {self.meta.min_nargs} arguments' && return 1")
        if self.meta.max_nargs is not None:
            if self.meta.max_nargs > 0:
                validation.append(f"[[ $# > {self.meta.max_nargs} ]] && echo 'Requires at most {self.meta.max_nargs} arguments' && return 1")
            else:
                validation.append(f"[[ $# > 0 ]] && echo 'Requires no arguments' && return 1")


        var_setters=[]
        for k, v in self.kwargs.items():
            var_setters.append(f"{k}={friendly_quote(v)}")

        param_setters=[]
        for k in self.kwargs:
            param_setters.append(f"{k}=$({_URLENCODER} ${k})")

        if self.meta.max_nargs != 0:
            var_setters.append(f'posargs="$@"')
            param_setters.append(f"posargs=$({_URLENCODER} $posargs)")

        param_str='&'.join(param_setters)

        request_url = f"localhost:{request_port}/{self.meta.name}?{param_str}"

        request_command = f'curl {friendly_quote(request_url)}'
        if self.meta.pipe_input:
            request_command += ' --data-binary @-'

            if self.meta.pipe_input is not True:
                request_command = self.meta.pipe_input + " | " + request_command

        return '\n  '.join(validation + var_setters + [request_command])

    def shell_func(self, request_port: int):
        content = self.shell_func_content(request_port)
        return f"{self.meta.name}() {{\n  {content}\n}}"

    def call(self, *args, **kwargs):
        return self.fn(*args, **kwargs)

_resolvables = []

def pipe_into(proc, data: Union[str, bytes], **popen_kwargs):
    if isinstance(data, str):
        data = bytes(data, encoding='utf=8')
    if isinstance(proc, str):
        proc = [proc]
    with subprocess.Popen(proc, stdin=subprocess.PIPE) as p:
        stdout, stderr = p.communicate(data)
    rtn = ""
    if stdout is not None:
        rtn += stdout
    if stderr is not None:
        rtn += stderr
    return rtn


def resolve(name=None, /, pipe_input=False, min_nargs=None, max_nargs=None, **kwargs):



    def _wrap(fn):

        argspec = inspect.getargspec(fn)
        nargs = len(argspec.args)

        if argspec.varargs is None and max_nargs is None:
            max_nargs = nargs

        if argspec.defaults and min_nargs is None:
            min_nargs = nargs - len(argspec.defaults)
        elif min_nargs is None:
            min_nargs = nargs
        if name is None:
            name = fn.__name__

        meta = ResolvableMeta(
            name=name, 
            pipe_input=pipe_input,
            min_nargs=min_nargs,
            max_nargs=max_nargs,
        )
        _resolvables.append(
            Resolvable(
                fn, kwargs, meta
            )
        )

        return fn

    return _wrap

def autoresolve(name: str, pipe_input=False, min_nargs=None, max_nargs=None):

    def auto_resolved_pipe(stdin: str, *args):
        assert not (min_nargs is not None and len(args) < min_nargs)
        assert not (max_nargs is not None and len(args) > max_nargs)

        return pipe_into([name] + args, stdin)

    def auto_resolved_nopipe(*args):
        assert not (min_nargs is not None and len(args) < min_nargs)
        assert not (max_nargs is not None and len(args) > max_nargs)

        return subprocess.check_output([name] + args)

    auto_resolved = auto_resolved_pipe if pipe_input else auto_resolved_nopipe

    auto_resolved.__name__ = f"{name}_resolve"

    meta = ResolvableMeta(
        name=name,
        pipe_input=pipe_input,
        min_nargs=min_nargs,
        max_nargs=max_nargs,
    )


    _resolvables.append(
        Resolvable(
            auto_resolved, {}, meta
        )
    )

_resolvers = []

@dataclass
class Resolver:

    _stdin: Optional[str] = None
    _args: Optional[List[str]] = None

    def pass_to(self, prog, *args):
        cmd = [prog]
        if self._args and not args:
            args = self._args
        cmd.extend(args)
        print(cmd)
        if self._stdin is not None:
            return pipe_into(cmd, self._stdin)
        else:
            return subprocess.check_output(cmd)

    @property
    def _n_call_args(self):
        argspec = inspect.getargspec(self._call)
        return len(argspec.args) - 1

    @classmethod
    def _call_wrapper_nopipe(cls, *args, **kwargs):
        obj = cls(**kwargs, _args=args)
        return obj._call(*args[:obj._n_call_args])

    @classmethod
    def _call_wrapper_pipe(cls, stdin, *args, **kwargs):
        kwargs['_stdin'] = stdin
        return cls._call_wrapper_nopipe(*args, **kwargs)


    @classmethod
    def __init_subclass__(cls, name: Optional[str] = None, pipe_input=None, min_nargs=None, max_nargs=None, **kwargs):
        super().__init_subclass__(**kwargs)
        if not hasattr(cls, '_call'):
            raise Exception(f"{cls} is not a valid Resolver subclass")

        argspec = inspect.getargspec(cls._call)

        nargs = len(argspec.args) - 1

        if argspec.varargs is None and max_nargs is None:
            max_nargs = nargs

        if argspec.defaults and min_nargs is None:
            min_nargs = nargs - len(argspec.defaults)
        elif min_nargs is None:
            min_nargs = nargs

        if name is None:
            name = cls.__name__

        cls = dataclass(cls)

        kwargs = {
            field.name: field.default
            for field in fields(cls)
            if field.default is not None and field.default is not _MISSING_TYPE
        }

        kwarg_values = list(kwargs.values())
        if isinstance(pipe_input, str):
            kwarg_values.append(pipe_input)

        max_arg_found = max_used_posarg(kwarg_values)
        if max_arg_found > min_nargs:
            min_nargs = max_arg_found
        if max_nargs is not None and max_arg_found > max_nargs:
            max_nargs = max_arg_found

        meta = ResolvableMeta(
            name=name,
            pipe_input=pipe_input,
            min_nargs=min_nargs,
            max_nargs=max_nargs,
        )

        resolved = cls._call_wrapper_pipe if pipe_input else cls._call_wrapper_nopipe

        _resolvables.append(
            Resolvable(
                resolved, kwargs, meta
            )
        )
