import json
import re
import subprocess
import shlex
import inspect
from typing import Callable, Dict, Optional, Union, Type, List
from dataclasses import dataclass, asdict, is_dataclass, fields, field


def max_used_posarg(values):
    max_arg_found = 0
    for v in values:
        for match in re.finditer(r"\$(\d+)", v):
            max_arg_found = max(max_arg_found, int(match.group(1)))
    return max_arg_found


def swap_quotes(s):
    return s.replace('"', "@@@").replace("'", '"').replace("@@@", "'")


def friendly_quote(s: str) -> str:
    """Returns a shlex.quote'd string that allows variable references inside

    By default, shlex.quote() returns a string in single quotes.
    We want to be able to have variable references, so we must replace them with double quotes.
    But if the original string has quotes in it, that can cause problems.
    So (simple!?) swap once, quote, then swap back
    """

    swapped = swap_quotes(s)
    quoted = shlex.quote(swapped)
    return swap_quotes(quoted)


_URLENCODER = "_pblib_urlencode"

urlencoder_shell_func = f"""{_URLENCODER}() {{
  python3 -c 'import urllib.parse, sys, shlex; print(urllib.parse.quote(shlex.join(sys.argv[1:])))' $@
}}"""


@dataclass
class Resolvable:
    fn: Callable
    help_fn: Callable
    name: str
    kwargs: Dict[str, str]

    min_posargs: int = 0
    pipe_input: Union[str, bool] = False
    file_input: Optional[str] = None

    def shell_func_content(self, request_port: int):
        """ Produces the body of the shell function corresponding to a remote call """
        help_condition = [
            f'if [[ "$#" < {self.min_posargs} || "$1" == "-h" || "$1" == "--help" ]]; then ',
            f"curl localhost:{request_port}/{self.name}/help",
            "return 1",
            "fi",
        ]

        var_setters = ['posargs="$@"']
        for k, v in self.kwargs.items():
            var_setters.append(f"{k}={friendly_quote(v)}")

        param_setters = [f"posargs=$({_URLENCODER} $posargs)"]
        for k in self.kwargs:
            param_setters.append(f"{k}=$({_URLENCODER} ${k})")

        param_str = "&".join(param_setters)

        request_url = f"localhost:{request_port}/{self.name}?{param_str}"

        request_command = f"curl {friendly_quote(request_url)}"
        if self.file_input:
            request_command += f" --data-binary @{self.file_input}"
        if self.pipe_input is True:
            request_command += " --data-binary @-"
        elif self.pipe_input:
            request_command = f"{self.pipe_input} | {request_command} --data-binary @-"

        return "\n  ".join(help_condition + var_setters + [request_command])

    def shell_func(self, request_port: int):
        content = self.shell_func_content(request_port)
        return f"{self.name}() {{\n  {content}\n}}"

    def call(self, *args, **kwargs):
        return self.fn(*args, **kwargs)


_resolvables = []


def pipe_into(proc, data: Union[str, bytes]):
    """ A wrapper to popen which pipes the provided data into the provided command """
    if isinstance(data, str):
        data = bytes(data, encoding="utf=8")
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
    """ TODO: Remove me, I think """

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
        raise NotImplementedError
        _resolvables.append(Resolvable(fn, kwargs, meta))

        return fn

    return _wrap


def autoresolve(
    name: str, pipe_input: bool = False, min_posargs=0, help_text: Optional[str] = None
):
    """Creates a shell function 'name' on the remote host that maps to 'name' on localhost

    (passes all arguments along)
    """

    if pipe_input:

        def auto_resolved(stdin: str, *args):
            assert not (min_posargs is not None and len(args) < min_posargs)
            return pipe_into([name] + list(args), stdin)

    else:

        def auto_resolved(*args):
            assert not (min_posargs is not None and len(args) < min_posargs)
            return subprocess.check_output([name] + list(args))

    auto_resolved.__name__ = f"{name}_resolve"

    if help_text:

        def help_fn():
            return help_text

    else:

        def help_fn():
            func_help = subprocess.check_output([name, "--help"])
            return f"Remotely calls {name}:\n{func_help}"

    _resolvables.append(
        Resolvable(auto_resolved, help_fn, name, {}, min_posargs, pipe_input)
    )


@dataclass
class Resolver:
    """ Define a _call() method in a subclass to specify behavior"""

    _stdin: Optional[str] = None
    _args: List[str] = field(default_factory=list)

    def pass_to(self, prog, *args):
        cmd = [prog]
        cmd.extend(args)
        if self._stdin is not None:
            return pipe_into(cmd, self._stdin)
        else:
            return subprocess.check_output(cmd)

    def pass_args_to(self, prog):
        return self.pass_to(prog, *self._args)

    @property
    def _n_call_args(self):
        argspec = inspect.getargspec(self._call)
        return len(argspec.args) - 1

    @classmethod
    def _call_wrapper_nopipe(cls, *args, **kwargs):
        obj = cls(**kwargs, _args=args)
        if len(args) < obj._n_call_args:
            return obj._help()
        return obj._call(*args[: obj._n_call_args])

    @classmethod
    def _call_wrapper_pipe(cls, stdin, *args, **kwargs):
        kwargs["_stdin"] = stdin
        return cls._call_wrapper_nopipe(*args, **kwargs)

    @classmethod
    def __init_subclass__(
        cls,
        name: Optional[str] = None,
        pipe_input=None,
        file_input=None,
        min_posargs=0,
        **kwargs,
    ):
        super().__init_subclass__(**kwargs)
        if not hasattr(cls, "_call"):
            # TODO: Print error, not raise exception. Could be okay if multiple layers of inheritance
            # TODO: _help() should be classmethod
            raise Exception(f"{cls} must define '_call()'")

        if not hasattr(cls, "_help"):
            help_str = cls.__doc__ + "\n"
        else:
            # TODO: _help() should be classmethod or staticmethod
            # TODO: Use parameters from _call method instead?
            help_str = cls._help() + "\n"

        if name is None:
            name = cls.__name__

        cls = dataclass(cls)

        kwargs = {
            field.name: field.default
            for field in fields(cls)
            if isinstance(field.default, str)
        }

        resolved = (
            cls._call_wrapper_pipe
            if (pipe_input or file_input)
            else cls._call_wrapper_nopipe
        )

        _resolvables.append(
            Resolvable(
                resolved,
                lambda: help_str,
                name,
                kwargs,
                min_posargs,
                pipe_input,
                file_input,
            )
        )
