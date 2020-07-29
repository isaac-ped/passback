from passbacklib import _funclib
from local_commands import *
from flask import request
import shlex

def make_endpoints(app, funclib = _funclib):
    for funcname, props in funclib.items():
        def endpoint(name = funcname, props=props):
            kwargs = request.args
            if props['data']:
                props['fn'](request.get_data(), **kwargs)
            else:
                props['fn'](**kwargs)
            return ''

        if props.get('data'):
            methods = ['POST']
        else:
            methods = ['GET']

        app.add_url_rule(f'/{funcname}', funcname, endpoint, methods=methods)

    app.add_url_rule(f'/', 'aliases', aliases)


def calls(funclib= _funclib):
    calls={}
    for funcname, props in funclib.items():
        params=[]
        for k, v in props['kwargs'].items():
            params.append(shlex.quote(f'{k}="')+v+shlex.quote('"'))
        param_string = shlex.quote('&').join(params)
        prefix = shlex.quote(f'localhost:1138/{funcname}?')
        cmd = f'curl {prefix}{param_string}'
        if props['data']:
            cmd += ' --data-binary @-'
        calls[funcname] = cmd

    return calls

def aliases(funclib = _funclib):
    funcs = []
    for k, v in calls(funclib).items():
        funcs.append(f'{k}() {{ {v}; }}')
    return '; '.join(funcs)

if __name__ == '__main__':
    print(aliases())
