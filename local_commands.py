import os
import subprocess
from iterm2_local_commands import new_window, new_split
from monitorlib import resolve

@resolve(contents='$(cat)')
def lpbcopy(contents):
    with open('test.txt2', 'w') as f:
        f.write(contents)
    # TODO: This should use subprocess instead
    os.system(f"echo '{contents}' | pbcopy")


@resolve(directory='$(pwd)', shell="${SHELL}", host="${SSHNAME:-$HOSTNAME}")
def nwhere(directory, shell, host):
    new_window(f"ssh '{host}' 'cd {directory} && {shell}'")

@resolve(directory='$(pwd)', shell="${SHELL}", host="${SSHNAME:-$HOSTNAME}")
def nvshere(directory, shell, host):
    new_split(f"ssh '{host}' 'cd {directory} && {shell}'")
