import os
import subprocess
import shlex
import asyncio
#from iterm2_local_commands import new_window, new_split
from passbacklib import resolve

@resolve(_data='$(cat)')
def lpbcopy(data,/,):
    p = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE)
    p.communicate(input=data)


@resolve(directory='$(pwd)', shell="${SHELL}", host="${SSHNAME:-${HOSTNAME:-${HOST}}}")
def nwhere(*, directory, shell, host):
    new_window(f"ssh '{host}' 'cd {directory} && {shell}'")

@resolve(directory='$(pwd)', shell="${SHELL}", host="${SSHNAME:-${HOSTNAME:-${HOST}}}")
def nvshere(*,directory, shell, host):
    new_split(f"ssh '{host}' 'cd {directory} && {shell}'")
