from passbacklib import urlencoder_shell_func, _resolvables
from local_commands import *
from flask import request, make_response
import shlex
import traceback
from dataclasses import fields, dataclass


def add_resolvable_endpoint(app, resolvable):
    def endpoint():
        provided_args = request.args

        args = []
        if resolvable.pipe_input or resolvable.file_input:
            args = [request.get_data()]

        kwargs = dict(request.args)
        if "posargs" in kwargs:
            args += shlex.split(kwargs["posargs"])
            del kwargs["posargs"]

        try:
            rtn = resolvable.call(*args, **kwargs)
        except Exception as e:
            rtn = f"Error calling {resolvable.name} ({resolvable.fn.__name__})"
            rtn += f"\n{traceback.format_exc()}"
        return make_response(rtn)

    def help_endpoint():
        return make_response(resolvable.help_fn())

    name = resolvable.name
    if resolvable.pipe_input or resolvable.file_input:
        methods = ["POST"]
    else:
        methods = ["GET"]

    app.add_url_rule(f"/{name}", name, view_func=endpoint, methods=methods)
    app.add_url_rule(f"/{name}/help", f"{name}-help", view_func=help_endpoint)


def generate_shell_functions(port, resolvables=_resolvables):
    shell_functions = [urlencoder_shell_func]
    for resolvable in resolvables:
        shell_functions.append(resolvable.shell_func(port))
    return shell_functions


DEFAULT_PORT = 1138


def shell_functions_endpoint(resolvables=_resolvables):
    port = request.args.get("port", DEFAULT_PORT)
    return "\n".join(generate_shell_functions(port, resolvables)) + "\n"


def create_endpoints(app, resolvables=_resolvables):

    for resolvable in resolvables:
        add_resolvable_endpoint(app, resolvable)
    app.add_url_rule(f"/", "functions", view_func=shell_functions_endpoint)
